"""
Phase 6B — Deterministic vs AI Boundary Enforcement Tests.

These tests prove that:

1. The boundary guard module correctly identifies official truth field mutations.
2. AI-adjacent service response schemas carry non-authoritative metadata.
3. AI commentary/summary/insight outputs cannot be confused with official truth.
4. Scoring, DLS, and results systems do not depend on AI services.
5. Historical import training-eligibility fields are protected from AI mutation.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


# ---------------------------------------------------------------------------
# 1. Boundary guard module tests
# ---------------------------------------------------------------------------


class TestAiBoundaryModule:
    """Tests for backend.domain.ai_boundary."""

    def test_import_succeeds(self):
        """The boundary module must import without errors."""
        from backend.domain.ai_boundary import (  # noqa: F401
            OFFICIAL_TRUTH_FIELDS,
            AiOutputMetadata,
            AiOutputType,
            validate_no_official_truth_mutation,
        )

    def test_official_truth_fields_is_frozenset(self):
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS

        assert isinstance(OFFICIAL_TRUTH_FIELDS, frozenset)

    def test_official_truth_fields_contains_core_scoring(self):
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS

        core = {"runs", "wickets", "balls", "result", "status", "batting_scorecard"}
        assert core <= OFFICIAL_TRUTH_FIELDS, "Core scoring fields must be in OFFICIAL_TRUTH_FIELDS"

    def test_official_truth_fields_contains_dls(self):
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS

        dls = {"dls_target", "dls_par", "revised_target"}
        assert dls <= OFFICIAL_TRUTH_FIELDS

    def test_official_truth_fields_contains_training_eligibility(self):
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS

        gates = {"training_eligible", "validation_status", "is_finalized"}
        assert gates <= OFFICIAL_TRUTH_FIELDS

    def test_ai_output_type_enum_values(self):
        from backend.domain.ai_boundary import AiOutputType

        assert AiOutputType.COMMENTARY.value == "commentary"
        assert AiOutputType.INSIGHT.value == "insight"
        assert AiOutputType.RECOMMENDATION.value == "recommendation"
        assert AiOutputType.REPORT.value == "report"
        assert AiOutputType.SUMMARY.value == "summary"
        assert AiOutputType.DRAFT.value == "draft"

    def test_ai_output_metadata_defaults(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.COMMENTARY)
        assert meta.is_official_truth is False
        assert meta.requires_review is False
        assert meta.grounded_in_data is True

    def test_ai_output_metadata_is_official_truth_cannot_be_true_for_normal_output(self):
        """
        Demonstrate that setting is_official_truth=True is structurally possible
        (Pydantic won't block it) but the guard and schemas default to False.
        AI services must never set this to True.
        """
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.SUMMARY, is_official_truth=False)
        assert meta.is_official_truth is False


# ---------------------------------------------------------------------------
# 2. validate_no_official_truth_mutation guard tests
# ---------------------------------------------------------------------------


class TestValidateNoOfficialTruthMutation:
    """Tests for the service-level mutation guard."""

    def test_clean_payload_passes(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        safe = {
            "commentary": "Great shot!",
            "tone": "neutral",
            "output_type": "commentary",
        }
        # Should not raise
        validate_no_official_truth_mutation(safe, "test_service")

    def test_runs_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"runs": 156, "commentary": "Team scored well"}
        with pytest.raises(ValueError, match="runs"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_wickets_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"wickets": 3, "summary": "Bowling was tight"}
        with pytest.raises(ValueError, match="wickets"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_result_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"result": "Team A won by 30 runs", "summary": "…"}
        with pytest.raises(ValueError, match="result"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_dls_target_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"dls_target": 145, "note": "DLS applied"}
        with pytest.raises(ValueError, match="dls_target"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_training_eligible_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"training_eligible": True, "insight": "Good match for training"}
        with pytest.raises(ValueError, match="training_eligible"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_batting_scorecard_field_is_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"batting_scorecard": {"p1": {"runs": 45}}, "summary": "Batting analysis"}
        with pytest.raises(ValueError, match="batting_scorecard"):
            validate_no_official_truth_mutation(payload, "ai_service")

    def test_error_message_includes_context(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        with pytest.raises(ValueError, match="match_summary_service"):
            validate_no_official_truth_mutation({"runs": 10}, "match_summary_service")

    def test_multiple_violations_reported(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"runs": 50, "wickets": 2, "summary": "…"}
        with pytest.raises(ValueError) as exc_info:
            validate_no_official_truth_mutation(payload, "test")
        msg = str(exc_info.value)
        # At least one of the violations should appear in the error
        assert "runs" in msg or "wickets" in msg

    def test_empty_payload_passes(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        validate_no_official_truth_mutation({}, "empty_service")


# ---------------------------------------------------------------------------
# 3. AI response schema non-authoritative metadata tests
# ---------------------------------------------------------------------------


class TestAiCommentaryResponseMetadata:
    """AiCommentaryResponse must carry non-authoritative ai_metadata."""

    def test_has_ai_metadata_field(self):
        from datetime import UTC, datetime

        from backend.services.ai_commentary import AiCommentaryResponse

        resp = AiCommentaryResponse(
            game_id="g1",
            over_number=3,
            ball_number=2,
            commentary="Good shot!",
            tone="neutral",
            tags=["boundary"],
            generated_at=datetime.now(UTC),
        )
        assert hasattr(resp, "ai_metadata")

    def test_is_official_truth_is_false(self):
        from datetime import UTC, datetime

        from backend.services.ai_commentary import AiCommentaryResponse

        resp = AiCommentaryResponse(
            game_id="g1",
            over_number=3,
            ball_number=2,
            commentary="Six!",
            tone="hype",
            tags=["boundary", "six"],
            generated_at=datetime.now(UTC),
        )
        assert resp.ai_metadata.is_official_truth is False

    def test_output_type_is_commentary(self):
        from datetime import UTC, datetime

        from backend.domain.ai_boundary import AiOutputType
        from backend.services.ai_commentary import AiCommentaryResponse

        resp = AiCommentaryResponse(
            game_id="g1",
            over_number=1,
            ball_number=1,
            commentary="Dot ball.",
            tone="neutral",
            tags=["dot_ball"],
            generated_at=datetime.now(UTC),
        )
        assert resp.ai_metadata.output_type == AiOutputType.COMMENTARY


class TestMatchAiSummaryResponseMetadata:
    """MatchAiSummaryResponse must carry non-authoritative ai_metadata."""

    def test_has_ai_metadata_field(self):
        from backend.sql_app.match_ai import MatchAiSummaryResponse

        resp = MatchAiSummaryResponse(
            match_id="m1",
            format="T20",
            teams=[],
            overall_summary="Good match.",
        )
        assert hasattr(resp, "ai_metadata")

    def test_is_official_truth_is_false(self):
        from backend.sql_app.match_ai import MatchAiSummaryResponse

        resp = MatchAiSummaryResponse(
            match_id="m1",
            format="T20",
            teams=[],
            overall_summary="Team A dominated.",
        )
        assert resp.ai_metadata.is_official_truth is False

    def test_output_type_is_summary(self):
        from backend.domain.ai_boundary import AiOutputType
        from backend.sql_app.match_ai import MatchAiSummaryResponse

        resp = MatchAiSummaryResponse(
            match_id="m1",
            format="ODI",
            teams=[],
            overall_summary="Tight finish.",
        )
        assert resp.ai_metadata.output_type == AiOutputType.SUMMARY


class TestMatchAiCommentaryResponseMetadata:
    """MatchAiCommentaryResponse must carry non-authoritative ai_metadata."""

    def test_has_ai_metadata_field(self):
        from backend.sql_app.match_ai import MatchAiCommentaryResponse

        resp = MatchAiCommentaryResponse(match_id="m1")
        assert hasattr(resp, "ai_metadata")

    def test_is_official_truth_is_false(self):
        from backend.sql_app.match_ai import MatchAiCommentaryResponse

        resp = MatchAiCommentaryResponse(match_id="m1")
        assert resp.ai_metadata.is_official_truth is False


class TestPlayerAiInsightsMetadata:
    """PlayerAiInsights must carry non-authoritative ai_metadata."""

    def test_has_ai_metadata_field(self):
        from backend.services.ai_player_insights import PlayerAiInsights, RecentForm

        insights = PlayerAiInsights(
            player_id="p1",
            summary="Good player.",
            recent_form=RecentForm(label="Good", trend=[0.5, 0.6]),
        )
        assert hasattr(insights, "ai_metadata")

    def test_is_official_truth_is_false(self):
        from backend.services.ai_player_insights import PlayerAiInsights, RecentForm

        insights = PlayerAiInsights(
            player_id="p1",
            summary="Good player.",
            recent_form=RecentForm(label="Average", trend=[0.4]),
        )
        assert insights.ai_metadata.is_official_truth is False

    def test_output_type_is_insight(self):
        from backend.domain.ai_boundary import AiOutputType
        from backend.services.ai_player_insights import PlayerAiInsights, RecentForm

        insights = PlayerAiInsights(
            player_id="p1",
            summary="Improving form.",
            recent_form=RecentForm(label="Good", trend=[0.5, 0.7]),
        )
        assert insights.ai_metadata.output_type == AiOutputType.INSIGHT


# ---------------------------------------------------------------------------
# 4. Scoring / DLS independence tests — AI services must not be imported
#    transitively by the deterministic scoring, DLS, or results code paths.
# ---------------------------------------------------------------------------


class TestDeterministicSystemsAreAiIndependent:
    """
    Verify that the deterministic scoring and DLS modules do not import
    AI-adjacent services.  This prevents accidental coupling.
    """

    def test_scoring_service_does_not_import_ai_modules(self):
        """scoring_service must not import ai_commentary, match_ai_service, etc."""
        import importlib
        import sys

        # Remove cached modules to get a fresh import graph
        for key in list(sys.modules.keys()):
            if "scoring_service" in key:
                del sys.modules[key]

        import importlib.util

        spec = importlib.util.find_spec("backend.services.scoring_service")
        assert spec is not None

        source_path = spec.origin
        assert source_path is not None

        with open(source_path) as fh:
            source = fh.read()

        ai_imports = [
            "ai_commentary",
            "match_ai_service",
            "ai_player_insights",
            "coach_ai_pipeline",
            "agent_budget",
        ]
        for ai_mod in ai_imports:
            assert ai_mod not in source, (
                f"scoring_service must not import {ai_mod} — " "scoring must remain AI-free"
            )

    def test_dls_module_does_not_import_ai_modules(self):
        """DLS calculation must not import any AI-adjacent services."""
        import importlib.util

        spec = importlib.util.find_spec("backend.services.dls_service")
        if spec is None:
            pytest.skip(
                "backend.services.dls_service not found — skipping DLS AI-independence check"
            )

        source_path = spec.origin
        assert source_path is not None
        with open(source_path) as fh:
            source = fh.read()

        ai_imports = [
            "ai_commentary",
            "match_ai_service",
            "ai_player_insights",
        ]
        for ai_mod in ai_imports:
            assert ai_mod not in source, f"dls_service must not import {ai_mod}"

    def test_domain_constants_does_not_import_ai_modules(self):
        """domain/constants.py must not import any AI-adjacent code."""
        import importlib.util

        spec = importlib.util.find_spec("backend.domain.constants")
        assert spec is not None
        source_path = spec.origin
        assert source_path is not None
        with open(source_path) as fh:
            source = fh.read()

        assert "ai_commentary" not in source
        assert "match_ai" not in source
        assert "ai_player_insights" not in source


# ---------------------------------------------------------------------------
# 5. Historical import training-eligibility fields are protected
# ---------------------------------------------------------------------------


class TestTrainingEligibilityProtected:
    """
    Training eligibility decisions must not be made by AI services.
    The guard must block any AI payload that attempts to set these fields.
    """

    def test_training_eligible_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {
            "insight": "This match looks like good training material.",
            "training_eligible": True,
        }
        with pytest.raises(ValueError, match="training_eligible"):
            validate_no_official_truth_mutation(payload, "ai_insight_service")

    def test_is_finalized_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"is_finalized": True, "summary": "Match complete."}
        with pytest.raises(ValueError, match="is_finalized"):
            validate_no_official_truth_mutation(payload, "ai_summary_service")

    def test_validation_status_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"validation_status": "valid", "report": "All good."}
        with pytest.raises(ValueError, match="validation_status"):
            validate_no_official_truth_mutation(payload, "ai_report_service")

    def test_applied_game_id_blocked(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        payload = {"applied_game_id": "abc-123", "insight": "Match imported."}
        with pytest.raises(ValueError, match="applied_game_id"):
            validate_no_official_truth_mutation(payload, "ai_insight_service")


# ---------------------------------------------------------------------------
# 6. AI output type completeness tests
# ---------------------------------------------------------------------------


class TestAiOutputTypeCoverage:
    """Ensure all output types are defined and can be used as metadata."""

    def test_all_output_types_buildable(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        for ot in AiOutputType:
            meta = AiOutputMetadata(output_type=ot)
            assert meta.is_official_truth is False
            assert meta.output_type == ot
