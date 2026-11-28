"""Default-off, tenant-scoped three-Game trial with immutable audited consumption."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.services.organization_service import (
    OrganizationServiceError,
    get_organization_for_member,
)
from backend.services.organization_team_performance_access import TeamPerformanceAccessError
from backend.services.school_team_readiness_service import SelectedReadinessSource
from backend.sql_app import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

READ_ROLES = frozenset({"owner", "admin", "coach"})
ACTIVATION_ROLES = frozenset({"owner", "admin"})
TRIAL_DAYS = 90
REPORT_DAYS = 14


class TrialTransitionError(ValueError):
    """Safe trial-only policy conflict; Free match completion must ignore it."""


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _utc(value: dt.datetime) -> dt.datetime:
    return value.replace(tzinfo=dt.UTC) if value.tzinfo is None else value.astimezone(dt.UTC)


def _reason(reason: str) -> str:
    value = reason.strip()
    if not 1 <= len(value) <= 2000:
        raise TrialTransitionError("An audit reason of 1 to 2000 characters is required")
    return value


def _digest(deliveries: object) -> str | None:
    if not isinstance(deliveries, list):
        return None
    from backend.services.school_team_readiness_service import MAX_DELIVERY_PAYLOAD_BYTES

    payload = json.dumps(deliveries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_DELIVERY_PAYLOAD_BYTES:
        return None
    return hashlib.sha256(payload).hexdigest()


def _source_dict(source: SelectedReadinessSource) -> dict[str, object]:
    return {
        "game_id": source.game_id,
        "played_date": source.played_date.isoformat(),
        "metadata_revision": source.metadata_revision,
        "ledger_digest": source.ledger_digest,
    }


async def _operator(db: AsyncSession, user_id: str) -> models.User:
    user = await db.scalar(
        select(models.User).where(models.User.id == user_id, models.User.is_active.is_(True))
    )
    if user is None or not user.is_superuser:
        raise TeamPerformanceAccessError(403, "Trial management is unavailable")
    return user


async def _staff(
    db: AsyncSession,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
    *,
    roles: frozenset[str],
) -> models.Team:
    active = await db.scalar(
        select(models.User.id).where(
            models.User.id == actor_user_id, models.User.is_active.is_(True)
        )
    )
    if active is None:
        raise TeamPerformanceAccessError(404, "Organization not found")
    try:
        organization, membership = await get_organization_for_member(
            db, organization_id=organization_id, user_id=actor_user_id
        )
    except OrganizationServiceError as exc:
        raise TeamPerformanceAccessError(404, "Organization not found") from exc
    if organization.organization_type not in {"school", "club"} or membership.role not in roles:
        raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == team_id, models.Team.organization_id == organization_id
        )
    )
    if team is None:
        raise TeamPerformanceAccessError(404, "Team not found")
    if team.status != "active":
        raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
    return team


async def _availability(
    db: AsyncSession, organization_id: str
) -> models.TeamPerformanceTrialAvailability:
    available = await db.scalar(
        select(models.TeamPerformanceTrialAvailability).where(
            models.TeamPerformanceTrialAvailability.organization_id == organization_id,
            models.TeamPerformanceTrialAvailability.status == "enabled",
        )
    )
    if available is None:
        raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
    return available


async def require_trial_scope(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
    mode: Literal["trial_activation", "trial_report", "trial_system"],
) -> models.Team:
    """Separate trial authority; existing pilot grant checks remain unchanged."""
    if mode == "trial_system":
        team = await db.scalar(
            select(models.Team).where(
                models.Team.id == team_id,
                models.Team.organization_id == organization_id,
                models.Team.status == "active",
            )
        )
        if team is None:
            raise TeamPerformanceAccessError(404, "Team not found")
        await _availability(db, organization_id)
        return team
    team = await _staff(
        db,
        organization_id,
        team_id,
        actor_user_id,
        roles=ACTIVATION_ROLES if mode == "trial_activation" else READ_ROLES,
    )
    await _availability(db, organization_id)
    if mode != "trial_activation":
        trial = await db.scalar(
            select(models.TeamPerformanceTrial).where(
                models.TeamPerformanceTrial.organization_id == organization_id,
                models.TeamPerformanceTrial.team_id == team_id,
            )
        )
        now = _now()
        if trial is None or trial.state in {"revoked", "review_required"}:
            raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
        if trial.state == "active" and now >= _utc(trial.expires_at):
            raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
        if trial.state == "exhausted" and (
            trial.report_access_until is None or now >= _utc(trial.report_access_until)
        ):
            raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
        if trial.state not in {"active", "exhausted"}:
            raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
    return team


async def set_trial_availability(
    db: AsyncSession,
    *,
    organization_id: str,
    operator_user_id: str,
    enabled: bool,
    reason: str,
) -> models.TeamPerformanceTrialAvailability:
    await _operator(db, operator_user_id)
    audit_reason = _reason(reason)
    organization = await db.scalar(
        select(models.Organization)
        .where(
            models.Organization.id == organization_id,
            models.Organization.organization_type.in_({"school", "club"}),
        )
        .with_for_update()
    )
    if organization is None:
        raise TrialTransitionError("School/Club organization not found")
    row = await db.scalar(
        select(models.TeamPerformanceTrialAvailability)
        .where(models.TeamPerformanceTrialAvailability.organization_id == organization_id)
        .with_for_update()
    )
    status = "enabled" if enabled else "revoked"
    if row is not None and row.status == status:
        return row
    now = _now()
    if row is None:
        row = models.TeamPerformanceTrialAvailability(
            organization_id=organization_id,
            status=status,
            changed_by_user_id=operator_user_id,
            changed_at=now,
        )
        db.add(row)
    else:
        row.status = status
        row.changed_by_user_id = operator_user_id
        row.changed_at = now
    db.add(
        models.TeamPerformanceTrialAvailabilityEvent(
            organization_id=organization_id,
            status=status,
            actor_user_id=operator_user_id,
            reason=audit_reason,
            recorded_at=now,
        )
    )
    await db.flush()
    return row


async def activate_trial(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
    venue_timezone: str,
    reason: str,
) -> models.TeamPerformanceTrial:
    await require_trial_scope(
        db,
        organization_id=organization_id,
        team_id=team_id,
        actor_user_id=actor_user_id,
        mode="trial_activation",
    )
    audit_reason = _reason(reason)
    try:
        zone = ZoneInfo(venue_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise TrialTransitionError("A valid IANA venue timezone is required") from exc
    now = _now()
    local_date = now.astimezone(zone).date()
    from backend.services.school_team_readiness_service import (
        TeamReadinessRequest,
        evaluate_team_match_readiness,
    )

    readiness = await evaluate_team_match_readiness(
        db,
        TeamReadinessRequest(
            actor_user_id,
            organization_id,
            team_id,
            local_date,
            access_mode="trial_activation",
        ),
    )
    if readiness.state != "ready" or len(readiness.selected_sources) != 5:
        raise TrialTransitionError("Five verified prior matches are required")
    # Lock the Team row to serialize first activation before the unique constraint.
    team = await db.scalar(
        select(models.Team)
        .where(models.Team.id == team_id, models.Team.organization_id == organization_id)
        .with_for_update()
    )
    if team is None or team.status != "active":
        raise TeamPerformanceAccessError(404, "Team not found")
    existing = await db.scalar(
        select(models.TeamPerformanceTrial.id).where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
    )
    if existing is not None:
        raise TrialTransitionError("This Team has already had a trial")
    trial = models.TeamPerformanceTrial(
        organization_id=organization_id,
        team_id=team_id,
        policy_version=1,
        state="active",
        activated_by_user_id=actor_user_id,
        activated_at=now,
        venue_timezone=zone.key,
        activation_local_date=local_date,
        expires_at=now + dt.timedelta(days=TRIAL_DAYS),
        prerequisite_sources=[
            _source_dict(source) for source in reversed(readiness.selected_sources)
        ],
    )
    db.add(trial)
    await db.flush()
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="activated",
            event_key="activation",
            actor_user_id=actor_user_id,
            reason=audit_reason,
            evidence={
                "timezone": zone.key,
                "local_date": local_date.isoformat(),
                "prerequisites": trial.prerequisite_sources,
            },
            recorded_at=now,
        )
    )
    await db.flush()
    return trial


async def _current_source(
    db: AsyncSession,
    trial: models.TeamPerformanceTrial,
    game_id: str,
) -> dict[str, object] | None:
    """Apply the exact conservative readiness evidence rule to one Game."""
    from backend.services.school_team_readiness_service import _source, _validate_game_ledger

    game = await db.scalar(
        select(models.Game)
        .where(models.Game.id == game_id)
        .execution_options(populate_existing=True)
    )
    if (
        game is None
        or game.status != models.GameStatus.completed
        or game.match_purpose != "official"
    ):
        return None
    if game.match_type != "limited" or game.days_limit is not None or game.match_rules is not None:
        return None
    if (
        game.original_overs_limit != 25
        or game.original_format_trust_state not in {"setup_capture", "staff_corrected"}
        or game.original_format_source not in {"school_match_setup", "staff_correction"}
        or game.played_date_trust_state != "confirmed"
        or game.played_date_source != "staff_confirmed"
        or game.actual_played_date is None
    ):
        return None
    if _digest(game.deliveries) is None:
        return None
    ids = {
        team_id
        for side in (game.team_a, game.team_b)
        for org_id, team_id in [_source(side)]
        if org_id == trial.organization_id and team_id is not None
    }
    known = set(
        (
            await db.scalars(
                select(models.Team.id).where(
                    models.Team.organization_id == trial.organization_id, models.Team.id.in_(ids)
                )
            )
        ).all()
    )
    error, digest = await _validate_game_ledger(
        game,
        game.deliveries,
        organization_id=trial.organization_id,
        team_id=trial.team_id,
        existing_team_ids=known,
    )
    if error is not None or digest is None:
        return None
    return {
        "game_id": game.id,
        "played_date": game.actual_played_date.isoformat(),
        "metadata_revision": game.team_performance_metadata_revision,
        "ledger_digest": digest,
    }


async def _valid_consumptions(
    db: AsyncSession,
    trial_id: str,
) -> list[models.TeamPerformanceTrialConsumption]:
    rows = (
        await db.scalars(
            select(models.TeamPerformanceTrialConsumption)
            .where(models.TeamPerformanceTrialConsumption.trial_id == trial_id)
            .order_by(
                models.TeamPerformanceTrialConsumption.recorded_at,
                models.TeamPerformanceTrialConsumption.id,
            )
        )
    ).all()
    reversed_games = set(
        (
            await db.scalars(
                select(models.TeamPerformanceTrialEvent.game_id).where(
                    models.TeamPerformanceTrialEvent.trial_id == trial_id,
                    models.TeamPerformanceTrialEvent.kind == "reversed",
                )
            )
        ).all()
    )
    return [row for row in rows if row.game_id not in reversed_games]


async def _current_evidence_matches(
    db: AsyncSession,
    trial: models.TeamPerformanceTrial,
    source: dict[str, object],
) -> bool:
    current = await _current_source(db, trial, str(source["game_id"]))
    return current == source


async def _sources_match(
    db: AsyncSession,
    trial: models.TeamPerformanceTrial,
    sources: list[dict[str, object]],
) -> bool:
    for source in sources:
        if not await _current_evidence_matches(db, trial, source):
            return False
    return True


async def trial_status(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> dict[str, object]:
    await _staff(db, organization_id, team_id, actor_user_id, roles=READ_ROLES)
    await _availability(db, organization_id)
    trial = await db.scalar(
        select(models.TeamPerformanceTrial).where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
    )
    if trial is None:
        return {
            "state": "not_started",
            "games_used": 0,
            "games_remaining": 3,
            "expires_at": None,
            "report_access_until": None,
        }
    valid = await _valid_consumptions(db, trial.id)
    state = (
        "expired"
        if trial.state in {"active", "review_required"} and _now() >= _utc(trial.expires_at)
        else trial.state
    )
    if state not in {"revoked", "expired", "review_required"}:
        sources = [
            *trial.prerequisite_sources,
            *(
                {
                    "game_id": item.game_id,
                    "played_date": item.played_date.isoformat(),
                    "metadata_revision": item.metadata_revision,
                    "ledger_digest": item.ledger_digest,
                }
                for item in valid
            ),
        ]
        if not await _sources_match(db, trial, sources):
            state = "review_required"
    return {
        "state": state,
        "games_used": len(valid),
        "games_remaining": 3 - len(valid),
        "expires_at": trial.expires_at,
        "report_access_until": trial.report_access_until,
    }


async def record_completion_events(
    db: AsyncSession,
    *,
    game_id: str,
) -> list[models.TeamPerformanceTrialCompletion]:
    """Call after Free commit; a failure must be caught by the scoring boundary."""
    game = await db.scalar(select(models.Game).where(models.Game.id == game_id))
    if game is None or game.status != models.GameStatus.completed:
        return []
    from backend.services.school_team_readiness_service import _source

    scopes = {_source(side) for side in (game.team_a, game.team_b)}
    now = _now()
    trials = (
        await db.scalars(
            select(models.TeamPerformanceTrial).where(
                models.TeamPerformanceTrial.organization_id.in_({org for org, _ in scopes if org}),
                models.TeamPerformanceTrial.team_id.in_({team for _, team in scopes if team}),
                models.TeamPerformanceTrial.state == "active",
                models.TeamPerformanceTrial.expires_at > now,
            )
        )
    ).all()
    result: list[models.TeamPerformanceTrialCompletion] = []
    for trial in trials:
        if (trial.organization_id, trial.team_id) not in scopes:
            continue
        available = await db.scalar(
            select(models.TeamPerformanceTrialAvailability.status).where(
                models.TeamPerformanceTrialAvailability.organization_id == trial.organization_id
            )
        )
        if available != "enabled":
            continue
        existing = await db.scalar(
            select(models.TeamPerformanceTrialCompletion).where(
                models.TeamPerformanceTrialCompletion.trial_id == trial.id,
                models.TeamPerformanceTrialCompletion.game_id == game_id,
            )
        )
        if existing is not None:
            result.append(existing)
            continue
        latest_extension = await db.scalar(
            select(models.TeamPerformanceTrialEvent)
            .where(
                models.TeamPerformanceTrialEvent.trial_id == trial.id,
                models.TeamPerformanceTrialEvent.kind == "extended",
            )
            .order_by(models.TeamPerformanceTrialEvent.recorded_at.desc())
            .limit(1)
        )
        if latest_extension is not None:
            extension_time = _utc(latest_extension.recorded_at)
            if (
                game.actual_played_date is None
                or game.actual_played_date
                <= extension_time.astimezone(ZoneInfo(trial.venue_timezone)).date()
            ):
                # No immutable Game completion timestamp survives a missed capture.
                # Keep earlier and same-local-day Games out of a later extension.
                continue
        event = models.TeamPerformanceTrialCompletion(
            trial_id=trial.id,
            game_id=game_id,
            completed_at=now,
            evidence={
                "played_date": game.actual_played_date.isoformat()
                if game.actual_played_date
                else None,
                "played_date_trust_state": game.played_date_trust_state,
                "metadata_revision": game.team_performance_metadata_revision,
                "ledger_digest": _digest(game.deliveries),
                "status": game.status.value,
                "original_overs_limit": game.original_overs_limit,
            },
        )
        db.add(event)
        result.append(event)
    await db.flush()
    return result


async def record_completion_event(
    db: AsyncSession,
    *,
    game_id: str,
) -> models.TeamPerformanceTrialCompletion | None:
    """Convenience for one Team; the scoring boundary processes every scoped event."""
    events = await record_completion_events(db, game_id=game_id)
    return events[0] if events else None


async def process_completion_event(
    db: AsyncSession,
    *,
    completion_event_id: str,
) -> None:
    """Serialize every Team claim; a failed transaction is retriable by verification."""
    event = await db.scalar(
        select(models.TeamPerformanceTrialCompletion).where(
            models.TeamPerformanceTrialCompletion.id == completion_event_id
        )
    )
    if event is None:
        raise TrialTransitionError("Completion evidence not found")
    trial = await db.scalar(
        select(models.TeamPerformanceTrial)
        .where(
            models.TeamPerformanceTrial.id == event.trial_id,
        )
        .with_for_update()
    )
    if trial is None:
        return
    earlier = (
        await db.scalars(
            select(models.TeamPerformanceTrialCompletion)
            .where(
                models.TeamPerformanceTrialCompletion.trial_id == trial.id,
                models.TeamPerformanceTrialCompletion.completed_at <= event.completed_at,
            )
            .order_by(
                models.TeamPerformanceTrialCompletion.completed_at,
                models.TeamPerformanceTrialCompletion.id,
            )
            .limit(251)
        )
    ).all()
    if len(earlier) > 250:
        await _review(db, trial, event, "Completion event workload is too large")
        return
    for candidate in earlier:
        if trial.state != "active":
            break
        await _process_for_trial(db, trial, candidate)


async def _review(
    db: AsyncSession,
    trial: models.TeamPerformanceTrial,
    event: models.TeamPerformanceTrialCompletion,
    reason: str,
) -> None:
    key = f"review:{event.id}"
    exists = await db.scalar(
        select(models.TeamPerformanceTrialEvent.id).where(
            models.TeamPerformanceTrialEvent.trial_id == trial.id,
            models.TeamPerformanceTrialEvent.event_key == key,
        )
    )
    if exists is None:
        db.add(
            models.TeamPerformanceTrialEvent(
                trial_id=trial.id,
                kind="review",
                event_key=key,
                game_id=event.game_id,
                reason=reason,
                evidence={"completion_event_id": event.id},
                recorded_at=_now(),
            )
        )
    trial.state = "review_required"
    await db.flush()


async def _process_for_trial(
    db: AsyncSession,
    trial: models.TeamPerformanceTrial,
    event: models.TeamPerformanceTrialCompletion,
) -> None:
    if trial.state != "active":
        return
    if event.completed_at is None or _utc(event.completed_at) <= _utc(trial.activated_at):
        return
    if _utc(event.completed_at) >= _utc(trial.expires_at):
        return
    available = await db.scalar(
        select(models.TeamPerformanceTrialAvailability.status).where(
            models.TeamPerformanceTrialAvailability.organization_id == trial.organization_id
        )
    )
    organization = await db.scalar(
        select(models.Organization.status).where(models.Organization.id == trial.organization_id)
    )
    team = await db.scalar(select(models.Team.status).where(models.Team.id == trial.team_id))
    if available != "enabled" or organization != "active" or team != "active":
        return
    if any(item["game_id"] == event.game_id for item in trial.prerequisite_sources):
        return
    already = await db.scalar(
        select(models.TeamPerformanceTrialConsumption.id).where(
            models.TeamPerformanceTrialConsumption.trial_id == trial.id,
            models.TeamPerformanceTrialConsumption.game_id == event.game_id,
        )
    )
    if already is not None:
        return
    game = await db.scalar(select(models.Game).where(models.Game.id == event.game_id))
    if game is None or game.match_purpose != "official" or game.match_type != "limited":
        return
    if game.days_limit is not None or game.match_rules is not None:
        return
    if (
        game.original_format_trust_state in {"setup_capture", "staff_corrected"}
        and game.original_overs_limit != 25
    ):
        return
    valid = await _valid_consumptions(db, trial.id)
    if len(valid) >= 3:
        return
    if not await _sources_match(db, trial, trial.prerequisite_sources):
        await _review(db, trial, event, "Frozen prerequisite evidence changed")
        return
    current = await _current_source(db, trial, event.game_id)
    if current is None:
        await _review(db, trial, event, "Completion evidence is unavailable or ineligible")
        return
    if (
        current["played_date"] != event.evidence.get("played_date")
        or current["metadata_revision"] != event.evidence.get("metadata_revision")
        or current["ledger_digest"] != event.evidence.get("ledger_digest")
    ):
        await _review(db, trial, event, "Completion evidence changed after the event")
        return
    played_date = dt.date.fromisoformat(str(current["played_date"]))
    if played_date < trial.activation_local_date:
        await _review(db, trial, event, "Historical Game cannot consume a trial credit")
        return
    if played_date > _utc(event.completed_at).astimezone(ZoneInfo(trial.venue_timezone)).date():
        await _review(db, trial, event, "Game date is later than trusted completion")
        return
    prior = [
        *trial.prerequisite_sources,
        *(
            {
                "game_id": row.game_id,
                "played_date": row.played_date.isoformat(),
                "metadata_revision": row.metadata_revision,
                "ledger_digest": row.ledger_digest,
            }
            for row in valid
        ),
    ]
    if not await _sources_match(db, trial, prior):
        await _review(db, trial, event, "Previously verified Game evidence changed")
        return
    dates = [dt.date.fromisoformat(str(source["played_date"])) for source in prior]
    if any(date > played_date for date in dates):
        await _review(db, trial, event, "Game chronology is ambiguous")
        return
    for consumption in valid:
        if consumption.played_date != played_date:
            continue
        earlier_event = await db.get(
            models.TeamPerformanceTrialCompletion, consumption.completion_event_id
        )
        if earlier_event is None or _utc(earlier_event.completed_at) >= _utc(event.completed_at):
            await _review(db, trial, event, "Same-date completion order is unverified")
            return
    from backend.services.school_team_readiness_service import TeamReadinessRequest
    from backend.services.school_team_report_service import (
        compose_team_coach_report,
        safe_coach_report_response,
    )

    if played_date == dt.date.max:
        await _review(db, trial, event, "No safe report boundary exists")
        return
    report = await compose_team_coach_report(
        db,
        TeamReadinessRequest(
            trial.activated_by_user_id,
            trial.organization_id,
            trial.team_id,
            played_date + dt.timedelta(days=1),
            access_mode="trial_system",
        ),
    )
    expected = [*prior, current][-5:]
    selected = list(reversed(report.readiness.selected_sources))
    if (
        report.readiness.state != "ready"
        or report.form is None
        or [source.game_id for source in selected] != [source["game_id"] for source in expected]
        or any(
            _source_dict(actual) != intended
            for actual, intended in zip(selected, expected, strict=True)
        )
    ):
        await _review(db, trial, event, "Rolling five-match report evidence is unavailable")
        return
    ordinal = len(valid) + 1
    now = _now()
    db.add(
        models.TeamPerformanceTrialConsumption(
            trial_id=trial.id,
            game_id=event.game_id,
            completion_event_id=event.id,
            played_date=played_date,
            metadata_revision=int(str(current["metadata_revision"])),
            ledger_digest=str(current["ledger_digest"]),
            recorded_at=now,
        )
    )
    db.add(
        models.TeamPerformanceTrialSnapshot(
            trial_id=trial.id,
            ordinal=ordinal,
            report=safe_coach_report_response(report).model_dump(mode="json"),
            sources=expected,
            created_at=now,
        )
    )
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="consumed",
            event_key=f"consume:{event.id}",
            game_id=event.game_id,
            reason="Verified trusted completion event",
            evidence={"ordinal": ordinal, "source": current},
            recorded_at=now,
        )
    )
    if ordinal == 3:
        trial.state = "exhausted"
        trial.completed_at = _utc(event.completed_at)
        trial.report_access_until = _utc(event.completed_at) + dt.timedelta(days=REPORT_DAYS)
    await db.flush()


async def resolve_trial_review(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    operator_user_id: str,
    reason: str,
    reverse_game_id: str | None,
) -> models.TeamPerformanceTrial:
    await _operator(db, operator_user_id)
    audit_reason = _reason(reason)
    trial = await db.scalar(
        select(models.TeamPerformanceTrial)
        .where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
        .with_for_update()
    )
    if trial is None:
        raise TrialTransitionError("Trial not found")
    was_revoked = trial.state == "revoked"
    if trial.state != "review_required":
        currently_valid = await _valid_consumptions(db, trial.id)
        current_sources = [
            *trial.prerequisite_sources,
            *(
                {
                    "game_id": row.game_id,
                    "played_date": row.played_date.isoformat(),
                    "metadata_revision": row.metadata_revision,
                    "ledger_digest": row.ledger_digest,
                }
                for row in currently_valid
            ),
        ]
        if await _sources_match(db, trial, current_sources):
            raise TrialTransitionError("Trial is not awaiting review")
        db.add(
            models.TeamPerformanceTrialEvent(
                trial_id=trial.id,
                kind="review",
                event_key=f"review:correction:{uuid.uuid4()}",
                actor_user_id=operator_user_id,
                reason="Operator confirmed changed trial evidence",
                recorded_at=_now(),
            )
        )
        trial.state = "review_required"
    if reverse_game_id is not None:
        consumption = await db.scalar(
            select(models.TeamPerformanceTrialConsumption).where(
                models.TeamPerformanceTrialConsumption.trial_id == trial.id,
                models.TeamPerformanceTrialConsumption.game_id == reverse_game_id,
            )
        )
        if consumption is None:
            raise TrialTransitionError("Consumption not found")
        existing = await db.scalar(
            select(models.TeamPerformanceTrialEvent.id).where(
                models.TeamPerformanceTrialEvent.trial_id == trial.id,
                models.TeamPerformanceTrialEvent.event_key == f"reverse:{consumption.id}",
            )
        )
        if existing is not None:
            raise TrialTransitionError("Consumption was already reversed")
        source = {
            "game_id": consumption.game_id,
            "played_date": consumption.played_date.isoformat(),
            "metadata_revision": consumption.metadata_revision,
            "ledger_digest": consumption.ledger_digest,
        }
        if await _current_evidence_matches(db, trial, source):
            raise TrialTransitionError("Verified consumption remains valid")
        db.add(
            models.TeamPerformanceTrialEvent(
                trial_id=trial.id,
                kind="reversed",
                event_key=f"reverse:{consumption.id}",
                game_id=consumption.game_id,
                actor_user_id=operator_user_id,
                reason=audit_reason,
                evidence={"consumption_id": consumption.id},
                recorded_at=_now(),
            )
        )
        await db.flush()
    if not await _sources_match(db, trial, trial.prerequisite_sources):
        raise TrialTransitionError("Frozen prerequisite evidence remains disputed")
    valid = await _valid_consumptions(db, trial.id)
    sources = [
        {
            "game_id": row.game_id,
            "played_date": row.played_date.isoformat(),
            "metadata_revision": row.metadata_revision,
            "ledger_digest": row.ledger_digest,
        }
        for row in valid
    ]
    if not await _sources_match(db, trial, sources):
        raise TrialTransitionError("Another consumption remains disputed")
    now = _now()
    if was_revoked:
        trial.state = "revoked"
    elif now >= _utc(trial.expires_at):
        trial.state = "expired"
    elif len(valid) == 3:
        trial.state = "exhausted"
    else:
        trial.state = "active"
        trial.completed_at = None
        trial.report_access_until = None
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="resolved",
            event_key=f"resolve:{uuid.uuid4()}",
            actor_user_id=operator_user_id,
            reason=audit_reason,
            evidence={"reversed_game_id": reverse_game_id, "valid_games": len(valid)},
            recorded_at=now,
        )
    )
    await db.flush()
    return trial


async def extend_trial_for_system_fault(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    operator_user_id: str,
    new_expires_at: dt.datetime,
    reason: str,
) -> models.TeamPerformanceTrial:
    await _operator(db, operator_user_id)
    audit_reason = _reason(reason)
    if new_expires_at.tzinfo is None:
        raise TrialTransitionError("Extension timestamp requires a timezone")
    trial = await db.scalar(
        select(models.TeamPerformanceTrial)
        .where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
        .with_for_update()
    )
    if trial is None or trial.state == "revoked":
        raise TrialTransitionError("Trial cannot be extended")
    previous = _utc(trial.expires_at)
    if _utc(new_expires_at) <= max(previous, _now()):
        raise TrialTransitionError("Extension must move the deadline into the future")
    trial.expires_at = _utc(new_expires_at)
    if trial.state == "expired":
        trial.state = "active"
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="extended",
            event_key=f"extend:{uuid.uuid4()}",
            actor_user_id=operator_user_id,
            reason=audit_reason,
            evidence={
                "old_expires_at": previous.isoformat(),
                "new_expires_at": _utc(new_expires_at).isoformat(),
                "verified_system_fault": True,
            },
            recorded_at=_now(),
        )
    )
    await db.flush()
    return trial


async def request_trial_verification(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
    game_id: str,
) -> bool:
    await require_trial_scope(
        db,
        organization_id=organization_id,
        team_id=team_id,
        actor_user_id=actor_user_id,
        mode="trial_activation",
    )
    game = await db.scalar(select(models.Game).where(models.Game.id == game_id))
    from backend.services.school_team_readiness_service import _source

    if game is None or (organization_id, team_id) not in {
        _source(game.team_a),
        _source(game.team_b),
    }:
        raise TeamPerformanceAccessError(404, "Game not found")
    event = await db.scalar(
        select(models.TeamPerformanceTrialCompletion).where(
            models.TeamPerformanceTrialCompletion.trial_id
            == select(models.TeamPerformanceTrial.id)
            .where(
                models.TeamPerformanceTrial.organization_id == organization_id,
                models.TeamPerformanceTrial.team_id == team_id,
            )
            .scalar_subquery(),
            models.TeamPerformanceTrialCompletion.game_id == game_id,
        )
    )
    if event is None:
        await request_trial_review(
            db,
            organization_id=organization_id,
            team_id=team_id,
            actor_user_id=actor_user_id,
            game_id=game_id,
            reason="Trusted completion event unavailable; review requested",
        )
        return False
    await process_completion_event(db, completion_event_id=event.id)
    return True


async def request_trial_review(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
    game_id: str,
    reason: str,
) -> None:
    await require_trial_scope(
        db,
        organization_id=organization_id,
        team_id=team_id,
        actor_user_id=actor_user_id,
        mode="trial_activation",
    )
    audit_reason = _reason(reason)
    game = await db.scalar(select(models.Game).where(models.Game.id == game_id))
    from backend.services.school_team_readiness_service import _source

    if game is None or (organization_id, team_id) not in {
        _source(game.team_a),
        _source(game.team_b),
    }:
        raise TeamPerformanceAccessError(404, "Game not found")
    trial = await db.scalar(
        select(models.TeamPerformanceTrial)
        .where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
        .with_for_update()
    )
    if trial is None or trial.state in {"revoked", "expired"}:
        raise TrialTransitionError("Trial review is unavailable")
    trial.state = "review_required"
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="review_requested",
            event_key=f"review_request:{uuid.uuid4()}",
            game_id=game_id,
            actor_user_id=actor_user_id,
            reason=audit_reason,
            recorded_at=_now(),
        )
    )
    await db.flush()


async def retained_trial_report(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> dict[str, object]:
    await require_trial_scope(
        db,
        organization_id=organization_id,
        team_id=team_id,
        actor_user_id=actor_user_id,
        mode="trial_report",
    )
    trial = await db.scalar(
        select(models.TeamPerformanceTrial).where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
    )
    if trial is None:
        raise TeamPerformanceAccessError(403, "Team Performance trial is unavailable")
    effective_status = await trial_status(
        db,
        organization_id=organization_id,
        team_id=team_id,
        actor_user_id=actor_user_id,
    )
    if effective_status["state"] == "review_required":
        raise TrialTransitionError("Verified report evidence changed; review is required")
    valid = await _valid_consumptions(db, trial.id)
    if not valid:
        raise TrialTransitionError("No verified trial report is available")
    snapshots = (
        await db.scalars(
            select(models.TeamPerformanceTrialSnapshot)
            .where(
                models.TeamPerformanceTrialSnapshot.trial_id == trial.id,
                models.TeamPerformanceTrialSnapshot.ordinal == len(valid),
            )
            .order_by(models.TeamPerformanceTrialSnapshot.created_at.desc())
        )
    ).all()
    snapshot = next(
        (item for item in snapshots if item.sources[-1]["game_id"] == valid[-1].game_id), None
    )
    if snapshot is None:
        raise TrialTransitionError("Verified report snapshot is unavailable")
    if not await _sources_match(db, trial, snapshot.sources):
        raise TrialTransitionError("Verified report evidence changed; review is required")
    return snapshot.report


async def handle_completed_game_after_free_commit(db: AsyncSession, game_id: str) -> None:
    """Best-effort automatic trial work after the Free Game transaction is durable.

    The independently committed completion event can be retried through controlled
    verification if downstream processing fails. No trial exception reaches scoring.
    """
    import logging

    if not isinstance(db, AsyncSession):
        return

    try:
        events = await record_completion_events(db, game_id=game_id)
        if not events:
            return
        event_ids = [event.id for event in events]
        await db.commit()
    except Exception:
        await db.rollback()
        logging.getLogger(__name__).exception(
            "Trial completion capture failed for Game %s", game_id
        )
        return
    for event_id in event_ids:
        try:
            await process_completion_event(db, completion_event_id=event_id)
            await db.commit()
        except Exception:
            await db.rollback()
            logging.getLogger(__name__).exception(
                "Trial completion processing failed for Game %s", game_id
            )


async def revoke_trial(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    operator_user_id: str,
    reason: str,
) -> models.TeamPerformanceTrial:
    await _operator(db, operator_user_id)
    audit_reason = _reason(reason)
    trial = await db.scalar(
        select(models.TeamPerformanceTrial)
        .where(
            models.TeamPerformanceTrial.organization_id == organization_id,
            models.TeamPerformanceTrial.team_id == team_id,
        )
        .with_for_update()
    )
    if trial is None:
        raise TrialTransitionError("Trial not found")
    if trial.state == "revoked":
        return trial
    trial.state = "revoked"
    db.add(
        models.TeamPerformanceTrialEvent(
            trial_id=trial.id,
            kind="revoked",
            event_key="revocation",
            actor_user_id=operator_user_id,
            reason=audit_reason,
            recorded_at=_now(),
        )
    )
    await db.flush()
    return trial
