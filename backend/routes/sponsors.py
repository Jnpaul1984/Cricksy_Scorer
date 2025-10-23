from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, List, Optional, Dict, Literal, Union, cast

import datetime as dt
UTC = getattr(dt, "UTC", dt.timezone.utc)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.sql_app import models, crud
from backend.sql_app.database import get_db
from backend.utils.common import (
    MAX_UPLOAD_BYTES,
    detect_image_ext as _detect_image_ext,
    parse_iso_dt as _parse_iso_dt,
    iso_or_none as _iso_or_none,
)

router = APIRouter(tags=["sponsors"])

# Ensure static dir exists
SPONSORS_DIR: Path = settings.SPONSORS_DIR
SPONSORS_DIR.mkdir(parents=True, exist_ok=True)

class SponsorImpressionIn(BaseModel):
    game_id: str
    sponsor_id: str
    at: Optional[str] = None  # ISO-8601

class SponsorImpressionsOut(BaseModel):
    inserted: int
    ids: List[int]

class SponsorItem(BaseModel):
    name: Optional[str] = None
    logoUrl: Optional[str] = None
    clickUrl: Optional[str] = None
    image_url: Optional[str] = None
    img: Optional[str] = None
    link_url: Optional[str] = None
    url: Optional[str] = None
    alt: Optional[str] = None
    rail: Optional[Literal["left", "right", "badge"]] = None
    maxPx: Optional[Union[int, str]] = None
    size: Optional[Union[int, str]] = None

class SponsorsManifest(BaseModel):
    items: List[SponsorItem]

@router.post("/sponsors")
async def create_sponsor(
    name: str = Form(...),
    logo: UploadFile = File(...),
    click_url: Optional[str] = Form(None),
    weight: int = Form(1),
    surfaces: Optional[str] = Form(None),   # JSON array as string
    start_at: Optional[str] = Form(None),   # ISO-8601
    end_at: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if weight < 1 or weight > 5:
        raise HTTPException(status_code=400, detail="weight must be between 1 and 5")

    data = await logo.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5MB limit")

    ext = _detect_image_ext(data, logo.content_type, logo.filename)
    if ext is None:
        raise HTTPException(status_code=400, detail="Only SVG, PNG or WebP images are allowed")

    try:
        parsed_any: Any = json.loads(surfaces) if surfaces else ["all"]
    except Exception as err:
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings") from err

    if not isinstance(parsed_any, list):
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")

    parsed_list: List[Any] = cast(List[Any], parsed_any)
    for itm in parsed_list:
        if not isinstance(itm, str):
            raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")
    surfaces_list: List[str] = [str(itm) for itm in parsed_list] or ["all"]

    start_dt = _parse_iso_dt(start_at)
    end_dt = _parse_iso_dt(end_at)

    SPONSORS_DIR.mkdir(parents=True, exist_ok=True)
    fid = os.urandom(8).hex()
    filename = f"{fid}.{ext}"
    fpath = SPONSORS_DIR / filename
    fpath.write_bytes(data)

    rec = models.Sponsor(
        name=name,
        logo_path=f"sponsors/{filename}",
        click_url=click_url,
        weight=int(weight),
        surfaces=surfaces_list,
        start_at=start_dt,
        end_at=end_dt,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    logo_url = f"/static/{rec.logo_path}"

    return {
        "id": rec.id,
        "name": rec.name,
        "logo_url": logo_url,
        "click_url": rec.click_url,
        "weight": rec.weight,
        "surfaces": rec.surfaces,
        "start_at": _iso_or_none(rec.start_at),
        "end_at": _iso_or_none(rec.end_at),
        "created_at": _iso_or_none(rec.created_at),
        "updated_at": _iso_or_none(rec.updated_at),
    }

@router.get("/games/{game_id}/sponsors")
async def get_game_sponsors(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[dict[str, Any]]:
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    now = dt.datetime.now(UTC)

    Sponsor = models.Sponsor
    conditions = [
        or_(Sponsor.start_at.is_(None), Sponsor.start_at <= now),
        or_(Sponsor.end_at.is_(None), Sponsor.end_at >= now),
    ]
    if hasattr(Sponsor, "is_active"):
        conditions.append(getattr(Sponsor, "is_active") == True)  # noqa: E712

    stmt = (
        select(Sponsor)
        .where(and_(*conditions))
        .order_by(Sponsor.weight.desc(), Sponsor.created_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()

    out: List[dict[str, Any]] = []
    for r in rows:
        rid: int = int(r.id)
        name: str = str(r.name)
        logo_path: str = str(r.logo_path)
        click_url: Optional[str] = str(r.click_url) if r.click_url is not None else None
        weight: int = int(r.weight)

        raw_surfaces_any: Any = getattr(r, "surfaces", None)
        if isinstance(raw_surfaces_any, (list, tuple)):
            surfaces: List[str] = (r.surfaces or ["all"])
        else:
            surfaces = ["all"]

        out.append(
            {
                "id": rid,
                "name": name,
                "logoUrl": f"/static/{logo_path}",
                "clickUrl": click_url,
                "weight": weight,
                "surfaces": surfaces,
            }
        )
    return out

@router.get("/static/sponsors/{brand}/manifest.json", response_model=SponsorsManifest)
def sponsors_manifest(brand: str) -> SponsorsManifest:
    items: List[SponsorItem] = [
        SponsorItem(logoUrl=f"/static/sponsors/{brand}/Cricksy.png",       alt="Cricksy",         rail="left",  maxPx=120),
        SponsorItem(logoUrl=f"/static/sponsors/{brand}/Cricksy_no_bg.png", alt="Cricksy (no bg)", rail="right", maxPx=140),
        SponsorItem(logoUrl=f"/static/sponsors/{brand}/Cricksy_mono.png",  alt="Presented by Cricksy"),
        SponsorItem(logoUrl="/static/sponsors/cricksy/Cricksy_outline.png",        alt="Cricksy outline"),
        SponsorItem(logoUrl="/static/sponsors/cricksy/Cricksy_Black_&_white.png",  alt="Cricksy B/W"),
        SponsorItem(logoUrl="/static/sponsors/cricksy/Cricksy_colored_circle.png", alt="Cricksy circle"),
    ]
    return SponsorsManifest(items=items)

@router.post("/sponsor_impressions", response_model=SponsorImpressionsOut)
async def log_sponsor_impressions(
    body: Union[SponsorImpressionIn, List[SponsorImpressionIn]],
    db: AsyncSession = Depends(get_db),
):
    items: List[SponsorImpressionIn] = body if isinstance(body, list) else [body]

    if len(items) == 0:
        raise HTTPException(status_code=400, detail="Empty payload")
    if len(items) > 20:
        raise HTTPException(status_code=400, detail="Batch too large; max 20")

    game_ids = {it.game_id for it in items}
    sponsor_ids = {it.sponsor_id for it in items}

    res_games = await db.execute(select(models.Game.id).where(models.Game.id.in_(list(game_ids))))
    found_games = {g for (g,) in res_games.all()}
    missing_games = [g for g in game_ids if g not in found_games]
    if missing_games:
        raise HTTPException(status_code=400, detail=f"Unknown game_id(s): {missing_games}")

    res_sps = await db.execute(select(models.Sponsor.id).where(models.Sponsor.id.in_(list(sponsor_ids))))
    found_sps = {s for (s,) in res_sps.all()}
    missing_sps = [s for s in sponsor_ids if s not in found_sps]
    if missing_sps:
        raise HTTPException(status_code=400, detail=f"Unknown sponsor_id(s): {missing_sps}")

    rows: List[models.SponsorImpression] = []
    now = dt.datetime.now(UTC)
    for it in items:
        at_dt = _parse_iso_dt(it.at) or now
        rows.append(
            models.SponsorImpression(
                game_id=it.game_id,
                sponsor_id=it.sponsor_id,
                at=at_dt,
            )
        )

    db.add_all(rows)
    await db.commit()

    for r in rows:
        await db.refresh(r)

    return SponsorImpressionsOut(
        inserted=len(rows),
        ids=[int(r.id) for r in rows],
    )