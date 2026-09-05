from __future__ import annotations

import pytest

from backend.domain.coach_analysis_v2_contract import (
    CaptureProfile,
    CoachingMetricResultV2,
    ValidityState,
)
from backend.services.batting_v2_metric_pack import build_batting_v2_findings_insights
from backend.services.bowling_v2_metric_pack import build_bowling_v2_findings_insights
from backend.services.fielding_v2_metric_pack import build_fielding_v2_findings_insights
from backend.services.wicketkeeping_v2_metric_pack import build_wicketkeeping_v2_findings_insights


def _metric(metric_id: str, discipline: str) -> CoachingMetricResultV2:
    return CoachingMetricResultV2(
        metric_version="pose_metrics.v1",
        metric_id=metric_id,
        discipline=discipline,
        raw_value=0.42,
        unit="score",
        normalized_score=0.42,
        confidence_score=0.42,
        validity_state=ValidityState.LOW_CONFIDENCE,
        unavailable_reason="Measurement confidence was too low to treat this as a coaching weakness.",
        capture_profile=CaptureProfile(
            camera_view="side",
            sample_fps=10.0,
            effective_analysis_fps=10.0,
            source_video_fps=30.0,
            analysis_mode=discipline,
            discipline=discipline,
            metric_version="pose_metrics.v1",
            source_model="MediaPipe Pose Landmarker Full",
        ),
    )


@pytest.mark.parametrize(
    ("builder", "metric_id", "discipline"),
    [
        (build_batting_v2_findings_insights, "batting_downswing_head_stability_score", "batting"),
        (
            build_bowling_v2_findings_insights,
            "pace_bowling_approach_head_stability_score",
            "pace_bowling",
        ),
        (
            build_wicketkeeping_v2_findings_insights,
            "wicketkeeping_reaction_head_stability_score",
            "wicketkeeping",
        ),
        (
            build_fielding_v2_findings_insights,
            "fielding_reaction_head_stability_score",
            "fielding",
        ),
    ],
)
def test_low_confidence_metrics_are_not_reported_as_concerns(
    builder, metric_id: str, discipline: str
) -> None:
    insights = builder([_metric(metric_id, discipline)])

    assert insights["strengths"] == []
    assert insights["concerns"] == []
    assert insights["limitations"][0]["metric_id"] == metric_id
