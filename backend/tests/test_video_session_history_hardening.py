from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.sql_app.models import (
    OwnerTypeEnum,
    VideoAnalysisJob,
    VideoAnalysisJobStatus,
    VideoSession,
    VideoSessionStatus,
)


@pytest.mark.asyncio
async def test_session_history_includes_metadata(
    async_client, db_session, auth_headers, test_user
) -> None:
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="History Metadata Session",
        player_ids=["player-1"],
        status=VideoSessionStatus.ready,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    older_job = VideoAnalysisJob(
        session_id=session.id,
        status=VideoAnalysisJobStatus.failed,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    latest_job = VideoAnalysisJob(
        session_id=session.id,
        status=VideoAnalysisJobStatus.done,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([older_job, latest_job])
    await db_session.commit()

    resp = await async_client.get(
        "/api/coaches/plus/sessions?limit=10&offset=0", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    target = next(item for item in payload if item["id"] == session.id)
    assert target["analysis_job_count"] == 2
    assert target["latest_job_id"] == latest_job.id
    assert target["latest_job_status"] == "done"
    assert isinstance(target["latest_job_created_at"], str)
    assert target["latest_job_results_available"] is False
    assert target["latest_job_report_available"] is False
    assert target["latest_job_pdf_available"] is False
    assert set(target["missing_artifacts"]) == {"analysis_results", "analysis_report", "pdf_export"}


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_other_coach_history(
    async_client, db_session, auth_headers, other_auth_headers, test_user
) -> None:
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Private Session",
        player_ids=["player-2"],
        status=VideoSessionStatus.uploaded,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    job = VideoAnalysisJob(
        session_id=session.id,
        status=VideoAnalysisJobStatus.queued,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    session_resp = await async_client.get(
        f"/api/coaches/plus/sessions/{session.id}",
        headers=other_auth_headers,
    )
    assert session_resp.status_code == 403

    list_jobs_resp = await async_client.get(
        f"/api/coaches/plus/sessions/{session.id}/analysis-jobs",
        headers=other_auth_headers,
    )
    assert list_jobs_resp.status_code == 403

    get_job_resp = await async_client.get(
        f"/api/coaches/plus/analysis-jobs/{job.id}",
        headers=other_auth_headers,
    )
    assert get_job_resp.status_code == 403

    own_resp = await async_client.get(
        f"/api/coaches/plus/sessions/{session.id}",
        headers=auth_headers,
    )
    assert own_resp.status_code == 200


@pytest.mark.asyncio
async def test_job_history_includes_artifact_availability(
    async_client, db_session, auth_headers, test_user
) -> None:
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Artifact Session",
        player_ids=["player-3"],
        status=VideoSessionStatus.ready,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    job = VideoAnalysisJob(
        session_id=session.id,
        # Use legacy-complete status explicitly to ensure both completed+done paths stay covered.
        status=VideoAnalysisJobStatus.completed,
        quick_results={"ok": True},
        quick_report={"summary": "ready"},
        pdf_s3_key="coach_plus/reports/job.pdf",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.get(
        f"/api/coaches/plus/sessions/{session.id}/analysis-jobs",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert len(payload) == 1
    item = payload[0]
    assert item["results_available"] is True
    assert item["report_available"] is True
    assert item["pdf_available"] is True
    assert item["missing_artifacts"] == []


@pytest.mark.asyncio
async def test_completed_job_without_artifacts_is_marked_missing(
    async_client, db_session, auth_headers, test_user
) -> None:
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Missing Artifact Session",
        player_ids=["player-4"],
        status=VideoSessionStatus.ready,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    job = VideoAnalysisJob(
        session_id=session.id,
        status=VideoAnalysisJobStatus.done,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.get(
        f"/api/coaches/plus/analysis-jobs/{job.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    item = resp.json()
    assert item["results_available"] is False
    assert item["report_available"] is False
    assert item["pdf_available"] is False
    assert set(item["missing_artifacts"]) == {"analysis_results", "analysis_report", "pdf_export"}
