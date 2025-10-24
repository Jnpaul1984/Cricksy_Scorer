"""
Seed utility for local development.

Creates a single game with minimal teams and attaches a simple result
directly in the database, using your app's async SQLAlchemy session and CRUD helpers.

Usage:
  - Ensure DATABASE_URL points at a reachable DB (defaults in backend/sql_app/database.py)
  - Run: `python -m scripts.seed_dev_data`
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from backend.sql_app import crud, schemas
from backend.sql_app.database import SessionLocal


async def seed_one_game() -> dict[str, Any]:
    async with SessionLocal() as session:
        team_a_name = "Dev Team A"
        team_b_name = "Dev Team B"

        game_id = str(uuid.uuid4())

        game_create = schemas.GameCreate(
            team_a_name=team_a_name,
            team_b_name=team_b_name,
            players_a=["A1", "A2"],
            players_b=["B1", "B2"],
            match_type=schemas.MatchType.limited,
            overs_limit=20,
            days_limit=None,
            overs_per_day=None,
            dls_enabled=False,
            interruptions=[],
            toss_winner_team=team_a_name,
            decision="bat",
        )

        # Batting/bowling sides inferred from toss/decision in main.py; mirror here
        batting_team = team_a_name
        bowling_team = team_b_name

        team_a = {
            "name": team_a_name,
            "players": [
                {"id": str(uuid.uuid4()), "name": n} for n in game_create.players_a
            ],
        }
        team_b = {
            "name": team_b_name,
            "players": [
                {"id": str(uuid.uuid4()), "name": n} for n in game_create.players_b
            ],
        }

        # Minimal scorecards
        batting_scorecard: dict[str, Any] = {}
        bowling_scorecard: dict[str, Any] = {}

        db_game = await crud.create_game(
            db=session,
            game=game_create,
            game_id=game_id,
            batting_team=batting_team,
            bowling_team=bowling_team,
            team_a=team_a,
            team_b=team_b,
            batting_scorecard=batting_scorecard,
            bowling_scorecard=bowling_scorecard,
        )

        # Attach a simple result payload (same shape used by the results endpoint)
        result_payload = {
            "match_id": game_id,
            "winner": team_a_name,
            "team_a_score": 150,
            "team_b_score": 120,
            "winner_team_name": team_a_name,
            "method": "by runs",
            "margin": 30,
            "result_text": f"{team_a_name} won by 30 runs",
        }
        db_game.result = json.dumps(result_payload)

        await crud.update_game(session, db_game)

        return {"id": db_game.id, "result": result_payload}


async def amain() -> None:
    info = await seed_one_game()
    print("Seeded game:")
    print(json.dumps(info, indent=2))


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
