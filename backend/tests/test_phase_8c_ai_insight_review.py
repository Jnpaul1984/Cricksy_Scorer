"""
Phase 8C — AI Insight Feedback + Review Workflow Tests.

Validates:

1. Review state contract (schema validation, state lifecycle).
2. Submit feedback/review decision success case.
3. Unauthorized reviewer (non-analyst role) is blocked.
4. Invalid insight_type is rejected.
5. Official cricket truth is never mutated through the review service.
6. AiInsightReview model carries advisory-only marker in schema response.
7. AI insight confidence/limitations/explanation remain visible in source schemas.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str = "analyst_pro", org_id: str | None = "org-1") -> object:
    """Build a minimal mock user for service-level tests."""
    from unittest.mock import MagicMock

    from backend.sql_app.models import RoleEnum

    user = MagicMock()
    user.id = "user-001"
    user.org_id = org_id
    user.role = RoleEnum(role)
    return user


# ---------------------------------------------------------------------------
# 1. Schema contract validation
# ---------------------------------------------------------------------------


class TestAiInsightReviewSchemas:
    """AiInsightReviewSubmit and AiInsightReviewStateResponse must validate correctly."""

    def test_submit_schema_accepts_valid_approved(self):
        from backend.api.schemas.ai_insight_review import AiInsightReviewSubmit
        from backend.sql_app.models import AiInsightReviewState

        payload = AiInsightReviewSubmit(review_state=AiInsightReviewState.approved)
        assert payload.review_state == AiInsightReviewState.approved
        assert payload.feedback_type is None
        assert payload.note is None

    def test_submit_schema_accepts_all_valid_states(self):
        from backend.api.schemas.ai_insight_review import AiInsightReviewSubmit
        from backend.sql_app.models import AiInsightReviewState

        for state in AiInsightReviewState:
            payload = AiInsightReviewSubmit(review_state=state)
            assert payload.review_state == state

    def test_submit_schema_accepts_feedback_type(self):
        from backend.api.schemas.ai_insight_review import AiInsightReviewSubmit
        from backend.sql_app.models import AiInsightFeedbackType, AiInsightReviewState

        payload = AiInsightReviewSubmit(
            review_state=AiInsightReviewState.flagged,
            feedback_type=AiInsightFeedbackType.unsafe,
            note="This claim is not supported by match data.",
        )
        assert payload.feedback_type == AiInsightFeedbackType.unsafe
        assert payload.note is not None

    def test_state_response_is_advisory_only(self):
        from backend.api.schemas.ai_insight_review import AiInsightReviewStateResponse
        from backend.sql_app.models import AiInsightReviewState

        resp = AiInsightReviewStateResponse(
            insight_type="summary",
            insight_id="match-001",
            current_state=AiInsightReviewState.pending,
        )
        assert resp.is_advisory_only is True

    def test_state_response_pending_default(self):
        from backend.api.schemas.ai_insight_review import AiInsightReviewStateResponse
        from backend.sql_app.models import AiInsightReviewState

        resp = AiInsightReviewStateResponse(
            insight_type="insight",
            insight_id="player-001",
            current_state=AiInsightReviewState.pending,
        )
        assert resp.current_state == AiInsightReviewState.pending
        assert resp.latest_review is None
        assert resp.total_reviews == 0


# ---------------------------------------------------------------------------
# 2. Service-level permission checks
# ---------------------------------------------------------------------------


class TestReviewServicePermissions:
    """Permission checks in the service layer."""

    def test_analyst_pro_is_reviewer(self):
        from backend.services.ai_insight_review_service import _is_reviewer

        user = _make_user(role="analyst_pro")
        assert _is_reviewer(user) is True

    def test_org_pro_is_reviewer(self):
        from backend.services.ai_insight_review_service import _is_reviewer

        user = _make_user(role="org_pro")
        assert _is_reviewer(user) is True

    def test_free_user_is_not_reviewer(self):
        from backend.services.ai_insight_review_service import _is_reviewer

        user = _make_user(role="free")
        assert _is_reviewer(user) is False

    def test_coach_pro_is_not_reviewer(self):
        from backend.services.ai_insight_review_service import _is_reviewer

        user = _make_user(role="coach_pro")
        assert _is_reviewer(user) is False

    def test_assert_reviewer_raises_for_free_user(self):
        from backend.services.ai_insight_review_service import _assert_reviewer

        user = _make_user(role="free")
        with pytest.raises(PermissionError, match="not authorised"):
            _assert_reviewer(user)

    def test_assert_reviewer_does_not_raise_for_analyst_pro(self):
        from backend.services.ai_insight_review_service import _assert_reviewer

        user = _make_user(role="analyst_pro")
        _assert_reviewer(user)  # Should not raise


# ---------------------------------------------------------------------------
# 3. Official cricket truth boundary
# ---------------------------------------------------------------------------


class TestAiBoundaryProtection:
    """AI insight review must never mutate official cricket truth fields."""

    def test_validate_no_official_truth_mutation_blocks_runs(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        with pytest.raises(ValueError, match="official cricket truth"):
            validate_no_official_truth_mutation(
                {"runs": 42, "note": "test"},
                "ai_insight_review_service",
            )

    def test_validate_no_official_truth_mutation_blocks_wickets(self):
        from backend.domain.ai_boundary import validate_no_official_truth_mutation

        with pytest.raises(ValueError, match="official cricket truth"):
            validate_no_official_truth_mutation(
                {"wickets": 3},
                "test",
            )

    def test_review_payload_does_not_contain_truth_fields(self):
        """Review submit payload fields must not overlap OFFICIAL_TRUTH_FIELDS."""
        from backend.api.schemas.ai_insight_review import AiInsightReviewSubmit
        from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS
        from backend.sql_app.models import AiInsightReviewState

        payload = AiInsightReviewSubmit(
            review_state=AiInsightReviewState.approved,
            note="Looks good.",
        )
        payload_keys = set(payload.model_dump().keys())
        overlap = OFFICIAL_TRUTH_FIELDS & payload_keys
        assert not overlap, (
            f"Review submit payload unexpectedly overlaps official truth fields: {overlap}"
        )

    def test_ai_insight_review_state_enum_values(self):
        """Enum values must match the spec lock."""
        from backend.sql_app.models import AiInsightReviewState

        assert AiInsightReviewState.pending.value == "pending"
        assert AiInsightReviewState.approved.value == "approved"
        assert AiInsightReviewState.rejected.value == "rejected"
        assert AiInsightReviewState.changes_requested.value == "changes_requested"
        assert AiInsightReviewState.flagged.value == "flagged"

    def test_ai_insight_feedback_type_enum_values(self):
        """Feedback type enum values must match the spec lock."""
        from backend.sql_app.models import AiInsightFeedbackType

        assert AiInsightFeedbackType.useful.value == "useful"
        assert AiInsightFeedbackType.not_useful.value == "not_useful"
        assert AiInsightFeedbackType.unsafe.value == "unsafe"
        assert AiInsightFeedbackType.unsupported_claim.value == "unsupported_claim"


# ---------------------------------------------------------------------------
# 4. Route-level HTTP integration tests (in-memory DB)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    from backend.app import create_app

    _, fastapi_app = create_app()
    return fastapi_app


@pytest_asyncio.fixture(scope="module")
async def client(app):
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_and_login(client: AsyncClient, role: str, suffix: str = "") -> str:
    """Register a user with *role*, login, and return the bearer token."""
    email = f"{role}{suffix}@test.com"
    password = "pass1234"

    await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    # Promote role if needed
    from backend import security as sec
    from backend.sql_app.models import RoleEnum

    user = sec.find_in_memory_user_by_email(email)
    if user is not None:
        user.role = RoleEnum(role)

    login = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return login.json().get("access_token", "")


class TestAiInsightReviewRoutes:
    """HTTP-level integration tests for /ai-insights/review/* endpoints."""

    @pytest.mark.asyncio
    async def test_get_review_state_returns_pending_when_no_reviews(self, client):
        token = await _register_and_login(client, "analyst_pro", suffix="_get1")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/ai-insights/review/summary/match-xyz",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["current_state"] == "pending"
        assert data["is_advisory_only"] is True
        assert data["total_reviews"] == 0

    @pytest.mark.asyncio
    async def test_submit_review_creates_record(self, client):
        token = await _register_and_login(client, "analyst_pro", suffix="_sub1")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/ai-insights/review/summary/match-abc",
            json={"review_state": "approved", "feedback_type": "useful", "note": "Good insight."},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["review_state"] == "approved"
        assert data["feedback_type"] == "useful"
        assert data["note"] == "Good insight."

    @pytest.mark.asyncio
    async def test_unauthorized_user_is_blocked_on_get(self, client):
        token = await _register_and_login(client, "free", suffix="_blocked_get")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/ai-insights/review/summary/match-xyz",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_unauthorized_user_is_blocked_on_post(self, client):
        token = await _register_and_login(client, "coach_pro", suffix="_blocked_post")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/ai-insights/review/summary/match-xyz",
            json={"review_state": "approved"},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_invalid_insight_type_is_rejected(self, client):
        token = await _register_and_login(client, "analyst_pro", suffix="_invtype")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/ai-insights/review/INVALID_TYPE/match-xyz",
            json={"review_state": "approved"},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client):
        resp = await client.get("/ai-insights/review/summary/match-xyz")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_org_pro_can_submit_review(self, client):
        token = await _register_and_login(client, "org_pro", suffix="_orgpro1")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/ai-insights/review/report/report-001",
            json={"review_state": "changes_requested", "note": "Needs more context."},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_response_carries_advisory_only_marker(self, client):
        token = await _register_and_login(client, "analyst_pro", suffix="_adv1")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(
            "/ai-insights/review/summary/any-match",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["is_advisory_only"] is True


# ---------------------------------------------------------------------------
# 5. AI insight metadata fields remain visible (regression guard)
# ---------------------------------------------------------------------------


class TestAiInsightMetadataPreserved:
    """Existing confidence/limitations/source_refs fields must remain visible."""

    def test_ai_output_metadata_confidence_score_still_present(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType

        meta = AiOutputMetadata(
            output_type=AiOutputType.SUMMARY,
            confidence_score=0.75,
            limitations=["Small sample."],
        )
        assert meta.confidence_score == 0.75
        assert meta.limitations == ["Small sample."]
        assert meta.is_official_truth is False
        assert meta.requires_review is False

    def test_ai_output_metadata_source_refs_visible(self):
        from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType, AiSourceReference

        meta = AiOutputMetadata(
            output_type=AiOutputType.INSIGHT,
            source_refs=[AiSourceReference(type="match", id="m1", label="Match 1")],
        )
        assert len(meta.source_refs) == 1
        assert meta.source_refs[0].type == "match"

    def test_player_ai_insights_has_ai_metadata(self):
        from backend.services.ai_player_insights import PlayerAiInsights

        schema_fields = PlayerAiInsights.model_fields
        assert "ai_metadata" in schema_fields

    def test_match_ai_summary_has_ai_metadata(self):
        from backend.services.ai_match_summary import MatchAiSummary

        schema_fields = MatchAiSummary.model_fields
        assert "ai_metadata" in schema_fields
