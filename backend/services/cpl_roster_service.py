"""Phase 10T — CPL Current-Season Roster service.

Provides controlled add/update/list operations for:
- CplCurrentSeasonTeam records
- CplCurrentSeasonPlayer records
- Roster import preview + apply (CSV / JSON rows)

Key behaviors:
- Normalized player/team names prevent duplicates (case-insensitive + diacritics)
- Returning-player detection: check prior-season entries in the same competition
- Import preview shows new / matched / duplicate / returning without mutating DB
- Import apply is idempotent for already-existing records
- No historical import data is ever mutated by this service
"""

from __future__ import annotations

import unicodedata
import re
import difflib

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.cpl_roster import (
    CplPlayerCreate,
    CplPlayerListResponse,
    CplPlayerResponse,
    CplPlayerUpdate,
    CplTeamCreate,
    CplTeamListResponse,
    CplTeamResponse,
    CplTeamUpdate,
    RosterImportApplyRequest,
    RosterImportApplyResponse,
    RosterImportPreviewPlayer,
    RosterImportPreviewResponse,
    RosterImportPreviewTeam,
    RosterImportRow,
)
from backend.sql_app.models import (
    CplCurrentSeasonPlayer,
    CplCurrentSeasonTeam,
    CplRosterPlayerStatus,
    CplRosterTeamStatus,
)

VALID_COMPETITION_CODES = {
    "CPL_MEN",
    "WCPL",
    "IPL",
    "BBL",
    "PSL",
    "WPL",
    "THE_HUNDRED",
    "INTERNATIONAL",
    "DOMESTIC",
}
KNOWN_ROLES = {"batsman", "bowler", "all-rounder", "wicketkeeper", "wicketkeeper-batsman"}


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """Normalize a player or team name for duplicate detection.

    - Lowercase
    - Strip leading/trailing whitespace
    - Remove diacritics (NFD decomposition → drop combining chars)
    - Collapse internal whitespace
    """
    nfd = unicodedata.normalize("NFD", name)
    ascii_approx = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", ascii_approx.lower().strip())


def _is_valid_competition_code(competition_code: str) -> bool:
    return competition_code.strip().upper() in VALID_COMPETITION_CODES


def _is_valid_season(season: str) -> bool:
    s = season.strip()
    return bool(re.fullmatch(r"\d{4}", s))


def _find_similar_name(normalized_name: str, existing_names: list[str]) -> str | None:
    if not existing_names:
        return None
    best = None
    best_ratio = 0.0
    for candidate in existing_names:
        if candidate == normalized_name:
            continue
        ratio = difflib.SequenceMatcher(a=normalized_name, b=candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = candidate
    if best_ratio >= 0.88:
        return best
    return None


# ---------------------------------------------------------------------------
# Team operations
# ---------------------------------------------------------------------------


async def create_team(
    db: AsyncSession,
    data: CplTeamCreate,
) -> CplCurrentSeasonTeam:
    """Register a new team. Raises ValueError on duplicate."""
    if not _is_valid_competition_code(data.competition_code):
        raise ValueError(f"Invalid competition code '{data.competition_code}'.")
    if not _is_valid_season(data.season):
        raise ValueError(f"Invalid season '{data.season}'. Expected YYYY format.")
    normalized = _normalize_name(data.team_name)
    existing = await _get_team_by_normalized(db, data.competition_code, data.season, normalized)
    if existing:
        raise ValueError(
            f"Team '{data.team_name}' already exists for " f"{data.competition_code} {data.season}."
        )
    team = CplCurrentSeasonTeam(
        competition_code=data.competition_code,
        season=data.season,
        team_name=data.team_name,
        normalized_team_name=normalized,
        team_short_name=data.team_short_name,
        country=data.country,
        coach_name=data.coach_name,
        captain_name=data.captain_name,
        status=CplRosterTeamStatus(data.status),
        home_ground=data.home_ground,
        source_note=data.source_note,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


async def list_teams(
    db: AsyncSession,
    competition_code: str = "CPL_MEN",
    season: str | None = None,
    search: str | None = None,
    status: str | None = None,
) -> CplTeamListResponse:
    stmt = select(CplCurrentSeasonTeam).where(
        CplCurrentSeasonTeam.competition_code == competition_code
    )
    if season:
        stmt = stmt.where(CplCurrentSeasonTeam.season == season)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(CplCurrentSeasonTeam.team_name.ilike(like))
    if status:
        stmt = stmt.where(CplCurrentSeasonTeam.status == CplRosterTeamStatus(status))
    stmt = stmt.order_by(CplCurrentSeasonTeam.team_name)
    result = await db.execute(stmt)
    teams = list(result.scalars().all())
    return CplTeamListResponse(
        teams=[CplTeamResponse.model_validate(t) for t in teams],
        total=len(teams),
    )


async def update_team(
    db: AsyncSession,
    team_id: str,
    data: CplTeamUpdate,
) -> CplCurrentSeasonTeam | None:
    result = await db.execute(
        select(CplCurrentSeasonTeam).where(CplCurrentSeasonTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if team is None:
        return None
    if data.team_name is not None:
        team.team_name = data.team_name
        team.normalized_team_name = _normalize_name(data.team_name)
    if data.team_short_name is not None:
        team.team_short_name = data.team_short_name
    if data.country is not None:
        team.country = data.country
    if data.coach_name is not None:
        team.coach_name = data.coach_name
    if data.captain_name is not None:
        team.captain_name = data.captain_name
    if data.status is not None:
        team.status = CplRosterTeamStatus(data.status)
    if data.home_ground is not None:
        team.home_ground = data.home_ground
    if data.source_note is not None:
        team.source_note = data.source_note
    await db.commit()
    await db.refresh(team)
    return team


async def delete_team(db: AsyncSession, team_id: str) -> bool:
    result = await db.execute(
        select(CplCurrentSeasonTeam).where(CplCurrentSeasonTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if team is None:
        return False
    in_use = await db.execute(
        select(CplCurrentSeasonPlayer.id)
        .where(
            CplCurrentSeasonPlayer.competition_code == team.competition_code,
            CplCurrentSeasonPlayer.season == team.season,
            CplCurrentSeasonPlayer.team_name == team.team_name,
        )
        .limit(1)
    )
    if in_use.scalar_one_or_none() is not None:
        raise ValueError("Team cannot be deleted because players are still assigned to it.")
    await db.delete(team)
    await db.commit()
    return True


async def _get_team_by_normalized(
    db: AsyncSession,
    competition_code: str,
    season: str,
    normalized: str,
) -> CplCurrentSeasonTeam | None:
    result = await db.execute(
        select(CplCurrentSeasonTeam).where(
            CplCurrentSeasonTeam.competition_code == competition_code,
            CplCurrentSeasonTeam.season == season,
            CplCurrentSeasonTeam.normalized_team_name == normalized,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Player operations
# ---------------------------------------------------------------------------


async def _detect_returning(
    db: AsyncSession,
    competition_code: str,
    season: str,
    normalized_name: str,
) -> tuple[bool, str | None, str | None]:
    """Check if this player appeared in any prior season of the same competition.

    Returns (is_returning, prior_season_label).
    """
    result = await db.execute(
        select(CplCurrentSeasonPlayer)
        .where(
            CplCurrentSeasonPlayer.competition_code == competition_code,
            CplCurrentSeasonPlayer.normalized_player_name == normalized_name,
            CplCurrentSeasonPlayer.season != season,
        )
        .order_by(CplCurrentSeasonPlayer.season.desc())
        .limit(1)
    )
    prior = result.scalar_one_or_none()
    if prior:
        return True, prior.season, prior.team_name
    return False, None, None


async def delete_player(db: AsyncSession, player_id: str) -> bool:
    result = await db.execute(
        select(CplCurrentSeasonPlayer).where(CplCurrentSeasonPlayer.id == player_id)
    )
    player = result.scalar_one_or_none()
    if player is None:
        return False
    if player.status == CplRosterPlayerStatus.active:
        raise ValueError("Active players cannot be deleted. Disable or retire first.")
    await db.delete(player)
    await db.commit()
    return True


async def retire_player(db: AsyncSession, player_id: str) -> CplCurrentSeasonPlayer | None:
    result = await db.execute(
        select(CplCurrentSeasonPlayer).where(CplCurrentSeasonPlayer.id == player_id)
    )
    player = result.scalar_one_or_none()
    if player is None:
        return None
    player.status = CplRosterPlayerStatus.retired
    await db.commit()
    await db.refresh(player)
    return player


async def disable_player(db: AsyncSession, player_id: str) -> CplCurrentSeasonPlayer | None:
    result = await db.execute(
        select(CplCurrentSeasonPlayer).where(CplCurrentSeasonPlayer.id == player_id)
    )
    player = result.scalar_one_or_none()
    if player is None:
        return None
    player.status = CplRosterPlayerStatus.disabled
    await db.commit()
    await db.refresh(player)
    return player


async def create_player(
    db: AsyncSession,
    data: CplPlayerCreate,
) -> CplCurrentSeasonPlayer:
    """Register a new player. Raises ValueError on duplicate."""
    if not _is_valid_competition_code(data.competition_code):
        raise ValueError(f"Invalid competition code '{data.competition_code}'.")
    if not _is_valid_season(data.season):
        raise ValueError(f"Invalid season '{data.season}'. Expected YYYY format.")
    normalized = _normalize_name(data.player_name)
    existing = await _get_player_by_normalized(db, data.competition_code, data.season, normalized)
    if existing:
        raise ValueError(
            f"Player '{data.player_name}' already exists for "
            f"{data.competition_code} {data.season}."
        )
    is_returning, prior_season, _prior_team_name = await _detect_returning(
        db, data.competition_code, data.season, normalized
    )
    player = CplCurrentSeasonPlayer(
        competition_code=data.competition_code,
        season=data.season,
        player_name=data.player_name,
        normalized_player_name=normalized,
        display_name=data.display_name,
        aliases=data.aliases,
        team_name=data.team_name,
        role=data.role,
        nationality=data.nationality,
        date_of_birth=data.date_of_birth,
        batting_style=data.batting_style,
        bowling_style=data.bowling_style,
        status=CplRosterPlayerStatus(data.status),
        is_returning=is_returning,
        prior_season=prior_season,
        source_note=data.source_note,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def update_player(
    db: AsyncSession,
    player_id: str,
    data: CplPlayerUpdate,
) -> CplCurrentSeasonPlayer | None:
    result = await db.execute(
        select(CplCurrentSeasonPlayer).where(CplCurrentSeasonPlayer.id == player_id)
    )
    player = result.scalar_one_or_none()
    if player is None:
        return None
    if data.display_name is not None:
        player.display_name = data.display_name
    if data.aliases is not None:
        player.aliases = data.aliases
    if data.team_name is not None:
        player.team_name = data.team_name
    if data.role is not None:
        player.role = data.role
    if data.nationality is not None:
        player.nationality = data.nationality
    if data.date_of_birth is not None:
        player.date_of_birth = data.date_of_birth
    if data.batting_style is not None:
        player.batting_style = data.batting_style
    if data.bowling_style is not None:
        player.bowling_style = data.bowling_style
    if data.status is not None:
        player.status = CplRosterPlayerStatus(data.status)
    if data.source_note is not None:
        player.source_note = data.source_note
    await db.commit()
    await db.refresh(player)
    return player


async def list_players(
    db: AsyncSession,
    competition_code: str = "CPL_MEN",
    season: str | None = None,
    team_name: str | None = None,
    status: str | None = None,
    role: str | None = None,
    nationality: str | None = None,
    player_search: str | None = None,
) -> CplPlayerListResponse:
    stmt = select(CplCurrentSeasonPlayer).where(
        CplCurrentSeasonPlayer.competition_code == competition_code
    )
    if season:
        stmt = stmt.where(CplCurrentSeasonPlayer.season == season)
    if team_name:
        stmt = stmt.where(CplCurrentSeasonPlayer.team_name == team_name)
    if status:
        stmt = stmt.where(CplCurrentSeasonPlayer.status == CplRosterPlayerStatus(status))
    if role:
        stmt = stmt.where(CplCurrentSeasonPlayer.role.ilike(f"%{role.strip()}%"))
    if nationality:
        stmt = stmt.where(CplCurrentSeasonPlayer.nationality.ilike(f"%{nationality.strip()}%"))
    if player_search:
        stmt = stmt.where(CplCurrentSeasonPlayer.player_name.ilike(f"%{player_search.strip()}%"))
    stmt = stmt.order_by(CplCurrentSeasonPlayer.player_name)
    result = await db.execute(stmt)
    players = list(result.scalars().all())
    returning_count = sum(1 for p in players if p.is_returning)
    new_count = len(players) - returning_count
    return CplPlayerListResponse(
        players=[CplPlayerResponse.model_validate(p) for p in players],
        total=len(players),
        returning_count=returning_count,
        new_count=new_count,
    )


async def _get_player_by_normalized(
    db: AsyncSession,
    competition_code: str,
    season: str,
    normalized: str,
) -> CplCurrentSeasonPlayer | None:
    result = await db.execute(
        select(CplCurrentSeasonPlayer).where(
            CplCurrentSeasonPlayer.competition_code == competition_code,
            CplCurrentSeasonPlayer.season == season,
            CplCurrentSeasonPlayer.normalized_player_name == normalized,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Roster import preview (read-only, no DB mutation)
# ---------------------------------------------------------------------------


async def preview_roster_import(
    db: AsyncSession,
    rows: list[RosterImportRow],
    competition_code: str,
    season: str,
) -> RosterImportPreviewResponse:
    """Compute a dry-run preview of a roster import without mutating the DB."""
    blockers: list[str] = []
    warnings: list[str] = []
    if not _is_valid_competition_code(competition_code):
        blockers.append(f"Invalid competition code '{competition_code}'.")
    if not _is_valid_season(season):
        blockers.append(f"Invalid season '{season}'. Expected YYYY format.")

    # Load existing teams and players for this competition/season
    existing_teams_result = await db.execute(
        select(CplCurrentSeasonTeam).where(
            CplCurrentSeasonTeam.competition_code == competition_code,
            CplCurrentSeasonTeam.season == season,
        )
    )
    existing_teams = {
        t.normalized_team_name: t.team_name for t in existing_teams_result.scalars().all()
    }

    existing_players_result = await db.execute(
        select(CplCurrentSeasonPlayer).where(
            CplCurrentSeasonPlayer.competition_code == competition_code,
            CplCurrentSeasonPlayer.season == season,
        )
    )
    existing_players = {
        p.normalized_player_name: p.player_name for p in existing_players_result.scalars().all()
    }

    new_teams: list[RosterImportPreviewTeam] = []
    existing_teams_matched: list[str] = []
    new_players: list[RosterImportPreviewPlayer] = []
    existing_matched: list[str] = []
    duplicates: list[RosterImportPreviewPlayer] = []
    returning_players: list[str] = []
    transfers: list[RosterImportPreviewPlayer] = []
    possible_duplicates: list[RosterImportPreviewPlayer] = []

    seen_teams: set[str] = set()
    seen_players: set[str] = set()  # normalized names seen in this batch
    seen_rows: set[tuple[str, str, str, str]] = set()
    existing_normalized_names = list(existing_players.keys())

    for idx, row in enumerate(rows):
        # Validate required fields
        if not row.player.strip():
            blockers.append(f"Row {idx}: player name is empty.")
            continue
        if not row.team or not row.team.strip():
            blockers.append(f"Row {idx}: team is required.")
            continue
        if not _is_valid_competition_code(row.competition):
            blockers.append(f"Row {idx}: invalid competition '{row.competition}'.")
            continue
        if not _is_valid_season(row.season):
            blockers.append(f"Row {idx}: invalid season '{row.season}'.")
            continue
        dedupe_key = (
            _normalize_name(row.competition),
            row.season.strip(),
            _normalize_name(row.team),
            _normalize_name(row.player),
        )
        if dedupe_key in seen_rows:
            blockers.append(f"Row {idx}: duplicate row in import.")
            continue
        seen_rows.add(dedupe_key)

        norm_player = _normalize_name(row.player)
        norm_team = _normalize_name(row.team) if row.team else None
        if row.role and row.role.strip().lower() not in KNOWN_ROLES:
            warnings.append(f"Row {idx}: unknown role '{row.role}'.")
        if not row.nationality:
            warnings.append(f"Row {idx}: nationality missing for '{row.player}'.")
        if not row.batting_style:
            warnings.append(f"Row {idx}: batting style missing for '{row.player}'.")
        if not row.bowling_style:
            warnings.append(f"Row {idx}: bowling style missing for '{row.player}'.")

        # Team detection
        if norm_team and norm_team not in seen_teams:
            seen_teams.add(norm_team)
            if norm_team in existing_teams:
                existing_teams_matched.append(existing_teams[norm_team])
            else:
                new_teams.append(
                    RosterImportPreviewTeam(
                        team_name=row.team or "",
                        is_new=True,
                        is_existing_match=False,
                    )
                )

        # Player detection
        is_dup_in_batch = norm_player in seen_players
        is_existing = norm_player in existing_players
        seen_players.add(norm_player)

        # Returning detection (check prior seasons)
        is_returning, prior_season, prior_team_name = await _detect_returning(
            db, competition_code, season, norm_player
        )

        if is_returning:
            display = row.player
            if display not in returning_players:
                returning_players.append(display)

        similar_existing = _find_similar_name(norm_player, existing_normalized_names)
        similar_existing_player = (
            existing_players.get(similar_existing) if similar_existing else None
        )
        is_transfer = bool(
            is_returning
            and prior_team_name
            and row.team
            and _normalize_name(prior_team_name) != _normalize_name(row.team)
        )
        preview_player = RosterImportPreviewPlayer(
            row_index=idx,
            player_name=row.player,
            team_name=row.team,
            status=row.status,
            role=row.role,
            nationality=row.nationality,
            is_transfer=is_transfer,
            previous_team_name=prior_team_name,
            similar_existing_player=similar_existing_player,
            is_new=not is_existing and not is_dup_in_batch,
            is_duplicate=is_dup_in_batch or is_existing,
            is_returning=is_returning,
            prior_season=prior_season,
            warning=f"Duplicate in import batch (row {idx})"
            if is_dup_in_batch
            else ("Already in roster for this season" if is_existing else None),
        )

        if is_dup_in_batch:
            duplicates.append(preview_player)
            warnings.append(f"Row {idx}: '{row.player}' appears more than once in the import.")
        elif is_existing:
            existing_matched.append(existing_players[norm_player])
        else:
            new_players.append(preview_player)
        if is_transfer:
            transfers.append(preview_player)
        if similar_existing_player and not is_existing:
            possible_duplicates.append(preview_player)
            warnings.append(
                f"Row {idx}: '{row.player}' may duplicate existing player '{similar_existing_player}'."
            )

    can_apply = len(blockers) == 0

    return RosterImportPreviewResponse(
        competition_code=competition_code,
        season=season,
        total_rows=len(rows),
        new_teams=new_teams,
        existing_teams_matched=existing_teams_matched,
        new_players=new_players,
        existing_players_matched=existing_matched,
        duplicates=duplicates,
        returning_players=returning_players,
        transfers=transfers,
        possible_duplicates=possible_duplicates,
        warnings=warnings,
        blockers=blockers,
        can_apply=can_apply,
    )


# ---------------------------------------------------------------------------
# Roster import apply
# ---------------------------------------------------------------------------


async def apply_roster_import(
    db: AsyncSession,
    request: RosterImportApplyRequest,
) -> RosterImportApplyResponse:
    """Apply a roster import. Must have confirm=True.

    Idempotent: existing records are not duplicated.
    Returns a summary of changes made.
    """
    if not request.confirm:
        return RosterImportApplyResponse(
            competition_code=request.competition_code,
            season=request.season,
            applied=False,
            errors=["Import was not confirmed. Set confirm=true to apply."],
        )
    if not _is_valid_competition_code(request.competition_code):
        return RosterImportApplyResponse(
            competition_code=request.competition_code,
            season=request.season,
            applied=False,
            errors=[f"Invalid competition code '{request.competition_code}'."],
        )
    if not _is_valid_season(request.season):
        return RosterImportApplyResponse(
            competition_code=request.competition_code,
            season=request.season,
            applied=False,
            errors=[f"Invalid season '{request.season}'. Expected YYYY format."],
        )

    teams_created = 0
    teams_matched = 0
    players_created = 0
    players_updated = 0
    players_skipped = 0
    returning_detected = 0
    warnings: list[str] = []
    errors: list[str] = []

    for idx, row in enumerate(request.rows):
        if not row.player.strip():
            errors.append(f"Row {idx}: player name is empty — skipped.")
            continue
        if not row.team or not row.team.strip():
            errors.append(f"Row {idx}: team is required — skipped.")
            continue
        if row.role and row.role.strip().lower() not in KNOWN_ROLES:
            warnings.append(f"Row {idx}: unknown role '{row.role}'.")

        # --- Team ---
        if row.team:
            norm_team = _normalize_name(row.team)
            existing_team = await _get_team_by_normalized(
                db, request.competition_code, request.season, norm_team
            )
            if existing_team:
                teams_matched += 1
            else:
                team = CplCurrentSeasonTeam(
                    competition_code=request.competition_code,
                    season=request.season,
                    team_name=row.team,
                    normalized_team_name=norm_team,
                    source_note=row.source_note,
                )
                db.add(team)
                try:
                    await db.flush()
                    teams_created += 1
                except IntegrityError:
                    await db.rollback()
                    warnings.append(
                        f"Row {idx}: team '{row.team}' already exists (race condition skipped)."
                    )
                    teams_matched += 1

        # --- Player ---
        norm_player = _normalize_name(row.player)
        existing_player = await _get_player_by_normalized(
            db, request.competition_code, request.season, norm_player
        )
        if existing_player:
            # Idempotent update of mutable fields
            if row.status:
                existing_player.status = CplRosterPlayerStatus(row.status)
            if row.team:
                existing_player.team_name = row.team
            if row.role:
                existing_player.role = row.role
            if row.nationality:
                existing_player.nationality = row.nationality
            if row.date_of_birth:
                existing_player.date_of_birth = row.date_of_birth
            if row.batting_style:
                existing_player.batting_style = row.batting_style
            if row.bowling_style:
                existing_player.bowling_style = row.bowling_style
            players_updated += 1
        else:
            is_returning, prior_season, _prior_team_name = await _detect_returning(
                db, request.competition_code, request.season, norm_player
            )
            if is_returning:
                returning_detected += 1
            player = CplCurrentSeasonPlayer(
                competition_code=request.competition_code,
                season=request.season,
                player_name=row.player,
                normalized_player_name=norm_player,
                team_name=row.team,
                role=row.role,
                nationality=row.nationality,
                date_of_birth=row.date_of_birth,
                batting_style=row.batting_style,
                bowling_style=row.bowling_style,
                status=CplRosterPlayerStatus(row.status),
                is_returning=is_returning,
                prior_season=prior_season,
                source_note=row.source_note,
            )
            db.add(player)
            try:
                await db.flush()
                players_created += 1
            except IntegrityError:
                await db.rollback()
                warnings.append(
                    f"Row {idx}: player '{row.player}' already exists (race condition skipped)."
                )
                players_skipped += 1

    await db.commit()

    return RosterImportApplyResponse(
        competition_code=request.competition_code,
        season=request.season,
        teams_created=teams_created,
        teams_matched=teams_matched,
        players_created=players_created,
        players_updated=players_updated,
        players_skipped_duplicate=players_skipped,
        returning_players_detected=returning_detected,
        warnings=warnings,
        errors=errors,
        applied=True,
    )
