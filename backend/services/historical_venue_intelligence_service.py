from __future__ import annotations

import datetime as dt
import re
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import (
    HistoricalCompetitionVenueUsage,
    HistoricalVenueAlias,
    HistoricalVenueIntelligence,
    HistoricalVenueResolutionDecision,
    HistoricalVenueResolutionQueue,
    HistoricalVenueResolutionState,
    HistoricalVenueVerificationStatus,
)

UTC = getattr(dt, "UTC", dt.timezone.utc)
_VENUE_STRIP_RE = re.compile(r"[^a-z0-9\s]")
_MULTISPACE_RE = re.compile(r"\s+")
_VENUE_KEYWORDS = frozenset(
    {"oval", "stadium", "ground", "park", "arena", "field", "centre", "center", "cricket"}
)


def normalize_venue_name(name: str | None) -> str:
    value = (name or "").strip().lower()
    value = _VENUE_STRIP_RE.sub(" ", value)
    return _MULTISPACE_RE.sub(" ", value).strip()


def _append_unique(sequence: list[Any], item: Any) -> list[Any]:
    if item not in sequence:
        sequence.append(item)
    return sequence


def _append_unique_dict_by_keys(
    rows: list[dict[str, Any]],
    candidate: dict[str, Any],
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    for row in rows:
        if not isinstance(row, dict):
            continue
        if all(row.get(field) == candidate.get(field) for field in key_fields):
            return rows
    rows.append(candidate)
    return rows


def _has_specific_venue_tokens(normalized_raw: str) -> bool:
    tokens = {token for token in normalized_raw.split(" ") if token}
    return bool(tokens.intersection(_VENUE_KEYWORDS)) or len(tokens) >= 3


async def _upsert_alias(
    db: AsyncSession,
    *,
    venue_id: str,
    alias_name: str,
    source_schema: str | None,
    source_system: str | None,
    confidence_score: float | None,
    provenance_reference: dict[str, Any],
    now: dt.datetime,
) -> None:
    normalized_alias = normalize_venue_name(alias_name)
    if not normalized_alias:
        return
    existing = (
        (
            await db.execute(
                select(HistoricalVenueAlias).where(
                    HistoricalVenueAlias.venue_id == venue_id,
                    HistoricalVenueAlias.normalized_alias == normalized_alias,
                )
            )
        )
        .scalars()
        .first()
    )
    if existing is None:
        db.add(
            HistoricalVenueAlias(
                venue_id=venue_id,
                alias_name=alias_name.strip(),
                normalized_alias=normalized_alias,
                source_schema=source_schema,
                source_system=source_system,
                confidence_score=confidence_score,
                provenance_reference=provenance_reference,
                first_seen=now,
                last_seen=now,
            )
        )
        return
    existing.last_seen = now
    if source_schema and not existing.source_schema:
        existing.source_schema = source_schema
    if source_system and not existing.source_system:
        existing.source_system = source_system
    if confidence_score is not None:
        existing.confidence_score = confidence_score
    existing.provenance_reference = {
        **(existing.provenance_reference or {}),
        **provenance_reference,
    }
    db.add(existing)


async def _upsert_usage(
    db: AsyncSession,
    *,
    venue_id: str,
    competition_name: str | None,
    season: str | None,
    source_schema: str | None,
    source_system: str | None,
    game_id: str | None,
    provenance_reference: dict[str, Any],
) -> None:
    usage = (
        (
            await db.execute(
                select(HistoricalCompetitionVenueUsage).where(
                    HistoricalCompetitionVenueUsage.canonical_venue_id == venue_id,
                    HistoricalCompetitionVenueUsage.competition_name == competition_name,
                    HistoricalCompetitionVenueUsage.season == season,
                    HistoricalCompetitionVenueUsage.source_schema == source_schema,
                    HistoricalCompetitionVenueUsage.source_system == source_system,
                )
            )
        )
        .scalars()
        .first()
    )
    if usage is None:
        usage = HistoricalCompetitionVenueUsage(
            canonical_venue_id=venue_id,
            competition_name=competition_name,
            season=season,
            source_schema=source_schema,
            source_system=source_system,
            matches_count=1,
            game_references=[game_id] if game_id else [],
            provenance_references=[provenance_reference],
        )
        db.add(usage)
        return
    usage.matches_count = int(usage.matches_count or 0) + 1
    usage.game_references = (
        _append_unique(list(usage.game_references or []), game_id)
        if game_id
        else list(usage.game_references or [])
    )
    usage.provenance_references = _append_unique_dict_by_keys(
        list(usage.provenance_references or []),
        provenance_reference,
        ("batch_id", "game_id", "source_hash_sha256"),
    )
    db.add(usage)


async def _upsert_queue(
    db: AsyncSession,
    *,
    decision_id: str,
    raw_imported_value: str,
    normalized_raw_value: str,
    source_schema: str | None,
    source_system: str | None,
    reason: str,
    provenance_reference: dict[str, Any],
    now: dt.datetime,
) -> None:
    queue_row = (
        (
            await db.execute(
                select(HistoricalVenueResolutionQueue).where(
                    HistoricalVenueResolutionQueue.normalized_raw_value == normalized_raw_value,
                    HistoricalVenueResolutionQueue.source_schema == source_schema,
                    HistoricalVenueResolutionQueue.source_system == source_system,
                    HistoricalVenueResolutionQueue.reason == reason,
                )
            )
        )
        .scalars()
        .first()
    )
    if queue_row is None:
        queue_row = HistoricalVenueResolutionQueue(
            decision_id=decision_id,
            raw_imported_value=raw_imported_value,
            normalized_raw_value=normalized_raw_value,
            source_schema=source_schema,
            source_system=source_system,
            queue_state="pending",
            reason=reason,
            review_required=True,
            provenance_references=[provenance_reference],
            last_seen=now,
        )
        db.add(queue_row)
        return
    queue_row.last_seen = now
    queue_row.queue_state = "pending"
    queue_row.review_required = True
    queue_row.decision_id = decision_id
    queue_row.provenance_references = _append_unique_dict_by_keys(
        list(queue_row.provenance_references or []),
        provenance_reference,
        ("batch_id", "game_id", "source_hash_sha256"),
    )
    db.add(queue_row)


async def _mark_queue_resolved(
    db: AsyncSession,
    *,
    normalized_raw_value: str,
    source_schema: str | None,
    source_system: str | None,
    now: dt.datetime,
) -> None:
    pending_rows = (
        (
            await db.execute(
                select(HistoricalVenueResolutionQueue).where(
                    HistoricalVenueResolutionQueue.normalized_raw_value == normalized_raw_value,
                    HistoricalVenueResolutionQueue.source_schema == source_schema,
                    HistoricalVenueResolutionQueue.source_system == source_system,
                    HistoricalVenueResolutionQueue.queue_state == "pending",
                )
            )
        )
        .scalars()
        .all()
    )
    for row in pending_rows:
        row.queue_state = "resolved"
        row.review_required = False
        row.resolved_at = now
        row.last_seen = now
        db.add(row)


async def resolve_historical_venue(
    db: AsyncSession,
    *,
    batch_id: str,
    game_id: str,
    source_schema: str | None,
    source_system: str | None,
    source_provenance: dict[str, Any],
    competition_context: dict[str, Any],
    match_date: str | None,
    raw_venue_value: str | None,
    venue_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = dt.datetime.now(UTC)
    raw_value = (raw_venue_value or "").strip()
    normalized_raw = normalize_venue_name(raw_value)
    canonical_venue: HistoricalVenueIntelligence | None = None
    matched_by: str | None = None
    confidence_score: float | None = None
    unresolved_reason: str | None = None
    review_required = False
    resolution_state = HistoricalVenueResolutionState.unresolved

    if not raw_value or not normalized_raw:
        unresolved_reason = "empty_raw_venue"
        review_required = True
    else:
        exact_candidates = (
            (
                await db.execute(
                    select(HistoricalVenueIntelligence).where(
                        HistoricalVenueIntelligence.canonical_name.ilike(raw_value)
                    )
                )
            )
            .scalars()
            .all()
        )
        if len(exact_candidates) == 1:
            canonical_venue = exact_candidates[0]
            matched_by = "exact_match"
            confidence_score = 1.0
        elif len(exact_candidates) > 1:
            unresolved_reason = "multiple_exact_candidates"
            review_required = True
        else:
            normalized_candidates = (
                (
                    await db.execute(
                        select(HistoricalVenueIntelligence).where(
                            (
                                HistoricalVenueIntelligence.normalized_canonical_name
                                == normalized_raw
                            )
                            | (HistoricalVenueIntelligence.normalized_short_name == normalized_raw)
                        )
                    )
                )
                .scalars()
                .all()
            )
            if len(normalized_candidates) == 1:
                canonical_venue = normalized_candidates[0]
                matched_by = "normalized_match"
                confidence_score = 0.99
            elif len(normalized_candidates) > 1:
                unresolved_reason = "multiple_normalized_candidates"
                review_required = True
            else:
                alias_rows = (
                    (
                        await db.execute(
                            select(HistoricalVenueAlias).where(
                                HistoricalVenueAlias.normalized_alias == normalized_raw
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                alias_venue_ids = {row.venue_id for row in alias_rows}
                if len(alias_venue_ids) == 1:
                    canonical_venue = await db.get(
                        HistoricalVenueIntelligence, next(iter(alias_venue_ids))
                    )
                    matched_by = "alias_match"
                    confidence_score = 0.98
                elif len(alias_venue_ids) > 1:
                    unresolved_reason = "multiple_alias_candidates"
                    review_required = True
                else:
                    venues = (await db.execute(select(HistoricalVenueIntelligence))).scalars().all()
                    fuzzy_candidates: list[tuple[float, HistoricalVenueIntelligence]] = []
                    for venue in venues:
                        candidate_names = {
                            venue.canonical_name,
                            venue.short_name,
                            *(venue.alternate_names or []),
                        }
                        for alias_row in (
                            await db.execute(
                                select(HistoricalVenueAlias).where(
                                    HistoricalVenueAlias.venue_id == venue.id
                                )
                            )
                        ).scalars():
                            candidate_names.add(alias_row.alias_name)
                        best_for_venue = 0.0
                        for candidate_name in candidate_names:
                            candidate_norm = normalize_venue_name(candidate_name)
                            if not candidate_norm:
                                continue
                            score = SequenceMatcher(None, normalized_raw, candidate_norm).ratio()
                            best_for_venue = max(best_for_venue, score)
                        if best_for_venue > 0:
                            fuzzy_candidates.append((best_for_venue, venue))
                    fuzzy_candidates.sort(key=lambda item: item[0], reverse=True)
                    if fuzzy_candidates:
                        best_score, best_venue = fuzzy_candidates[0]
                        second_score = fuzzy_candidates[1][0] if len(fuzzy_candidates) > 1 else 0.0
                        if best_score >= 0.95 and (best_score - second_score) >= 0.03:
                            canonical_venue = best_venue
                            matched_by = "controlled_fuzzy_match"
                            confidence_score = round(best_score, 2)
                        elif best_score >= 0.85:
                            matched_by = "controlled_fuzzy_match"
                            confidence_score = round(best_score, 2)
                            unresolved_reason = "low_confidence_fuzzy_match"
                            review_required = True
                        else:
                            unresolved_reason = "deterministic_rules_no_match"
                    elif _has_specific_venue_tokens(normalized_raw):
                        canonical_venue = HistoricalVenueIntelligence(
                            canonical_name=raw_value,
                            normalized_canonical_name=normalized_raw,
                            short_name=None,
                            normalized_short_name=None,
                            alternate_names=[],
                            city=str((venue_context or {}).get("city") or "").strip() or None,
                            region=str((venue_context or {}).get("region") or "").strip() or None,
                            country=str((venue_context or {}).get("country") or "").strip() or None,
                            latitude=None,
                            longitude=None,
                            timezone=None,
                            venue_type=None,
                            indoor_outdoor=None,
                            verification_status=HistoricalVenueVerificationStatus.unverified,
                            confidence_score=0.9,
                            source_type="historical_import",
                            created_from_import=True,
                            notes="Auto-created from historical import venue backfill.",
                            provenance_references=[
                                {
                                    "batch_id": batch_id,
                                    "game_id": game_id,
                                    "source_hash_sha256": source_provenance.get(
                                        "source_hash_sha256"
                                    ),
                                    "source_schema": source_schema,
                                    "source_system": source_system,
                                    "match_date": match_date,
                                }
                            ],
                            first_seen=now,
                            last_seen=now,
                        )
                        db.add(canonical_venue)
                        await db.flush()
                        matched_by = "created_from_import"
                        confidence_score = 0.9
                    else:
                        unresolved_reason = "deterministic_rules_no_match"
                        review_required = True

    if canonical_venue is not None:
        resolution_state = HistoricalVenueResolutionState.resolved
        review_required = review_required or (
            confidence_score is not None and confidence_score < 0.95
        )
        canonical_venue.last_seen = now
        canonical_venue.provenance_references = _append_unique_dict_by_keys(
            list(canonical_venue.provenance_references or []),
            {
                "batch_id": batch_id,
                "game_id": game_id,
                "source_hash_sha256": source_provenance.get("source_hash_sha256"),
                "source_schema": source_schema,
                "source_system": source_system,
            },
            ("batch_id", "game_id", "source_hash_sha256"),
        )
        if (
            review_required
            and canonical_venue.verification_status == HistoricalVenueVerificationStatus.unverified
        ):
            canonical_venue.verification_status = HistoricalVenueVerificationStatus.review_required
        db.add(canonical_venue)
    else:
        review_required = True

    provenance_reference = {
        "batch_id": batch_id,
        "game_id": game_id,
        "source_hash_sha256": source_provenance.get("source_hash_sha256"),
        "source_schema": source_schema,
        "source_system": source_system,
        "match_date": match_date,
    }
    resolution_snapshot = {
        "raw_imported_value": raw_value,
        "normalized_raw_value": normalized_raw,
        "canonical_venue_id": canonical_venue.id if canonical_venue else None,
        "canonical_name": canonical_venue.canonical_name if canonical_venue else None,
        "matched_by": matched_by,
        "confidence_score": confidence_score,
        "resolution_state": resolution_state.value,
        "unresolved_reason": unresolved_reason,
        "review_required": review_required,
        "venue_context": venue_context or {},
    }

    decision = (
        (
            await db.execute(
                select(HistoricalVenueResolutionDecision).where(
                    HistoricalVenueResolutionDecision.game_id == game_id,
                    HistoricalVenueResolutionDecision.normalized_raw_value == normalized_raw,
                    HistoricalVenueResolutionDecision.source_schema == source_schema,
                    HistoricalVenueResolutionDecision.source_system == source_system,
                )
            )
        )
        .scalars()
        .first()
    )
    if decision is None:
        decision = HistoricalVenueResolutionDecision(
            batch_id=batch_id,
            game_id=game_id,
            raw_imported_value=raw_value or "unknown",
            normalized_raw_value=normalized_raw or "unknown",
            canonical_venue_id=canonical_venue.id if canonical_venue else None,
            resolution_state=(
                HistoricalVenueResolutionState.review_required
                if review_required
                else resolution_state
            ),
            matched_by=matched_by,
            confidence_score=confidence_score,
            unresolved_reason=unresolved_reason,
            source_schema=source_schema,
            source_system=source_system,
            competition_name=str(competition_context.get("competition_name") or "").strip() or None,
            season=str(competition_context.get("season") or "").strip() or None,
            review_required=review_required,
            provenance_references=[provenance_reference],
            resolution_snapshot=resolution_snapshot,
        )
        db.add(decision)
        await db.flush()
    else:
        decision.canonical_venue_id = canonical_venue.id if canonical_venue else None
        decision.resolution_state = (
            HistoricalVenueResolutionState.review_required if review_required else resolution_state
        )
        decision.matched_by = matched_by
        decision.confidence_score = confidence_score
        decision.unresolved_reason = unresolved_reason
        decision.review_required = review_required
        decision.provenance_references = _append_unique_dict_by_keys(
            list(decision.provenance_references or []),
            provenance_reference,
            ("batch_id", "game_id", "source_hash_sha256"),
        )
        decision.resolution_snapshot = resolution_snapshot
        db.add(decision)

    if canonical_venue is not None and raw_value:
        await _upsert_alias(
            db,
            venue_id=canonical_venue.id,
            alias_name=raw_value,
            source_schema=source_schema,
            source_system=source_system,
            confidence_score=confidence_score,
            provenance_reference=provenance_reference,
            now=now,
        )
        await _upsert_usage(
            db,
            venue_id=canonical_venue.id,
            competition_name=str(competition_context.get("competition_name") or "").strip() or None,
            season=str(competition_context.get("season") or "").strip() or None,
            source_schema=source_schema,
            source_system=source_system,
            game_id=game_id,
            provenance_reference=provenance_reference,
        )
        await _mark_queue_resolved(
            db,
            normalized_raw_value=normalized_raw,
            source_schema=source_schema,
            source_system=source_system,
            now=now,
        )
    else:
        await _upsert_queue(
            db,
            decision_id=decision.id,
            raw_imported_value=raw_value or "unknown",
            normalized_raw_value=normalized_raw or "unknown",
            source_schema=source_schema,
            source_system=source_system,
            reason=unresolved_reason or "unresolved",
            provenance_reference=provenance_reference,
            now=now,
        )

    return {
        **resolution_snapshot,
        "decision_id": decision.id,
    }


async def list_venue_intelligence(
    db: AsyncSession, *, limit: int = 100
) -> list[HistoricalVenueIntelligence]:
    return (
        (
            await db.execute(
                select(HistoricalVenueIntelligence)
                .order_by(HistoricalVenueIntelligence.updated_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def list_unresolved_venues(
    db: AsyncSession, *, limit: int = 100
) -> list[HistoricalVenueResolutionQueue]:
    return (
        (
            await db.execute(
                select(HistoricalVenueResolutionQueue)
                .where(HistoricalVenueResolutionQueue.queue_state == "pending")
                .order_by(HistoricalVenueResolutionQueue.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def list_venue_resolution_snapshots(
    db: AsyncSession,
    *,
    limit: int = 100,
    batch_id: str | None = None,
    game_id: str | None = None,
) -> list[HistoricalVenueResolutionDecision]:
    stmt = select(HistoricalVenueResolutionDecision).order_by(
        HistoricalVenueResolutionDecision.created_at.desc()
    )
    if batch_id:
        stmt = stmt.where(HistoricalVenueResolutionDecision.batch_id == batch_id)
    if game_id:
        stmt = stmt.where(HistoricalVenueResolutionDecision.game_id == game_id)
    return (await db.execute(stmt.limit(limit))).scalars().all()


async def list_venue_usage_stats(
    db: AsyncSession,
    *,
    limit: int = 100,
    competition_name: str | None = None,
    season: str | None = None,
) -> list[HistoricalCompetitionVenueUsage]:
    stmt = select(HistoricalCompetitionVenueUsage).order_by(
        HistoricalCompetitionVenueUsage.matches_count.desc(),
        HistoricalCompetitionVenueUsage.updated_at.desc(),
    )
    if competition_name:
        stmt = stmt.where(HistoricalCompetitionVenueUsage.competition_name == competition_name)
    if season:
        stmt = stmt.where(HistoricalCompetitionVenueUsage.season == season)
    return (await db.execute(stmt.limit(limit))).scalars().all()


async def list_venue_aliases(
    db: AsyncSession,
    *,
    limit: int = 100,
    venue_id: str | None = None,
) -> list[HistoricalVenueAlias]:
    stmt = select(HistoricalVenueAlias).order_by(HistoricalVenueAlias.updated_at.desc())
    if venue_id:
        stmt = stmt.where(HistoricalVenueAlias.venue_id == venue_id)
    return (await db.execute(stmt.limit(limit))).scalars().all()
