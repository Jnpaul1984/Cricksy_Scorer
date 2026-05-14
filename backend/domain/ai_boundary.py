"""
Phase 6B — Deterministic vs AI Boundary Enforcement.

Core rule:
    Deterministic systems calculate facts.
    AI systems explain, summarize, recommend, or communicate.

Hard gate:
    No LLM may calculate, overwrite, or mutate official cricket truth.

This module defines:
- AiOutputType: enum classifying the nature of every AI output.
- OFFICIAL_TRUTH_FIELDS: the set of official cricket truth field names that
  AI-adjacent code must never write to or expose as authoritative data.
- AiOutputMetadata: a Pydantic model that every AI response schema should
  embed so callers can see the non-authoritative nature of the output.
- validate_no_official_truth_mutation: a service-level guard that raises
  ValueError when AI code attempts to set an official truth field.
"""

from __future__ import annotations

import enum
from typing import Any, Final

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# AI output type classification
# ---------------------------------------------------------------------------


class AiOutputType(enum.StrEnum):
    """
    Classify the nature of an AI-adjacent output.

    Every AI response must be one of these types.  None of them represents
    official cricket truth — they are all advisory, reviewable, or
    communicative outputs.
    """

    COMMENTARY = "commentary"
    """Short natural-language commentary on a single delivery or phase."""

    INSIGHT = "insight"
    """Rule-based or model-derived analytical insight about a player or match."""

    RECOMMENDATION = "recommendation"
    """Coaching recommendation or suggested action."""

    REPORT = "report"
    """A reviewable narrative report (coach report, analyst report, etc.)."""

    SUMMARY = "summary"
    """A high-level match or player summary."""

    DRAFT = "draft"
    """A draft output that requires human review before use."""


# ---------------------------------------------------------------------------
# Official cricket truth fields
# ---------------------------------------------------------------------------

OFFICIAL_TRUTH_FIELDS: Final[frozenset[str]] = frozenset(
    {
        # Core scoring
        "runs",
        "total_runs",
        "runs_scored",
        "runs_off_bat",
        "extra_runs",
        # Balls / overs
        "balls",
        "balls_faced",
        "overs_completed",
        "balls_this_over",
        "overs_limit",
        # Wickets
        "wickets",
        "total_wickets",
        "is_wicket",
        "dismissal_type",
        "dismissed_player_id",
        # Innings state
        "current_inning",
        "innings1_completed",
        "innings2_completed",
        "batting_team_name",
        # Match result
        "result",
        "status",
        "winner",
        "match_result",
        # Scorecard / official stats
        "batting_scorecard",
        "bowling_scorecard",
        "i1_runs",
        "i1_wickets",
        "i2_runs",
        "i2_wickets",
        # DLS
        "dls_target",
        "dls_par",
        "revised_target",
        "team2_resources",
        "team1_resources",
        # Historical import / training eligibility
        "training_eligible",
        "validation_status",
        "registration_status",
        "is_finalized",
        "applied_game_id",
    }
)
"""
The set of Game / delivery / historical-import fields that represent official
cricket truth.  AI-adjacent code must never write to these fields.
"""


# ---------------------------------------------------------------------------
# AI output metadata — embedded in every AI response schema
# ---------------------------------------------------------------------------


class AiOutputMetadata(BaseModel):
    """
    Metadata embedded in every AI-adjacent response to make its
    non-authoritative nature explicit and machine-readable.

    Consumers must not treat any AI response containing this metadata as
    official cricket truth.
    """

    output_type: AiOutputType = Field(
        description="Classification of this output (commentary, insight, recommendation, etc.)."
    )
    is_official_truth: bool = Field(
        default=False,
        description=(
            "Always False for AI outputs.  Official cricket truth is owned by "
            "deterministic scoring, DLS, and results systems only."
        ),
    )
    requires_review: bool = Field(
        default=False,
        description=(
            "True when this output is high-impact (e.g., coach report, youth feedback) "
            "and must pass a human review queue before use."
        ),
    )
    grounded_in_data: bool = Field(
        default=True,
        description=(
            "True when this output is derived exclusively from stored, validated match "
            "data.  False if any content was generated without a direct data source."
        ),
    )


# ---------------------------------------------------------------------------
# Service-level guard
# ---------------------------------------------------------------------------


def validate_no_official_truth_mutation(
    payload: dict[str, Any],
    context: str = "AI service",
) -> None:
    """
    Raise ValueError if *payload* contains any official cricket truth field.

    This guard should be called at the boundary between AI-adjacent services
    and any code path that could persist data into official game/player/import
    records.

    Args:
        payload: The dict produced by an AI-adjacent service.
        context: A short label identifying the calling service (for error messages).

    Raises:
        ValueError: If *payload* contains one or more protected official truth fields.

    Example::

        # In an AI route, before persisting anything:
        validate_no_official_truth_mutation(ai_response.model_dump(), "match_ai_service")
    """
    violations = OFFICIAL_TRUTH_FIELDS & set(payload.keys())
    if violations:
        raise ValueError(
            f"[Phase 6B boundary violation] {context} attempted to set official "
            f"cricket truth field(s): {sorted(violations)}.  "
            "AI outputs must never mutate official scoring, result, DLS, or "
            "historical-import truth.  Remove these fields from the AI response."
        )
