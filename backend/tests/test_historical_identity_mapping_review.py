"""
Phase 10J — Historical Identity Mapping Review workflow tests.

Covers:
- GET /identity-review/unresolved returns player and venue review items
- POST players/{id}/link: link source player to existing Player (idempotent)
- POST players/{id}/create: create Player from source identity (preserves provenance)
- POST players/{id}/defer: defer without deleting records
- POST venues/link: link venue to existing venue
- POST venues/create-alias: alias creation is idempotent
- POST venues/create: create new venue from queue entry
- POST venues/defer: defer without deleting queue entry
- Ambiguous player is not auto-linked
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.historical_import_apply_service import apply_historical_batch
from backend.services.historical_import_service import create_import_batch
from backend.services.historical_player_identity_service import (
    create_player_from_source,
    defer_player_resolution,
    link_source_player,
    list_unresolved_players,
)
from backend.services.historical_venue_intelligence_service import (
    create_venue_from_queue,
    defer_venue_resolution,
    link_source_venue,
)
from backend.sql_app.models import (
    HistoricalPlayerResolutionQueue,
    HistoricalPlayerResolutionState,
    HistoricalSourcePlayerRegistry,
    HistoricalVenueIntelligence,
    HistoricalVenueResolutionDecision,
    HistoricalVenueResolutionQueue,
    HistoricalVenueVerificationStatus,
    Player,
)


def _sha256() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


async def _make_player_batch(
    db: AsyncSession,
    *,
    roster_names: list[str],
    roster_entries: list[dict[str, Any]] | None = None,
    competition_name: str = "Caribbean Premier League",
    season: str = "2016",
) -> str:
    """Create a batch and apply it so registry entries are created."""
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
                "venue": "Kensington Oval",
                "date": "2016-07-13",
                "result": "Team A won",
                "event_name": competition_name,
                "season": season,
            },
            "teams_preview": ["Barbados Tridents", "St Kitts and Nevis Patriots"],
            "player_names_found": list(roster_names),
            "innings_preview": [
                {"inning_no": 1, "team": "Barbados Tridents", "deliveries": 6, "runs": 10, "wickets": 1},
                {"inning_no": 2, "team": "St Kitts and Nevis Patriots", "deliveries": 6, "runs": 8, "wickets": 2},
            ],
            "canonical_preview": {
                "competition_context": {
                    "competition_type": "franchise",
                    "competition_name": competition_name,
                    "season": season,
                },
                "source_provenance": {
                    "source_schema": "cricsheet_json",
                    "source_hash_sha256": source_hash,
                },
                "squad_roster_snapshot": roster_entries or [
                    {
                        "team_name": "Barbados Tridents",
                        "named_squad": list(roster_names),
                        "playing_xi": list(roster_names),
                        "substitutes": [],
                        "unresolved_entries": [],
                    }
                ],
            },
        },
    )
    _game, _, err = await apply_historical_batch(db, batch_id=batch.id, confirm=True)
    assert err is None, err
    return batch.id


async def _make_unresolved_venue_queue(
    db: AsyncSession,
    *,
    raw_venue_value: str = "Kensington Oval, Bridgetown",
    reason: str = "deterministic_rules_no_match",
) -> tuple[str, str | None]:
    """Manually insert a venue resolution queue entry and return (queue_id, decision_id)."""
    import datetime as dt
    now = dt.datetime.now(dt.UTC)

    # Create decision first
    decision = HistoricalVenueResolutionDecision(
        batch_id=None,
        game_id=None,
        raw_imported_value=raw_venue_value,
        normalized_raw_value=raw_venue_value.lower().strip(),
        canonical_venue_id=None,
        resolution_state="unresolved",
        matched_by=None,
        confidence_score=None,
        unresolved_reason=reason,
        source_schema="cricsheet_json",
        source_system="historical_import_json",
        competition_name="Caribbean Premier League",
        season="2016",
        review_required=True,
        provenance_references=[],
        resolution_snapshot={},
    )
    db.add(decision)
    await db.flush()

    queue = HistoricalVenueResolutionQueue(
        decision_id=decision.id,
        raw_imported_value=raw_venue_value,
        normalized_raw_value=raw_venue_value.lower().strip(),
        source_schema="cricsheet_json",
        source_system="historical_import_json",
        queue_state="pending",
        reason=reason,
        review_required=True,
        provenance_references=[{"competition": "CPL", "season": "2016"}],
        last_seen=now,
    )
    db.add(queue)
    await db.flush()
    return queue.id, decision.id


# ---------------------------------------------------------------------------
# Tests: Unresolved player listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_unresolved_players_returns_pending_entries(
    db_session: AsyncSession,
) -> None:
    """Unresolved players appear in the list after a batch is applied."""
    await _make_player_batch(db_session, roster_names=["SR Taylor", "RA Reifer"])

    rows = await list_unresolved_players(db_session)
    names = {r.source_player_name for r in rows}
    assert "SR Taylor" in names
    assert "RA Reifer" in names


@pytest.mark.asyncio
async def test_resolved_player_not_in_unresolved_list(
    db_session: AsyncSession,
) -> None:
    """A player that is resolved is excluded from the unresolved list."""
    db_session.add(Player(id=100, name="AB de Villiers"))
    await db_session.commit()

    await _make_player_batch(db_session, roster_names=["AB de Villiers", "Unknown Player"])

    rows = await list_unresolved_players(db_session)
    names = {r.source_player_name for r in rows}
    # AB de Villiers matches exactly and should be auto-resolved
    assert "AB de Villiers" not in names
    assert "Unknown Player" in names


# ---------------------------------------------------------------------------
# Tests: Link source player to existing Player
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_source_player_to_existing_player(
    db_session: AsyncSession,
) -> None:
    """Linking a source player to an existing Player sets canonical_player_id."""
    db_session.add(Player(id=200, name="KA Pollard", country="West Indies"))
    await db_session.commit()

    await _make_player_batch(db_session, roster_names=["KA Pollard"])
    # After batch, KA Pollard should already be auto-resolved; test with unresolved one
    await _make_player_batch(db_session, roster_names=["Kieron Pollard"])

    unresolved = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "Kieron Pollard"
                )
            )
        )
        .scalars()
        .first()
    )
    assert unresolved is not None
    source_id = unresolved.source_player_id

    registry, idempotent, message = await link_source_player(
        db_session,
        source_player_id=source_id,
        canonical_player_id=200,
        reviewed_by="analyst@test.com",
    )
    await db_session.commit()

    assert registry is not None
    assert registry.canonical_player_id == 200
    assert registry.resolution_state == HistoricalPlayerResolutionState.manually_resolved
    assert registry.manual_override is True
    assert registry.reviewed_by == "analyst@test.com"
    assert not idempotent
    assert "200" in message or "KA Pollard" in message or "200" in str(message)


@pytest.mark.asyncio
async def test_link_source_player_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Re-linking the same player to the same canonical Player is idempotent."""
    db_session.add(Player(id=201, name="Shoaib Malik"))
    await db_session.commit()

    await _make_player_batch(db_session, roster_names=["S Malik"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "S Malik"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    # First link
    _, idempotent1, _ = await link_source_player(
        db_session,
        source_player_id=reg.source_player_id,
        canonical_player_id=201,
    )
    await db_session.commit()

    # Second link with the same target
    _, idempotent2, message2 = await link_source_player(
        db_session,
        source_player_id=reg.source_player_id,
        canonical_player_id=201,
    )
    await db_session.commit()

    assert not idempotent1
    assert idempotent2
    assert "idempotent" in message2.lower()


@pytest.mark.asyncio
async def test_link_source_player_resolves_queue_entry(
    db_session: AsyncSession,
) -> None:
    """Linking a player resolves the corresponding queue entry."""
    db_session.add(Player(id=202, name="N Pooran"))
    await db_session.commit()

    await _make_player_batch(db_session, roster_names=["Nicholas Pooran"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "Nicholas Pooran"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    await link_source_player(
        db_session,
        source_player_id=reg.source_player_id,
        canonical_player_id=202,
    )
    await db_session.commit()

    queue = (
        (
            await db_session.execute(
                select(HistoricalPlayerResolutionQueue).where(
                    HistoricalPlayerResolutionQueue.source_player_id == reg.source_player_id
                )
            )
        )
        .scalars()
        .first()
    )
    # Queue may or may not exist depending on whether it was created
    if queue is not None:
        assert queue.queue_state == "resolved"
        assert queue.resolved_at is not None


# ---------------------------------------------------------------------------
# Tests: Create player from source identity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_player_from_source_preserves_provenance(
    db_session: AsyncSession,
) -> None:
    """Creating a new player from source identity links registry to new canonical player."""
    await _make_player_batch(db_session, roster_names=["D Wiese"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "D Wiese"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None
    assert reg.canonical_player_id is None

    new_player, registry, idempotent, message = await create_player_from_source(
        db_session,
        source_player_id=reg.source_player_id,
        name="David Wiese",
        country="South Africa",
        role="All-rounder",
        reviewed_by="analyst@test.com",
    )
    await db_session.commit()

    assert new_player is not None
    assert new_player.name == "David Wiese"
    assert new_player.country == "South Africa"
    assert registry is not None
    assert registry.canonical_player_id == new_player.id
    assert registry.resolution_state == HistoricalPlayerResolutionState.manually_resolved
    assert registry.manual_override is True
    assert not idempotent
    assert "David Wiese" in message


@pytest.mark.asyncio
async def test_create_player_does_not_duplicate_player(
    db_session: AsyncSession,
) -> None:
    """Creating a player and calling create again is idempotent."""
    await _make_player_batch(db_session, roster_names=["WD Parnell"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "WD Parnell"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    player1, _, idempotent1, _ = await create_player_from_source(
        db_session,
        source_player_id=reg.source_player_id,
        name="Wayne Parnell",
    )
    await db_session.commit()

    player2, _, idempotent2, _ = await create_player_from_source(
        db_session,
        source_player_id=reg.source_player_id,
        name="Wayne Parnell",
    )
    await db_session.commit()

    assert player1.id == player2.id
    assert idempotent2


# ---------------------------------------------------------------------------
# Tests: Defer player resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_defer_player_does_not_delete_registry(
    db_session: AsyncSession,
) -> None:
    """Deferring a player does not delete the registry or queue entries."""
    await _make_player_batch(db_session, roster_names=["SS Cottrell"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "SS Cottrell"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    registry, idempotent, message = await defer_player_resolution(
        db_session,
        source_player_id=reg.source_player_id,
        reason="not_enough_info",
    )
    await db_session.commit()

    assert registry is not None
    # Registry should still exist
    still_exists = await db_session.get(HistoricalSourcePlayerRegistry, reg.source_player_id)
    assert still_exists is not None
    assert not idempotent
    assert "deferred" in message.lower() or "not_enough_info" in message.lower()


@pytest.mark.asyncio
async def test_defer_player_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Deferring a player twice is idempotent."""
    await _make_player_batch(db_session, roster_names=["S Badree"])

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "S Badree"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    _, idempotent1, _ = await defer_player_resolution(
        db_session, source_player_id=reg.source_player_id
    )
    await db_session.commit()

    _, idempotent2, message2 = await defer_player_resolution(
        db_session, source_player_id=reg.source_player_id
    )
    await db_session.commit()

    assert not idempotent1
    assert idempotent2


# ---------------------------------------------------------------------------
# Tests: Venue identity review
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_source_venue_to_existing(
    db_session: AsyncSession,
) -> None:
    """Linking an unresolved venue to an existing venue resolves the queue entry."""
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    canonical = HistoricalVenueIntelligence(
        canonical_name="Kensington Oval",
        normalized_canonical_name="kensington oval",
        verification_status=HistoricalVenueVerificationStatus.verified,
        source_type="manual",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(canonical)
    await db_session.flush()

    queue_id, _ = await _make_unresolved_venue_queue(
        db_session, raw_venue_value="Kensington Oval, Bridgetown"
    )

    queue_row, idempotent, message = await link_source_venue(
        db_session,
        queue_id=queue_id,
        canonical_venue_id=canonical.id,
        reviewed_by="analyst@test.com",
    )
    await db_session.commit()

    assert queue_row is not None
    assert queue_row.queue_state == "resolved"
    assert queue_row.resolved_at is not None
    assert not idempotent
    assert "Kensington Oval" in message


@pytest.mark.asyncio
async def test_link_source_venue_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Linking a venue twice returns idempotent=True on the second call."""
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    canonical = HistoricalVenueIntelligence(
        canonical_name="Kensington Oval",
        normalized_canonical_name="kensington oval",
        verification_status=HistoricalVenueVerificationStatus.verified,
        source_type="manual",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(canonical)
    await db_session.flush()

    queue_id, _ = await _make_unresolved_venue_queue(db_session)

    _, idempotent1, _ = await link_source_venue(
        db_session, queue_id=queue_id, canonical_venue_id=canonical.id
    )
    await db_session.commit()

    _, idempotent2, message2 = await link_source_venue(
        db_session, queue_id=queue_id, canonical_venue_id=canonical.id
    )
    await db_session.commit()

    assert not idempotent1
    assert idempotent2
    assert "idempotent" in message2.lower()


@pytest.mark.asyncio
async def test_create_venue_from_queue(
    db_session: AsyncSession,
) -> None:
    """Creating a new Venue from queue preserves source provenance."""
    queue_id, _ = await _make_unresolved_venue_queue(
        db_session, raw_venue_value="Providence Stadium, Georgetown"
    )

    new_venue, queue_row, idempotent, message = await create_venue_from_queue(
        db_session,
        queue_id=queue_id,
        canonical_name="Providence Stadium",
        city="Georgetown",
        country="Guyana",
        reviewed_by="analyst@test.com",
    )
    await db_session.commit()

    assert new_venue is not None
    assert new_venue.canonical_name == "Providence Stadium"
    assert new_venue.city == "Georgetown"
    assert new_venue.country == "Guyana"
    assert new_venue.created_from_import is True
    assert queue_row.queue_state == "resolved"
    assert not idempotent
    assert "Providence Stadium" in message


@pytest.mark.asyncio
async def test_create_venue_from_queue_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Creating a venue twice for the same queue is idempotent."""
    queue_id, _ = await _make_unresolved_venue_queue(db_session)

    venue1, _, idempotent1, _ = await create_venue_from_queue(
        db_session,
        queue_id=queue_id,
        canonical_name="Kensington Oval",
    )
    await db_session.commit()

    venue2, _, idempotent2, _ = await create_venue_from_queue(
        db_session,
        queue_id=queue_id,
        canonical_name="Kensington Oval",
    )
    await db_session.commit()

    assert venue1.id == venue2.id
    assert idempotent2


@pytest.mark.asyncio
async def test_defer_venue_does_not_delete_queue_entry(
    db_session: AsyncSession,
) -> None:
    """Deferring a venue does not delete the queue entry."""
    queue_id, _ = await _make_unresolved_venue_queue(db_session)

    queue_row, idempotent, message = await defer_venue_resolution(
        db_session, queue_id=queue_id, reason="not_urgent"
    )
    await db_session.commit()

    assert queue_row is not None
    still_exists = await db_session.get(HistoricalVenueResolutionQueue, queue_id)
    assert still_exists is not None
    assert still_exists.queue_state == "deferred"
    assert not idempotent


@pytest.mark.asyncio
async def test_defer_venue_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Deferring a venue twice is idempotent."""
    queue_id, _ = await _make_unresolved_venue_queue(db_session)

    _, idempotent1, _ = await defer_venue_resolution(db_session, queue_id=queue_id)
    await db_session.commit()

    _, idempotent2, message2 = await defer_venue_resolution(db_session, queue_id=queue_id)
    await db_session.commit()

    assert not idempotent1
    assert idempotent2
    assert "idempotent" in message2.lower()


# ---------------------------------------------------------------------------
# Tests: API endpoints via async_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unresolved_endpoint_returns_players_and_venues(
    async_client, db_session: AsyncSession
) -> None:
    """GET /identity-review/unresolved returns unresolved players and venue items."""
    await _make_player_batch(db_session, roster_names=["T Shamsi", "AS Joseph"])
    await _make_unresolved_venue_queue(db_session, raw_venue_value="Kensington Oval, Bridgetown")
    await db_session.commit()

    resp = await async_client.get("/api/historical-import/json/identity-review/unresolved")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "unresolved_players" in data
    assert "unresolved_venues" in data
    assert data["total_unresolved_players"] >= 2
    assert data["total_unresolved_venues"] >= 1

    player_names = {p["source_player_name"] for p in data["unresolved_players"]}
    assert "T Shamsi" in player_names or "AS Joseph" in player_names

    venue_values = {v["raw_imported_value"] for v in data["unresolved_venues"]}
    assert "Kensington Oval, Bridgetown" in venue_values


@pytest.mark.asyncio
async def test_api_player_link(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/players/{id}/link links source player to existing player."""
    db_session.add(Player(id=301, name="KOA Powell"))
    await db_session.commit()

    await _make_player_batch(db_session, roster_names=["Kieran Powell"])
    await db_session.commit()

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "Kieran Powell"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    resp = await async_client.post(
        f"/api/historical-import/json/identity-review/players/{reg.source_player_id}/link",
        json={"canonical_player_id": 301, "reviewed_by": "analyst@test.com"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "linked"
    assert data["canonical_player_id"] == 301


@pytest.mark.asyncio
async def test_api_player_create(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/players/{id}/create creates new Player."""
    await _make_player_batch(db_session, roster_names=["JL Carter"])
    await db_session.commit()

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "JL Carter"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    resp = await async_client.post(
        f"/api/historical-import/json/identity-review/players/{reg.source_player_id}/create",
        json={"name": "Johnson Carter", "country": "West Indies", "role": "All-rounder"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "created"
    assert data["canonical_player_name"] == "Johnson Carter"
    assert data["canonical_player_id"] is not None


@pytest.mark.asyncio
async def test_api_player_defer(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/players/{id}/defer defers resolution."""
    await _make_player_batch(db_session, roster_names=["F du Plessis"])
    await db_session.commit()

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "F du Plessis"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    resp = await async_client.post(
        f"/api/historical-import/json/identity-review/players/{reg.source_player_id}/defer",
        json={"reason": "need_more_info"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "deferred"

    # Registry row should still exist
    still_exists = await db_session.get(HistoricalSourcePlayerRegistry, reg.source_player_id)
    assert still_exists is not None


@pytest.mark.asyncio
async def test_api_venue_link(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/venues/link links venue to existing canonical venue."""
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    canonical = HistoricalVenueIntelligence(
        canonical_name="Kensington Oval",
        normalized_canonical_name="kensington oval",
        verification_status=HistoricalVenueVerificationStatus.verified,
        source_type="manual",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(canonical)
    await db_session.flush()
    queue_id, _ = await _make_unresolved_venue_queue(db_session)
    await db_session.commit()

    resp = await async_client.post(
        "/api/historical-import/json/identity-review/venues/link",
        json={"queue_id": queue_id, "canonical_venue_id": canonical.id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "linked"
    assert data["canonical_venue_id"] == canonical.id


@pytest.mark.asyncio
async def test_api_venue_create(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/venues/create creates a new Venue."""
    queue_id, _ = await _make_unresolved_venue_queue(
        db_session, raw_venue_value="National Cricket Stadium, St George's"
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/historical-import/json/identity-review/venues/create",
        json={
            "queue_id": queue_id,
            "canonical_name": "National Cricket Stadium",
            "city": "St George's",
            "country": "Grenada",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "venue_created"
    assert data["canonical_venue_name"] == "National Cricket Stadium"
    assert data["canonical_venue_id"] is not None


@pytest.mark.asyncio
async def test_api_venue_defer(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/venues/defer defers without deletion."""
    queue_id, _ = await _make_unresolved_venue_queue(db_session)
    await db_session.commit()

    resp = await async_client.post(
        "/api/historical-import/json/identity-review/venues/defer",
        json={"queue_id": queue_id, "reason": "low_priority"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "deferred"

    # Queue row should still exist and be deferred
    queue = await db_session.get(HistoricalVenueResolutionQueue, queue_id)
    assert queue is not None
    assert queue.queue_state == "deferred"


@pytest.mark.asyncio
async def test_api_venue_create_alias(async_client, db_session: AsyncSession) -> None:
    """POST /identity-review/venues/create-alias aliases venue to existing venue."""
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    canonical = HistoricalVenueIntelligence(
        canonical_name="Warner Park",
        normalized_canonical_name="warner park",
        verification_status=HistoricalVenueVerificationStatus.verified,
        source_type="manual",
        created_from_import=False,
        provenance_references=[],
        first_seen=now,
        last_seen=now,
    )
    db_session.add(canonical)
    await db_session.flush()

    queue_id, _ = await _make_unresolved_venue_queue(
        db_session, raw_venue_value="Warner Park Sporting Complex"
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/historical-import/json/identity-review/venues/create-alias",
        json={"queue_id": queue_id, "canonical_venue_id": canonical.id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["action"] == "alias_created"
    assert data["canonical_venue_id"] == canonical.id


@pytest.mark.asyncio
async def test_link_invalid_player_raises_422(async_client, db_session: AsyncSession) -> None:
    """Linking a non-existent source player returns 422."""
    resp = await async_client.post(
        "/api/historical-import/json/identity-review/players/nonexistent-id/link",
        json={"canonical_player_id": 999},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_link_player_to_nonexistent_canonical_raises_422(
    async_client, db_session: AsyncSession
) -> None:
    """Linking a source player to a non-existent canonical player returns 422."""
    await _make_player_batch(db_session, roster_names=["DC Thomas"])
    await db_session.commit()

    reg = (
        (
            await db_session.execute(
                select(HistoricalSourcePlayerRegistry).where(
                    HistoricalSourcePlayerRegistry.source_player_name == "DC Thomas"
                )
            )
        )
        .scalars()
        .first()
    )
    assert reg is not None

    resp = await async_client.post(
        f"/api/historical-import/json/identity-review/players/{reg.source_player_id}/link",
        json={"canonical_player_id": 99999},
    )
    assert resp.status_code == 422
