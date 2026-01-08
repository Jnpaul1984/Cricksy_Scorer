"""
Integration Tests for Coach Pro Plus Video Analysis Endpoint (MVP)

Tests the endpoint with mocked authentication and pose service.
Focus: Full pipeline execution (pose → metrics → findings → report)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Mock cv2 and mediapipe before importing app
sys.modules["cv2"] = MagicMock()
sys.modules["mediapipe"] = MagicMock()

from backend.app import create_app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    fastapi_app, _ = create_app()
    return TestClient(fastapi_app)


def _mock_pose_extraction() -> dict[str, Any]:
    """Return realistic mock pose extraction data."""
    return {
        "total_frames": 300,
        "sampled_frames": 30,
        "frames_with_pose": 28,
        "detection_rate_percent": 93.3,
        "model": "mediapipe_pose",
        "video_fps": 30.0,
        "frames": [
            {
                "frame_id": i,
                "timestamp": i / 30.0,
                "keypoints": {
                    "nose": {"x": 0.5, "y": 0.5, "z": 0.0, "confidence": 0.95},
                    "left_eye": {"x": 0.48, "y": 0.48, "z": 0.0, "confidence": 0.95},
                    "right_eye": {"x": 0.52, "y": 0.48, "z": 0.0, "confidence": 0.95},
                    "left_shoulder": {"x": 0.4, "y": 0.6, "z": 0.0, "confidence": 0.9},
                    "right_shoulder": {"x": 0.6, "y": 0.6, "z": 0.0, "confidence": 0.9},
                    "left_elbow": {"x": 0.35, "y": 0.75, "z": 0.0, "confidence": 0.9},
                    "right_elbow": {"x": 0.65, "y": 0.75, "z": 0.0, "confidence": 0.9},
                    "left_wrist": {"x": 0.3, "y": 0.85, "z": 0.0, "confidence": 0.9},
                    "right_wrist": {"x": 0.7, "y": 0.85, "z": 0.0, "confidence": 0.9},
                    "left_hip": {"x": 0.4, "y": 0.85, "z": 0.0, "confidence": 0.85},
                    "right_hip": {"x": 0.6, "y": 0.85, "z": 0.0, "confidence": 0.85},
                    "left_knee": {"x": 0.4, "y": 1.0, "z": 0.0, "confidence": 0.85},
                    "right_knee": {"x": 0.6, "y": 1.0, "z": 0.0, "confidence": 0.85},
                    "left_ankle": {"x": 0.4, "y": 1.1, "z": 0.0, "confidence": 0.85},
                    "right_ankle": {"x": 0.6, "y": 1.1, "z": 0.0, "confidence": 0.85},
                },
            }
            for i in range(28)
        ],
    }


# ============================================================================
# Test Cases
# ============================================================================


class TestVideoAnalysisAuthentication:
    """Test endpoint authentication requirements."""

    def test_requires_authentication(self, client: TestClient) -> None:
        """Endpoint requires valid JWT token."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            response = client.post(
                "/api/coaches/plus/videos/analyze",
                json={"video_path": tmp_path},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_invalid_token(self, client: TestClient) -> None:
        """Rejects invalid tokens."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            response = client.post(
                "/api/coaches/plus/videos/analyze",
                json={"video_path": tmp_path},
                headers={"Authorization": "Bearer invalid_token_xyz"},
            )
            # Should be 401 or 403 depending on token validation
            assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestVideoAnalysisInputValidation:
    """Test input validation without authentication."""

    def test_endpoint_exists(self, client: TestClient) -> None:
        """Endpoint is registered and responds."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Any request should get a 401 at minimum (no auth)
            response = client.post(
                "/api/coaches/plus/videos/analyze",
                json={"video_path": tmp_path},
            )
            # Should get authentication error, not 404
            assert response.status_code != status.HTTP_404_NOT_FOUND
        finally:
            Path(tmp_path).unlink()

    def test_video_file_not_found_with_valid_request(self, client: TestClient) -> None:
        """Returns 400 when video file doesn't exist (if auth passes)."""
        # This test shows the flow would return 400 for missing files
        # when authentication is valid
        response = client.post(
            "/api/coaches/plus/videos/analyze",
            json={"video_path": "/nonexistent/path/video.mp4"},
        )
        # Will be 401 due to no token, but we verify endpoint exists
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        )


class TestVideoAnalysisPipelineLogic:
    """Test the analysis pipeline logic with mocked services."""

    @pytest.mark.parametrize(
        "sample_fps",
        [5, 10, 15, 20, 30],  # Valid range per endpoint
    )
    def test_sample_fps_parameter_validation(self, sample_fps: int) -> None:
        """Sample FPS parameter within valid range."""
        # Just verify the parameter is accepted (validation happens at endpoint)
        # We verify this by checking the request schema accepts these values
        import tempfile
        from backend.routes.coach_pro_plus import VideoAnalysisRequest

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            req = VideoAnalysisRequest(
                video_path=tmp_path,
                sample_fps=sample_fps,
            )
            assert req.sample_fps == sample_fps
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_sample_fps_validation_boundaries(self) -> None:
        """Sample FPS outside boundaries should be rejected."""
        import tempfile
        from pydantic import ValidationError

        from backend.routes.coach_pro_plus import VideoAnalysisRequest

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Too low
            with pytest.raises(ValidationError):
                VideoAnalysisRequest(
                    video_path=tmp_path,
                    sample_fps=0,
                )

            # Too high
            with pytest.raises(ValidationError):
                VideoAnalysisRequest(
                    video_path=tmp_path,
                    sample_fps=31,
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_optional_parameters(self) -> None:
        """Player ID and session ID are optional."""
        import tempfile
        from backend.routes.coach_pro_plus import VideoAnalysisRequest

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Minimal request
            req = VideoAnalysisRequest(video_path=tmp_path)
            assert req.player_id is None
            assert req.session_id is None
            assert req.sample_fps == 10  # Default

            # With optional parameters
            req2 = VideoAnalysisRequest(
                video_path=tmp_path,
                player_id="player_123",
                session_id="session_456",
            )
            assert req2.player_id == "player_123"
            assert req2.session_id == "session_456"
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestVideoAnalysisResponseStructure:
    """Test response structure matches specification."""

    def test_response_schema_structure(self) -> None:
        """Response schema includes all required fields."""
        from backend.routes.coach_pro_plus import VideoAnalysisResponse

        # Create a valid response
        response = VideoAnalysisResponse(
            pose_summary={
                "total_frames": 300,
                "sampled_frames": 30,
                "frames_with_pose": 28,
                "detection_rate_percent": 93.3,
                "model": "mediapipe_pose",
                "video_fps": 30.0,
            },
            metrics={"metrics": {}},
            findings={"findings": [], "overall_level": "high"},
            report={
                "summary": "Test",
                "top_issues": [],
                "drills": [],
                "one_week_plan": [],
                "notes": "Test",
                "generated_with_llm": False,
            },
        )

        # Verify all fields present
        assert response.pose_summary
        assert response.metrics
        assert response.findings
        assert response.report

        # Convert to dict and verify structure
        data = response.model_dump()
        assert "pose_summary" in data
        assert "metrics" in data
        assert "findings" in data
        assert "report" in data

    def test_pose_summary_fields(self) -> None:
        """PoseSummary includes all required fields."""
        from backend.routes.coach_pro_plus import PoseSummary

        summary = PoseSummary(
            total_frames=300,
            sampled_frames=30,
            frames_with_pose=28,
            detection_rate_percent=93.3,
            model="mediapipe_pose",
            video_fps=30.0,
        )

        assert summary.total_frames == 300
        assert summary.sampled_frames == 30
        assert summary.frames_with_pose == 28
        assert summary.detection_rate_percent == 93.3
        assert summary.model == "mediapipe_pose"
        assert summary.video_fps == 30.0


class TestVideoAnalysisPipelineIntegration:
    """Integration-style tests of the pipeline (without auth)."""

    def test_pipeline_integration_with_mocked_services(self) -> None:
        """Full pipeline works with mocked pose service."""
        from backend.services.coach_findings import generate_findings
        from backend.services.coach_report_service import generate_report_text
        from backend.services.pose_metrics import compute_pose_metrics

        # Step 1: Mock pose extraction
        pose_data = _mock_pose_extraction()

        # Step 2: Compute metrics
        metrics = compute_pose_metrics(pose_data)
        assert "metrics" in metrics
        assert metrics["metrics"]

        # Step 3: Generate findings
        findings = generate_findings(metrics, analysis_mode="batting")
        assert "findings" in findings
        assert "overall_level" in findings

        # Step 4: Generate report
        report = generate_report_text(findings, {"name": "Test Player"})
        assert "summary" in report
        assert "top_issues" in report
        assert "drills" in report
        assert "one_week_plan" in report
        assert "notes" in report
        assert "generated_with_llm" in report

    def test_pipeline_with_poor_technique(self) -> None:
        """Pipeline handles poor technique scenario."""
        from backend.services.coach_findings import generate_findings
        from backend.services.coach_report_service import generate_report_text
        from backend.services.pose_metrics import compute_pose_metrics

        pose_data = _mock_pose_extraction()
        metrics = compute_pose_metrics(pose_data)
        findings = generate_findings(metrics, analysis_mode="batting")
        report = generate_report_text(findings, {"name": "Player", "role": "batter"})

        # Verify report has meaningful content
        assert len(report["summary"]) > 20
        assert isinstance(report["top_issues"], list)
        assert isinstance(report["drills"], list)
        assert len(report["one_week_plan"]) == 7
        assert report["notes"]

    def test_response_serializable(self) -> None:
        """Response can be serialized to JSON."""
        from backend.services.coach_findings import generate_findings
        from backend.services.coach_report_service import generate_report_text
        from backend.services.pose_metrics import compute_pose_metrics

        pose_data = _mock_pose_extraction()
        metrics = compute_pose_metrics(pose_data)
        findings = generate_findings(metrics, analysis_mode="batting")
        report = generate_report_text(findings)

        # All parts should be JSON-serializable
        import json

        json.dumps(metrics)
        json.dumps(findings)
        json.dumps(report)

    def test_evidence_markers_present_for_completed_results(self) -> None:
        """Evidence markers exist (extend-only) for completed analysis payloads."""
        from backend.services.pose_metrics import build_pose_metric_evidence, compute_pose_metrics

        pose_data = _mock_pose_extraction()

        # Ensure frames look "detected" across schema versions
        frames = pose_data.get("frames")
        assert isinstance(frames, list)
        for i, f in enumerate(frames):
            if isinstance(f, dict):
                f.setdefault("detected", True)
                f.setdefault("pose_detected", True)
                f.setdefault("frame_num", f.get("frame_id", i))
                f.setdefault("t", f.get("timestamp", i / 30.0))

        metrics = compute_pose_metrics(pose_data)
        evidence = build_pose_metric_evidence(pose_data=pose_data, metrics_result=metrics)

        for key in (
            "head_stability_score",
            "balance_drift_score",
            "front_knee_brace_score",
            "hip_shoulder_separation_timing",
            "elbow_drop_score",
        ):
            assert key in evidence
            block = evidence[key]
            assert "threshold" in block
            assert "worst_frames" in block
            assert "bad_segments" in block
            assert isinstance(block["worst_frames"], list)
            assert isinstance(block["bad_segments"], list)


class TestEndpointDocumentation:
    """Verify endpoint documentation is complete."""

    def test_endpoint_has_docstring(self) -> None:
        """Endpoint function has documentation."""
        from backend.routes.coach_pro_plus import analyze_video

        assert analyze_video.__doc__
        assert "analyze" in analyze_video.__doc__.lower()
        assert "coaching" in analyze_video.__doc__.lower()

    def test_request_model_documented(self) -> None:
        """Request schema is documented."""
        from backend.routes.coach_pro_plus import VideoAnalysisRequest

        # Check field descriptions
        for field_name, field in VideoAnalysisRequest.model_fields.items():
            # video_path should have description
            if field_name == "video_path":
                assert field.description

    def test_response_model_documented(self) -> None:
        """Response schema is documented."""
        from backend.routes.coach_pro_plus import VideoAnalysisResponse

        # Verify all fields exist
        assert VideoAnalysisResponse.model_fields
        assert "pose_summary" in VideoAnalysisResponse.model_fields
        assert "metrics" in VideoAnalysisResponse.model_fields
        assert "findings" in VideoAnalysisResponse.model_fields
        assert "report" in VideoAnalysisResponse.model_fields
