from __future__ import annotations

import pytest

from backend.services import (
    batting_v2_metric_pack,
    bowling_v2_metric_pack,
    fielding_v2_metric_pack,
    wicketkeeping_v2_metric_pack,
)
from backend.services.coaching_action_registry import (
    ACTION_REGISTRY_VERSION,
    COACHING_ACTIONS,
    PRODUCTION_METRIC_ACTION_CONTRACTS,
    governed_actions_for,
)


@pytest.mark.parametrize(
    "metric_id",
    sorted(PRODUCTION_METRIC_ACTION_CONTRACTS),
)
def test_every_production_metric_maps_to_its_exact_governed_action(metric_id: str) -> None:
    discipline, phase, expected_action_id = PRODUCTION_METRIC_ACTION_CONTRACTS[metric_id]
    actions = governed_actions_for(metric_id=metric_id, discipline=discipline, phase=phase)

    assert [action["action_id"] for action in actions] == [expected_action_id]
    assert {action["discipline"] for action in actions} == {discipline}
    assert all(action["version"] == ACTION_REGISTRY_VERSION for action in actions)


def test_registry_contract_covers_all_five_production_metric_packs() -> None:
    production_metric_ids = (
        batting_v2_metric_pack._BATTING_V2_METRIC_IDS
        | bowling_v2_metric_pack._PACE_BOWLING_METRIC_IDS
        | bowling_v2_metric_pack._SPIN_BOWLING_METRIC_IDS
        | wicketkeeping_v2_metric_pack._WICKETKEEPING_V2_METRIC_IDS
        | fielding_v2_metric_pack._FIELDING_V2_METRIC_IDS
    )

    assert set(PRODUCTION_METRIC_ACTION_CONTRACTS) == production_metric_ids
    assert {contract[0] for contract in PRODUCTION_METRIC_ACTION_CONTRACTS.values()} == {
        "batting",
        "pace_bowling",
        "spin_bowling",
        "wicketkeeping",
        "fielding",
    }


@pytest.mark.parametrize(
    ("metric_id", "discipline", "phase", "expected_action_id"),
    [
        (
            "batting_setup_head_alignment_ratio",
            "batting",
            "setup",
            "batting-base-alignment",
        ),
        (
            "pace_bowling_release_arm_angle_degrees",
            "pace_bowling",
            "release",
            "pace-release-follow-through",
        ),
        (
            "spin_bowling_pivot_alignment_ratio",
            "spin_bowling",
            "pivot",
            "spin-gather-pivot",
        ),
        (
            "wicketkeeping_ready_base_width_ratio",
            "wicketkeeping",
            "ready",
            "keeping-ready-movement",
        ),
        (
            "fielding_transfer_balance_ratio",
            "fielding",
            "transfer",
            "fielding-transfer-throw",
        ),
    ],
)
def test_compatibility_aliases_are_exact_and_documented_by_contract(
    metric_id: str, discipline: str, phase: str, expected_action_id: str
) -> None:
    actions = governed_actions_for(metric_id=metric_id, discipline=discipline, phase=phase)

    assert [action["action_id"] for action in actions] == [expected_action_id]


def test_registry_actions_are_coach_governed_and_provenanced() -> None:
    assert COACHING_ACTIONS
    for action in COACHING_ACTIONS:
        payload = action.as_payload()
        assert payload["review_status"] == "approved_for_coach_review"
        assert payload["requires_coach_approval"] is True
        assert payload["player_facing_eligible"] is False
        assert payload["provenance"]
        assert payload["metric_ids"]
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


def test_discipline_mismatch_does_not_cross_map() -> None:
    assert (
        governed_actions_for(
            metric_id="fielding_ready_stance_width_ratio",
            discipline="batting",
            phase="ready",
        )
        == []
    )


def test_phase_mismatch_does_not_cross_map() -> None:
    assert (
        governed_actions_for(
            metric_id="wicketkeeping_set_stance_width_ratio",
            discipline="wicketkeeping",
            phase="ready",
        )
        == []
    )


@pytest.mark.parametrize(
    "metric_id",
    [
        "fielding_unrelated_balance_ratio",
        "fielding_ready_stance_width_ratio_extra",
        "batting_fielding_ready_stance_width_ratio",
    ],
)
def test_unrelated_or_fuzzy_metric_ids_do_not_map(metric_id: str) -> None:
    assert governed_actions_for(metric_id=metric_id, discipline="fielding", phase="ready") == []
