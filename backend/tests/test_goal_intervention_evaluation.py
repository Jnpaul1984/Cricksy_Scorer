from __future__ import annotations

from backend.services.goal_intervention_evaluation import evaluate_v2_goals_against_longitudinal


def _observation(
    job_id: str, raw: float | None, *, comparable: bool = True, normalized: float | None = None
):
    return {
        "session_id": f"session-{job_id}",
        "job_id": job_id,
        "raw_value": raw,
        "normalized_score": normalized,
        "unit": "score",
        "confidence_score": 0.8,
        "comparable": comparable,
        "within_session_consistency": {"value": 0.2},
    }


def _series(
    history: list[dict],
    *,
    metric_id: str = "batting_downswing_head_stability_score",
    discipline: str = "batting",
):
    return {
        "discipline": discipline,
        "metric_id": metric_id,
        "phase": "downswing",
        "action_type": None,
        "comparable_session_count": len([item for item in history if item.get("comparable")]),
        "trend": {"confidence_score": 0.7, "limitations": []},
        "history": history,
    }


def _progress(series: list[dict]):
    return {"series": series}


def test_goal_evaluation_higher_target_achieved() -> None:
    goals = [
        {
            "goal_id": "g1",
            "player_id": "p1",
            "discipline": "batting",
            "metric_id": "batting_downswing_head_stability_score",
            "phase": "downswing",
            "target_type": "increase_to_threshold",
            "target_value": 0.7,
        }
    ]
    payload = _progress([_series([_observation("j1", 0.55), _observation("j2", 0.74)])])

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j2",
    )

    assert result[0]["status"] == "achieved"
    assert result[0]["baseline"]["raw_value"] == 0.55
    assert result[0]["latest"]["raw_value"] == 0.74


def test_goal_evaluation_lower_target_regressing() -> None:
    goals = [
        {
            "goal_id": "g2",
            "player_id": "p1",
            "discipline": "wicketkeeping",
            "metric_id": "wicketkeeping_movement_lateral_displacement_ratio",
            "target_type": "decrease_to_threshold",
            "target_value": 0.4,
        }
    ]
    payload = _progress(
        [
            _series(
                [_observation("j1", 0.5), _observation("j2", 0.7)],
                metric_id="wicketkeeping_movement_lateral_displacement_ratio",
                discipline="wicketkeeping",
            )
        ]
    )

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j2",
    )

    assert result[0]["status"] == "regressing"


def test_goal_evaluation_range_target_unchanged() -> None:
    goals = [
        {
            "goal_id": "g3",
            "player_id": "p1",
            "discipline": "batting",
            "metric_id": "batting_setup_stance_width_ratio",
            "target_type": "stay_within_range",
            "target_min": 1.1,
            "target_max": 1.3,
        }
    ]
    payload = _progress(
        [
            _series(
                [_observation("j1", 1.6), _observation("j2", 1.61)],
                metric_id="batting_setup_stance_width_ratio",
            )
        ]
    )

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j2",
    )

    assert result[0]["status"] == "unchanged"


def test_goal_evaluation_insufficient_data() -> None:
    goals = [
        {
            "goal_id": "g4",
            "player_id": "p1",
            "discipline": "batting",
            "metric_id": "batting_downswing_head_stability_score",
            "target_type": "increase_to_threshold",
            "target_value": 0.7,
        }
    ]
    payload = _progress([_series([_observation("j1", 0.55)])])

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j1",
    )

    assert result[0]["status"] == "insufficient_data"


def test_goal_evaluation_non_comparable_latest_session() -> None:
    goals = [
        {
            "goal_id": "g5",
            "player_id": "p1",
            "discipline": "batting",
            "metric_id": "batting_downswing_head_stability_score",
            "target_type": "increase_to_threshold",
            "target_value": 0.7,
        }
    ]
    payload = _progress(
        [
            _series(
                [
                    _observation("j1", 0.55, comparable=True),
                    _observation("j2", 0.74, comparable=False),
                ]
            )
        ]
    )

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j2",
    )

    assert result[0]["status"] == "non_comparable"


def test_goal_evaluation_unsupported_target_type() -> None:
    goals = [
        {
            "goal_id": "g6",
            "player_id": "p1",
            "discipline": "batting",
            "metric_id": "batting_downswing_head_stability_score",
            "target_type": "custom_direction",
            "target_value": 0.7,
        }
    ]
    payload = _progress([_series([_observation("j1", 0.55), _observation("j2", 0.74)])])

    result = evaluate_v2_goals_against_longitudinal(
        v2_goals=goals,
        longitudinal_progress=payload,
        latest_job_id="j2",
    )

    assert result[0]["status"] == "unsupported"
