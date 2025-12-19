"""
API routes for ball type clustering analysis.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_async_db
from backend.services.ball_type_clusterer import (
    BallTypeClusterer,
    DeliveryType,
)
from backend.sql_app.models import (
    Player,
    BowlingScorecard,
    BattingScorecard,
    Game,
)

router = APIRouter(prefix="/ball-clustering", tags=["ball_clustering"])


@router.get("/bowlers/{bowler_id}/delivery-clusters")
async def get_bowler_delivery_clusters(
    bowler_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get delivery type clusters for a bowler.
    Shows primary delivery types, variation, and effectiveness.
    """
    try:
        # Fetch bowler
        stmt = select(Player).where(Player.id == bowler_id)
        result = await db.execute(stmt)
        bowler = result.scalar_one_or_none()

        if not bowler:
            raise HTTPException(status_code=404, detail="Bowler not found")

        # Fetch all bowling scorecards
        stmt = select(BowlingScorecard).where(
            BowlingScorecard.bowler_id == bowler_id
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        if not scorecards:
            return {
                "status": "success",
                "bowler_id": bowler_id,
                "bowler_name": bowler.name,
                "message": "No bowling data available",
                "profile": None,
            }

        # Create delivery list from scorecards
        deliveries = [
            {
                "delivery_id": f"{sc.id}_delivery_{i}",
                "bowler_id": bowler_id,
                "bowler_name": bowler.name,
                "pace": 70,  # Default, would come from detailed delivery data
                "spin": 0,
                "line": "middle",  # Would vary in real data
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": sc.runs_conceded // max(1, sc.deliveries_bowled),
                "is_wicket": sc.wickets > 0,
            }
            for sc in scorecards
            for i in range(max(1, sc.deliveries_bowled))
        ]

        # Analyze bowler
        profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id=bowler_id,
            bowler_name=bowler.name,
            deliveries=deliveries,
        )

        return {
            "status": "success",
            "bowler_id": bowler_id,
            "bowler_name": bowler.name,
            "profile": {
                "total_deliveries": profile.total_deliveries,
                "delivery_clusters": [
                    {
                        "cluster_id": c.cluster_id,
                        "delivery_type": c.delivery_type,
                        "cluster_name": c.cluster_name,
                        "description": c.description,
                        "sample_count": c.sample_count,
                        "effectiveness_percentage": round(c.effectiveness_percentage, 1),
                        "success_rate": round(c.success_rate, 1),
                        "average_runs_conceded": c.average_runs_conceded,
                    }
                    for c in profile.delivery_clusters
                ],
                "primary_clusters": profile.primary_clusters,
                "variation_score": round(profile.variation_score, 1),
                "clustering_accuracy": round(profile.clustering_accuracy, 1),
                "most_effective_cluster": profile.most_effective_cluster,
                "least_effective_cluster": profile.least_effective_cluster,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster analysis failed: {str(e)}")


@router.get("/batters/{batter_id}/delivery-vulnerabilities")
async def get_batter_delivery_vulnerabilities(
    batter_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Analyze batter's vulnerability to different ball types.
    """
    try:
        # Fetch batter
        stmt = select(Player).where(Player.id == batter_id)
        result = await db.execute(stmt)
        batter = result.scalar_one_or_none()

        if not batter:
            raise HTTPException(status_code=404, detail="Batter not found")

        # Fetch all batting scorecards
        stmt = select(BattingScorecard).where(
            BattingScorecard.player_id == batter_id
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        if not scorecards:
            return {
                "status": "success",
                "batter_id": batter_id,
                "batter_name": batter.name,
                "message": "No batting data available",
                "vulnerability": None,
            }

        # Create faced deliveries list
        faced_deliveries = [
            {
                "delivery_id": f"{sc.id}_faced_{i}",
                "pace": 70,  # Would come from detailed data
                "spin": 0,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": sc.runs_scored // max(1, sc.deliveries_faced),
                "is_wicket": sc.is_dismissed,
            }
            for sc in scorecards
            for i in range(max(1, sc.deliveries_faced))
        ]

        # Analyze vulnerabilities
        vulnerability = BallTypeClusterer.analyze_batter_vulnerabilities(
            batter_id=batter_id,
            batter_name=batter.name,
            faced_deliveries=faced_deliveries,
        )

        return {
            "status": "success",
            "batter_id": batter_id,
            "batter_name": batter.name,
            "vulnerability": {
                "vulnerable_clusters": vulnerability.vulnerable_clusters,
                "vulnerable_delivery_types": {
                    k: round(v, 2)
                    for k, v in vulnerability.vulnerable_delivery_types.items()
                },
                "strong_against": vulnerability.strong_against,
                "dismissal_delivery_types": vulnerability.dismissal_delivery_types,
                "recommended_bowling_strategy": vulnerability.recommended_bowling_strategy,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vulnerability analysis failed: {str(e)}")


@router.get("/matchups/{bowler_id}/vs/{batter_id}/cluster-analysis")
async def get_matchup_cluster_analysis(
    bowler_id: str,
    batter_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Analyze bowler's delivery clusters vs batter's vulnerabilities.
    """
    try:
        # Fetch both players
        bowler_stmt = select(Player).where(Player.id == bowler_id)
        bowler_result = await db.execute(bowler_stmt)
        bowler = bowler_result.scalar_one_or_none()

        batter_stmt = select(Player).where(Player.id == batter_id)
        batter_result = await db.execute(batter_stmt)
        batter = batter_result.scalar_one_or_none()

        if not bowler:
            raise HTTPException(status_code=404, detail="Bowler not found")
        if not batter:
            raise HTTPException(status_code=404, detail="Batter not found")

        # Get bowler scorecards
        bowler_stmt = select(BowlingScorecard).where(
            BowlingScorecard.bowler_id == bowler_id
        )
        bowler_result = await db.execute(bowler_stmt)
        bowler_scorecards = bowler_result.scalars().all()

        # Get batter scorecards
        batter_stmt = select(BattingScorecard).where(
            BattingScorecard.player_id == batter_id
        )
        batter_result = await db.execute(batter_stmt)
        batter_scorecards = batter_result.scalars().all()

        if not bowler_scorecards or not batter_scorecards:
            return {
                "status": "success",
                "bowler_id": bowler_id,
                "batter_id": batter_id,
                "message": "Insufficient data for matchup analysis",
                "analysis": None,
            }

        # Create delivery lists
        bowler_deliveries = [
            {
                "delivery_id": f"{sc.id}_b_{i}",
                "pace": 70,
                "spin": 0,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": sc.runs_conceded // max(1, sc.deliveries_bowled),
                "is_wicket": sc.wickets > 0,
            }
            for sc in bowler_scorecards
            for i in range(max(1, sc.deliveries_bowled))
        ]

        batter_faced = [
            {
                "delivery_id": f"{sc.id}_f_{i}",
                "pace": 70,
                "spin": 0,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": sc.runs_scored // max(1, sc.deliveries_faced),
                "is_wicket": sc.is_dismissed,
            }
            for sc in batter_scorecards
            for i in range(max(1, sc.deliveries_faced))
        ]

        # Analyze both
        bowler_profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id=bowler_id,
            bowler_name=bowler.name,
            deliveries=bowler_deliveries,
        )

        batter_vulnerability = BallTypeClusterer.analyze_batter_vulnerabilities(
            batter_id=batter_id,
            batter_name=batter.name,
            faced_deliveries=batter_faced,
        )

        # Find overlap (bowler's strong deliveries vs batter's vulnerabilities)
        overlap_clusters = list(
            set(bowler_profile.primary_clusters)
            & set(batter_vulnerability.vulnerable_clusters)
        )

        recommendation = ""
        if overlap_clusters:
            recommendation = f"Use {', '.join(overlap_clusters)} for maximum effectiveness"
        else:
            if bowler_profile.most_effective_cluster:
                recommendation = f"Primary strategy: {bowler_profile.most_effective_cluster}"

        return {
            "status": "success",
            "bowler_id": bowler_id,
            "batter_id": batter_id,
            "analysis": {
                "bowler_primary_clusters": bowler_profile.primary_clusters,
                "batter_vulnerable_clusters": batter_vulnerability.vulnerable_clusters,
                "effective_overlap": overlap_clusters,
                "bowler_variation_score": round(bowler_profile.variation_score, 1),
                "strategic_recommendation": recommendation,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matchup analysis failed: {str(e)}")


@router.get("/cluster-types")
async def get_cluster_types():
    """Get all available delivery cluster types."""
    cluster_types = [
        {
            "type": dtype,
            "name": dtype.replace("_", " ").title(),
            "description": BallTypeClusterer.CLUSTER_DEFINITIONS.get(dtype, {}).get(
                "description", ""
            ),
        }
        for dtype in DeliveryType
    ]

    return {
        "status": "success",
        "cluster_types": cluster_types,
        "total_types": len(cluster_types),
    }
