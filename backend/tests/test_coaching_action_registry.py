from __future__ import annotations

import pytest

from backend.services.coaching_action_registry import (
    ACTION_REGISTRY_VERSION,
    COACHING_ACTIONS,
    governed_actions_for,
)


@pytest.mark.parametrize(
    ("metric_id", "discipline", "phase"),
    [
        ("batting_setup_head_alignment_ratio", "batting", "setup"),
        ("pace_bowling_release_arm_angle_degrees", "pace_bowling", "release"),
        ("spin_bowling_pivot_alignment_ratio", "spin_bowling", "pivot"),
        ("wicketkeeping_ready_base_width_ratio", "wicketkeeping", "ready"),
        ("fielding_transfer_balance_ratio", "fielding", "transfer"),
    ],
)
def test_registry_covers_each_discipline_without_cross_contamination(
    metric_id: str, discipline: str, phase: str
) -> None:
    actions = governed_actions_for(metric_id=metric_id, discipline=discipline, phase=phase)

    assert actions
    assert {action["discipline"] for action in actions} == {discipline}
    assert all(action["version"] == ACTION_REGISTRY_VERSION for action in actions)


def test_registry_actions_are_coach_governed_and_provenanced() -> None:
    assert COACHING_ACTIONS
    for action in COACHING_ACTIONS:
        payload = action.as_payload()
        assert payload["review_status"] == "approved_for_coach_review"
        assert payload["requires_coach_approval"] is True
        assert payload["player_facing_eligible"] is False
        assert payload["provenance"]
        assert payload["why_it_matters"]
        assert payload["coaching_objective"]
        assert payload["coaching_cue"]
        assert payload["drills"]
        assert payload["coach_observation"]
        assert payload["reassessment_criterion"]


def test_generic_bowling_mode_does_not_guess_pace_or_spin() -> None:
    assert (
        governed_actions_for(
            metric_id="bowling_release_alignment_ratio",
            discipline="bowling",
            phase="release",
        )
        == []
    )


def test_metric_prefix_is_authoritative_over_mismatched_discipline() -> None:
    actions = governed_actions_for(
        metric_id="fielding_collection_head_base_ratio",
        discipline="batting",
        phase="collection",
    )

    assert actions
    assert {action["discipline"] for action in actions} == {"fielding"}
