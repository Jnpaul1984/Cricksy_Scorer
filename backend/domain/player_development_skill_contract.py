"""
Phase 9G — Player Development Skill Contract Registry.

This module provides a runtime-neutral, deterministically importable registry of
governed skill contracts for the Cricksy Player Development Intelligence family.

Design rules (Phase 9G scope lock):
- Pure data only.  No I/O, no DB calls, no AI calls, no network calls.
- Deterministic: import has no side effects and produces identical output every time.
- Extends Phase 6C skill architecture; does NOT invent a parallel governance system.
- Every contract inherits Phase 6B deterministic-truth boundaries (ai_boundary.py).
- Every contract inherits Phase 6F confidence/uncertainty rules.
- Every contract declares required Phase 9G fields:
  allowed_outputs, forbidden_outputs, approval_required_before_activation,
  youth_safety_rules (non-empty), no_fake_data_rule, no_official_truth_mutation_rule,
  safe_language_rules, fallback_behaviors, evidence_ref_requirements.

Do NOT add runtime execution, AI calls, DB access, or plan-activation logic here.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Required fallback states — every skill must declare all of these.
# ---------------------------------------------------------------------------

REQUIRED_FALLBACK_STATES: Final[frozenset[str]] = frozenset(
    {
        "insufficient_data",
        "low_confidence_review_required",
        "needs_more_evidence",
        "coach_review_required",
        "blocked_by_youth_safety",
        "not_authorized",
        "unsupported_claim_blocked",
        "metadata_only_pending_full_import",
    }
)

# ---------------------------------------------------------------------------
# Required contract fields — every skill must define all of these.
# These extend the Phase 6C base fields with Phase 9G-specific additions.
# ---------------------------------------------------------------------------

REQUIRED_CONTRACT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        # Phase 6C base fields
        "skill_id",
        "name",
        "version",
        "category",
        "purpose",
        "allowed_roles",
        "supported_intents",
        "required_inputs",
        "optional_inputs",
        "forbidden_inputs",
        "deterministic_data_dependencies",
        "output_type",
        "ai_boundary_metadata",
        "confidence_fields",
        "limitations_fields",
        "validation_rules",
        "safety_rules",
        "youth_safety_rules",
        "organization_data_boundary_rules",
        "no_fake_data_rule",
        "review_required",
        "tests_required",
        "rollback_or_disable_strategy",
        # Phase 9G additional required fields
        "allowed_outputs",
        "forbidden_outputs",
        "approval_required_before_activation",
        "no_official_truth_mutation_rule",
        "safe_language_rules",
        "fallback_behaviors",
        "evidence_ref_requirements",
    }
)

# ---------------------------------------------------------------------------
# Unsafe label terms that must appear in every skill's forbidden_outputs list.
# ---------------------------------------------------------------------------

REQUIRED_FORBIDDEN_OUTPUT_TERMS: Final[frozenset[str]] = frozenset(
    {
        "weakest_player",
        "liability",
        "poor_performer",
        "talent_score",
        "selection_recommendation",
        "official_ranking",
    }
)

# ---------------------------------------------------------------------------
# Shared advisory metadata block (Phase 6B alignment)
# ---------------------------------------------------------------------------

_ADVISORY_BOUNDARY_METADATA: Final[dict[str, Any]] = {
    "is_official_truth": False,
    "requires_review": True,
    "grounded_in_data": True,
}

# ---------------------------------------------------------------------------
# Shared fallback behaviors (all required states)
# ---------------------------------------------------------------------------

_STANDARD_FALLBACK_BEHAVIORS: Final[dict[str, str]] = {
    "insufficient_data": (
        "Return advisory placeholder. Block generation. No fabricated content. No fake data."
    ),
    "low_confidence_review_required": (
        "Generate flagged draft only. Route to review queue. "
        "Suppress auto-display until coach reviews."
    ),
    "needs_more_evidence": (
        "Block generation. Request additional match, form, or checkpoint data before proceeding."
    ),
    "coach_review_required": (
        "Route to review queue. Status remains draft. Do not auto-surface to player or public."
    ),
    "blocked_by_youth_safety": (
        "Suppress output. Log unsafe label attempt. "
        "Flag for coach review. Return safe fallback message."
    ),
    "not_authorized": ("Block output entirely. Return authorization error. No partial data leak."),
    "unsupported_claim_blocked": (
        "Block the specific claim. Require evidence ref before re-generation is permitted."
    ),
    "metadata_only_pending_full_import": (
        "Return metadata stub only. Block full output until player data import is complete."
    ),
}

# ---------------------------------------------------------------------------
# Shared safety / language rules
# ---------------------------------------------------------------------------

_STANDARD_SAFE_LANGUAGE_RULES: Final[list[str]] = [
    "output_is_advisory_only",
    "no_talent_certainty_language",
    "no_selection_certainty_language",
    "no_negative_comparative_labels",
    "constructive_developmental_framing_required",
    "uncertainty_must_be_expressed_with_safe_fallback_language",
]

_STANDARD_YOUTH_SAFETY_RULES: Final[list[str]] = [
    "no_negative_comparative_labels_such_as_weakest_worst_liability",
    "framing_must_be_developmental_not_evaluative",
    "low_confidence_outputs_must_use_fallback_language",
    "no_ranking_of_youth_players",
    "constructive_language_only",
]

_STANDARD_VALIDATION_RULES: Final[list[str]] = [
    "must_call_validate_no_official_truth_mutation",
    "must_include_evidence_refs",
    "must_enforce_org_and_role_scoping",
    "must_not_activate_plan_without_coach_approval",
]

_STANDARD_SAFETY_RULES: Final[list[str]] = [
    "no_harmful_or_abusive_language",
    "no_negative_youth_labels",
    "no_talent_certainty_claims",
    "no_selection_or_scouting_conclusions",
    "no_medical_or_psychological_claims",
]

_STANDARD_ORG_BOUNDARY_RULES: Final[list[str]] = [
    "enforce_role_checks_from_allowed_roles",
    "enforce_org_id_scoping",
    "no_cross_org_player_data",
]

_STANDARD_CONFIDENCE_FIELDS: Final[list[str]] = [
    "data_quality_confidence",
    "sample_size_confidence",
    "overall_confidence",
    "recommendation_confidence",
]

_STANDARD_LIMITATIONS_FIELDS: Final[list[str]] = [
    "limitations",
]

# ---------------------------------------------------------------------------
# Skill contract registry
# ---------------------------------------------------------------------------

PLAYER_DEVELOPMENT_SKILL_REGISTRY: Final[dict[str, dict[str, Any]]] = {
    # ------------------------------------------------------------------
    # 1. player_weakness_detection.v1
    # ------------------------------------------------------------------
    "player_weakness_detection.v1": {
        "skill_id": "player_weakness_detection.v1",
        "name": "Player Weakness Detection Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Identify potential batting or bowling technique areas that match "
            "evidence suggests could benefit from focused development. "
            "Output is advisory and coach-reviewed. "
            "Does not rank players negatively."
        ),
        "allowed_roles": ["coach_pro", "coach_pro_plus", "org_pro"],
        "supported_intents": [
            "detect_weakness_areas",
            "identify_development_focus",
            "suggest_improvement_areas",
        ],
        "required_inputs": [
            "player_profile_id",
            "player_form_data",
            "match_delivery_data",
        ],
        "optional_inputs": [
            "video_analysis_tags",
            "coach_notes",
            "previous_weakness_tags",
        ],
        "forbidden_inputs": [
            "unrestricted_player_dump",
            "career_totals_mutation_request",
            "psychological_assessment",
            "medical_data",
            "ranking_request",
        ],
        "deterministic_data_dependencies": [
            "player_form.runs",
            "player_form.wickets",
            "player_form.batting_average",
            "analytics.player_analytics_career_summary_slice",
            "player_improvement_tracker.monthly_stats",
        ],
        "output_type": "insight",
        "ai_boundary_metadata": {**_ADVISORY_BOUNDARY_METADATA, "output_type": "insight"},
        "allowed_outputs": [
            "weakness_area_label",
            "evidence_refs",
            "confidence_score",
            "limitations",
            "ai_metadata",
            "coach_review_note",
            "suggested_focus_areas",
        ],
        "forbidden_outputs": [
            "weakest_player",
            "liability",
            "poor_performer",
            "worst_performer",
            "talent_score",
            "official_ranking",
            "selection_recommendation",
            "scouting_conclusion",
            "should_be_selected",
            "should_be_dropped",
            "psychological_diagnosis",
            "medical_diagnosis",
            "official_stat_overwrite",
            "fabricated_evidence_refs",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If deterministic data is unavailable, return insufficient_data. "
            "Fabricating weakness evidence is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "At least one match or form evidence ref is required per weakness area. "
            "Weakness areas without evidence refs are blocked."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled. "
            "Contract registry itself is always safe to import."
        ),
    },
    # ------------------------------------------------------------------
    # 2. player_development_plan.v1
    # ------------------------------------------------------------------
    "player_development_plan.v1": {
        "skill_id": "player_development_plan.v1",
        "name": "Player Development Plan Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Generate a structured, evidence-backed draft development plan for a player, "
            "including goals, drill assignments, and expected checkpoints. "
            "Draft only — activation requires explicit coach approval."
        ),
        "allowed_roles": ["coach_pro", "coach_pro_plus"],
        "supported_intents": [
            "generate_draft_plan",
            "suggest_development_goals",
            "scaffold_drill_assignments",
            "define_progress_checkpoints",
        ],
        "required_inputs": [
            "player_profile_id",
            "coach_user_id",
            "org_id",
            "player_form_data",
            "at_least_one_evidence_ref",
        ],
        "optional_inputs": [
            "previous_plan_id",
            "video_analysis_tags",
            "coach_notes",
            "weakness_detection_output",
        ],
        "forbidden_inputs": [
            "career_stat_mutation_request",
            "plan_activation_flag",
            "ranking_score_request",
            "scouting_report_request",
            "medical_data",
            "psychological_assessment",
            "auto_approve_flag",
        ],
        "deterministic_data_dependencies": [
            "player_form.period_start",
            "player_form.period_end",
            "player_improvement_tracker.monthly_stats",
            "player_development_plan.previous_plans",
            "coach_player_assignment",
        ],
        "output_type": "draft",
        "ai_boundary_metadata": {**_ADVISORY_BOUNDARY_METADATA, "output_type": "draft"},
        "allowed_outputs": [
            "plan_title",
            "plan_summary",
            "goals",
            "drill_assignments",
            "progress_checkpoints",
            "confidence_score",
            "evidence_refs",
            "ai_metadata",
            "limitations",
        ],
        "forbidden_outputs": [
            "automatic_plan_activation",
            "coach_approved_true_without_coach_action",
            "official_stat_overwrite",
            "talent_score",
            "official_ranking",
            "selection_recommendation",
            "should_be_selected",
            "should_be_dropped",
            "scouting_conclusion",
            "fabricated_evidence_refs",
            "weakest_player",
            "liability",
            "poor_performer",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If deterministic data is unavailable, return insufficient_data. "
            "Fabricating plan goals, drills, or checkpoints is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "Plan summary and goals must reference at least one deterministic evidence source. "
            "Plans without evidence refs are blocked from generation."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "draft_only_no_auto_activation_test",
            "coach_approval_required_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled. "
            "No plan records are created or modified by the contract registry itself."
        ),
    },
    # ------------------------------------------------------------------
    # 3. drill_recommendation.v1
    # ------------------------------------------------------------------
    "drill_recommendation.v1": {
        "skill_id": "drill_recommendation.v1",
        "name": "Drill Recommendation Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Suggest targeted drills that address identified development areas, "
            "backed by evidence from match delivery data or form trends. "
            "Output is advisory and coach-reviewed before assignment."
        ),
        "allowed_roles": ["coach_pro", "coach_pro_plus"],
        "supported_intents": [
            "recommend_drills",
            "suggest_training_focus",
            "link_drills_to_weakness_areas",
        ],
        "required_inputs": [
            "player_profile_id",
            "plan_id",
            "weakness_area_label",
            "at_least_one_evidence_ref",
        ],
        "optional_inputs": [
            "drill_history",
            "previous_assignments",
            "coach_preference_notes",
        ],
        "forbidden_inputs": [
            "career_stat_mutation_request",
            "auto_assign_flag",
            "scouting_report_request",
            "ranking_request",
            "medical_data",
            "psychological_assessment",
        ],
        "deterministic_data_dependencies": [
            "player_weakness_detection.v1_output",
            "player_form.batting_average",
            "player_form.strike_rate",
            "player_form.economy",
            "player_development_plan.goals",
        ],
        "output_type": "recommendation",
        "ai_boundary_metadata": {
            **_ADVISORY_BOUNDARY_METADATA,
            "output_type": "recommendation",
        },
        "allowed_outputs": [
            "drill_category",
            "drill_name",
            "drill_description",
            "frequency_suggestion",
            "evidence_refs",
            "confidence_score",
            "limitations",
            "ai_metadata",
        ],
        "forbidden_outputs": [
            "automatic_drill_assignment",
            "official_stat_overwrite",
            "improvement_certainty_claim",
            "fabricated_drill_evidence",
            "talent_score",
            "official_ranking",
            "selection_recommendation",
            "scouting_conclusion",
            "weakest_player",
            "liability",
            "poor_performer",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If deterministic data is unavailable, return insufficient_data. "
            "Fabricating drill descriptions or evidence refs is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "Each recommended drill must be linked to at least one weakness evidence ref "
            "from player_weakness_detection.v1 or a match data source."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "no_auto_assign_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled."
        ),
    },
    # ------------------------------------------------------------------
    # 4. progress_checkpoint_summary.v1
    # ------------------------------------------------------------------
    "progress_checkpoint_summary.v1": {
        "skill_id": "progress_checkpoint_summary.v1",
        "name": "Progress Checkpoint Summary Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Summarize player progress against a development plan's goals and checkpoints, "
            "using evidence from match stats and form data. "
            "Summaries are advisory and coach-reviewed. "
            "Does not assert unsupported 'has improved' claims."
        ),
        "allowed_roles": ["coach_pro", "coach_pro_plus", "org_pro"],
        "supported_intents": [
            "summarize_checkpoint_progress",
            "describe_development_trajectory",
            "highlight_milestone_evidence",
        ],
        "required_inputs": [
            "player_profile_id",
            "plan_id",
            "checkpoint_ids",
            "at_least_one_evidence_ref",
        ],
        "optional_inputs": [
            "form_period_range",
            "drill_completion_records",
            "coach_review_notes",
        ],
        "forbidden_inputs": [
            "career_stat_mutation_request",
            "official_improvement_certification",
            "talent_score_request",
            "ranking_request",
            "medical_data",
            "auto_publish_flag",
        ],
        "deterministic_data_dependencies": [
            "player_progress_checkpoint.status",
            "player_progress_checkpoint.evidence_refs",
            "player_form.period_start",
            "player_form.period_end",
            "player_form.form_score",
            "player_improvement_tracker.improvement_score",
        ],
        "output_type": "summary",
        "ai_boundary_metadata": {**_ADVISORY_BOUNDARY_METADATA, "output_type": "summary"},
        "allowed_outputs": [
            "checkpoint_status_summary",
            "progress_narrative",
            "evidence_refs",
            "confidence_score",
            "limitations",
            "ai_metadata",
            "review_notes",
        ],
        "forbidden_outputs": [
            "has_improved_certainty_assertion_without_checkpoint_evidence",
            "official_stat_overwrite",
            "official_ranking",
            "talent_score",
            "scouting_conclusion",
            "ready_to_be_selected",
            "fabricated_progress_evidence",
            "weakest_player",
            "liability",
            "poor_performer",
            "selection_recommendation",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If deterministic data is unavailable, return insufficient_data. "
            "Fabricating checkpoint evidence or progress claims is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "Every progress narrative claim must reference at least one checkpoint "
            "with a non-null evidence_refs list. "
            "Unsupported progress claims are blocked."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "no_unsupported_has_improved_claim_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled."
        ),
    },
    # ------------------------------------------------------------------
    # 5. team_development_overview.v1
    # ------------------------------------------------------------------
    "team_development_overview.v1": {
        "skill_id": "team_development_overview.v1",
        "name": "Team Development Overview Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Provide an org-scoped advisory overview of team-wide development activity, "
            "highlighting aggregate plan coverage and active drill areas. "
            "Advisory only. Does not rank players within the team."
        ),
        "allowed_roles": ["org_pro"],
        "supported_intents": [
            "overview_team_development_activity",
            "summarize_plan_coverage",
            "highlight_aggregate_drill_areas",
        ],
        "required_inputs": [
            "org_id",
            "team_id_or_season_scope",
        ],
        "optional_inputs": [
            "date_range",
            "filter_by_status",
        ],
        "forbidden_inputs": [
            "individual_player_ranking_request",
            "selection_recommendation_request",
            "talent_score_request",
            "scouting_report_request",
            "medical_data",
            "cross_org_data_request",
        ],
        "deterministic_data_dependencies": [
            "player_development_plan.status_aggregate_counts",
            "player_development_goal.category_distribution",
            "player_drill_assignment.drill_category_distribution",
            "player_progress_checkpoint.completion_aggregate",
        ],
        "output_type": "summary",
        "ai_boundary_metadata": {**_ADVISORY_BOUNDARY_METADATA, "output_type": "summary"},
        "allowed_outputs": [
            "plan_coverage_summary",
            "goal_category_distribution",
            "drill_area_distribution",
            "checkpoint_completion_rate",
            "confidence_score",
            "limitations",
            "ai_metadata",
            "advisory_note",
        ],
        "forbidden_outputs": [
            "individual_player_ranking",
            "weakest_player_on_team",
            "talent_score",
            "official_ranking",
            "selection_recommendation",
            "scouting_conclusion",
            "official_team_selection_list",
            "player_should_be_dropped",
            "fabricated_aggregate_evidence",
            "weakest_player",
            "liability",
            "poor_performer",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If no plan records exist, return insufficient_data advisory. "
            "Fabricating aggregate plan/drill data is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "All aggregate claims must be derivable from stored PlayerDevelopmentPlan "
            "and related records. No fabricated aggregate data is allowed."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "no_individual_ranking_in_team_overview_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled."
        ),
    },
    # ------------------------------------------------------------------
    # 6. player_development_report.v1
    # ------------------------------------------------------------------
    "player_development_report.v1": {
        "skill_id": "player_development_report.v1",
        "name": "Player Development Report Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Generate an advisory, evidence-backed development report for a player "
            "within a plan period. Readable by coach and org only. "
            "Not surfaced publicly or to the player unless a future phase "
            "explicitly governs that access."
        ),
        "allowed_roles": ["coach_pro", "coach_pro_plus", "org_pro"],
        "supported_intents": [
            "generate_development_report",
            "summarize_plan_period",
            "describe_checkpoint_progress_in_report",
        ],
        "required_inputs": [
            "player_profile_id",
            "plan_id",
            "at_least_one_evidence_ref",
        ],
        "optional_inputs": [
            "checkpoint_ids",
            "form_period_range",
            "drill_completion_summary",
            "coach_review_notes",
        ],
        "forbidden_inputs": [
            "public_surface_flag",
            "player_facing_access_flag",
            "talent_score_request",
            "scouting_report_request",
            "official_improvement_certification",
            "career_stat_mutation_request",
            "auto_publish_flag",
        ],
        "deterministic_data_dependencies": [
            "player_development_plan.title",
            "player_development_plan.summary",
            "player_development_goal.label",
            "player_development_goal.status",
            "player_progress_checkpoint.evidence_refs",
            "player_form.batting_average",
            "player_form.form_score",
            "player_improvement_tracker.improvement_score",
        ],
        "output_type": "report",
        "ai_boundary_metadata": {**_ADVISORY_BOUNDARY_METADATA, "output_type": "report"},
        "allowed_outputs": [
            "report_title",
            "report_narrative",
            "goals_summary",
            "checkpoints_summary",
            "evidence_refs",
            "confidence_score",
            "limitations",
            "ai_metadata",
            "advisory_disclaimer",
            "review_status",
        ],
        "forbidden_outputs": [
            "official_ranking",
            "talent_score",
            "scouting_conclusion",
            "public_report_exposure",
            "player_is_ready_for_selection",
            "has_improved_certainty_assertion_without_checkpoint_evidence",
            "cross_org_player_data",
            "fabricated_report_evidence",
            "automatic_report_publish",
            "weakest_player",
            "liability",
            "poor_performer",
            "selection_recommendation",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": _STANDARD_VALIDATION_RULES,
        "safety_rules": _STANDARD_SAFETY_RULES,
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If deterministic plan or checkpoint data is unavailable, return insufficient_data. "
            "Fabricating report narrative, evidence refs, or progress claims is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite official player stats, career totals, "
            "match results, scorecards, DLS values, or innings state. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": _STANDARD_SAFE_LANGUAGE_RULES,
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "Every narrative section must reference at least one deterministic evidence source. "
            "Reports without evidence refs are blocked from generation."
        ),
        "fallback_behaviors": dict(_STANDARD_FALLBACK_BEHAVIORS),
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "no_public_surface_test",
            "coach_review_required_before_surfacing_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "Return insufficient_data fallback when disabled. "
            "No reports are published or mutated by the contract registry itself."
        ),
    },
    # ------------------------------------------------------------------
    # 7. coaching_video_evidence_skill.v1
    # ------------------------------------------------------------------
    "coaching_video_evidence_skill.v1": {
        "skill_id": "coaching_video_evidence_skill.v1",
        "name": "Coaching Video Evidence Skill",
        "version": "1.0.0",
        "category": "player_development",
        "purpose": (
            "Transform structured Coach Pro Plus video-analysis evidence into "
            "coach-reviewable player development advisory recommendations. "
            "Output is advisory only and never official cricket truth."
        ),
        "allowed_roles": ["coach_pro_plus", "org_pro"],
        "supported_intents": [
            "derive_recommendation_from_video_evidence",
            "summarize_video_analysis_findings_for_coach_review",
            "prepare_evidence_linked_development_advisory",
        ],
        "required_inputs": [
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
        ],
        "optional_inputs": [
            "coach_goals",
            "goal_compliance_pct",
            "previous_plan_id",
            "coach_notes",
        ],
        "forbidden_inputs": [
            "official_truth_mutation_request",
            "match_result_mutation_request",
            "scorecard_mutation_request",
            "innings_state_mutation_request",
            "dls_mutation_request",
            "player_stats_mutation_request",
            "always_running_mode",
            "player_auto_publish_without_review",
        ],
        "deterministic_data_dependencies": [
            "coach_pro_plus.video_session.id",
            "coach_pro_plus.analysis_job.id",
            "coach_pro_plus.evidence_markers.metric_name",
            "coach_pro_plus.evidence_markers.timestamp_s",
            "coach_pro_plus.evidence_markers.frame_num",
            "coach_pro_plus.evidence_markers.score",
            "coach_pro_plus.evidence_markers.threshold",
            "coach_pro_plus.evidence_markers.finding_label",
        ],
        "output_type": "recommendation",
        "ai_boundary_metadata": {
            **_ADVISORY_BOUNDARY_METADATA,
            "output_type": "recommendation",
            "coach_authority_required": True,
        },
        "output_contract": {
            "required_fields": [
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
            ],
            "advisory_only": True,
            "requires_coach_review_before_player_facing_use": True,
        },
        "allowed_outputs": [
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
            "advisory_disclaimer",
        ],
        "forbidden_outputs": [
            "official_ranking",
            "talent_score",
            "selection_recommendation",
            "weakest_player",
            "liability",
            "poor_performer",
            "official_cricket_truth_assertion",
            "unreviewed_player_facing_output",
            "scorecard_mutation",
            "match_result_mutation",
            "innings_state_mutation",
            "dls_mutation",
            "player_stats_mutation",
            "medical_diagnosis_statement",
            "psychological_diagnosis_statement",
            "fabricated_evidence_reference",
        ],
        "confidence_fields": _STANDARD_CONFIDENCE_FIELDS,
        "limitations_fields": _STANDARD_LIMITATIONS_FIELDS,
        "validation_rules": [
            *_STANDARD_VALIDATION_RULES,
            "must_require_video_analysis_job_id",
            "must_require_video_session_id",
            "must_require_analysis_mode",
            "must_require_evidence_markers",
            "must_preserve_video_timestamps_in_evidence_refs",
            "must_require_coach_review_before_player_facing_use",
            "execution_must_be_event_triggered_not_always_running",
        ],
        "safety_rules": [
            *_STANDARD_SAFETY_RULES,
            "no_unapproved_player_facing_ai_output",
            "coach_remains_authority_for_player_development_decisions",
        ],
        "youth_safety_rules": _STANDARD_YOUTH_SAFETY_RULES,
        "organization_data_boundary_rules": _STANDARD_ORG_BOUNDARY_RULES,
        "no_fake_data_rule": (
            "If required structured video evidence is missing or insufficient, return "
            "insufficient_data or needs_more_evidence fallback. "
            "Fabricating markers, timestamps, frames, or findings is forbidden."
        ),
        "no_official_truth_mutation_rule": (
            "This skill must never overwrite scoring, match results, player stats, "
            "DLS values, scorecards, innings state, or any official cricket truth. "
            "Call validate_no_official_truth_mutation before persisting any output."
        ),
        "safe_language_rules": [
            *_STANDARD_SAFE_LANGUAGE_RULES,
            "no_medical_or_psychological_diagnosis_language",
            "coach_review_disclaimer_required_before_player_visibility",
        ],
        "review_required": True,
        "approval_required_before_activation": True,
        "evidence_ref_requirements": (
            "Every recommendation must include evidence_refs tied to video_session_id "
            "and video_analysis_job_id with marker timestamps and/or frame references. "
            "Outputs without timestamp-preserving evidence refs are blocked."
        ),
        "fallback_behaviors": {
            **_STANDARD_FALLBACK_BEHAVIORS,
            "insufficient_data": (
                "Return advisory placeholder indicating insufficient structured video "
                "evidence. Require additional markers before recommendation generation."
            ),
            "needs_more_evidence": (
                "Block recommendation generation until additional structured markers "
                "with timestamps/frames are provided."
            ),
            "coach_review_required": (
                "Hold output in review queue. Do not surface to player-facing channels "
                "until coach approval is recorded."
            ),
        },
        "tests_required": [
            "contract_validation_test",
            "no_official_truth_mutation_test",
            "no_fake_data_test",
            "youth_safety_rules_test",
            "evidence_ref_requirement_test",
            "forbidden_output_terms_test",
            "fallback_behavior_coverage_test",
            "role_authorization_test",
            "coach_review_required_before_player_facing_use_test",
            "video_evidence_marker_schema_test",
        ],
        "rollback_or_disable_strategy": (
            "Feature flag disable at skill-implementation layer. "
            "When disabled or insufficient evidence is present, return insufficient_data "
            "fallback and emit no player-facing recommendation."
        ),
    },
}

# ---------------------------------------------------------------------------
# Public helper: retrieve a single contract (read-only)
# ---------------------------------------------------------------------------

REQUIRED_SKILL_IDS: Final[frozenset[str]] = frozenset(PLAYER_DEVELOPMENT_SKILL_REGISTRY.keys())


def get_skill_contract(skill_id: str) -> dict[str, Any]:
    """
    Return the contract dict for *skill_id*, or raise KeyError if not registered.

    This helper is runtime-neutral: it only reads from the in-process registry dict.
    It does not call any AI provider, DB, or external service.
    """
    if skill_id not in PLAYER_DEVELOPMENT_SKILL_REGISTRY:
        raise KeyError(
            f"Player development skill '{skill_id}' is not registered in "
            "PLAYER_DEVELOPMENT_SKILL_REGISTRY."
        )
    return PLAYER_DEVELOPMENT_SKILL_REGISTRY[skill_id]
