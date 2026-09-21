"""Phase 7I saved-School-Team match creation without changing cricket truth."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from backend.api.schemas.school_matches import (
    ExternalOpponentSelection,
    SchoolMatchCreate,
    SchoolMatchSideSelection,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app import models
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

SCHOOL_MATCH_CAPABILITIES = (
    "school_match_playing_xi",
    "school_persistent_teams",
    "school_team_rosters",
)
SCHOOL_MATCH_CREATE_ROLES = frozenset({"owner", "admin", "coach", "scorer"})


@dataclass(frozen=True)
class SchoolMatchServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class EligiblePlayer:
    team_membership: models.SchoolTeamPlayerMembership
    school_membership: models.SchoolPlayerMembership
    profile: models.PlayerProfile


@dataclass(frozen=True)
class EligibleSide:
    team: models.Team
    players: tuple[EligiblePlayer, ...]
    captain_profile_id: str
    wicketkeeper_profile_id: str


def _forbidden() -> SchoolMatchServiceError:
    return SchoolMatchServiceError(403, "Insufficient organization role")


def _team_not_found() -> SchoolMatchServiceError:
    return SchoolMatchServiceError(404, "Team not found")


def _invalid(detail: str) -> SchoolMatchServiceError:
    return SchoolMatchServiceError(422, detail)


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
) -> None:
    for capability in SCHOOL_MATCH_CAPABILITIES:
        await require_organization_capability(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            capability=capability,
        )
    organization, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if (
        organization.organization_type != "school"
        or membership.role not in SCHOOL_MATCH_CREATE_ROLES
    ):
        raise _forbidden()


async def _eligible_side(
    db: AsyncSession,
    *,
    organization_id: str,
    selection: SchoolMatchSideSelection,
) -> EligibleSide:
    if len(set(selection.playing_xi_membership_ids)) != 11:
        raise _invalid("Playing XI must contain 11 distinct Team roster memberships")
    selected_ids = set(selection.playing_xi_membership_ids)
    if selection.captain_membership_id not in selected_ids:
        raise _invalid("Captain must belong to the selected playing XI")
    if selection.wicketkeeper_membership_id not in selected_ids:
        raise _invalid("Wicketkeeper must belong to the selected playing XI")

    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == selection.team_id,
            models.Team.organization_id == organization_id,
        )
    )
    if team is None:
        raise _team_not_found()
    if team.status != "active":
        raise SchoolMatchServiceError(409, "Archived Team cannot be used for match setup")

    result = await db.execute(
        select(
            models.SchoolTeamPlayerMembership,
            models.SchoolPlayerMembership,
            models.PlayerProfile,
        )
        .join(
            models.SchoolPlayerMembership,
            and_(
                models.SchoolPlayerMembership.id
                == models.SchoolTeamPlayerMembership.school_player_membership_id,
                models.SchoolPlayerMembership.organization_id
                == models.SchoolTeamPlayerMembership.organization_id,
            ),
        )
        .join(
            models.PlayerProfile,
            models.PlayerProfile.player_id == models.SchoolPlayerMembership.player_profile_id,
        )
        .where(
            models.SchoolTeamPlayerMembership.id.in_(selected_ids),
            models.SchoolTeamPlayerMembership.organization_id == organization_id,
            models.SchoolTeamPlayerMembership.team_id == selection.team_id,
        )
    )
    rows = result.tuples().all()
    by_membership_id = {
        row[0].id: EligiblePlayer(
            team_membership=row[0],
            school_membership=row[1],
            profile=row[2],
        )
        for row in rows
    }
    if set(by_membership_id) != selected_ids:
        raise _invalid("One or more selected players are not eligible for this Team")

    players = tuple(by_membership_id[item_id] for item_id in selection.playing_xi_membership_ids)
    if any(
        player.team_membership.status != "active"
        or player.school_membership.status != "active"
        or player.team_membership.organization_id != organization_id
        or player.school_membership.organization_id != organization_id
        for player in players
    ):
        raise _invalid("One or more selected players are not eligible for this Team")
    profile_ids = [player.profile.player_id for player in players]
    if len(set(profile_ids)) != 11:
        raise _invalid("Playing XI cannot contain a duplicate canonical player")

    return EligibleSide(
        team=team,
        players=players,
        captain_profile_id=by_membership_id[selection.captain_membership_id].profile.player_id,
        wicketkeeper_profile_id=by_membership_id[
            selection.wicketkeeper_membership_id
        ].profile.player_id,
    )


def _team_snapshot(organization_id: str, side: EligibleSide) -> dict[str, Any]:
    players = [
        {
            "id": player.profile.player_id,
            "name": player.profile.player_name,
            "player_profile_id": player.profile.player_id,
            "school_player_membership_id": player.school_membership.id,
            "school_team_player_membership_id": player.team_membership.id,
        }
        for player in side.players
    ]
    return {
        "name": side.team.name,
        "players": players,
        "playing_xi": [player["id"] for player in players],
        "school_source": {
            "organization_id": organization_id,
            "team_id": side.team.id,
        },
    }


def _external_snapshot(selection: ExternalOpponentSelection) -> tuple[dict[str, Any], str, str]:
    players = [{"id": f"external:{uuid.uuid4()}", "name": name} for name in selection.player_names]
    snapshot = {
        "name": selection.team_name,
        "players": players,
        "playing_xi": [player["id"] for player in players],
    }
    return (
        snapshot,
        players[selection.captain_index]["id"],
        players[selection.wicketkeeper_index]["id"],
    )


def _batting_scorecard(team: dict[str, Any]) -> dict[str, Any]:
    return {
        player["id"]: {
            "player_id": player["id"],
            "player_name": player["name"],
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }
        for player in team["players"]
    }


def _bowling_scorecard(team: dict[str, Any]) -> dict[str, Any]:
    return {
        player["id"]: {
            "player_id": player["id"],
            "player_name": player["name"],
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
        for player in team["players"]
    }


async def create_school_match(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: SchoolMatchCreate,
    actor_user_id: str,
) -> models.Game:
    """Validate current School eligibility, then freeze it into one Game snapshot."""
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )
    side_a: EligibleSide | None = None
    side_b: EligibleSide | None = None
    if payload.mode == "school_vs_school":
        assert payload.team_a is not None and payload.team_b is not None
        if payload.team_a.team_id == payload.team_b.team_id:
            raise _invalid("A match requires two different saved Teams")
        side_a = await _eligible_side(
            db,
            organization_id=organization_id,
            selection=payload.team_a,
        )
        side_b = await _eligible_side(
            db,
            organization_id=organization_id,
            selection=payload.team_b,
        )
        profile_ids_a = {player.profile.player_id for player in side_a.players}
        profile_ids_b = {player.profile.player_id for player in side_b.players}
        if profile_ids_a & profile_ids_b:
            raise _invalid("A canonical player cannot appear for both sides in one match")
        team_a = _team_snapshot(organization_id, side_a)
        team_b = _team_snapshot(organization_id, side_b)
        captain_a = side_a.captain_profile_id
        keeper_a = side_a.wicketkeeper_profile_id
        captain_b = side_b.captain_profile_id
        keeper_b = side_b.wicketkeeper_profile_id
    else:
        assert payload.school_side is not None and payload.external_opponent is not None
        school_selection = payload.team_a if payload.school_side == "team_a" else payload.team_b
        assert school_selection is not None
        school = await _eligible_side(
            db,
            organization_id=organization_id,
            selection=school_selection,
        )
        school_snapshot = _team_snapshot(organization_id, school)
        external_snapshot, external_captain, external_keeper = _external_snapshot(
            payload.external_opponent
        )
        if school_snapshot["name"].casefold() == external_snapshot["name"].casefold():
            raise _invalid("School and external opponent Team names must be different")
        if payload.school_side == "team_a":
            side_a = school
            team_a, team_b = school_snapshot, external_snapshot
            captain_a, keeper_a = school.captain_profile_id, school.wicketkeeper_profile_id
            captain_b, keeper_b = external_captain, external_keeper
        else:
            side_b = school
            team_a, team_b = external_snapshot, school_snapshot
            captain_a, keeper_a = external_captain, external_keeper
            captain_b, keeper_b = school.captain_profile_id, school.wicketkeeper_profile_id
    toss_team = team_a if payload.toss_winner_side == "team_a" else team_b
    other_team = team_b if payload.toss_winner_side == "team_a" else team_a
    batting_team = toss_team if payload.decision == "bat" else other_team
    bowling_team = other_team if payload.decision == "bat" else toss_team

    game = models.Game(
        id=str(uuid.uuid4()),
        team_a=team_a,
        team_b=team_b,
        match_type=payload.match_type,
        overs_limit=payload.overs_limit if payload.match_type == "limited" else None,
        days_limit=payload.days_limit if payload.match_type == "multi_day" else None,
        overs_per_day=(payload.overs_per_day if payload.match_type == "multi_day" else None),
        dls_enabled=payload.dls_enabled,
        interruptions=[],
        toss_winner_team=toss_team["name"],
        decision=payload.decision,
        batting_team_name=batting_team["name"],
        bowling_team_name=bowling_team["name"],
        batting_scorecard=_batting_scorecard(batting_team),
        bowling_scorecard=_bowling_scorecard(bowling_team),
        current_inning=0,
        status=models.GameStatus.innings_break,
        publication_state="private",
        created_by_user_id=actor_user_id,
        team_a_captain_id=captain_a,
        team_a_keeper_id=keeper_a,
        team_b_captain_id=captain_b,
        team_b_keeper_id=keeper_b,
    )
    db.add(game)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.school_match_create_failed",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(game)
    logger.info(
        "organization.school_match_created",
        organization_id=organization_id,
        game_id=game.id,
        team_a_id=side_a.team.id if side_a is not None else None,
        team_b_id=side_b.team.id if side_b is not None else None,
        actor_user_id=actor_user_id,
    )
    return game
