"""
Phase 9G — Player Development Skill Contract Tests.

Validates the shape and governance rules of every skill in the
Player Development Skill Contract Registry.

Tests are contract-shape only — no DB, no AI calls, no live generation.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


# ---------------------------------------------------------------------------
# 1. Registry is deterministically importable
# ---------------------------------------------------------------------------


class TestRegistryImport:
    """Contract registry must import without errors and be deterministic."""

    def test_registry_imports_cleanly(self) -> None:
        from backend.domain.player_development_skill_contract import (  # noqa: F401
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
            REQUIRED_CONTRACT_FIELDS,
            REQUIRED_FALLBACK_STATES,
            REQUIRED_FORBIDDEN_OUTPUT_TERMS,
            REQUIRED_SKILL_IDS,
            get_skill_contract,
        )

    def test_registry_is_a_dict(self) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        assert isinstance(PLAYER_DEVELOPMENT_SKILL_REGISTRY, dict)

    def test_registry_is_non_empty(self) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        assert len(PLAYER_DEVELOPMENT_SKILL_REGISTRY) > 0

    def test_registry_is_deterministic(self) -> None:
        """Importing twice should return identical results."""
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY as reg1,
        )
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY as reg2,
        )

        assert reg1 is reg2

    def test_get_skill_contract_returns_registered_skill(self) -> None:
        from backend.domain.player_development_skill_contract import get_skill_contract

        contract = get_skill_contract("player_weakness_detection.v1")
        assert isinstance(contract, dict)
        assert contract["skill_id"] == "player_weakness_detection.v1"

    def test_get_skill_contract_raises_for_unknown_skill(self) -> None:
        from backend.domain.player_development_skill_contract import get_skill_contract

        with pytest.raises(KeyError, match="not registered"):
            get_skill_contract("nonexistent_skill.v1")


# ---------------------------------------------------------------------------
# 2. All required skills are present
# ---------------------------------------------------------------------------


REQUIRED_SKILL_IDS_EXPECTED = {
    "player_weakness_detection.v1",
    "player_development_plan.v1",
    "drill_recommendation.v1",
    "progress_checkpoint_summary.v1",
    "team_development_overview.v1",
    "player_development_report.v1",
}


class TestRequiredSkillsPresent:
    """All six Phase 9G required skills must be in the registry."""

    @pytest.mark.parametrize("skill_id", sorted(REQUIRED_SKILL_IDS_EXPECTED))
    def test_skill_is_registered(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        assert (
            skill_id in PLAYER_DEVELOPMENT_SKILL_REGISTRY
        ), f"Required skill '{skill_id}' is missing from the registry."

    def test_all_required_skills_present(self) -> None:
        from backend.domain.player_development_skill_contract import REQUIRED_SKILL_IDS

        missing = REQUIRED_SKILL_IDS_EXPECTED - REQUIRED_SKILL_IDS
        assert not missing, f"Missing required skills: {missing}"


# ---------------------------------------------------------------------------
# 3. Every skill has all required fields
# ---------------------------------------------------------------------------


def _all_skill_ids() -> list[str]:
    from backend.domain.player_development_skill_contract import (
        PLAYER_DEVELOPMENT_SKILL_REGISTRY,
    )

    return list(PLAYER_DEVELOPMENT_SKILL_REGISTRY.keys())


class TestRequiredFieldsPresent:
    """Every skill must define all required contract fields."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_all_required_fields_present(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
            REQUIRED_CONTRACT_FIELDS,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        missing = REQUIRED_CONTRACT_FIELDS - set(contract.keys())
        assert not missing, f"Skill '{skill_id}' is missing required fields: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 4. Every skill has a versioned skill_id
# ---------------------------------------------------------------------------


class TestVersionedSkillId:
    """Every skill must have a versioned skill_id (format: name.vN)."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_skill_id_is_versioned(self, skill_id: str) -> None:
        assert (
            ".v" in skill_id
        ), f"Skill ID '{skill_id}' does not follow the versioned format 'name.vN'."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_skill_id_matches_registry_key(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        assert (
            contract["skill_id"] == skill_id
        ), f"skill_id field '{contract['skill_id']}' does not match registry key '{skill_id}'."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_version_field_is_present_and_string(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        assert isinstance(
            contract.get("version"), str
        ), f"Skill '{skill_id}' version field must be a string."


# ---------------------------------------------------------------------------
# 5. Every skill declares no_official_truth_mutation_rule
# ---------------------------------------------------------------------------


class TestNoOfficialTruthMutationRule:
    """Every skill must explicitly declare the no-official-truth-mutation rule."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_no_official_truth_mutation_rule_is_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rule = contract.get("no_official_truth_mutation_rule", "")
        assert (
            isinstance(rule, str) and len(rule) > 0
        ), f"Skill '{skill_id}' must declare a non-empty no_official_truth_mutation_rule."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_no_official_truth_mutation_rule_references_guard(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rule = contract.get("no_official_truth_mutation_rule", "")
        assert "validate_no_official_truth_mutation" in rule, (
            f"Skill '{skill_id}' no_official_truth_mutation_rule must reference "
            "validate_no_official_truth_mutation."
        )

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_validation_rules_includes_no_official_truth_mutation_call(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        validation_rules = contract.get("validation_rules", [])
        assert "must_call_validate_no_official_truth_mutation" in validation_rules, (
            f"Skill '{skill_id}' validation_rules must include "
            "'must_call_validate_no_official_truth_mutation'."
        )

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_ai_boundary_metadata_is_not_official_truth(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        meta = contract.get("ai_boundary_metadata", {})
        assert (
            meta.get("is_official_truth") is False
        ), f"Skill '{skill_id}' ai_boundary_metadata.is_official_truth must be False."


# ---------------------------------------------------------------------------
# 6. Every skill declares no_fake_data_rule
# ---------------------------------------------------------------------------


class TestNoFakeDataRule:
    """Every skill must explicitly declare the no-fake-data rule."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_no_fake_data_rule_is_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rule = contract.get("no_fake_data_rule", "")
        assert (
            isinstance(rule, str) and len(rule) > 0
        ), f"Skill '{skill_id}' must declare a non-empty no_fake_data_rule."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_no_fake_data_rule_references_insufficient_data(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rule = contract.get("no_fake_data_rule", "")
        assert (
            "insufficient_data" in rule
        ), f"Skill '{skill_id}' no_fake_data_rule must reference the insufficient_data fallback."


# ---------------------------------------------------------------------------
# 7. Every skill declares youth_safety_rules (non-empty)
# ---------------------------------------------------------------------------


class TestYouthSafetyRules:
    """Every skill must declare non-empty youth safety rules."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_youth_safety_rules_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rules = contract.get("youth_safety_rules")
        assert (
            isinstance(rules, list) and len(rules) > 0
        ), f"Skill '{skill_id}' must declare a non-empty youth_safety_rules list."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_youth_safety_rules_include_no_negative_labels(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        rules = contract.get("youth_safety_rules", [])
        # At least one rule must address negative comparative labels
        has_negative_label_rule = any(
            "negative" in r or "label" in r or "ranking" in r for r in rules
        )
        assert has_negative_label_rule, (
            f"Skill '{skill_id}' youth_safety_rules must include a rule "
            "addressing negative labels or rankings."
        )


# ---------------------------------------------------------------------------
# 8. Every skill declares evidence_ref_requirements
# ---------------------------------------------------------------------------


class TestEvidenceRefRequirements:
    """Every skill must declare evidence reference requirements."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_evidence_ref_requirements_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        req = contract.get("evidence_ref_requirements", "")
        assert (
            isinstance(req, str) and len(req) > 0
        ), f"Skill '{skill_id}' must declare a non-empty evidence_ref_requirements."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_validation_rules_include_evidence_refs(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        validation_rules = contract.get("validation_rules", [])
        assert (
            "must_include_evidence_refs" in validation_rules
        ), f"Skill '{skill_id}' validation_rules must include 'must_include_evidence_refs'."


# ---------------------------------------------------------------------------
# 9. Every skill declares fallback_behaviors covering all required states
# ---------------------------------------------------------------------------


class TestFallbackBehaviors:
    """Every skill must declare all required fallback states."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_fallback_behaviors_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        fallbacks = contract.get("fallback_behaviors")
        assert (
            isinstance(fallbacks, dict) and len(fallbacks) > 0
        ), f"Skill '{skill_id}' must declare a non-empty fallback_behaviors dict."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_all_required_fallback_states_covered(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
            REQUIRED_FALLBACK_STATES,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        fallbacks = contract.get("fallback_behaviors", {})
        missing = REQUIRED_FALLBACK_STATES - set(fallbacks.keys())
        assert (
            not missing
        ), f"Skill '{skill_id}' fallback_behaviors is missing states: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 10. forbidden_outputs include all required unsafe terms
# ---------------------------------------------------------------------------


class TestForbiddenOutputs:
    """Every skill's forbidden_outputs must include all required unsafe output terms."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_forbidden_outputs_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        forbidden = contract.get("forbidden_outputs")
        assert (
            isinstance(forbidden, list) and len(forbidden) > 0
        ), f"Skill '{skill_id}' must declare a non-empty forbidden_outputs list."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_forbidden_outputs_include_required_terms(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
            REQUIRED_FORBIDDEN_OUTPUT_TERMS,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        forbidden_set = set(contract.get("forbidden_outputs", []))
        missing = REQUIRED_FORBIDDEN_OUTPUT_TERMS - forbidden_set
        assert not missing, (
            f"Skill '{skill_id}' forbidden_outputs is missing required unsafe terms: "
            f"{sorted(missing)}"
        )

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_forbidden_outputs_excludes_unsafe_youth_labels(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        unsafe_labels = {"weakest_player", "liability", "poor_performer"}
        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        forbidden_set = set(contract.get("forbidden_outputs", []))
        missing = unsafe_labels - forbidden_set
        assert not missing, (
            f"Skill '{skill_id}' forbidden_outputs must include youth-unsafe labels: "
            f"{sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# 11. review_required and approval_required_before_activation
# ---------------------------------------------------------------------------


class TestReviewAndApprovalRequirements:
    """Every skill must require review and coach approval before activation."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_review_required_is_true(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        assert (
            contract.get("review_required") is True
        ), f"Skill '{skill_id}' review_required must be True."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_approval_required_before_activation_is_true(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        assert (
            contract.get("approval_required_before_activation") is True
        ), f"Skill '{skill_id}' approval_required_before_activation must be True."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_ai_boundary_metadata_requires_review(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        meta = contract.get("ai_boundary_metadata", {})
        assert (
            meta.get("requires_review") is True
        ), f"Skill '{skill_id}' ai_boundary_metadata.requires_review must be True."


# ---------------------------------------------------------------------------
# 12. tests_required is non-empty
# ---------------------------------------------------------------------------


class TestTestsRequired:
    """Every skill must declare a non-empty tests_required list."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_tests_required_is_non_empty(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        tests_required = contract.get("tests_required")
        assert (
            isinstance(tests_required, list) and len(tests_required) > 0
        ), f"Skill '{skill_id}' must declare a non-empty tests_required list."

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_tests_required_includes_contract_validation_test(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        tests_required = contract.get("tests_required", [])
        assert (
            "contract_validation_test" in tests_required
        ), f"Skill '{skill_id}' tests_required must include 'contract_validation_test'."


# ---------------------------------------------------------------------------
# 13. deterministic_data_dependencies declared
# ---------------------------------------------------------------------------


class TestDeterministicDataDependencies:
    """Every skill must declare deterministic data dependencies."""

    @pytest.mark.parametrize("skill_id", _all_skill_ids())
    def test_deterministic_data_dependencies_declared(self, skill_id: str) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
        deps = contract.get("deterministic_data_dependencies")
        assert (
            isinstance(deps, list) and len(deps) > 0
        ), f"Skill '{skill_id}' must declare non-empty deterministic_data_dependencies."


# ---------------------------------------------------------------------------
# 14. Phase 6B boundary module is importable alongside this registry
# ---------------------------------------------------------------------------


class TestPhase6BCompatibility:
    """The contract registry must coexist with Phase 6B ai_boundary module."""

    def test_ai_boundary_module_importable(self) -> None:
        from backend.domain.ai_boundary import (  # noqa: F401
            OFFICIAL_TRUTH_FIELDS,
            AiOutputMetadata,
            AiOutputType,
            validate_no_official_truth_mutation,
        )

    def test_skill_output_types_align_with_ai_boundary_output_types(self) -> None:
        from backend.domain.ai_boundary import AiOutputType
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        valid_output_types = {ot.value for ot in AiOutputType}
        for skill_id, contract in PLAYER_DEVELOPMENT_SKILL_REGISTRY.items():
            output_type = contract.get("output_type", "")
            assert output_type in valid_output_types, (
                f"Skill '{skill_id}' output_type '{output_type}' is not in "
                f"AiOutputType: {valid_output_types}"
            )

    def test_skill_contracts_do_not_set_official_truth(self) -> None:
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        for skill_id, contract in PLAYER_DEVELOPMENT_SKILL_REGISTRY.items():
            meta = contract.get("ai_boundary_metadata", {})
            assert meta.get("is_official_truth") is not True, (
                f"Skill '{skill_id}' ai_boundary_metadata.is_official_truth must be False, "
                "not True."
            )

    def test_validate_no_official_truth_mutation_guard_is_callable(self) -> None:
        """Guard must be callable — referenced in every skill's validation_rules."""
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        # Should not raise for clean player-development advisory payload
        validate_no_official_truth_mutation(
            {
                "weakness_area_label": "front_foot_technique",
                "confidence_score": 0.72,
                "limitations": ["small_sample_size"],
            },
            "player_weakness_detection_test",
        )

    def test_official_truth_fields_not_in_any_allowed_outputs(self) -> None:
        """Allowed outputs must not include any field name from OFFICIAL_TRUTH_FIELDS."""
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS
        from backend.domain.player_development_skill_contract import (
            PLAYER_DEVELOPMENT_SKILL_REGISTRY,
        )

        for skill_id, contract in PLAYER_DEVELOPMENT_SKILL_REGISTRY.items():
            allowed_outputs = set(contract.get("allowed_outputs", []))
            overlap = OFFICIAL_TRUTH_FIELDS & allowed_outputs
            assert not overlap, (
                f"Skill '{skill_id}' allowed_outputs must not contain official truth fields: "
                f"{sorted(overlap)}"
            )
