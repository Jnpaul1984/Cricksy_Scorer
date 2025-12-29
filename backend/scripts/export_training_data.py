"""
Export Training Data from Database
===================================

This script exports match data from your PostgreSQL/SQLite database
to CSV snapshots for model retraining.

Usage:
    # Export all matches
    python -m backend.scripts.export_training_data

    # Export only recent matches (last N days)
    python -m backend.scripts.export_training_data --days 30

    # Export specific match format
    python -m backend.scripts.export_training_data --format t20
"""

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_async_session_maker
from backend.sql_app.models import Delivery, Game


async def export_match_snapshots(
    match_format: str | None = None,
    days: int | None = None,
    output_dir: Path | None = None,
) -> None:
    """
    Export match data to training snapshots.

    Args:
        match_format: Filter by match format (t20, odi, test)
        days: Export only matches from last N days
        output_dir: Output directory (default: backend/snapshots/{format}/)
    """
    SessionLocal = get_async_session_maker()

    async with SessionLocal() as session:
        print(f"\n{'=' * 60}")
        print("Exporting Training Data from Database")
        print(f"{'=' * 60}\n")

        # Build query for games
        stmt = select(Game).where(Game.status == "complete")

        if match_format:
            stmt = stmt.where(Game.match_type == match_format)

        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(Game.created_at >= cutoff_date)

        result = await session.execute(stmt)
        games = result.scalars().all()

        print(f"Found {len(games)} completed matches to export\n")

        if len(games) == 0:
            print("[WARN] No completed matches found. Play some matches first!")
            return

        # Group by match format
        games_by_format = {}
        for game in games:
            fmt = game.match_type or "unknown"
            if fmt not in games_by_format:
                games_by_format[fmt] = []
            games_by_format[fmt].append(game)

        # Export each format
        for fmt, fmt_games in games_by_format.items():
            await export_format_snapshots(session, fmt, fmt_games, output_dir)

        print("\n[OK] Export complete!")
        print("\nNext steps:")
        print("  1. Review snapshots in backend/snapshots/")
        print("  2. Run training: python -m backend.train_win_predictors t20")
        print("  3. Run training: python -m backend.train_score_predictors t20")
        print("  4. Commit updated models: git add backend/ml_models/")
        print("  5. Deploy: git push (models bundled in Docker image)\n")


async def export_format_snapshots(
    session: AsyncSession,
    match_format: str,
    games: list[Game],
    output_dir: Path | None = None,
) -> None:
    """Export snapshots for a specific match format."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "snapshots" / match_format
    else:
        output_dir = output_dir / match_format

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{match_format.upper()}] Exporting {len(games)} matches...")

    exported_count = 0
    for i, game in enumerate(games, 1):
        try:
            # Export this game's deliveries
            await export_game_to_csv(session, game, output_dir)
            exported_count += 1

            if i % 50 == 0:
                print(f"  Exported {i}/{len(games)} matches...")
        except Exception as e:
            print(f"  [WARN] Failed to export game {game.id}: {e}")

    print(f"  [OK] Exported {exported_count}/{len(games)} matches to {output_dir}/\n")


async def export_game_to_csv(session: AsyncSession, game: Game, output_dir: Path) -> None:
    """
    Export a single game's deliveries to CSV format.

    CSV format matches what training scripts expect:
    - match_id, innings, over, ball, total_runs, wickets, completed_overs,
      balls_remaining, batting_team, bowling_team, winner, final_score
    """
    # Get all deliveries for this game
    stmt = (
        select(Delivery)
        .where(Delivery.game_id == game.id)
        .order_by(Delivery.innings_num, Delivery.over_num, Delivery.ball_num)
    )
    result = await session.execute(stmt)
    deliveries = result.scalars().all()

    if len(deliveries) == 0:
        return  # Skip games with no deliveries

    # Build snapshot rows (one row per delivery)
    rows = []
    for delivery in deliveries:
        # Calculate cumulative state at this delivery
        rows.append(
            {
                "match_id": game.id,
                "innings": delivery.innings_num,
                "over": delivery.over_num,
                "ball": delivery.ball_num,
                "total_runs": delivery.runs_scored or 0,
                "wickets": delivery.wickets_fallen or 0,
                "completed_overs": delivery.over_num,
                "balls_this_over": delivery.ball_num,
                "balls_remaining": calculate_balls_remaining(
                    game, delivery.innings_num, delivery.over_num, delivery.ball_num
                ),
                "batting_team": game.team1_name if delivery.innings_num == 1 else game.team2_name,
                "bowling_team": game.team2_name if delivery.innings_num == 1 else game.team1_name,
                "winner": game.winner_team_name or "",
                "final_score": game.team1_total if delivery.innings_num == 1 else game.team2_total,
            }
        )

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Calculate cumulative totals per innings
    df["total_runs"] = df.groupby("innings")["total_runs"].cumsum()
    df["wickets"] = df.groupby("innings")["wickets"].cumsum()

    # Save to CSV
    output_file = output_dir / f"match_{game.id}.csv"
    df.to_csv(output_file, index=False)


def calculate_balls_remaining(game: Game, innings: int, over: int, ball: int) -> int:
    """Calculate balls remaining in innings."""
    overs_limit = game.overs_limit or 20  # Default to T20
    total_balls = overs_limit * 6
    balls_bowled = (over * 6) + ball
    return max(0, total_balls - balls_bowled)


async def main():
    parser = argparse.ArgumentParser(description="Export training data from database")
    parser.add_argument(
        "--format",
        type=str,
        choices=["t20", "odi", "test"],
        help="Export only this match format",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Export only matches from last N days",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: backend/snapshots/)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None

    await export_match_snapshots(
        match_format=args.format,
        days=args.days,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    asyncio.run(main())
