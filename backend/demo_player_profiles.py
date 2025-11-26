"""
Demo script to create sample player profiles and test the player profile APIs.
This demonstrates the player profiles feature.
"""

import asyncio
import contextlib
import sys
from datetime import UTC

from sqlalchemy import select

from backend.sql_app import database as db
from backend.sql_app.database import SessionLocal  # backward-compatible alias
from backend.sql_app.models import AchievementType, PlayerAchievement, PlayerProfile

utc = UTC


async def create_sample_profiles():
    """Create sample player profiles for demonstration."""
    assert SessionLocal is not None, "Database not initialized"  # nosec
    async with SessionLocal() as db:
        print("Creating sample player profiles...")

        # Sample players
        players = [
            PlayerProfile(
                player_id="player-001",
                player_name="Sachin Tendulkar",
                total_matches=50,
                total_innings_batted=50,
                total_runs_scored=2500,
                total_balls_faced=2000,
                total_fours=250,
                total_sixes=50,
                times_out=40,
                highest_score=150,
                centuries=8,
                half_centuries=15,
                total_innings_bowled=20,
                total_overs_bowled=60.0,
                total_runs_conceded=480,
                total_wickets=15,
                best_bowling_figures="3/30",
                five_wicket_hauls=0,
                maidens=5,
                catches=25,
                stumpings=0,
                run_outs=8,
            ),
            PlayerProfile(
                player_id="player-002",
                player_name="Shane Warne",
                total_matches=45,
                total_innings_batted=40,
                total_runs_scored=800,
                total_balls_faced=900,
                total_fours=80,
                total_sixes=15,
                times_out=35,
                highest_score=60,
                centuries=0,
                half_centuries=3,
                total_innings_bowled=45,
                total_overs_bowled=180.0,
                total_runs_conceded=1350,
                total_wickets=75,
                best_bowling_figures="5/28",
                five_wicket_hauls=5,
                maidens=25,
                catches=20,
                stumpings=0,
                run_outs=3,
            ),
            PlayerProfile(
                player_id="player-003",
                player_name="Virat Kohli",
                total_matches=60,
                total_innings_batted=60,
                total_runs_scored=3200,
                total_balls_faced=2400,
                total_fours=320,
                total_sixes=80,
                times_out=48,
                highest_score=183,
                centuries=12,
                half_centuries=18,
                total_innings_bowled=5,
                total_overs_bowled=10.0,
                total_runs_conceded=120,
                total_wickets=2,
                best_bowling_figures="1/25",
                five_wicket_hauls=0,
                maidens=0,
                catches=35,
                stumpings=0,
                run_outs=12,
            ),
        ]

        for player in players:
            db.add(player)

        await db.commit()
        print(f"✓ Created {len(players)} player profiles")

        # Add some achievements
        achievements = [
            PlayerAchievement(
                player_id="player-001",
                achievement_type=AchievementType.century,
                title="Century Master",
                description="Scored 150 runs in a match",
                badge_icon="💯",
                achievement_metadata={"runs": 150, "balls": 120},
            ),
            PlayerAchievement(
                player_id="player-002",
                achievement_type=AchievementType.five_wickets,
                title="Five-Wicket Hero",
                description="Took 5 wickets for 28 runs",
                badge_icon="🎳",
                achievement_metadata={"wickets": 5, "runs": 28},
            ),
            PlayerAchievement(
                player_id="player-003",
                achievement_type=AchievementType.best_scorer,
                title="Best Scorer of the Match",
                description="Top scorer with 183 runs",
                badge_icon="🏏",
                achievement_metadata={"runs": 183, "match": "Match #45"},
            ),
        ]

        for achievement in achievements:
            db.add(achievement)

        await db.commit()
        print(f"✓ Created {len(achievements)} achievements")


async def display_profiles():
    """Display all player profiles."""
    assert SessionLocal is not None, "Database not initialized"  # nosec
    async with SessionLocal() as db:
        print("\n" + "=" * 80)
        print("PLAYER PROFILES")
        print("=" * 80)

        result = await db.execute(select(PlayerProfile))
        profiles = result.scalars().all()

        for profile in profiles:
            print(f"\n👤 {profile.player_name} (ID: {profile.player_id})")
            print("-" * 80)
            print(f"  📊 Matches: {profile.total_matches}")
            print(
                "  🏏 Batting: "
                + f"{profile.total_runs_scored} runs @ avg {profile.batting_average:.2f}, "
                + f"SR {profile.strike_rate:.2f}"
            )
            print(
                "            Centuries: "
                + f"{profile.centuries}, 50s: {profile.half_centuries}, "
                + f"HS: {profile.highest_score}"
            )
            print(
                "  ⚾ Bowling: "
                + f"{profile.total_wickets} wickets @ avg {profile.bowling_average:.2f}, "
                + f"Econ {profile.economy_rate:.2f}"
            )
            print(
                "            Best: "
                + f"{profile.best_bowling_figures or 'N/A'}, 5W: {profile.five_wicket_hauls}"
            )
            print(
                "  🧤 Fielding: "
                + f"{profile.catches} catches, {profile.stumpings} stumpings, "
                + f"{profile.run_outs} run-outs"
            )


async def display_leaderboards():
    """Display top 3 in various leaderboards."""
    assert SessionLocal is not None, "Database not initialized"  # nosec
    async with SessionLocal() as db:
        print("\n" + "=" * 80)
        print("LEADERBOARDS")
        print("=" * 80)

        # Most runs
        print("\n🏆 Most Runs:")
        result = await db.execute(
            select(PlayerProfile)
            .order_by(PlayerProfile.total_runs_scored.desc())
            .limit(3)
        )
        for rank, profile in enumerate(result.scalars().all(), 1):
            print(f"  {rank}. {profile.player_name}: {profile.total_runs_scored} runs")

        # Most wickets
        print("\n🏆 Most Wickets:")
        result = await db.execute(
            select(PlayerProfile).order_by(PlayerProfile.total_wickets.desc()).limit(3)
        )
        for rank, profile in enumerate(result.scalars().all(), 1):
            print(f"  {rank}. {profile.player_name}: {profile.total_wickets} wickets")

        # Best batting average
        print("\n🏆 Best Batting Average (min 10 dismissals):")
        result = await db.execute(
            select(PlayerProfile)
            .where(PlayerProfile.times_out >= 10)
            .order_by(
                (PlayerProfile.total_runs_scored / PlayerProfile.times_out).desc()
            )
            .limit(3)
        )
        for rank, profile in enumerate(result.scalars().all(), 1):
            print(f"  {rank}. {profile.player_name}: {profile.batting_average:.2f}")


async def display_achievements():
    """Display all achievements."""
    assert SessionLocal is not None, "Database not initialized"  # nosec
    async with SessionLocal() as db:
        print("\n" + "=" * 80)
        print("ACHIEVEMENTS")
        print("=" * 80)

        result = await db.execute(
            select(PlayerAchievement).order_by(PlayerAchievement.earned_at.desc())
        )
        achievements = result.scalars().all()

        for achievement in achievements:
            print(f"\n{achievement.badge_icon or '🏅'} {achievement.title}")
            print(f"  Player: {achievement.player_id}")
            print(f"  {achievement.description}")
            print(f"  Type: {achievement.achievement_type.value}")


async def main():
    """Main demo function."""
    print("\n" + "=" * 80)
    print("PLAYER PROFILES FEATURE DEMO")
    print("=" * 80)

    # Ensure DB is initialised when running this script directly
    with contextlib.suppress(Exception):
        db.init_engine()

    # Create sample data
    await create_sample_profiles()

    # Display profiles
    await display_profiles()

    # Display leaderboards
    await display_leaderboards()

    # Display achievements
    await display_achievements()

    print("\n" + "=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)
    print("\nAPI Endpoints available:")
    print("  GET  /api/players/{player_id}/profile")
    print("  GET  /api/players/{player_id}/achievements")
    print("  POST /api/players/{player_id}/achievements")
    print("  GET  /api/players/leaderboard?metric={metric}&limit={limit}")
    print("\nFrontend Routes:")
    print("  /players/{player_id}/profile - View player profile")
    print("  /leaderboard - View leaderboards")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
