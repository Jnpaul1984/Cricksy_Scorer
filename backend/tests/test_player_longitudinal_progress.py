from __future__ import annotations

import datetime as dt
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("mediapipe", MagicMock())

from backend.services.player_longitudinal_progress import build_player_longitudinal_progress
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)


def _metric_payload(
    *,
    metric_id: str,
    raw_value: float,
    unit: str,
    discipline: str = "batting",
    metric_version: str = "batting_pose_metrics.v2.0.0",
    phase: str | None = None,
    camera_view: str = "side",
    sample_fps: float = 10.0,
    source_video_fps: float = 30.0,
    validity_state: str = "VALID",
    confidence_score: float = 0.9,
) -> dict[str, object]:
    return {
        "metric_version": metric_version,
        "metric_id": metric_id,
        "discipline": discipline,
        "phase": phase,
        "raw_value": raw_value,
        "unit": unit,
        "normalized_score": raw_value if unit == "score" else None,
        "confidence_score": confidence_score,
        "validity_state": validity_state,
        "capture_profile": {
            "camera_view": camera_view,
            "sample_fps": sample_fps,
            "effective_analysis_fps": sample_fps,
            "source_video_fps": source_video_fps,
            "discipline": discipline,
            "analysis_mode": "bowling" if "bowling" in discipline else discipline,
            "metric_version": metric_version,
            "source_model": "MediaPipe Pose Landmarker Full",
        },
        "aggregate_stats": {
            "count": 4,
            "valid_repetition_count": 4,
            "repetition_count": 4,
        },
        "consistency": {
            "status": "ANALYZED",
            "method": "population_standard_deviation",
            "classification": "stable",
            "value": 0.03,
            "valid_sample_count": 4,
            "limitations": [],
        },
    }


def _job(job_id: str, when: dt.datetime, metrics: list[dict[str, object]]) -> SimpleNamespace:
    return SimpleNamespace(
        id=job_id,
        created_at=when,
        completed_at=when,
        deep_results={"v2": {"metric_results": metrics}},
        quick_results=None,
        results=None,
    )


def _session(
    session_id: str,
    when: dt.datetime,
    *,
    player_id: str = "player-1",
    primary_player_id: str | None = "player-1",
    discipline: str = "batting",
    metrics: list[dict[str, object]] | None = None,
    player_ids: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        title=f"Session {session_id}",
        created_at=when,
        primary_player_id=primary_player_id,
        player_ids=player_ids or [player_id],
        discipline=discipline,
        coaching_focus="technique",
        analysis_jobs=[_job(f"job-{session_id}", when, metrics or [])],
    )


def test_longitudinal_progress_builds_baseline_latest_best_and_excludes_camera_mismatch() -> None:
    sessions = [
        _session(
            "s1",
            dt.datetime(2026, 1, 1, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_downswing_head_stability_score",
                    raw_value=0.55,
                    unit="score",
                    phase="downswing",
                )
            ],
        ),
        _session(
            "s2",
            dt.datetime(2026, 1, 10, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_downswing_head_stability_score",
                    raw_value=0.68,
                    unit="score",
                    phase="downswing",
                )
            ],
        ),
        _session(
            "s3",
            dt.datetime(2026, 1, 20, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_downswing_head_stability_score",
                    raw_value=0.78,
                    unit="score",
                    phase="downswing",
                )
            ],
        ),
        _session(
            "s4",
            dt.datetime(2026, 1, 25, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_downswing_head_stability_score",
                    raw_value=0.82,
                    unit="score",
                    phase="downswing",
                    camera_view="front",
                )
            ],
        ),
    ]

    result = build_player_longitudinal_progress(
        sessions,
        player_id="player-1",
        discipline_filter="batting",
    )

    assert result["series_count"] == 1
    series = result["series"][0]
    assert series["baseline"]["raw_value"] == 0.55
    assert series["latest"]["raw_value"] == 0.78
    assert series["best"]["raw_value"] == 0.78
    assert series["best_direction"] == "higher"
    assert series["trend"]["state"] == "improving"
    assert series["comparable_session_count"] == 3
    assert series["history_count"] == 4
    excluded = next(item for item in series["history"] if item["session_id"] == "s4")
    assert excluded["comparable"] is False
    assert any(
        "Camera views do not match." in reason for reason in excluded["comparability_reasons"]
    )


def test_longitudinal_progress_uses_target_range_best_and_mixed_trend() -> None:
    sessions = [
        _session(
            "s1",
            dt.datetime(2026, 2, 1, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_setup_stance_width_ratio",
                    raw_value=1.0,
                    unit="ratio",
                    phase="setup",
                )
            ],
        ),
        _session(
            "s2",
            dt.datetime(2026, 2, 8, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_setup_stance_width_ratio",
                    raw_value=1.35,
                    unit="ratio",
                    phase="setup",
                )
            ],
        ),
        _session(
            "s3",
            dt.datetime(2026, 2, 15, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_setup_stance_width_ratio",
                    raw_value=0.95,
                    unit="ratio",
                    phase="setup",
                )
            ],
        ),
    ]

    result = build_player_longitudinal_progress(
        sessions, player_id="player-1", discipline_filter="batting"
    )

    series = result["series"][0]
    assert series["best_direction"] == "target_range"
    assert series["best"]["raw_value"] == 1.35
    assert series["trend"]["state"] == "mixed"
    assert series["best_available"] is True


def test_longitudinal_progress_marks_unknown_metric_best_unavailable_and_insufficient() -> None:
    sessions = [
        _session(
            "s1",
            dt.datetime(2026, 3, 1, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_unknown_signal",
                    raw_value=0.4,
                    unit="ratio",
                    phase="setup",
                )
            ],
        ),
        _session(
            "s2",
            dt.datetime(2026, 3, 8, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="batting_unknown_signal",
                    raw_value=0.8,
                    unit="ratio",
                    phase="setup",
                    metric_version="batting_pose_metrics.v3.0.0",
                )
            ],
        ),
    ]

    result = build_player_longitudinal_progress(
        sessions, player_id="player-1", discipline_filter="batting"
    )

    series = result["series"][0]
    assert series["best_available"] is False
    assert series["trend"]["state"] == "insufficient_data"
    assert series["comparable_session_count"] == 1


def test_longitudinal_progress_reports_across_session_variability() -> None:
    sessions = [
        _session(
            "s1",
            dt.datetime(2026, 4, 1, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="wicketkeeping_movement_lateral_displacement_ratio",
                    raw_value=0.6,
                    unit="ratio",
                    discipline="wicketkeeping",
                    metric_version="wicketkeeping_pose_metrics.v2.0.0",
                    phase="movement",
                )
            ],
        ),
        _session(
            "s2",
            dt.datetime(2026, 4, 10, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="wicketkeeping_movement_lateral_displacement_ratio",
                    raw_value=1.8,
                    unit="ratio",
                    discipline="wicketkeeping",
                    metric_version="wicketkeeping_pose_metrics.v2.0.0",
                    phase="movement",
                )
            ],
        ),
        _session(
            "s3",
            dt.datetime(2026, 4, 17, tzinfo=UTC),
            metrics=[
                _metric_payload(
                    metric_id="wicketkeeping_movement_lateral_displacement_ratio",
                    raw_value=0.7,
                    unit="ratio",
                    discipline="wicketkeeping",
                    metric_version="wicketkeeping_pose_metrics.v2.0.0",
                    phase="movement",
                )
            ],
        ),
    ]

    result = build_player_longitudinal_progress(
        sessions,
        player_id="player-1",
        discipline_filter="wicketkeeping",
    )

    series = result["series"][0]
    assert series["across_session_consistency"]["classification"] == "variable"


@pytest.mark.asyncio
async def test_longitudinal_progress_route_enforces_assignments_and_player_isolation(
    async_client,
    db_session,
    auth_headers,
    other_auth_headers,
    test_user,
    other_user,
) -> None:
    profile = models.PlayerProfile(player_id="player-long-001", player_name="Longitudinal Player")
    other_profile = models.PlayerProfile(player_id="player-long-002", player_name="Other Player")
    db_session.add_all(
        [
            profile,
            other_profile,
            models.CoachPlayerAssignment(
                id="assign-long-001",
                coach_user_id=test_user.id,
                player_profile_id=profile.player_id,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    session_one = models.VideoSession(
        id="video-long-001",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Batting Day 1",
        player_ids=[profile.player_id],
        primary_player_id=profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    session_two = models.VideoSession(
        id="video-long-002",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Batting Day 2",
        player_ids=[profile.player_id],
        primary_player_id=profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    hidden_session = models.VideoSession(
        id="video-long-hidden",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=other_user.id,
        title="Other Player Session",
        player_ids=[other_profile.player_id],
        primary_player_id=other_profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    db_session.add_all([session_one, session_two, hidden_session])
    await db_session.commit()

    job_one = models.VideoAnalysisJob(
        id="job-long-001",
        session_id=session_one.id,
        status=models.VideoAnalysisJobStatus.done,
        deep_results={
            "v2": {
                "metric_results": [
                    _metric_payload(
                        metric_id="batting_downswing_head_stability_score",
                        raw_value=0.58,
                        unit="score",
                        phase="downswing",
                    )
                ]
            }
        },
    )
    job_two = models.VideoAnalysisJob(
        id="job-long-002",
        session_id=session_two.id,
        status=models.VideoAnalysisJobStatus.done,
        deep_results={
            "v2": {
                "metric_results": [
                    _metric_payload(
                        metric_id="batting_downswing_head_stability_score",
                        raw_value=0.74,
                        unit="score",
                        phase="downswing",
                    )
                ]
            }
        },
    )
    db_session.add_all([job_one, job_two])
    await db_session.commit()

    ok_resp = await async_client.get(
        f"/api/coaches/plus/players/{profile.player_id}/longitudinal-progress?discipline=batting",
        headers=auth_headers,
    )
    assert ok_resp.status_code == 200, ok_resp.text
    payload = ok_resp.json()
    assert payload["player_id"] == profile.player_id
    assert payload["series_count"] == 1
    assert payload["series"][0]["comparable_session_count"] == 2
    history_session_ids = {item["session_id"] for item in payload["series"][0]["history"]}
    assert history_session_ids == {session_one.id, session_two.id}

    forbidden_resp = await async_client.get(
        f"/api/coaches/plus/players/{profile.player_id}/longitudinal-progress?discipline=batting",
        headers=other_auth_headers,
    )
    assert forbidden_resp.status_code == 403


@pytest.mark.asyncio
async def test_v2_goal_linkage_and_evaluation_is_additive_and_deterministic(
    async_client,
    db_session,
    auth_headers,
    test_user,
) -> None:
    profile = models.PlayerProfile(player_id="player-goal-001", player_name="Goal Player")
    db_session.add_all(
        [
            profile,
            models.CoachPlayerAssignment(
                id="assign-goal-001",
                coach_user_id=test_user.id,
                player_profile_id=profile.player_id,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    session_one = models.VideoSession(
        id="video-goal-001",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Batting Baseline",
        player_ids=[profile.player_id],
        primary_player_id=profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    session_two = models.VideoSession(
        id="video-goal-002",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Batting Follow-up",
        player_ids=[profile.player_id],
        primary_player_id=profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    db_session.add_all([session_one, session_two])
    await db_session.commit()

    baseline_metric = _metric_payload(
        metric_id="batting_downswing_head_stability_score",
        raw_value=0.55,
        unit="score",
        phase="downswing",
    )
    followup_metric = _metric_payload(
        metric_id="batting_downswing_head_stability_score",
        raw_value=0.78,
        unit="score",
        phase="downswing",
    )
    baseline_job = models.VideoAnalysisJob(
        id="job-goal-001",
        session_id=session_one.id,
        status=models.VideoAnalysisJobStatus.completed,
        deep_results={"v2": {"metric_results": [baseline_metric]}},
        deep_findings={"findings": []},
    )
    followup_job = models.VideoAnalysisJob(
        id="job-goal-002",
        session_id=session_two.id,
        status=models.VideoAnalysisJobStatus.completed,
        deep_results={"v2": {"metric_results": [followup_metric]}},
        deep_findings={"findings": []},
    )
    db_session.add_all([baseline_job, followup_job])
    await db_session.commit()

    set_resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{followup_job.id}/set-goals",
        headers=auth_headers,
        json={
            "zones": [],
            "metrics": [],
            "v2_goals": [
                {
                    "goal_id": "goal-v2-001",
                    "player_id": profile.player_id,
                    "discipline": "batting",
                    "metric_id": "batting_downswing_head_stability_score",
                    "phase": "downswing",
                    "target_type": "increase_to_threshold",
                    "target_value": 0.7,
                    "baseline_job_id": baseline_job.id,
                    "approval_state": "coach_only",
                    "visible_to_player": False,
                }
            ],
            "interventions": [
                {
                    "intervention_type": "drill",
                    "activity": "Head stability net drill",
                    "frequency": "3x weekly",
                    "linked_goal_ids": ["goal-v2-001"],
                    "completion_state": "planned",
                }
            ],
        },
    )
    assert set_resp.status_code == 200, set_resp.text

    calc_resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{followup_job.id}/calculate-compliance",
        headers=auth_headers,
    )
    assert calc_resp.status_code == 200, calc_resp.text
    payload = calc_resp.json()
    assert "v2_target_evidence" in payload
    assert payload["v2_target_evidence"][0]["status"] == "achieved"
    assert payload["v2_target_evidence"][0]["baseline"]["job_id"] == baseline_job.id
    assert payload["v2_target_evidence"][0]["latest"]["job_id"] == followup_job.id
    assert payload["interventions"][0]["completion_state"] == "planned"
    assert "inferred_adherence" not in payload["interventions"][0]


@pytest.mark.asyncio
async def test_v2_goal_linkage_rejects_cross_player_and_unsupported_metric(
    async_client,
    db_session,
    auth_headers,
    test_user,
) -> None:
    owner_profile = models.PlayerProfile(player_id="player-goal-010", player_name="Owner Player")
    other_profile = models.PlayerProfile(player_id="player-goal-011", player_name="Other Player")
    db_session.add_all(
        [
            owner_profile,
            other_profile,
            models.CoachPlayerAssignment(
                id="assign-goal-010",
                coach_user_id=test_user.id,
                player_profile_id=owner_profile.player_id,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    session = models.VideoSession(
        id="video-goal-010",
        owner_type=models.OwnerTypeEnum.coach,
        owner_id=test_user.id,
        title="Goal Link Test",
        player_ids=[owner_profile.player_id],
        primary_player_id=owner_profile.player_id,
        discipline="batting",
        analysis_context=models.AnalysisContext.batting,
        camera_view=models.CameraView.side,
        status=models.VideoSessionStatus.ready,
    )
    db_session.add(session)
    await db_session.commit()

    job = models.VideoAnalysisJob(
        id="job-goal-010",
        session_id=session.id,
        status=models.VideoAnalysisJobStatus.completed,
        deep_results={
            "v2": {
                "metric_results": [
                    _metric_payload(
                        metric_id="batting_downswing_head_stability_score",
                        raw_value=0.6,
                        unit="score",
                        phase="downswing",
                    )
                ]
            }
        },
        deep_findings={"findings": []},
    )
    db_session.add(job)
    await db_session.commit()

    cross_player_resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/set-goals",
        headers=auth_headers,
        json={
            "v2_goals": [
                {
                    "goal_id": "goal-v2-cross",
                    "player_id": other_profile.player_id,
                    "discipline": "batting",
                    "metric_id": "batting_downswing_head_stability_score",
                    "target_type": "increase_to_threshold",
                    "target_value": 0.75,
                }
            ]
        },
    )
    assert cross_player_resp.status_code == 403

    unsupported_metric_resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/set-goals",
        headers=auth_headers,
        json={
            "v2_goals": [
                {
                    "goal_id": "goal-v2-unsupported",
                    "player_id": owner_profile.player_id,
                    "discipline": "batting",
                    "metric_id": "batting_non_existent_metric",
                    "target_type": "increase_to_threshold",
                    "target_value": 0.75,
                }
            ]
        },
    )
    assert unsupported_metric_resp.status_code == 422
