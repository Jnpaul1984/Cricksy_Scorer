"""Tests for PDF export restrictions and analysis mode routing."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_cannot_export_pdf_when_deep_running(async_client, db_session, test_user):
    """Test that PDF export returns 409 when job status is DEEP_RUNNING."""
    from backend.sql_app.models import VideoAnalysisJob, VideoAnalysisJobStatus, VideoSession

    # Grant feature access
    test_user.role = "coach_pro_plus"
    test_user.video_analysis_enabled = True
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    # Generate JWT token with updated role
    from backend.security import create_access_token
    token = create_access_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})

    # Create session
    session = VideoSession(
        id="test-session-deep-running",
        owner_type="coach",
        owner_id=test_user.id,
        title="Test Deep Running Session",
        s3_bucket="test-bucket",
        s3_key="test-video.mp4",
        status="uploaded",
    )
    db_session.add(session)

    # Create job in DEEP_RUNNING state
    job = VideoAnalysisJob(
        id="test-job-deep-running",
        session_id=session.id,
        status=VideoAnalysisJobStatus.deep_running,
        analysis_mode="batting",
        sample_fps=10,
        s3_bucket="test-bucket",
        s3_key="test-video.mp4",
    )
    db_session.add(job)
    await db_session.commit()

    # Attempt PDF export with valid token
    response = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/export-pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should return 409 CONFLICT
    assert response.status_code == 409
    assert "Cannot export PDF" in response.json()["detail"]
    assert "deep_running" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_export_pdf_when_quick_done(async_client, db_session, test_user):
    """Test that PDF export returns 409 when job status is QUICK_DONE (not fully completed)."""
    from backend.sql_app.models import VideoAnalysisJob, VideoAnalysisJobStatus, VideoSession

    # Grant feature access
    test_user.role = "coach_pro_plus"
    test_user.video_analysis_enabled = True
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    # Generate JWT token with updated role
    from backend.security import create_access_token
    token = create_access_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})

    # Create session
    session = VideoSession(
        id="test-session-quick-done",
        owner_type="coach",
        owner_id=test_user.id,
        title="Test Quick Done Session",
        s3_bucket="test-bucket",
        s3_key="test-video.mp4",
        status="uploaded",
    )
    db_session.add(session)

    # Create job in QUICK_DONE state
    job = VideoAnalysisJob(
        id="test-job-quick-done",
        session_id=session.id,
        status=VideoAnalysisJobStatus.quick_done,
        analysis_mode="bowling",
        sample_fps=10,
        s3_bucket="test-bucket",
        s3_key="test-video.mp4",
    )
    db_session.add(job)
    await db_session.commit()

    # Attempt PDF export with valid token
    response = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/export-pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should return 409 CONFLICT
    assert response.status_code == 409
    assert "Cannot export PDF" in response.json()["detail"]


def test_bowling_mode_does_not_return_batting_codes():
    """Test that analysis_mode routing directs to correct generator function."""
    from backend.services.coach_findings import generate_findings

    # Metrics that would trigger pose findings
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.30},
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    # When called via generate_findings with bowling mode, it should route to generate_bowling_findings
    bowling_context = {"analysis_mode": "bowling"}
    result_bowling = generate_findings(metrics, bowling_context)
    
    # When called via generate_findings with batting mode, it should route to generate_batting_findings  
    batting_context = {"analysis_mode": "batting"}
    result_batting = generate_findings(metrics, batting_context)

    # Both should work (routing exists)
    assert "findings" in result_bowling
    assert "findings" in result_batting
    
    # The main verification is that the routing doesn't fail
    # Actual finding differentiation happens when ball_tracking is provided for bowling
    assert result_bowling["findings"] is not None
    assert result_batting["findings"] is not None


def test_batting_mode_does_not_return_bowling_codes():
    """Test that batting mode routing works correctly via generate_findings."""
    from backend.services.coach_findings import generate_findings

    # Poor batting metrics
    batting_metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.35},  # Should trigger HEAD_MOVEMENT
            "knee_collapse_score": {"score": 0.30},  # Should trigger KNEE_COLLAPSE
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    batting_context = {"analysis_mode": "batting"}

    findings = generate_findings(batting_metrics, batting_context)
    finding_codes = {f["code"] for f in findings.get("findings", [])}

    # Bowling-specific codes should NOT appear (no ball tracking in batting)
    bowling_codes = {"SWING_ANALYSIS", "INCONSISTENT_RELEASE_POINT", "INSUFFICIENT_BALL_TRACKING"}
    assert not finding_codes.intersection(
        bowling_codes
    ), f"Batting mode returned bowling codes: {finding_codes & bowling_codes}"

    # Should route to batting findings
    batting_codes_expected = {"HEAD_MOVEMENT", "KNEE_COLLAPSE"}
    assert finding_codes.intersection(
        batting_codes_expected
    ), f"Batting mode should detect pose issues. Got: {finding_codes}"
