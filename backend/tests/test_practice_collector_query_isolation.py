from __future__ import annotations

from backend.services import org_stats
from backend.routes.analyst_pro import get_analyst_players
from backend.sql_app.database import SessionLocal
from backend.sql_app.models import Game, GameStatus, RoleEnum, User
from backend.sql_app.models import Team
from backend.sql_app.models import HistoricalImportBatch
from backend.services.analyst_registry_service import build_analyst_registry
from backend.services.model_training_dataset_builder import DatasetBuildRequest, build_model_training_dataset
from backend.services.historical_stats_aggregation_service import get_historical_stats_summary
from backend.services.tournament_intelligence_service import _fetch_eligible_games
import uuid
import pytest


def test_org_stats_game_queries_are_official_only() -> None:
    source = org_stats.calculate_org_stats.__code__.co_consts
    assert any("official" in value for value in source if isinstance(value, str))


def test_analyst_players_query_is_official_only() -> None:
    from backend.routes import analyst_pro

    source = analyst_pro.get_analyst_players.__code__.co_consts
    assert any("official" in value for value in source if isinstance(value, str))


@pytest.mark.asyncio
async def test_analyst_players_excludes_practice_and_keeps_official() -> None:
    async with SessionLocal() as session:
        user = User(id=str(uuid.uuid4()), email="analyst-proof@example.com", hashed_password="x", role=RoleEnum.analyst_pro)
        session.add(user)
        for purpose, runs in (("official", 11), ("practice", 99)):
            session.add(Game(id=str(uuid.uuid4()), created_by_user_id=user.id, match_purpose=purpose, status=GameStatus.completed, batting_scorecard={"Only official": {"runs": runs, "balls_faced": 10}}, bowling_scorecard={}))
        await session.commit()
        response = await get_analyst_players(current_user=user, match_id=None, db=session)
        assert [(row.player, row.runs) for row in response.items] == [("Only official", 11)]


@pytest.mark.asyncio
async def test_analyst_registry_excludes_practice_historical_game() -> None:
    async with SessionLocal() as session:
        user = User(id=str(uuid.uuid4()), email="registry-proof@example.com", hashed_password="x", role=RoleEnum.analyst_pro)
        batch = HistoricalImportBatch(id=str(uuid.uuid4()), owner_user_id=user.id, source_format="cricsheet_json", source_hash_sha256="a" * 64, status="valid", is_finalized=True)
        session.add_all([user, batch])
        meta = {"is_historical": True, "batch_id": batch.id, "match_date": "2024-01-01"}
        for purpose in ("official", "practice"):
            session.add(Game(id=str(uuid.uuid4()), created_by_user_id=user.id, match_purpose=purpose, status=GameStatus.completed, phases={"historical_import": meta}, team_a={"name": "A"}, team_b={"name": "B"}))
        await session.commit()
        response = await build_analyst_registry(user, session)
        assert len(response.entries) == 1


@pytest.mark.asyncio
async def test_training_builder_excludes_practice_historical_game() -> None:
    async with SessionLocal() as session:
        rows = []
        innings = [{"inning_no": 1, "team": "A", "runs": 10, "wickets": 1, "legal_balls": 6}]
        for purpose, digest in (("official", "b"), ("practice", "c")):
            game = Game(id=str(uuid.uuid4()), match_purpose=purpose, status=GameStatus.completed, team_a={"name": "A"}, team_b={"name": "B"})
            batch = HistoricalImportBatch(id=str(uuid.uuid4()), source_format="cricsheet_json", source_hash_sha256=digest * 64, status="valid", is_finalized=True, applied_game_id=game.id)
            game.phases = {"historical_import": {"is_historical": True, "batch_id": batch.id}, "historical_innings_summary": innings}
            session.add_all([game, batch]); rows.append(game.id)
        await session.commit()
        result = await build_model_training_dataset(session, DatasetBuildRequest())
        assert result["included_match_ids"] == [rows[0]]


@pytest.mark.asyncio
async def test_historical_summary_excludes_practice_historical_game() -> None:
    async with SessionLocal() as session:
        user = User(id=str(uuid.uuid4()), email="summary-proof@example.com", hashed_password="x", role=RoleEnum.analyst_pro)
        session.add(user); ids = []
        for purpose, digest in (("official", "d"), ("practice", "e")):
            game = Game(id=str(uuid.uuid4()), created_by_user_id=user.id, match_purpose=purpose, status=GameStatus.completed, team_a={"name": "A"}, team_b={"name": "B"})
            batch = HistoricalImportBatch(id=str(uuid.uuid4()), owner_user_id=user.id, source_format="cricsheet_json", source_hash_sha256=digest * 64, status="valid", is_finalized=True, applied_game_id=game.id)
            game.phases = {"historical_import": {"is_historical": True, "batch_id": batch.id}}
            session.add_all([game, batch]); ids.append(game.id)
        await session.commit()
        summary = await get_historical_stats_summary(session, user)
        assert summary.total_eligible_matches == 1
        assert [row.match_id for row in summary.matches] == [ids[0]]


@pytest.mark.asyncio
async def test_tournament_intelligence_excludes_practice_historical_game() -> None:
    async with SessionLocal() as session:
        user = User(id=str(uuid.uuid4()), email="tournament-proof@example.com", hashed_password="x", role=RoleEnum.analyst_pro)
        session.add(user); ids = []
        for purpose, digest in (("official", "f"), ("practice", "0")):
            game = Game(id=str(uuid.uuid4()), created_by_user_id=user.id, match_purpose=purpose, status=GameStatus.completed, team_a={"name": "A"}, team_b={"name": "B"})
            batch = HistoricalImportBatch(id=str(uuid.uuid4()), owner_user_id=user.id, source_format="cricsheet_json", source_hash_sha256=digest * 64, status="valid", is_finalized=True, applied_game_id=game.id)
            game.phases = {"historical_import": {"is_historical": True, "batch_id": batch.id}}
            session.add_all([game, batch]); ids.append(game.id)
        await session.commit()
        rows = await _fetch_eligible_games(session, user)
        assert [row[0].id for row in rows] == [ids[0]]
