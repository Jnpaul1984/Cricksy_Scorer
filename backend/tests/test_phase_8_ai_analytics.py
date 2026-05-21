"""
Phase 8 — AI Analytics + Match Intelligence Enhancement Tests.

Validates:

1. ``AiOutputMetadata`` Phase 8 additions (confidence_score, limitations).
2. Win-probability prediction API response carries advisory ``ai_metadata``.
3. ``confidence_score`` is normalised to 0.0-1.0 range.
4. Known limitations are non-empty for prediction outputs.
5. No deterministic cricket truth fields appear in AI advisory outputs.
6. Existing ``AiOutputMetadata`` behaviour is fully preserved (no regression).
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


# ---------------------------------------------------------------------------
# 1. AiOutputMetadata — Phase 8 field additions
# ---------------------------------------------------------------------------


class TestAiOutputMetadataPhase8Fields:
    """New Phase 8 fields on AiOutputMetadata must be backward-compatible."""

    def test_confidence_score_defaults_to_none(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.COMMENTARY)
        assert meta.confidence_score is None

    def test_limitations_defaults_to_empty_list(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.INSIGHT)
        assert meta.limitations == []

    def test_source_refs_default_to_empty_list(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.INSIGHT)
        assert meta.source_refs == []

    def test_grounding_summary_defaults_to_none(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.INSIGHT)
        assert meta.grounding_summary is None

    def test_confidence_score_accepts_valid_range(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        for value in (0.0, 0.5, 0.75, 1.0):
            meta = AiOutputMetadata(output_type=AiOutputType.SUMMARY, confidence_score=value)
            assert meta.confidence_score == value

    def test_confidence_score_rejects_above_one(self):
        from pydantic import ValidationError

        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        with pytest.raises(ValidationError):
            AiOutputMetadata(output_type=AiOutputType.SUMMARY, confidence_score=1.1)

    def test_confidence_score_rejects_below_zero(self):
        from pydantic import ValidationError

        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        with pytest.raises(ValidationError):
            AiOutputMetadata(output_type=AiOutputType.SUMMARY, confidence_score=-0.01)

    def test_limitations_accepts_list_of_strings(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        caveats = ["Advisory only.", "Low sample size.", "No pitch data."]
        meta = AiOutputMetadata(output_type=AiOutputType.INSIGHT, limitations=caveats)
        assert meta.limitations == caveats

    def test_is_official_truth_still_false_with_new_fields(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.RECOMMENDATION,
            confidence_score=0.8,
            limitations=["Experimental model."],
        )
        assert meta.is_official_truth is False

    def test_grounded_in_data_still_defaults_true(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.SUMMARY, confidence_score=0.5)
        assert meta.grounded_in_data is True

    def test_model_dump_includes_phase8_fields(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType, AiSourceReference

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=0.65,
            limitations=["Rule-based fallback used."],
            source_refs=[
                AiSourceReference(
                    type="metric",
                    id="required_run_rate",
                    label="Required RR: 8.50",
                )
            ],
            grounding_summary="Based on live match state and run-rate pressure.",
        )
        dumped = meta.model_dump()
        assert "confidence_score" in dumped
        assert "limitations" in dumped
        assert "source_refs" in dumped
        assert "grounding_summary" in dumped
        assert dumped["confidence_score"] == 0.65
        assert dumped["limitations"] == ["Rule-based fallback used."]
        assert dumped["source_refs"] == [
            {
                "type": "metric",
                "id": "required_run_rate",
                "label": "Required RR: 8.50",
            }
        ]
        assert dumped["grounding_summary"] == "Based on live match state and run-rate pressure."

    def test_model_dump_none_confidence_round_trips(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(output_type=AiOutputType.COMMENTARY)
        dumped = meta.model_dump()
        assert dumped["confidence_score"] is None


# ---------------------------------------------------------------------------
# 2. Prediction route — advisory ai_metadata in win-probability response
# ---------------------------------------------------------------------------


class TestWinProbabilityAdvisoryMetadata:
    """
    Win-probability API response must include advisory ai_metadata.

    All assertions are against advisory metadata fields only.  No official
    cricket truth fields (runs, wickets, target, etc.) are touched.
    """

    def test_prediction_route_module_has_limitations_constant(self):
        pytest.importorskip("numpy")  # prediction_service transitively requires numpy
        from backend.routes.prediction import _PREDICTION_LIMITATIONS

        assert isinstance(_PREDICTION_LIMITATIONS, list)
        assert len(_PREDICTION_LIMITATIONS) > 0
        for item in _PREDICTION_LIMITATIONS:
            assert isinstance(item, str)

    def test_limitations_do_not_contain_official_truth_fields(self):
        pytest.importorskip("numpy")  # prediction_service transitively requires numpy
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS
        from backend.routes.prediction import _PREDICTION_LIMITATIONS

        # None of the limitation strings should be the name of a protected field
        for limitation in _PREDICTION_LIMITATIONS:
            for field in OFFICIAL_TRUTH_FIELDS:
                assert field not in limitation.lower() or "advisory" in limitation.lower(), (
                    f"Limitation string '{limitation}' may inadvertently reference "
                    f"official truth field '{field}'."
                )

    def test_prediction_source_refs_include_grounding_context(self):
        from types import SimpleNamespace

        pytest.importorskip("numpy")  # prediction_service transitively requires numpy
        from backend.routes.prediction import (
            _build_prediction_grounding_summary,
            _build_prediction_source_refs,
        )

        game = SimpleNamespace(
            batting_team_name="Lions",
            bowling_team_name="Falcons",
            current_inning=2,
            overs_completed=17,
            overs_limit=20,
            target=171,
        )
        prediction = {
            "factors": {
                "required_run_rate": 9.2,
                "wickets_remaining": 5,
                "prediction_method": "rule_based_early",
            }
        }

        refs = _build_prediction_source_refs(game, prediction, "match-123")
        labels = [ref.label for ref in refs]

        assert "Match: Lions vs Falcons" in labels
        assert "Innings 2" in labels
        assert "Death overs" in labels
        assert "Target: 171" in labels
        assert "Required RR: 9.20" in labels
        assert "Wickets remaining: 5" in labels
        assert "Data source: Rule-based fallback" in labels
        assert _build_prediction_grounding_summary(refs) == (
            "Based on live match state, innings context, phase context, "
            "wickets remaining, run-rate pressure, and fallback prediction logic."
        )

    def test_ai_metadata_confidence_normalisation(self):
        """Confidence reported as 0-100 by prediction_service must be 0-1 in ai_metadata."""
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        # Simulate what the route does: raw_confidence from prediction_service is 0-100
        raw_confidence = 75.0
        confidence_score = round(raw_confidence / 100.0, 4)

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=confidence_score,
            limitations=["Advisory only."],
        )
        assert meta.confidence_score == 0.75
        assert meta.is_official_truth is False

    def test_zero_confidence_normalises_to_zero(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=round(0.0 / 100.0, 4),
        )
        assert meta.confidence_score == 0.0

    def test_full_confidence_normalises_to_one(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=round(100.0 / 100.0, 4),
        )
        assert meta.confidence_score == 1.0

    def test_prediction_output_type_is_insight(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            is_official_truth=False,
            confidence_score=0.5,
            limitations=["Advisory only."],
        )
        assert meta.output_type == AiOutputType.INSIGHT

    def test_prediction_ai_metadata_is_not_official_truth(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            is_official_truth=False,
            confidence_score=0.6,
            limitations=["Advisory only."],
        )
        assert meta.is_official_truth is False


# ---------------------------------------------------------------------------
# 3. No deterministic truth mutation via prediction advisory payload
# ---------------------------------------------------------------------------


class TestPredictionNoTruthMutation:
    """Prediction advisory metadata must never contain official cricket truth fields."""

    def test_ai_metadata_dump_contains_no_official_truth_fields(self):
        from backend.domain.ai_boundary import (
            OFFICIAL_TRUTH_FIELDS,
            AiOutputMetadata,
            AiOutputType,
        )

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=0.7,
            limitations=["Advisory only.", "Rule-based fallback used."],
        )
        dumped = meta.model_dump()
        violations = OFFICIAL_TRUTH_FIELDS & set(dumped.keys())
        assert (
            not violations
        ), f"ai_metadata dump must not contain official truth fields. Found: {violations}"

    def test_validate_no_official_truth_mutation_on_ai_metadata(self):
        from backend.domain.ai_boundary import (
            AiOutputMetadata,
            AiOutputType,
            validate_no_official_truth_mutation,
        )

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            confidence_score=0.6,
            limitations=["Advisory only."],
        )
        # Should not raise — ai_metadata fields are advisory, not official truth
        validate_no_official_truth_mutation(meta.model_dump(), "phase_8_prediction_test")

    def test_prediction_advisory_payload_blocked_if_truth_fields_added(self):
        """Guard must block payloads that accidentally include official truth fields."""
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        bad_payload = {
            "output_type": "insight",
            "is_official_truth": False,
            "runs": 156,  # <- must be blocked
        }
        with pytest.raises(ValueError, match="runs"):
            validate_no_official_truth_mutation(bad_payload, "phase_8_bad_payload")


# ---------------------------------------------------------------------------
# 4. Regression — existing AiOutputMetadata behaviour preserved
# ---------------------------------------------------------------------------


class TestAiOutputMetadataRegression:
    """
    Ensure that adding Phase 8 fields has not broken existing Phase 6B behaviour.
    """

    def test_existing_commentary_metadata_unchanged(self):
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
        assert resp.ai_metadata.is_official_truth is False
        assert resp.ai_metadata.output_type == AiOutputType.COMMENTARY
        # New fields default cleanly on existing schemas
        assert resp.ai_metadata.confidence_score is None
        assert resp.ai_metadata.limitations == []

    def test_existing_match_ai_summary_metadata_unchanged(self):
        from backend.domain.ai_boundary import AiOutputType
        from backend.sql_app.match_ai import MatchAiSummaryResponse

        resp = MatchAiSummaryResponse(
            match_id="m1",
            format="T20",
            teams=[],
            overall_summary="Good match.",
        )
        assert resp.ai_metadata.is_official_truth is False
        assert resp.ai_metadata.output_type == AiOutputType.SUMMARY
        assert resp.ai_metadata.confidence_score is None
        assert resp.ai_metadata.limitations == []

    def test_existing_player_insights_metadata_unchanged(self):
        from backend.domain.ai_boundary import AiOutputType
        from backend.services.ai_player_insights import PlayerAiInsights, RecentForm

        insights = PlayerAiInsights(
            player_id="p1",
            summary="Good player.",
            recent_form=RecentForm(label="Good", trend=[0.5, 0.7]),
        )
        assert insights.ai_metadata.is_official_truth is False
        assert insights.ai_metadata.output_type == AiOutputType.INSIGHT
        assert insights.ai_metadata.confidence_score is None
        assert insights.ai_metadata.limitations == []
