from __future__ import annotations

import datetime as dt
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from backend.sql_app import schemas, tournament_crud

UTC = getattr(dt, "UTC", dt.UTC)


@dataclass
class _TournamentRecord:
    id: str
    name: str
    description: str | None
    tournament_type: str
    start_date: dt.datetime | None
    end_date: dt.datetime | None
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime
    team_ids: list[int] = field(default_factory=list)
    fixture_ids: list[str] = field(default_factory=list)


class InMemoryTournamentRepository:
    """Simple in-memory replica for tournament CRUD operations used in CI."""

    def __init__(self) -> None:
        self._tournaments: dict[str, _TournamentRecord] = {}
        self._teams: dict[int, dict[str, Any]] = {}
        self._fixtures: dict[str, dict[str, Any]] = {}
        self._team_seq: int = 1

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(UTC)

    def _serialize_team(self, team_record: dict[str, Any]) -> schemas.TournamentTeamResponse:
        return schemas.TournamentTeamResponse(**team_record)

    def _serialize_tournament(self, record: _TournamentRecord) -> schemas.TournamentResponse:
        teams = [self._serialize_team(self._teams[tid]) for tid in record.team_ids]
        payload = {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "tournament_type": record.tournament_type,
            "start_date": record.start_date,
            "end_date": record.end_date,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        return schemas.TournamentResponse(**payload, teams=teams)

    def _serialize_fixture(self, fixture_record: dict[str, Any]) -> schemas.FixtureResponse:
        return schemas.FixtureResponse(**fixture_record)

    # ------------------------------------------------------------------ tournaments
    async def create_tournament(
        self, db: object, tournament_in: schemas.TournamentCreate
    ) -> schemas.TournamentResponse:
        tournament_id = str(uuid.uuid4())
        now = self._now()
        record = _TournamentRecord(
            id=tournament_id,
            name=tournament_in.name,
            description=tournament_in.description,
            tournament_type=tournament_in.tournament_type or "league",
            start_date=tournament_in.start_date,
            end_date=tournament_in.end_date,
            status="upcoming",
            created_at=now,
            updated_at=now,
        )
        self._tournaments[tournament_id] = record
        return self._serialize_tournament(record)

    async def get_tournament(
        self, db: object, tournament_id: str
    ) -> schemas.TournamentResponse | None:
        record = self._tournaments.get(tournament_id)
        return self._serialize_tournament(record) if record else None

    async def get_tournaments(
        self, db: object, skip: int = 0, limit: int = 100
    ) -> list[schemas.TournamentResponse]:
        ordered = sorted(
            self._tournaments.values(),
            key=lambda rec: rec.created_at,
            reverse=True,
        )
        window = ordered[skip : skip + limit if limit is not None else None]
        return [self._serialize_tournament(rec) for rec in window]

    async def update_tournament(
        self, db: object, tournament_id: str, tournament_update: schemas.TournamentUpdate
    ) -> schemas.TournamentResponse | None:
        record = self._tournaments.get(tournament_id)
        if record is None:
            return None

        update_data = tournament_update.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            if hasattr(record, field_name):
                setattr(record, field_name, value)
        record.updated_at = self._now()
        return self._serialize_tournament(record)

    async def delete_tournament(self, db: object, tournament_id: str) -> bool:
        record = self._tournaments.pop(tournament_id, None)
        if record is None:
            return False

        for team_id in record.team_ids:
            self._teams.pop(team_id, None)
        for fixture_id in record.fixture_ids:
            self._fixtures.pop(fixture_id, None)
        return True

    # ------------------------------------------------------------------------ teams
    async def add_team_to_tournament(
        self, db: object, tournament_id: str, team_data: schemas.TeamAdd
    ) -> schemas.TournamentTeamResponse | None:
        record = self._tournaments.get(tournament_id)
        if record is None:
            return None

        team_id = self._team_seq
        self._team_seq += 1
        team_record = {
            "id": team_id,
            "tournament_id": tournament_id,
            "team_name": team_data.team_name,
            "team_data": dict(team_data.team_data or {}),
            "matches_played": 0,
            "matches_won": 0,
            "matches_lost": 0,
            "matches_drawn": 0,
            "points": 0,
            "net_run_rate": 0.0,
        }
        self._teams[team_id] = team_record
        record.team_ids.append(team_id)
        return self._serialize_team(team_record)

    async def get_tournament_teams(
        self, db: object, tournament_id: str
    ) -> list[schemas.TournamentTeamResponse]:
        record = self._tournaments.get(tournament_id)
        if record is None:
            return []

        teams = [self._teams[tid] for tid in record.team_ids]
        teams.sort(key=lambda t: (t["points"], t["net_run_rate"]), reverse=True)
        return [self._serialize_team(team) for team in teams]

    async def update_team_stats(
        self,
        db: object,
        tournament_id: str,
        team_name: str,
        *,
        won: bool = False,
        lost: bool = False,
        drawn: bool = False,
        runs_scored: int = 0,
        runs_conceded: int = 0,
        overs_faced: float = 0.0,
        overs_bowled: float = 0.0,
    ) -> schemas.TournamentTeamResponse | None:
        record = self._tournaments.get(tournament_id)
        if record is None:
            return None

        team_record = next(
            (
                self._teams[tid]
                for tid in record.team_ids
                if self._teams[tid]["team_name"] == team_name
            ),
            None,
        )
        if team_record is None:
            return None

        team_record["matches_played"] += 1
        if won:
            team_record["matches_won"] += 1
            team_record["points"] += 2
        elif lost:
            team_record["matches_lost"] += 1
        elif drawn:
            team_record["matches_drawn"] += 1
            team_record["points"] += 1

        if overs_faced > 0 and overs_bowled > 0:
            run_rate_for = runs_scored / overs_faced
            run_rate_against = runs_conceded / overs_bowled
            team_record["net_run_rate"] = run_rate_for - run_rate_against

        return self._serialize_team(team_record)

    async def get_points_table(
        self, db: object, tournament_id: str
    ) -> list[schemas.PointsTableEntry]:
        teams = await self.get_tournament_teams(db, tournament_id)
        return [
            schemas.PointsTableEntry(
                team_name=team.team_name,
                matches_played=team.matches_played,
                matches_won=team.matches_won,
                matches_lost=team.matches_lost,
                matches_drawn=team.matches_drawn,
                points=team.points,
                net_run_rate=team.net_run_rate,
            )
            for team in teams
        ]

    # --------------------------------------------------------------------- fixtures
    async def create_fixture(
        self, db: object, fixture_in: schemas.FixtureCreate
    ) -> schemas.FixtureResponse | None:
        record = self._tournaments.get(fixture_in.tournament_id)
        if record is None:
            return None

        fixture_id = str(uuid.uuid4())
        now = self._now()
        fixture_record = {
            "id": fixture_id,
            "tournament_id": fixture_in.tournament_id,
            "match_number": fixture_in.match_number,
            "team_a_name": fixture_in.team_a_name,
            "team_b_name": fixture_in.team_b_name,
            "venue": fixture_in.venue,
            "scheduled_date": fixture_in.scheduled_date,
            "game_id": None,
            "status": "scheduled",
            "result": None,
            "created_at": now,
            "updated_at": now,
        }
        self._fixtures[fixture_id] = fixture_record
        record.fixture_ids.append(fixture_id)
        return self._serialize_fixture(fixture_record)

    async def get_fixture(self, db: object, fixture_id: str) -> schemas.FixtureResponse | None:
        record = self._fixtures.get(fixture_id)
        return self._serialize_fixture(record) if record else None

    async def get_tournament_fixtures(
        self, db: object, tournament_id: str
    ) -> list[schemas.FixtureResponse]:
        record = self._tournaments.get(tournament_id)
        if record is None:
            return []

        fixtures = [self._fixtures[fid] for fid in record.fixture_ids]

        def _fixture_sort_key(fix: dict[str, Any]) -> tuple[dt.datetime, int]:
            scheduled = fix["scheduled_date"] or dt.datetime(1970, 1, 1, tzinfo=UTC)
            match_number = fix["match_number"] or 0
            return (scheduled, match_number)

        fixtures.sort(key=_fixture_sort_key)
        return [self._serialize_fixture(fix) for fix in fixtures]

    async def update_fixture(
        self, db: object, fixture_id: str, fixture_update: schemas.FixtureUpdate
    ) -> schemas.FixtureResponse | None:
        record = self._fixtures.get(fixture_id)
        if record is None:
            return None

        update_data = fixture_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            record[key] = value
        record["updated_at"] = self._now()
        return self._serialize_fixture(record)

    async def delete_fixture(self, db: object, fixture_id: str) -> bool:
        record = self._fixtures.pop(fixture_id, None)
        if record is None:
            return False

        tournament = self._tournaments.get(record["tournament_id"])
        if tournament:
            with suppress(ValueError):
                tournament.fixture_ids.remove(fixture_id)
        return True


def enable_in_memory_tournaments(
    repository: InMemoryTournamentRepository | None,
) -> None:
    """Register (or clear) the in-memory repository with tournament CRUD."""

    tournament_crud.set_in_memory_repository(repository)
