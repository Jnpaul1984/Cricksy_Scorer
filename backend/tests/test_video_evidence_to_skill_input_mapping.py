from __future__ import annotations

import copy
import os

import pytest

from backend.domain.player_development_skill_contract import PLAYER_DEVELOPMENT_SKILL_REGISTRY
from backend.services.video_evidence_skill_mapping import (
    MAX_EVIDENCE_MARKERS,
    VideoEvidenceSkillInputInsufficientDataError,
    VideoEvidenceSkillMappingError,
    build_coaching_video_evidence_skill_input,
)
from backend.sql_app.models import (
    OwnerTypeEnum,
    VideoAnalysisJob,
    VideoAnalysisJobStatus,
    VideoSession,
    VideoSessionStatus,
)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


def _session(session_id: str = "session-1") -> VideoSession:
    return VideoSession(
        id=session_id,
        owner_type=OwnerTypeEnum.coach,
        owner_id="coach-1",
        title="Session",
        player_ids=["player-1"],
        status=VideoSessionStatus.ready,
    )


def _job(
    *,
    session_id: str = "session-1",
    status: VideoAnalysisJobStatus = VideoAnalysisJobStatus.done,
    analysis_mode: str | None = "batting",
    deep_results: dict[str, object] | None = None,
    quick_results: dict[str, object] | None = None,
    results: dict[str, object] | None = None,
) -> VideoAnalysisJob:
    return VideoAnalysisJob(
        id="job-1",
        session_id=session_id,
        sample_fps=10,
        include_frames=False,
        status=status,
        analysis_mode=analysis_mode,
        deep_results=deep_results,
        quick_results=quick_results,
        results=results,
    )


def _build_payload(video_session: VideoSession, job: VideoAnalysisJob) -> dict[str, object]:
    return build_coaching_video_evidence_skill_input(
        player_profile_id="player-1",
        coach_user_id="coach-1",
        org_id="org-1",
        video_session=video_session,
        video_analysis_job=job,
    )


def test_completed_deep_job_evidence_maps_to_skill_input() -> None:
    session = _session()
    job = _job(
        deep_results={
            "metrics": {
                "evidence": {
                    "head_stability_score": {
                        "threshold": 0.6,
                        "worst_frames": [{"frame_num": 11, "timestamp_s": 1.1, "score": 0.2}],
                        "bad_segments": [{"start_frame": 10, "start_timestamp_s": 1.0, "min_score": 0.15}],
                    }
                }
            }
        }
    )

    payload = _build_payload(session, job)

    markers = payload["evidence_markers"]
    assert isinstance(markers, list)
    assert len(markers) == 2
    assert payload["analysis_mode"] == "batting"
    assert payload["video_analysis_job_id"] == "job-1"


def test_completed_quick_job_maps_when_deep_is_absent() -> None:
    session = _session()
    job = _job(
        deep_results=None,
        quick_results={
            "evidence": {
                "balance_drift_score": {
                    "threshold": 0.65,
                    "worst_frames": [{"frame_num": 30, "timestamp_s": 3.0, "score": 0.3}],
                }
            }
        },
    )

    payload = _build_payload(session, job)
    marker = payload["evidence_markers"][0]  # type: ignore[index]
    assert marker["metric_name"] == "balance_drift_score"  # type: ignore[index]
    assert marker["timestamp_s"] == 3.0  # type: ignore[index]


def test_deep_evidence_is_preferred_over_quick_evidence() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {
                    "worst_frames": [{"frame_num": 1, "timestamp_s": 1.0, "score": 0.2}]
                }
            }
        },
        quick_results={
            "evidence": {
                "balance_drift_score": {
                    "worst_frames": [{"frame_num": 99, "timestamp_s": 99.0, "score": 0.01}]
                }
            }
        },
    )

    payload = _build_payload(session, job)
    markers = payload["evidence_markers"]
    assert isinstance(markers, list)
    assert markers[0]["metric_name"] == "head_stability_score"
    assert markers[0]["timestamp_s"] == 1.0


def test_legacy_results_evidence_maps_when_quick_and_deep_absent() -> None:
    session = _session()
    job = _job(
        deep_results=None,
        quick_results=None,
        results={
            "metrics": {
                "evidence": {
                    "elbow_drop_score": {
                        "threshold": 0.7,
                        "worst_frames": [{"frame_num": 8, "timestamp_s": 0.8, "score": 0.44}],
                    }
                }
            }
        },
    )

    payload = _build_payload(session, job)
    marker = payload["evidence_markers"][0]  # type: ignore[index]
    assert marker["metric_name"] == "elbow_drop_score"  # type: ignore[index]
    assert marker["threshold"] == 0.7  # type: ignore[index]


def test_marker_timestamps_are_preserved() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {
                    "worst_frames": [{"frame_num": 17, "timestamp_s": 2.75, "score": 0.33}]
                }
            }
        }
    )

    payload = _build_payload(session, job)
    marker = payload["evidence_markers"][0]  # type: ignore[index]
    assert marker["timestamp_s"] == 2.75  # type: ignore[index]


def test_markers_without_timestamps_are_excluded() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {
                    "worst_frames": [
                        {"frame_num": 9, "score": 0.2},
                        {"frame_num": 10, "timestamp_s": 1.0, "score": 0.21},
                    ]
                }
            }
        }
    )

    payload = _build_payload(session, job)
    markers = payload["evidence_markers"]
    assert isinstance(markers, list)
    assert len(markers) == 1
    assert markers[0]["frame_num"] == 10


def test_mapping_is_capped_to_max_evidence_markers() -> None:
    session = _session()
    worst_frames = [
        {"frame_num": idx, "timestamp_s": float(idx), "score": 0.2}
        for idx in range(MAX_EVIDENCE_MARKERS + 7)
    ]
    job = _job(
        deep_results={"evidence": {"head_stability_score": {"worst_frames": worst_frames}}},
    )

    payload = _build_payload(session, job)
    markers = payload["evidence_markers"]
    assert isinstance(markers, list)
    assert len(markers) == MAX_EVIDENCE_MARKERS


def test_non_completed_jobs_are_rejected() -> None:
    session = _session()
    job = _job(
        status=VideoAnalysisJobStatus.queued,
        deep_results={
            "evidence": {"head_stability_score": {"worst_frames": [{"timestamp_s": 1.0}]}}
        },
    )

    with pytest.raises(VideoEvidenceSkillMappingError):
        _build_payload(session, job)


def test_session_job_mismatch_is_rejected() -> None:
    session = _session(session_id="session-a")
    job = _job(
        session_id="session-b",
        deep_results={
            "evidence": {"head_stability_score": {"worst_frames": [{"timestamp_s": 1.0}]}}
        },
    )

    with pytest.raises(VideoEvidenceSkillMappingError):
        _build_payload(session, job)


def test_missing_analysis_mode_is_rejected() -> None:
    session = _session()
    job = _job(
        analysis_mode=None,
        deep_results={
            "evidence": {"head_stability_score": {"worst_frames": [{"timestamp_s": 1.0}]}}
        },
    )

    with pytest.raises(VideoEvidenceSkillMappingError):
        _build_payload(session, job)


def test_no_valid_evidence_returns_controlled_insufficient_data_error() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {"worst_frames": [{"frame_num": 1, "score": 0.2}]}
            }
        }
    )

    with pytest.raises(VideoEvidenceSkillInputInsufficientDataError):
        _build_payload(session, job)


def test_malformed_evidence_structures_are_rejected() -> None:
    session = _session()
    job = _job(deep_results={"evidence": "invalid"})
    with pytest.raises(VideoEvidenceSkillMappingError):
        _build_payload(session, job)


def test_output_required_fields_match_contract() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {
                    "threshold": 0.6,
                    "worst_frames": [{"frame_num": 4, "timestamp_s": 1.2, "score": 0.3}],
                }
            }
        }
    )

    payload = _build_payload(session, job)
    contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY["coaching_video_evidence_skill.v1"]
    required_inputs = set(contract["required_inputs"])  # type: ignore[arg-type]

    required_top_level = {
        "player_profile_id",
        "coach_user_id",
        "org_id",
        "video_session_id",
        "video_analysis_job_id",
        "analysis_mode",
        "evidence_markers",
    }
    assert required_top_level.issubset(required_inputs)
    assert required_top_level.issubset(set(payload.keys()))

    marker = payload["evidence_markers"][0]  # type: ignore[index]
    for key in ("metric_name", "timestamp_s", "frame_num", "score", "threshold", "finding_label"):
        assert key in marker


def test_mapper_does_not_mutate_job_session_or_truth_fields() -> None:
    session = _session()
    job = _job(
        deep_results={
            "evidence": {
                "head_stability_score": {
                    "threshold": 0.6,
                    "worst_frames": [{"frame_num": 2, "timestamp_s": 0.2, "score": 0.1}],
                }
            }
        },
        quick_results={"evidence": {"balance_drift_score": {"worst_frames": [{"timestamp_s": 9.9}]}}},
    )

    session_before = {
        "id": session.id,
        "status": session.status,
        "title": session.title,
        "player_ids": copy.deepcopy(session.player_ids),
    }
    job_before = {
        "id": job.id,
        "session_id": job.session_id,
        "status": job.status,
        "analysis_mode": job.analysis_mode,
        "deep_results": copy.deepcopy(job.deep_results),
        "quick_results": copy.deepcopy(job.quick_results),
        "results": copy.deepcopy(job.results),
    }

    payload = _build_payload(session, job)
    assert payload["evidence_markers"]

    assert session.id == session_before["id"]
    assert session.status == session_before["status"]
    assert session.title == session_before["title"]
    assert session.player_ids == session_before["player_ids"]

    assert job.id == job_before["id"]
    assert job.session_id == job_before["session_id"]
    assert job.status == job_before["status"]
    assert job.analysis_mode == job_before["analysis_mode"]
    assert job.deep_results == job_before["deep_results"]
    assert job.quick_results == job_before["quick_results"]
    assert job.results == job_before["results"]
