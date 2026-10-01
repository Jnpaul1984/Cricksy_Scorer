"""Block 4C sponsor proposal, independent Cricksy approval, and immediate takedown."""
from __future__ import annotations

import datetime as dt
import base64
import hashlib
import hmac
import uuid
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.security import get_current_active_user
from backend.config.settings import settings
from backend.services.organization_publication_service import _current_membership
from backend.services.organization_service import OrganizationServiceError
from backend.sql_app.database import get_db
from backend.sql_app import models

router = APIRouter(tags=["organization-sponsors"])
SURFACE = "public_organization_homepage"
_REPORT_WINDOW_SECONDS = 60
_REPORT_MAX_PER_WINDOW = 60
_REPORT_CAPABILITY_SECONDS = 300

def _allowed_categories() -> set[str]:
    return {item.strip().lower() for item in settings.SPONSOR_ALLOWED_CATEGORIES.split(",") if item.strip()}

def _policy_enabled(category: str | None = None) -> None:
    if not settings.SPONSOR_PLACEMENTS_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sponsor placements are not enabled by policy")
    if category is not None and category.strip().lower() not in _allowed_categories():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sponsor category is not enabled by policy")

class ProposalIn(BaseModel):
    sponsor_name: str
    category: str
    sponsor_url: HttpUrl | None = None


class VisibilityIn(BaseModel):
    enabled: bool


class SponsorReportEventIn(BaseModel):
    capability: str = Field(min_length=32, max_length=1024)
    event_id: str = Field(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")

def _platform_admin(user: models.User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Platform administrator authority required")


def _reporting_enabled() -> None:
    if not settings.SPONSOR_AGGREGATE_REPORTING_ENABLED:
        raise HTTPException(status_code=503, detail="Sponsor aggregate reporting is not enabled by policy")


async def _issue_reporting_capability(db: AsyncSession, placement_id: str, event_type: Literal["display", "click"]) -> str:
    now = dt.datetime.now(dt.UTC)
    await db.execute(delete(models.SponsorPlacementReportingCapability).where(models.SponsorPlacementReportingCapability.expires_at < now))
    nonce = str(uuid.uuid4())
    db.add(models.SponsorPlacementReportingCapability(nonce=nonce, placement_id=placement_id, event_type=event_type, expires_at=now + dt.timedelta(seconds=_REPORT_CAPABILITY_SECONDS)))
    return nonce


def _public_report_view_key(placement: models.OrganizationSponsorPlacement) -> str:
    """Stable opaque per-placement revision key; never a viewer identifier."""
    revision = placement.approved_at.isoformat() if placement.approved_at else "unapproved"
    digest = hmac.new(settings.app_secret_key.encode(), f"{placement.id}:{revision}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:18]).rstrip(b"=").decode()


async def _consume_rate_bucket(db: AsyncSession, placement_id: str, now: dt.datetime) -> bool:
    table = models.SponsorPlacementReportRateBucket.__table__
    bucket = now.replace(second=0, microsecond=0)
    insert = pg_insert if db.bind and db.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(table).values(placement_id=placement_id, bucket_start=bucket, event_count=1).on_conflict_do_update(index_elements=["placement_id", "bucket_start"], set_={"event_count": table.c.event_count + 1}, where=table.c.event_count < _REPORT_MAX_PER_WINDOW).returning(table.c.event_count)
    return (await db.execute(statement)).first() is not None

async def _audit(db: AsyncSession, placement: models.OrganizationSponsorPlacement, action: str, actor: str) -> None:
    db.add(models.OrganizationSponsorPlacementAudit(placement_id=placement.id, organization_id=placement.organization_id, action=action, actor_user_id=actor))


async def _visibility_audit(db: AsyncSession, scope: str, actor: str, enabled: bool, organization_id: str | None = None, placement_id: str | None = None) -> None:
    db.add(models.SponsorVisibilityAudit(scope=scope, actor_user_id=actor, visibility_enabled=enabled, organization_id=organization_id, placement_id=placement_id))


async def _global_visibility(db: AsyncSession) -> bool:
    setting = await db.get(models.SponsorVisibilityGlobalSetting, "global")
    return bool(setting and setting.visibility_enabled)


async def _organization_visibility(db: AsyncSession, organization_id: str) -> bool:
    setting = await db.get(models.OrganizationSponsorVisibilitySetting, organization_id)
    return bool(setting and setting.visibility_enabled)


def _page_metadata(page: int, page_size: int, total: int) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "total": total, "pages": max(1, (total + page_size - 1) // page_size)}


async def _visibility_snapshot(db: AsyncSession, organization_page: int = 1, placement_page: int = 1, page_size: int = 50, states: tuple[str, ...] = ("proposed", "approved")) -> dict[str, object]:
    placement_filter = models.OrganizationSponsorPlacement.state.in_(states)
    organization_ids = select(models.OrganizationSponsorPlacement.organization_id).where(placement_filter).distinct()
    organization_total = await db.scalar(select(func.count()).select_from(models.Organization).where(models.Organization.id.in_(organization_ids))) or 0
    organization_rows = (await db.execute(
        select(models.Organization, models.OrganizationSponsorVisibilitySetting)
        .outerjoin(models.OrganizationSponsorVisibilitySetting, models.OrganizationSponsorVisibilitySetting.organization_id == models.Organization.id)
        .where(models.Organization.id.in_(organization_ids))
        .order_by(models.Organization.name)
        .offset((organization_page - 1) * page_size).limit(page_size)
    )).all()
    placement_total = await db.scalar(select(func.count()).select_from(models.OrganizationSponsorPlacement).where(placement_filter)) or 0
    placements = (await db.scalars(
        select(models.OrganizationSponsorPlacement).where(placement_filter).order_by(models.OrganizationSponsorPlacement.created_at.desc()).offset((placement_page - 1) * page_size).limit(page_size)
    )).all()
    return {
        "global_enabled": await _global_visibility(db),
        "organizations": [
            {"id": organization.id, "label": organization.name, "type": organization.organization_type, "enabled": bool(setting and setting.visibility_enabled)}
            for organization, setting in organization_rows
        ],
        "placements": [
            {"id": placement.id, "sponsor_name": placement.sponsor_name, "category": placement.category, "orgid": placement.organization_id, "state": placement.state, "enabled": placement.visibility_enabled}
            for placement in placements
        ],
        "page": {"organizations": _page_metadata(organization_page, page_size, organization_total), "placements": _page_metadata(placement_page, page_size, placement_total)},
        "states": list(states),
    }


def _requested_states(states: str) -> tuple[str, ...]:
    return tuple(item for item in states.split(",") if item in {"proposed", "approved", "taken_down"}) or ("proposed", "approved")

@router.get("/api/platform/sponsor-placements")
async def review_queue(user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), states: str = Query("proposed,approved")):
    _platform_admin(user)
    requested_states = _requested_states(states)
    total = await db.scalar(select(func.count()).select_from(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.state.in_(requested_states))) or 0
    rows = (await db.execute(
        select(models.OrganizationSponsorPlacement, models.Organization.name)
        .join(models.Organization, models.Organization.id == models.OrganizationSponsorPlacement.organization_id)
        .where(models.OrganizationSponsorPlacement.state.in_(requested_states))
        .order_by(models.OrganizationSponsorPlacement.created_at)
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    return {"items": [
        {"id": placement.id, "organization_id": placement.organization_id, "organization_label": organization_name,
         "sponsor_name": placement.sponsor_name, "category": placement.category, "state": placement.state}
        for placement, organization_name in rows
    ], "page": _page_metadata(page, page_size, total), "states": list(requested_states)}


@router.get("/api/platform/sponsor-visibility")
async def sponsor_visibility(user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], organization_page: int = Query(1, ge=1), placement_page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), states: str = Query("proposed,approved")):
    _platform_admin(user)
    requested_states = _requested_states(states)
    return await _visibility_snapshot(db, organization_page, placement_page, page_size, requested_states)


@router.patch("/api/platform/sponsor-visibility/global")
async def set_global_sponsor_visibility(payload: VisibilityIn, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], organization_page: int = Query(1, ge=1), placement_page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), states: str = Query("proposed,approved")):
    _platform_admin(user)
    setting = await db.get(models.SponsorVisibilityGlobalSetting, "global")
    if setting is None:
        setting = models.SponsorVisibilityGlobalSetting(key="global")
        db.add(setting)
    setting.visibility_enabled = payload.enabled
    await _visibility_audit(db, "global", user.id, payload.enabled)
    await db.commit()
    return await _visibility_snapshot(db, organization_page, placement_page, page_size, _requested_states(states))


@router.patch("/api/platform/sponsor-visibility/organizations/{organization_id}")
async def set_organization_sponsor_visibility(organization_id: str, payload: VisibilityIn, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], organization_page: int = Query(1, ge=1), placement_page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), states: str = Query("proposed,approved")):
    _platform_admin(user)
    if await db.get(models.Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    setting = await db.get(models.OrganizationSponsorVisibilitySetting, organization_id)
    if setting is None:
        setting = models.OrganizationSponsorVisibilitySetting(organization_id=organization_id)
        db.add(setting)
    setting.visibility_enabled = payload.enabled
    await _visibility_audit(db, "organization", user.id, payload.enabled, organization_id=organization_id)
    await db.commit()
    return await _visibility_snapshot(db, organization_page, placement_page, page_size, _requested_states(states))


@router.patch("/api/platform/sponsor-visibility/placements/{placement_id}")
async def set_placement_sponsor_visibility(placement_id: str, payload: VisibilityIn, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], organization_page: int = Query(1, ge=1), placement_page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), states: str = Query("proposed,approved")):
    _platform_admin(user)
    placement = await db.scalar(select(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.id == placement_id).with_for_update())
    if placement is None:
        raise HTTPException(status_code=404, detail="Sponsor placement not found")
    placement.visibility_enabled = payload.enabled
    await _visibility_audit(db, "placement", user.id, payload.enabled, organization_id=placement.organization_id, placement_id=placement.id)
    await db.commit()
    return await _visibility_snapshot(db, organization_page, placement_page, page_size, _requested_states(states))

@router.post("/api/organizations/{organization_id}/sponsor-placements", status_code=201)
async def propose(organization_id: str, payload: ProposalIn, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    _policy_enabled(payload.category)
    try:
        await _current_membership(db, organization_id=organization_id, actor_user_id=user.id, manage=True)
    except OrganizationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    placement = models.OrganizationSponsorPlacement(organization_id=organization_id, sponsor_name=payload.sponsor_name.strip(), category=payload.category.strip().lower(), sponsor_url=str(payload.sponsor_url) if payload.sponsor_url else None, proposed_by_user_id=user.id)
    if not placement.sponsor_name:
        raise HTTPException(status_code=422, detail="Sponsor name is required")
    db.add(placement); await db.flush(); await _audit(db, placement, "proposed", user.id); await db.commit(); await db.refresh(placement)
    return {"id": placement.id, "state": placement.state, "placement_surface": SURFACE}

@router.post("/api/platform/sponsor-placements/{placement_id}/approve")
async def approve(placement_id: str, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    _platform_admin(user)
    placement = await db.scalar(select(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.id == placement_id).with_for_update())
    if placement is None: raise HTTPException(status_code=404, detail="Sponsor placement not found")
    _policy_enabled(placement.category)
    if placement.state != "proposed": raise HTTPException(status_code=409, detail="Only a current proposal may be approved")
    # A platform account cannot turn its own organization's proposal into an approval.
    if placement.proposed_by_user_id == user.id: raise HTTPException(status_code=403, detail="Proposer cannot approve a sponsor placement")
    # Lock and retire every previously-active placement so later takedown can never
    # resurrect an earlier sponsor. The DB partial unique index is the race backstop.
    prior = (await db.scalars(select(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.organization_id == placement.organization_id, models.OrganizationSponsorPlacement.state == "approved").with_for_update())).all()
    now = await db.scalar(select(func.now()))
    for active in prior:
        active.state = "taken_down"; active.taken_down_by_user_id = user.id; active.taken_down_at = now
        await _audit(db, active, "superseded", user.id)
    await db.flush()
    placement.state = "approved"; placement.approved_by_user_id = user.id
    placement.approved_at = now; await _audit(db, placement, "approved", user.id); await db.commit()
    return {"id": placement.id, "state": placement.state}

@router.post("/api/platform/sponsor-placements/{placement_id}/takedown")
async def takedown(placement_id: str, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    _platform_admin(user)
    placement = await db.scalar(select(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.id == placement_id).with_for_update())
    if placement is None: raise HTTPException(status_code=404, detail="Sponsor placement not found")
    if placement.state != "approved": raise HTTPException(status_code=409, detail="Only an approved placement may be taken down")
    placement.state = "taken_down"; placement.taken_down_by_user_id = user.id
    placement.taken_down_at = await db.scalar(select(func.now())); await _audit(db, placement, "taken_down", user.id); await db.commit()
    return {"id": placement.id, "state": placement.state}


@router.post("/api/public/sponsor-placement-events", status_code=202)
async def record_public_placement_event(payload: SponsorReportEventIn, db: Annotated[AsyncSession, Depends(get_db)]):
    """Accept a bounded anonymous display/click event only for a live public placement.

    No cookies, IP addresses, user agents, user IDs, or player data are accepted or stored.
    ``event_id`` is an opaque one-event nonce retained for two days solely to reject replays.
    """
    _reporting_enabled()
    # Idempotent retries never consume a fresh one-time nonce or rate quota.
    # The UUID has no viewer semantics; it is an anonymous event nonce only.
    if await db.get(models.SponsorPlacementReportDedup, payload.event_id) is not None:
        return {"accepted": True, "duplicate": True}
    now = dt.datetime.now(dt.UTC)
    try:
        consumed = await db.execute(update(models.SponsorPlacementReportingCapability).where(
            models.SponsorPlacementReportingCapability.nonce == payload.capability,
            models.SponsorPlacementReportingCapability.expires_at >= now,
            models.SponsorPlacementReportingCapability.consumed_at.is_(None),
        ).values(consumed_at=now).returning(models.SponsorPlacementReportingCapability.placement_id, models.SponsorPlacementReportingCapability.event_type))
        capability = consumed.first()
    except Exception:
        capability = None
    if capability is None:
        raise HTTPException(status_code=404, detail="No eligible sponsor placement")
    placement_id, event_type = capability
    placement = await db.scalar(select(models.OrganizationSponsorPlacement).where(
        models.OrganizationSponsorPlacement.id == placement_id,
        models.OrganizationSponsorPlacement.state == "approved",
        models.OrganizationSponsorPlacement.visibility_enabled.is_(True),
    ))
    if placement is None or not settings.SPONSOR_PLACEMENTS_ENABLED or placement.category.strip().lower() not in _allowed_categories() or not await _global_visibility(db) or not await _organization_visibility(db, placement.organization_id):
        raise HTTPException(status_code=404, detail="No eligible sponsor placement")
    public_settings = await db.get(models.OrganizationPublicSettings, placement.organization_id)
    if public_settings is None or public_settings.publication_state != "published":
        raise HTTPException(status_code=404, detail="No eligible sponsor placement")
    today = dt.datetime.now(dt.UTC).date()
    # The nonce has no subject semantics and is deliberately pruned on every write.
    await db.execute(delete(models.SponsorPlacementReportDedup).where(models.SponsorPlacementReportDedup.received_at < now - dt.timedelta(hours=48)))
    await db.execute(delete(models.SponsorPlacementReportRateBucket).where(models.SponsorPlacementReportRateBucket.bucket_start < now - dt.timedelta(hours=48)))
    if not await _consume_rate_bucket(db, placement.id, now):
        # Retention cleanup is intentionally durable even when a new event is rejected.
        await db.commit()
        raise HTTPException(status_code=429, detail="Sponsor event rate limit exceeded")
    db.add(models.SponsorPlacementReportDedup(event_id=payload.event_id, placement_id=placement.id, received_date=today))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"accepted": True, "duplicate": True}
    table = models.SponsorPlacementDailyMetric.__table__
    insert = pg_insert if db.bind and db.bind.dialect.name == "postgresql" else sqlite_insert
    increment = {"display_count": table.c.display_count + (1 if event_type == "display" else 0), "click_count": table.c.click_count + (1 if event_type == "click" else 0)}
    await db.execute(insert(table).values(placement_id=placement.id, metric_date=today, display_count=1 if event_type == "display" else 0, click_count=1 if event_type == "click" else 0).on_conflict_do_update(index_elements=["placement_id", "metric_date"], set_=increment))
    await db.commit()
    return {"accepted": True, "duplicate": False}


async def _aggregate_report(db: AsyncSession, organization_id: str | None, start: dt.date, end: dt.date) -> dict[str, object]:
    query = select(
        models.SponsorPlacementDailyMetric.metric_date,
        func.coalesce(func.sum(models.SponsorPlacementDailyMetric.display_count), 0),
        func.coalesce(func.sum(models.SponsorPlacementDailyMetric.click_count), 0),
    ).join(models.OrganizationSponsorPlacement, models.OrganizationSponsorPlacement.id == models.SponsorPlacementDailyMetric.placement_id).where(
        models.SponsorPlacementDailyMetric.metric_date >= start,
        models.SponsorPlacementDailyMetric.metric_date <= end,
    )
    if organization_id is not None:
        query = query.where(models.OrganizationSponsorPlacement.organization_id == organization_id)
    rows = (await db.execute(query.group_by(models.SponsorPlacementDailyMetric.metric_date).order_by(models.SponsorPlacementDailyMetric.metric_date))).all()
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "buckets": [
        {"date": day.isoformat(), "displays": int(displays), "clicks": int(clicks)} for day, displays, clicks in rows
    ]}


def _report_range(start: dt.date | None, end: dt.date | None) -> tuple[dt.date, dt.date]:
    last = end or dt.datetime.now(dt.UTC).date()
    first = start or last - dt.timedelta(days=30)
    if first > last or (last - first).days > 31:
        raise HTTPException(status_code=422, detail="Reporting window must be between zero and 31 days")
    return first, last


@router.get("/api/organizations/{organization_id}/sponsor-reporting")
async def organization_sponsor_reporting(organization_id: str, user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], start_date: dt.date | None = None, end_date: dt.date | None = None):
    _reporting_enabled()
    try:
        await _current_membership(db, organization_id=organization_id, actor_user_id=user.id, manage=True)
    except OrganizationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    start, end = _report_range(start_date, end_date)
    return await _aggregate_report(db, organization_id, start, end)


@router.get("/api/platform/sponsor-reporting")
async def platform_sponsor_reporting(user: Annotated[models.User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], start_date: dt.date | None = None, end_date: dt.date | None = None):
    _reporting_enabled(); _platform_admin(user)
    start, end = _report_range(start_date, end_date)
    return await _aggregate_report(db, None, start, end)

@router.get("/api/public/organizations/{public_identifier}/sponsor-placement")
async def public_placement(public_identifier: str, db: Annotated[AsyncSession, Depends(get_db)]):
    def absent() -> JSONResponse:
        return JSONResponse({"detail": "No sponsor placement"}, status_code=404, headers={"Cache-Control": "no-store, max-age=0"})
    public_settings = await db.scalar(select(models.OrganizationPublicSettings).where(models.OrganizationPublicSettings.public_identifier == public_identifier, models.OrganizationPublicSettings.publication_state == "published"))
    if public_settings is None: raise HTTPException(status_code=404, detail="Public page not found")
    if not await _global_visibility(db) or not await _organization_visibility(db, public_settings.organization_id):
        return absent()
    placement = await db.scalar(select(models.OrganizationSponsorPlacement).where(models.OrganizationSponsorPlacement.organization_id == public_settings.organization_id, models.OrganizationSponsorPlacement.state == "approved", models.OrganizationSponsorPlacement.visibility_enabled.is_(True), models.OrganizationSponsorPlacement.placement_surface == SURFACE).order_by(models.OrganizationSponsorPlacement.approved_at.desc()))
    if placement is None or not settings.SPONSOR_PLACEMENTS_ENABLED or placement.category.strip().lower() not in _allowed_categories():
        return absent()
    response = {"sponsor_name": placement.sponsor_name, "sponsor_url": placement.sponsor_url, "placement_surface": SURFACE}
    if settings.SPONSOR_AGGREGATE_REPORTING_ENABLED:
        response["reporting"] = {"report_view_key": _public_report_view_key(placement), "display_capability": await _issue_reporting_capability(db, placement.id, "display"), "click_capability": await _issue_reporting_capability(db, placement.id, "click")}
        await db.commit()
    return JSONResponse(response, headers={"Cache-Control": "no-store, max-age=0"})
