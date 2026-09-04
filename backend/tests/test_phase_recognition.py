from __future__ import annotations

from backend.domain.coach_analysis_v2_contract import RepetitionActionRecordV2, ValidityState
from backend.services.phase_recognition import attach_phase_recognition, recognize_repetition_phases


def _repetition(
    *,
    repetition_id: str,
    discipline: str = "batting",
    start_ts: float = 1.0,
    end_ts: float = 2.0,
    start_frame: int = 30,
    end_frame: int = 60,
    confidence: float = 0.84,
    validity_state: ValidityState = ValidityState.VALID,
) -> RepetitionActionRecordV2:
    return RepetitionActionRecordV2(
        repetition_id=repetition_id,
        session_id="session-1",
        job_id="job-1",
        discipline=discipline,
        action_type="batting_shot" if discipline == "batting" else "bowling_delivery",
        start_ts=start_ts,
        end_ts=end_ts,
        start_frame=start_frame,
        end_frame=end_frame,
        segmentation_method="pose_motion_v1",
        segmentation_confidence=confidence,
        manual_override=False,
        validity_state=validity_state,
        insufficient_reason=None,
        evidence_refs=[],
        metric_refs=[],
    )


def test_recognize_repetition_phases_batting_stays_in_bounds_and_uses_proxy_without_ball() -> None:
    repetitions = [_repetition(repetition_id="rep-1")]
    phases, summary = recognize_repetition_phases(
        discipline="batting",
        repetitions=repetitions,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    assert summary["validity_state"] == ValidityState.VALID.value
    assert phases
    contact_phase = next(
        (phase for phase in phases if phase.phase_name == "contact_proxy_window"),
        None,
    )
    assert contact_phase is not None
    assert contact_phase.validity_state == ValidityState.LOW_CONFIDENCE
    assert not any(phase.phase_name == "contact" for phase in phases)
    assert [phase.start_ts for phase in phases if phase.start_ts is not None] == sorted(
        [phase.start_ts for phase in phases if phase.start_ts is not None]
    )
    for phase in phases:
        assert phase.start_ts is not None
        assert phase.end_ts is not None
        assert 1.0 <= phase.start_ts < phase.end_ts <= 2.0
        assert phase.start_frame is not None and phase.end_frame is not None
        assert 30 <= phase.start_frame < phase.end_frame <= 60


def test_recognize_repetition_phases_bowling_uses_ball_release_when_available() -> None:
    repetitions = [_repetition(repetition_id="rep-1", discipline="bowling")]
    phases, summary = recognize_repetition_phases(
        discipline="bowling",
        repetitions=repetitions,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        ball_tracking={"trajectory": {"release_point": {"timestamp": 1.8}}},
    )

    assert summary["validity_state"] == ValidityState.VALID.value
    release_phase = next((phase for phase in phases if phase.phase_name == "release"), None)
    assert release_phase is not None
    assert release_phase.requires_object_evidence is True
    assert release_phase.detection_method == "pose_ball_hybrid_v1"


def test_recognize_repetition_phases_does_not_invent_release_without_ball_evidence() -> None:
    repetitions = [_repetition(repetition_id="rep-1", discipline="bowling")]
    phases, _ = recognize_repetition_phases(
        discipline="bowling",
        repetitions=repetitions,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    assert not any(phase.phase_name == "release" for phase in phases)
    assert any(phase.phase_name == "release_proxy_window" for phase in phases)


def test_recognize_repetition_phases_fails_safely_for_unsupported_camera() -> None:
    repetitions = [_repetition(repetition_id="rep-1")]
    phases, summary = recognize_repetition_phases(
        discipline="batting",
        repetitions=repetitions,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="other",
    )

    assert phases == []
    assert summary["validity_state"] == ValidityState.UNSUPPORTED_CAMERA_VIEW.value


def test_recognize_repetition_phases_supports_spin_wicketkeeping_and_fielding_baselines() -> None:
    for discipline in ("spin_bowling", "wicketkeeping", "fielding"):
        repetitions = [_repetition(repetition_id=f"rep-{discipline}", discipline="bowling")]
        phases, summary = recognize_repetition_phases(
            discipline="bowling" if "bowling" in discipline else discipline,
            session_discipline=discipline if "bowling" in discipline else None,
            repetitions=repetitions,
            sample_fps=10.0,
            source_video_fps=30.0,
            camera_view="side",
        )
        assert phases
        assert summary["recognized_repetitions"] == 1


def test_attach_phase_recognition_serializes_into_payload() -> None:
    payload = {
        "meta": {},
        "v2": {
            "repetitions": [
                _repetition(repetition_id="rep-1").model_dump(mode="json"),
            ]
        },
    }

    updated = attach_phase_recognition(
        results_payload=payload,
        discipline="batting",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    assert isinstance(updated["v2"]["phases"], list)
    assert updated["v2"]["phases"][0]["repetition_id"] == "rep-1"
    assert updated["meta"]["phase_recognition"]["phases_count"] >= 1
