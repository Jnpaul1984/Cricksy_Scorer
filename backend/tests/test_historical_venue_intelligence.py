from __future__ import annotations

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.services.historical_import_apply_service import apply_historical_batch
from backend.services.historical_import_service import create_import_batch
from backend.services.historical_venue_intelligence_service import normalize_venue_name
from backend.sql_app.models import (
    Game,
    HistoricalCompetitionVenueUsage,
    HistoricalImportBatch,
    HistoricalVenueAlias,
    HistoricalVenueIntelligence,
    HistoricalVenueResolutionDecision,
    HistoricalVenueResolutionQueue,
    HistoricalVenueResolutionState,
    HistoricalVenueVerificationStatus,
)


def _sha256() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


async def _apply_batch_with_venue(
    db: AsyncSession,
    *,
    venue: str,
    competition_name: str = "Caribbean Premier League",
    season: str = "2013",
) -> tuple[str, str]:
    source_hash = _sha256()
    batch = await create_import_batch(
        db,
        source_hash_sha256=source_hash,
        source_format="cricsheet_json",
        status="valid",
        error_count=0,
        warning_count=0,
        innings_count=2,
        delivery_count=12,
        dry_run_summary={
            "metadata_preview": {
                "match_type": "t20",
                "venue": venue,
                "date": "2013-07-30",
                "result": "Team A won",
                "event_name": competition_name,
                "season": season,
            },
            "teams_preview": ["Team A", "Team B"],
            "player_names_found": ["Player A", "Player B"],
            "innings_preview": [
                {"inning_no": 1, "team": "Team A", "deliveries": 6, "runs": 10, "wickets": 1},
                {"inning_no": 2, "team": "Team B", "deliveries": 6, "runs": 8, "wickets": 2},
            ],
            "canonical_preview": {
                "competition_context": {
                    "competition_type": "franchise",
                    "competition_name": competition_name,
                    "season": season,
                },
                "venue_context": {
                    "venue_name": venue,
                    "city": "Bridgetown",
                    "country": "Barbados",
                    "source_venue_raw": venue,
                },
                "source_provenance": {
                    "source_schema": "cricsheet_json",
                    "source_hash_sha256": source_hash,
                },
                "squad_roster_snapshot": [
                    {
                        "team_name": "Team A",
                        "named_squad": ["Player A", "Player B"],
                        "playing_xi": ["Player A"],
                        "substitutes": [],
                        "unresolved_entries": [],
                    }
                ],
            },
        },
    )
    game, _, err = await apply_historical_batch(db, batch_id=batch.id, confirm=True)
    assert err is None, err
    assert game is not None
    return batch.id, game.id


@pytest.mark.asyncio
async def test_phase10h_exact_venue_resolution(db_session: AsyncSession) -> None:
    now = dt.datetime.now(getattr(dt, "UTC", dt.timezone.utc))
    venue = HistoricalVenueIntelligence(
        canonical_name="Kensington Oval",
        normalized_canonical_name=normalize_venue_name("Kensington Oval"),
        short_name="Kensington",
        normalized_short_name=normalize_venue_name("Kensington"),
        alternate_names=[],
        city="Bridgetown",
        country="Barbados",
        verification_status=HistoricalVenueVerificationStatus.verified,
        confidence_score=1.0,
        source_type="manual_seed",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(venue)
    await db_session.flush()
    await _apply_batch_with_venue(db_session, venue="Kensington Oval")
    decision = (await db_session.execute(select(HistoricalVenueResolutionDecision))).scalars().first()
    assert decision is not None
    assert decision.canonical_venue_id == venue.id
    assert decision.matched_by == "exact_match"
    assert decision.resolution_state == HistoricalVenueResolutionState.resolved


@pytest.mark.asyncio
async def test_phase10h_alias_and_normalized_resolution(db_session: AsyncSession) -> None:
    now = dt.datetime.now(getattr(dt, "UTC", dt.timezone.utc))
    venue = HistoricalVenueIntelligence(
        canonical_name="Kensington Oval",
        normalized_canonical_name=normalize_venue_name("Kensington Oval"),
        short_name="Kensington",
        normalized_short_name=normalize_venue_name("Kensington"),
        alternate_names=[],
        verification_status=HistoricalVenueVerificationStatus.verified,
        confidence_score=1.0,
        source_type="manual_seed",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(venue)
    await db_session.flush()
    db_session.add(
        HistoricalVenueAlias(
            venue_id=venue.id,
            alias_name="Kensington O.",
            normalized_alias=normalize_venue_name("Kensington O."),
            source_schema="cricsheet_json",
            source_system="historical_import_json",
            confidence_score=0.98,
            provenance_reference={},
            first_seen=now,
            last_seen=now,
        )
    )
    await db_session.commit()

    await _apply_batch_with_venue(db_session, venue="Kensington O.")
    await _apply_batch_with_venue(db_session, venue="kEnsington  oval!!", season="2014")
    rows = (
        await db_session.execute(
            select(HistoricalVenueResolutionDecision).order_by(HistoricalVenueResolutionDecision.created_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].matched_by == "alias_match"
    assert rows[1].matched_by == "normalized_match"


@pytest.mark.asyncio
async def test_phase10h_unresolved_low_confidence_and_review_required(db_session: AsyncSession) -> None:
    now = dt.datetime.now(getattr(dt, "UTC", dt.timezone.utc))
    db_session.add_all(
        [
            HistoricalVenueIntelligence(
                canonical_name="Kensington Oval",
                normalized_canonical_name=normalize_venue_name("Kensington Oval"),
                short_name=None,
                normalized_short_name=None,
                alternate_names=[],
                verification_status=HistoricalVenueVerificationStatus.verified,
                confidence_score=1.0,
                source_type="manual_seed",
                created_from_import=False,
                provenance_references=[],
                first_seen=now,
                last_seen=now,
            ),
            HistoricalVenueIntelligence(
                canonical_name="Providence Stadium",
                normalized_canonical_name=normalize_venue_name("Providence Stadium"),
                short_name=None,
                normalized_short_name=None,
                alternate_names=[],
                verification_status=HistoricalVenueVerificationStatus.verified,
                confidence_score=1.0,
                source_type="manual_seed",
                created_from_import=False,
                provenance_references=[],
                first_seen=now,
                last_seen=now,
            ),
        ]
    )
    await db_session.commit()

    await _apply_batch_with_venue(db_session, venue="Providence")
    decision = (await db_session.execute(select(HistoricalVenueResolutionDecision))).scalars().first()
    assert decision is not None
    assert decision.canonical_venue_id is None
    assert decision.unresolved_reason in {"low_confidence_fuzzy_match", "deterministic_rules_no_match"}
    assert decision.review_required is True
    queue = (await db_session.execute(select(HistoricalVenueResolutionQueue))).scalars().first()
    assert queue is not None
    assert queue.queue_state == "pending"


@pytest.mark.asyncio
async def test_phase10h_provenance_and_import_integration_preserved(db_session: AsyncSession) -> None:
    batch_id, game_id = await _apply_batch_with_venue(db_session, venue="Sample Cricket Ground")
    decision = (
        await db_session.execute(
            select(HistoricalVenueResolutionDecision).where(
                HistoricalVenueResolutionDecision.batch_id == batch_id,
                HistoricalVenueResolutionDecision.game_id == game_id,
            )
        )
    ).scalars().first()
    assert decision is not None
    assert decision.provenance_references
    provenance = decision.provenance_references[0]
    assert provenance["batch_id"] == batch_id
    assert provenance["game_id"] == game_id
    assert provenance["source_schema"] == "cricsheet_json"

    game = (await db_session.execute(select(Game).where(Game.id == game_id))).scalars().first()
    assert game is not None
    hist_meta = (game.phases or {}).get("historical_import", {})
    venue_resolution = hist_meta.get("venue_resolution")
    assert isinstance(venue_resolution, dict)
    assert venue_resolution["decision_id"] == decision.id


@pytest.mark.asyncio
async def test_phase10h_unresolved_never_blocks_import(db_session: AsyncSession) -> None:
    batch_id, game_id = await _apply_batch_with_venue(db_session, venue="Mystery Venue")
    batch = await db_session.get(HistoricalImportBatch, batch_id)
    assert batch is not None
    assert batch.is_finalized is True
    assert batch.applied_game_id == game_id
    decision = (
        await db_session.execute(
            select(HistoricalVenueResolutionDecision).where(
                HistoricalVenueResolutionDecision.batch_id == batch_id
            )
        )
    ).scalars().first()
    assert decision is not None
    assert decision.review_required is True


@pytest.mark.asyncio
async def test_phase10h_duplicate_prevention_and_usage_stats(db_session: AsyncSession) -> None:
    await _apply_batch_with_venue(db_session, venue="Auto Create Stadium", competition_name="CPL")
    await _apply_batch_with_venue(db_session, venue="Auto Create Stadium", competition_name="CPL")

    venue_count = await db_session.scalar(
        select(func.count()).select_from(HistoricalVenueIntelligence).where(
            HistoricalVenueIntelligence.normalized_canonical_name == "auto create stadium"
        )
    )
    assert venue_count == 1

    usage = (await db_session.execute(select(HistoricalCompetitionVenueUsage))).scalars().first()
    assert usage is not None
    assert usage.matches_count == 2


@pytest.mark.asyncio
async def test_phase10h_review_required_for_ambiguous_exact_match(db_session: AsyncSession) -> None:
    now = dt.datetime.now(getattr(dt, "UTC", dt.timezone.utc))
    db_session.add_all(
        [
            HistoricalVenueIntelligence(
                canonical_name="Shared Ground",
                normalized_canonical_name=normalize_venue_name("Shared Ground"),
                short_name=None,
                normalized_short_name=None,
                alternate_names=[],
                city="City A",
                verification_status=HistoricalVenueVerificationStatus.unverified,
                confidence_score=0.8,
                source_type="seed",
                created_from_import=False,
                provenance_references=[],
                first_seen=now,
                last_seen=now,
            ),
            HistoricalVenueIntelligence(
                canonical_name="Shared Ground",
                normalized_canonical_name=normalize_venue_name("Shared Ground"),
                short_name=None,
                normalized_short_name=None,
                alternate_names=[],
                city="City B",
                verification_status=HistoricalVenueVerificationStatus.unverified,
                confidence_score=0.8,
                source_type="seed",
                created_from_import=False,
                provenance_references=[],
                first_seen=now,
                last_seen=now,
            ),
        ]
    )
    await db_session.commit()

    await _apply_batch_with_venue(db_session, venue="Shared Ground")
    decision = (await db_session.execute(select(HistoricalVenueResolutionDecision))).scalars().first()
    assert decision is not None
    assert decision.resolution_state == HistoricalVenueResolutionState.review_required
    assert decision.unresolved_reason == "multiple_exact_candidates"
    queue = (await db_session.execute(select(HistoricalVenueResolutionQueue))).scalars().first()
    assert queue is not None
    assert queue.review_required is True


def test_phase10h_venue_routes_read_only_smoke() -> None:
    client = TestClient(app)
    assert client.get("/api/historical-import/json/venues/intelligence").status_code == 200
    assert client.get("/api/historical-import/json/venues/unresolved").status_code == 200
    assert client.get("/api/historical-import/json/venues/resolution-snapshots").status_code == 200
    assert client.get("/api/historical-import/json/venues/usage").status_code == 200
    assert client.get("/api/historical-import/json/venues/aliases").status_code == 200
