from __future__ import annotations

from backend.domain.coach_analysis_v2_contract import ValidityState
from backend.services.repetition_segmentation import (
    attach_repetition_segmentation,
    refine_bowling_repetitions_with_ball_tracking,
    segment_repetitions,
)


def _frame(
    frame_num: int,
    timestamp: float,
    left_wrist: tuple[float, float],
    right_wrist: tuple[float, float],
    *,
    detected: bool = True,
    shoulder_y: float = 0.42,
) -> dict[str, object]:
    return {
        "frame_num": frame_num,
        "timestamp": timestamp,
        "detected": detected,
        "keypoints": {
            "nose": {"x": 0.5, "y": 0.18},
            "left_shoulder": {"x": 0.42, "y": shoulder_y},
            "right_shoulder": {"x": 0.58, "y": shoulder_y},
            "left_elbow": {"x": 0.40, "y": 0.52},
            "right_elbow": {"x": 0.60, "y": 0.52},
            "left_wrist": {"x": left_wrist[0], "y": left_wrist[1]},
            "right_wrist": {"x": right_wrist[0], "y": right_wrist[1]},
            "left_hip": {"x": 0.45, "y": 0.70},
            "right_hip": {"x": 0.55, "y": 0.70},
            "left_knee": {"x": 0.45, "y": 0.88},
            "right_knee": {"x": 0.55, "y": 0.88},
            "left_ankle": {"x": 0.45, "y": 0.98},
            "right_ankle": {"x": 0.55, "y": 0.98},
        },
    }


def test_segment_repetitions_detects_stable_batting_windows() -> None:
    frames = [
        _frame(0, 0.0, (0.42, 0.60), (0.58, 0.60)),
        _frame(1, 0.1, (0.43, 0.60), (0.57, 0.60)),
        _frame(2, 0.2, (0.44, 0.59), (0.56, 0.59)),
        _frame(3, 0.3, (0.50, 0.54), (0.62, 0.55)),
        _frame(4, 0.4, (0.58, 0.48), (0.71, 0.50)),
        _frame(5, 0.5, (0.64, 0.46), (0.76, 0.48)),
        _frame(6, 0.6, (0.66, 0.47), (0.78, 0.49)),
        _frame(7, 0.7, (0.67, 0.48), (0.79, 0.50)),
        _frame(8, 0.8, (0.44, 0.60), (0.56, 0.60)),
        _frame(9, 0.9, (0.43, 0.60), (0.57, 0.60)),
        _frame(10, 1.0, (0.42, 0.60), (0.58, 0.60)),
        _frame(11, 1.1, (0.42, 0.60), (0.58, 0.60)),
        _frame(12, 1.2, (0.42, 0.60), (0.58, 0.60)),
        _frame(13, 1.3, (0.42, 0.60), (0.58, 0.60)),
        _frame(14, 1.4, (0.42, 0.60), (0.58, 0.60)),
        _frame(15, 1.5, (0.42, 0.60), (0.58, 0.60)),
        _frame(16, 1.6, (0.50, 0.54), (0.62, 0.54)),
        _frame(17, 1.7, (0.59, 0.47), (0.72, 0.48)),
        _frame(18, 1.8, (0.66, 0.44), (0.80, 0.45)),
        _frame(19, 1.9, (0.68, 0.45), (0.82, 0.46)),
        _frame(20, 2.0, (0.69, 0.46), (0.83, 0.47)),
    ]

    repetitions, summary = segment_repetitions(
        discipline="batting",
        frames=frames,
        session_id="session-1",
        job_id="job-1",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        metric_refs=["head_stability_score"],
    )

    assert summary["repetitions_count"] == 2
    assert [rep.action_type for rep in repetitions] == ["batting_shot", "batting_shot"]
    assert repetitions[0].start_frame < repetitions[0].end_frame < repetitions[1].start_frame
    assert repetitions[0].start_ts < repetitions[0].end_ts < repetitions[1].start_ts
    assert all(rep.validity_state == ValidityState.VALID for rep in repetitions)


def test_segment_repetitions_returns_insufficient_result_for_low_motion_input() -> None:
    frames = [
        _frame(index, index * 0.1, (0.45 + (index * 0.002), 0.60), (0.55 + (index * 0.002), 0.60))
        for index in range(12)
    ]

    repetitions, summary = segment_repetitions(
        discipline="batting",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    assert repetitions == []
    assert summary["validity_state"] == ValidityState.NOT_MEASURABLE.value
    assert "Insufficient motion/action evidence" in str(summary["insufficient_reason"])


def test_segment_repetitions_falls_back_to_generic_fielding_type_when_subtype_is_uncertain() -> None:
    frames = [
        _frame(0, 0.0, (0.40, 0.62), (0.60, 0.60)),
        _frame(1, 0.1, (0.42, 0.61), (0.64, 0.56)),
        _frame(2, 0.2, (0.44, 0.60), (0.71, 0.46)),
        _frame(3, 0.3, (0.46, 0.59), (0.77, 0.34)),
        _frame(4, 0.4, (0.47, 0.58), (0.81, 0.27)),
        _frame(5, 0.5, (0.48, 0.58), (0.83, 0.24)),
    ]

    repetitions, _ = segment_repetitions(
        discipline="fielding",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    assert len(repetitions) == 1
    assert repetitions[0].action_type == "fielding_action"
    assert repetitions[0].segmentation_confidence is not None
    assert repetitions[0].validity_state in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}


def test_segment_repetitions_fails_safely_on_unsupported_capture_metadata() -> None:
    repetitions, summary = segment_repetitions(
        discipline="wicketkeeping",
        frames=[_frame(0, 0.0, (0.45, 0.6), (0.55, 0.6))],
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="other",
    )

    assert repetitions == []
    assert summary["validity_state"] == ValidityState.UNSUPPORTED_CAMERA_VIEW.value


def test_attach_repetition_segmentation_serializes_summary_and_records() -> None:
    payload = {
        "metrics": {"metrics": {"head_stability_score": {"score": 0.8}}},
        "meta": {},
        "v2": {"repetitions": []},
    }
    updated = attach_repetition_segmentation(
        results_payload=payload,
        discipline="bowling",
        frames=[
            _frame(0, 0.0, (0.40, 0.62), (0.60, 0.60)),
            _frame(1, 0.1, (0.43, 0.59), (0.62, 0.56)),
            _frame(2, 0.2, (0.47, 0.55), (0.66, 0.50)),
            _frame(3, 0.3, (0.51, 0.51), (0.70, 0.44)),
            _frame(4, 0.4, (0.54, 0.49), (0.72, 0.41)),
            _frame(5, 0.5, (0.55, 0.48), (0.73, 0.40)),
        ],
        session_id="session-1",
        job_id="job-2",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        metric_refs=["head_stability_score"],
    )

    assert updated["meta"]["repetition_segmentation"]["repetitions_count"] == 1
    repetition = updated["v2"]["repetitions"][0]
    assert repetition["job_id"] == "job-2"
    assert repetition["session_id"] == "session-1"
    assert repetition["metric_refs"] == ["head_stability_score"]


def test_refine_bowling_repetitions_with_ball_tracking_handles_missing_tracking_gracefully() -> None:
    repetitions, _ = segment_repetitions(
        discipline="bowling",
        frames=[
            _frame(0, 0.0, (0.40, 0.62), (0.60, 0.60)),
            _frame(1, 0.1, (0.43, 0.59), (0.62, 0.56)),
            _frame(2, 0.2, (0.47, 0.55), (0.66, 0.50)),
            _frame(3, 0.3, (0.51, 0.51), (0.70, 0.44)),
            _frame(4, 0.4, (0.54, 0.49), (0.72, 0.41)),
            _frame(5, 0.5, (0.55, 0.48), (0.73, 0.40)),
        ],
        session_id="session-1",
        job_id="job-3",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
    )

    refined, used_tracking = refine_bowling_repetitions_with_ball_tracking(
        repetitions=repetitions,
        ball_tracking={},
        job_id="job-3",
        session_id="session-1",
    )

    assert used_tracking is False
    assert refined == repetitions
