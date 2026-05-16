"""
Phase 9H.1 — Coaching Video Evidence Skill Contract Tests.

Contract-shape only tests for coaching_video_evidence_skill.v1.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


def _contract() -> dict[str, object]:
    from backend.domain.player_development_skill_contract import (
        PLAYER_DEVELOPMENT_SKILL_REGISTRY,
    )

    return PLAYER_DEVELOPMENT_SKILL_REGISTRY["coaching_video_evidence_skill.v1"]


def test_skill_exists_in_registry() -> None:
    from backend.domain.player_development_skill_contract import (
        PLAYER_DEVELOPMENT_SKILL_REGISTRY,
    )

    assert "coaching_video_evidence_skill.v1" in PLAYER_DEVELOPMENT_SKILL_REGISTRY


def test_skill_metadata_id_version_name_description() -> None:
    contract = _contract()

    assert contract["skill_id"] == "coaching_video_evidence_skill.v1"
    assert contract["version"] == "1.0.0"
    assert contract["name"] == "Coaching Video Evidence Skill"
    assert "coach-reviewable" in str(contract["purpose"]).lower()


def test_skill_allows_only_appropriate_coach_org_roles() -> None:
    contract = _contract()
    allowed_roles = contract["allowed_roles"]

    assert allowed_roles == ["coach_pro_plus", "org_pro"]


def test_required_structured_video_evidence_inputs_are_declared() -> None:
    contract = _contract()
    required_inputs = set(contract["required_inputs"])  # type: ignore[arg-type]

    expected_required = {
        "player_profile_id",
        "coach_user_id",
        "org_id",
        "video_session_id",
        "video_analysis_job_id",
        "analysis_mode",
        "evidence_markers",
        "evidence_markers[].metric_name",
        "evidence_markers[].timestamp_s",
        "evidence_markers[].frame_num",
        "evidence_markers[].score",
        "evidence_markers[].threshold",
        "evidence_markers[].finding_label",
    }
    assert expected_required.issubset(required_inputs)


def test_required_video_job_session_mode_and_markers_inputs() -> None:
    contract = _contract()
    required_inputs = set(contract["required_inputs"])  # type: ignore[arg-type]

    for field in (
        "video_analysis_job_id",
        "video_session_id",
        "analysis_mode",
        "evidence_markers",
    ):
        assert field in required_inputs


def test_output_contract_has_reviewable_evidence_confidence_fields() -> None:
    contract = _contract()
    output_contract = contract["output_contract"]
    assert isinstance(output_contract, dict)

    required_fields = set(output_contract["required_fields"])  # type: ignore[index]
    expected = {
        "recommendation_id",
        "skill_id",
        "skill_version",
        "player_profile_id",
        "video_session_id",
        "video_analysis_job_id",
        "analysis_mode",
        "confidence_score",
        "limitations",
        "evidence_refs",
        "recommendation_text",
        "suggested_drills",
        "focus_areas",
        "approval_state",
        "is_official_truth",
        "requires_review",
        "generated_at",
        "ai_metadata",
    }
    assert expected.issubset(required_fields)


def test_review_and_approval_required_before_player_facing_use() -> None:
    contract = _contract()
    output_contract = contract["output_contract"]

    assert contract["review_required"] is True
    assert contract["approval_required_before_activation"] is True
    assert output_contract["requires_coach_review_before_player_facing_use"] is True  # type: ignore[index]


def test_forbidden_outputs_include_official_truth_mutation_fields() -> None:
    contract = _contract()
    forbidden_outputs = set(contract["forbidden_outputs"])  # type: ignore[arg-type]

    expected_forbidden = {
        "scorecard_mutation",
        "match_result_mutation",
        "innings_state_mutation",
        "dls_mutation",
        "player_stats_mutation",
        "official_cricket_truth_assertion",
    }
    assert expected_forbidden.issubset(forbidden_outputs)


def test_contract_declares_governance_rules_for_advisory_reviewed_output() -> None:
    contract = _contract()
    safety_rules = set(contract["safety_rules"])  # type: ignore[arg-type]
    validation_rules = set(contract["validation_rules"])  # type: ignore[arg-type]
    evidence_requirements = str(contract["evidence_ref_requirements"]).lower()
    no_truth_mutation_rule = str(contract["no_official_truth_mutation_rule"]).lower()

    assert "coach_remains_authority_for_player_development_decisions" in safety_rules
    assert "must_require_coach_review_before_player_facing_use" in validation_rules
    assert "execution_must_be_event_triggered_not_always_running" in validation_rules
    assert "timestamp" in evidence_requirements
    assert "official cricket truth" in no_truth_mutation_rule
