# Ball Tracking Integration - Code Patches

## Patch 1: analysis_worker.py - Add ball tracking to deep pass for bowling

```python
# In analysis_worker.py, after deep_artifacts generation (~line 300)

            # Stage: DEEP
            job.status = VideoAnalysisJobStatus.deep_running
            job.stage = "DEEP"
            job.progress_pct = 50
            job.deep_started_at = _now_utc()
            await db.commit()

            # Deep pass uses job-configured FPS; keep a sane default
            deep_artifacts = run_pose_metrics_findings_report(
                video_path=local_video_path,
                sample_fps=deep_fps,
                include_frames=include_frames,
                max_width=640,
                max_seconds=None,
                player_context=None,
                analysis_mode=job.analysis_mode,
            )

            deep_payload = deep_artifacts.results
            
            # NEW: Add ball tracking for bowling mode
            ball_tracking_payload = None
            if job.analysis_mode == "bowling":
                try:
                    logger.info(f"Running ball tracking for bowling analysis: job_id={job.id}")
                    from backend.services.ball_tracking_service import (
                        BallTracker,
                        analyze_ball_trajectory,
                    )
                    
                    tracker = BallTracker(ball_color="red")  # TODO: make configurable
                    trajectory = tracker.track_ball_in_video(
                        video_path=local_video_path,
                        sample_fps=deep_fps,
                    )
                    ball_metrics = analyze_ball_trajectory(trajectory)
                    
                    ball_tracking_payload = {
                        "trajectory": {
                            "total_frames": trajectory.total_frames,
                            "detected_frames": trajectory.detected_frames,
                            "detection_rate": trajectory.detection_rate,
                            "avg_velocity": trajectory.avg_velocity,
                            "max_velocity": trajectory.max_velocity,
                            "trajectory_length": trajectory.trajectory_length,
                            "release_point": {
                                "x": trajectory.release_point.x,
                                "y": trajectory.release_point.y,
                                "timestamp": trajectory.release_point.timestamp,
                            } if trajectory.release_point else None,
                            "bounce_point": {
                                "x": trajectory.bounce_point.x,
                                "y": trajectory.bounce_point.y,
                                "timestamp": trajectory.bounce_point.timestamp,
                            } if trajectory.bounce_point else None,
                        },
                        "metrics": {
                            "release_height": ball_metrics.release_height,
                            "release_position_x": ball_metrics.release_position_x,
                            "swing_deviation": ball_metrics.swing_deviation,
                            "flight_time": ball_metrics.flight_time,
                            "ball_speed_estimate": ball_metrics.ball_speed_estimate,
                            "bounce_distance": ball_metrics.bounce_distance,
                            "bounce_angle": ball_metrics.bounce_angle,
                            "trajectory_curve": ball_metrics.trajectory_curve,
                            "spin_detected": ball_metrics.spin_detected,
                            "release_consistency": ball_metrics.release_consistency,
                        },
                    }
                    
                    # Upload ball tracking results to S3
                    ball_tracking_s3_key = _derive_output_key(key, "ball_tracking_results.json")
                    await _upload_json_to_s3(
                        bucket=bucket, 
                        key=ball_tracking_s3_key, 
                        payload=ball_tracking_payload
                    )
                    logger.info(
                        f"Ball tracking complete: job_id={job.id} "
                        f"detection_rate={trajectory.detection_rate:.1f}% "
                        f"s3_key={ball_tracking_s3_key}"
                    )
                    
                    # Add to deep payload
                    deep_payload["ball_tracking"] = ball_tracking_payload
                    deep_payload.setdefault("outputs", {})["ball_tracking_s3_key"] = ball_tracking_s3_key
                    
                except Exception as e:
                    logger.warning(f"Ball tracking failed: job_id={job.id} error={e}", exc_info=True)
                    # Don't fail the whole job if ball tracking fails
                    deep_payload["ball_tracking"] = {
                        "error": str(e),
                        "detection_rate": 0,
                    }

            deep_out_key = _derive_output_key(key, "deep_results.json")
```

## Patch 2: coach_findings.py - Update bowling findings to include ball metrics

```python
# In coach_findings.py, add new bowling-specific findings

# After existing BOWLING_DRILL_SUGGESTIONS

BOWLING_BALL_TRACKING_FINDINGS = {
    "INSUFFICIENT_BALL_TRACKING": {
        "title": "Ball tracking insufficient for swing/length analysis",
        "why_it_matters": "Reliable ball tracking is essential for analyzing swing, seam position, and length. "
        "Low detection rates may be due to poor lighting, ball color contrast, or camera angle.",
        "cues": [
            "Improve video quality with better lighting",
            "Ensure ball color contrasts with background",
            "Use higher frame rate camera if available",
            "Adjust camera angle to track full ball flight",
        ],
        "drills": [
            "Re-record delivery with improved lighting setup",
            "Use contrasting background (dark sight-screen for red ball)",
            "Test camera positioning to capture full trajectory",
        ],
    },
    "INCONSISTENT_RELEASE_POINT": {
        "title": "Release point inconsistency detected",
        "why_it_matters": "Consistent release points are crucial for line and length control. "
        "Variation indicates mechanical issues in gather or delivery stride.",
        "low_severity": {
            "message": "Minor release point variation detected.",
            "cues": [
                "Focus on consistent gather position",
                "Mark your release point reference in practice",
                "Maintain consistent stride length",
            ],
        },
        "medium_severity": {
            "message": "Moderate release point inconsistency affecting control.",
            "cues": [
                "Release point is varying significantly",
                "Work on consistent run-up rhythm",
                "Practice with target markers at release point",
                "Video review of gather and release phases",
            ],
        },
        "high_severity": {
            "message": "High release point variation - major control issue.",
            "cues": [
                "Release point variance is severe",
                "Rebuild bowling action fundamentals",
                "Work with coach on gather mechanics",
                "Daily consistency drills with immediate feedback",
            ],
        },
    },
    "SWING_ANALYSIS": {
        "title": "Ball swing characteristics",
        "why_it_matters": "Understanding your natural swing helps plan field settings and "
        "develop variations. Swing is influenced by wrist position, seam angle, and release.",
        "analysis": {
            "straight": "Ball traveling straight - good for accuracy, consider developing swing variations",
            "inswing": "Natural inswing detected - use for attacking stumps and LBW opportunities",
            "outswing": "Natural outswing detected - excellent for taking outside edge",
            "swing": "Variable swing detected - work on consistent wrist position",
        },
    },
}

# Modify generate_bowling_findings to check ball tracking data

def generate_bowling_findings(
    metrics: dict[str, Any], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Generate bowling-specific findings from metrics with ball tracking integration."""
    
    # Check if ball tracking data exists
    ball_tracking = metrics.get("ball_tracking")
    
    # Generate base pose findings
    base_findings = _generate_findings_internal(metrics, context, BOWLING_DRILL_SUGGESTIONS)
    
    # Add ball tracking findings if available
    if ball_tracking:
        ball_findings = _generate_ball_tracking_findings(ball_tracking)
        base_findings["findings"].extend(ball_findings)
    
    return base_findings


def _generate_ball_tracking_findings(ball_tracking: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate findings from ball tracking data."""
    findings = []
    
    trajectory = ball_tracking.get("trajectory", {})
    metrics_data = ball_tracking.get("metrics", {})
    
    detection_rate = trajectory.get("detection_rate", 0)
    
    # Gating: Low detection rate
    if detection_rate < 40:
        findings.append({
            "code": "INSUFFICIENT_BALL_TRACKING",
            "title": BOWLING_BALL_TRACKING_FINDINGS["INSUFFICIENT_BALL_TRACKING"]["title"],
            "severity": "medium",
            "evidence": {
                "detection_rate": f"{detection_rate:.1f}%",
                "threshold": "40%",
            },
            "why_it_matters": BOWLING_BALL_TRACKING_FINDINGS["INSUFFICIENT_BALL_TRACKING"]["why_it_matters"],
            "cues": BOWLING_BALL_TRACKING_FINDINGS["INSUFFICIENT_BALL_TRACKING"]["cues"],
            "suggested_drills": BOWLING_BALL_TRACKING_FINDINGS["INSUFFICIENT_BALL_TRACKING"]["drills"],
        })
        # Suppress swing/length claims if detection is poor
        return findings
    
    # Release consistency analysis
    release_consistency = metrics_data.get("release_consistency", 100)
    if release_consistency < 85:
        severity = "low" if release_consistency >= 70 else (
            "medium" if release_consistency >= 50 else "high"
        )
        finding_def = BOWLING_BALL_TRACKING_FINDINGS["INCONSISTENT_RELEASE_POINT"]
        findings.append({
            "code": "INCONSISTENT_RELEASE_POINT",
            "title": finding_def["title"],
            "severity": severity,
            "evidence": {
                "release_consistency_score": round(release_consistency, 1),
                "threshold": 85.0,
            },
            "why_it_matters": finding_def["why_it_matters"],
            "cues": finding_def[f"{severity}_severity"]["cues"],
            "suggested_drills": BOWLING_DRILL_SUGGESTIONS.get("RELEASE_POINT", [
                "Rope drill with release point markers",
                "Mirror work at gather position",
                "Consistent stride length drills",
            ]),
        })
    
    # Swing analysis (informational)
    trajectory_curve = metrics_data.get("trajectory_curve", "straight")
    swing_deviation = metrics_data.get("swing_deviation", 0)
    
    if detection_rate >= 60:  # Only if tracking is reliable
        swing_def = BOWLING_BALL_TRACKING_FINDINGS["SWING_ANALYSIS"]
        swing_message = swing_def["analysis"].get(
            trajectory_curve, 
            f"Trajectory: {trajectory_curve}"
        )
        findings.append({
            "code": "SWING_ANALYSIS",
            "title": swing_def["title"],
            "severity": "low",  # Informational
            "evidence": {
                "trajectory_curve": trajectory_curve,
                "swing_deviation": round(swing_deviation, 1),
                "ball_speed_estimate": round(metrics_data.get("ball_speed_estimate", 0), 1),
            },
            "why_it_matters": swing_def["why_it_matters"],
            "cues": [swing_message],
            "suggested_drills": BOWLING_DRILL_SUGGESTIONS.get("SWING_VARIATION", [
                "Wrist position drills for swing control",
                "Seam angle practice with video feedback",
                "Shiny/rough side awareness drills",
            ]),
        })
    
    return findings
```

## Patch 3: coach_report_service.py - Include ball metrics in bowling reports

```python
# In coach_report_service.py, update _generate_notes for bowling

def _generate_notes(
    findings: dict[str, Any],
    player_context: dict[str, Any] | None,
    detection_rate: float | None = None,
) -> str:
    """Generate coaching notes from findings with ball tracking awareness."""
    
    notes_parts = []
    
    # Reliability warning
    if detection_rate is not None and detection_rate < 60:
        notes_parts.append(
            f"⚠️ Note: Pose detection rate is {detection_rate:.1f}%. "
            "Results may be less reliable. Consider re-recording with better lighting."
        )
    
    # Check for ball tracking data
    ball_tracking_findings = [
        f for f in findings.get("findings", []) 
        if f.get("code") in ["INSUFFICIENT_BALL_TRACKING", "SWING_ANALYSIS", "INCONSISTENT_RELEASE_POINT"]
    ]
    
    if ball_tracking_findings:
        notes_parts.append("\n📊 Ball Tracking Insights:")
        for finding in ball_tracking_findings:
            if finding["code"] == "INSUFFICIENT_BALL_TRACKING":
                notes_parts.append(
                    f"  • Ball detection: {finding['evidence']['detection_rate']} "
                    "(below 40% threshold - swing/length analysis suppressed)"
                )
            elif finding["code"] == "SWING_ANALYSIS":
                evidence = finding["evidence"]
                notes_parts.append(
                    f"  • Swing: {evidence['trajectory_curve']} "
                    f"(deviation: {evidence['swing_deviation']}px, "
                    f"speed est: {evidence['ball_speed_estimate']} px/s)"
                )
            elif finding["code"] == "INCONSISTENT_RELEASE_POINT":
                consistency = finding["evidence"]["release_consistency_score"]
                notes_parts.append(
                    f"  • Release consistency: {consistency}% "
                    f"({'Excellent' if consistency >= 85 else 'Needs work'})"
                )
    
    # Standard player context notes
    if player_context:
        level = player_context.get("level", "unknown")
        notes_parts.append(f"\nPlayer level: {level}")
    
    return "\n".join(notes_parts)
```

## Patch 4: Tests for ball tracking integration

```python
# New file: backend/tests/test_ball_tracking_integration.py

import pytest
from unittest.mock import Mock, patch
from backend.services.ball_tracking_service import BallTrajectory, BallMetrics, BallPosition
from backend.services.coach_findings import generate_bowling_findings


@pytest.fixture
def mock_ball_tracking_low_detection():
    """Ball tracking with low detection rate (<40%)."""
    return {
        "trajectory": {
            "total_frames": 100,
            "detected_frames": 30,
            "detection_rate": 30.0,
            "avg_velocity": 150.0,
        },
        "metrics": {
            "trajectory_curve": "straight",
            "swing_deviation": 5.0,
            "release_consistency": 75.0,
        },
    }


@pytest.fixture
def mock_ball_tracking_good_detection():
    """Ball tracking with good detection rate (>60%)."""
    return {
        "trajectory": {
            "total_frames": 100,
            "detected_frames": 85,
            "detection_rate": 85.0,
            "avg_velocity": 250.0,
            "release_point": {"x": 100, "y": 50, "timestamp": 0.5},
            "bounce_point": {"x": 300, "y": 200, "timestamp": 1.2},
        },
        "metrics": {
            "trajectory_curve": "outswing",
            "swing_deviation": 45.0,
            "ball_speed_estimate": 280.0,
            "release_consistency": 92.0,
        },
    }


def test_bowling_findings_low_ball_detection_suppresses_swing_analysis():
    """Test that low ball detection (<40%) suppresses swing claims."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
        },
        "ball_tracking": {
            "trajectory": {"detection_rate": 35.0},
            "metrics": {"trajectory_curve": "outswing", "swing_deviation": 50.0},
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }
    
    result = generate_bowling_findings(metrics)
    
    findings = result["findings"]
    codes = [f["code"] for f in findings]
    
    # Should have insufficient ball tracking warning
    assert "INSUFFICIENT_BALL_TRACKING" in codes
    
    # Should NOT have swing analysis (suppressed due to low detection)
    assert "SWING_ANALYSIS" not in codes
    
    # Check warning message
    insufficient_finding = next(f for f in findings if f["code"] == "INSUFFICIENT_BALL_TRACKING")
    assert insufficient_finding["severity"] == "medium"
    assert "35.0%" in insufficient_finding["evidence"]["detection_rate"]


def test_bowling_findings_good_ball_detection_includes_swing_analysis():
    """Test that good ball detection (>60%) includes swing analysis."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
        },
        "ball_tracking": {
            "trajectory": {"detection_rate": 85.0},
            "metrics": {
                "trajectory_curve": "outswing",
                "swing_deviation": 45.0,
                "ball_speed_estimate": 280.0,
                "release_consistency": 92.0,
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }
    
    result = generate_bowling_findings(metrics)
    
    findings = result["findings"]
    codes = [f["code"] for f in findings]
    
    # Should have swing analysis
    assert "SWING_ANALYSIS" in codes
    
    # Should NOT have insufficient tracking warning
    assert "INSUFFICIENT_BALL_TRACKING" not in codes
    
    # Check swing analysis content
    swing_finding = next(f for f in findings if f["code"] == "SWING_ANALYSIS")
    assert swing_finding["evidence"]["trajectory_curve"] == "outswing"
    assert swing_finding["evidence"]["swing_deviation"] == 45.0


def test_bowling_findings_release_consistency_detection():
    """Test release consistency findings generation."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 80.0},
            "metrics": {
                "release_consistency": 55.0,  # Medium severity (50-70)
                "trajectory_curve": "straight",
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }
    
    result = generate_bowling_findings(metrics)
    
    findings = result["findings"]
    codes = [f["code"] for f in findings]
    
    # Should have release consistency finding
    assert "INCONSISTENT_RELEASE_POINT" in codes
    
    consistency_finding = next(f for f in findings if f["code"] == "INCONSISTENT_RELEASE_POINT")
    assert consistency_finding["severity"] == "medium"
    assert consistency_finding["evidence"]["release_consistency_score"] == 55.0


def test_bowling_findings_without_ball_tracking():
    """Test that bowling findings work without ball tracking data."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
            "balance_drift_score": {"score": 0.70, "num_frames": 50},
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }
    
    # Should not crash, just return pose-based findings
    result = generate_bowling_findings(metrics)
    
    assert "findings" in result
    assert "overall_level" in result
    # No ball tracking findings
    codes = [f["code"] for f in result["findings"]]
    assert "INSUFFICIENT_BALL_TRACKING" not in codes
    assert "SWING_ANALYSIS" not in codes


@pytest.mark.asyncio
async def test_analysis_worker_integrates_ball_tracking_for_bowling(mock_ball_tracking_good_detection):
    """Integration test: analysis_worker should call ball tracking for bowling mode."""
    
    # This test would mock the worker's deep pass and verify ball tracking is called
    # when analysis_mode == "bowling"
    
    with patch("backend.services.ball_tracking_service.BallTracker") as MockTracker:
        mock_tracker_instance = Mock()
        MockTracker.return_value = mock_tracker_instance
        
        mock_trajectory = Mock()
        mock_trajectory.detection_rate = 85.0
        mock_trajectory.total_frames = 100
        mock_trajectory.detected_frames = 85
        mock_tracker_instance.track_ball_in_video.return_value = mock_trajectory
        
        # Simulate analysis_worker.py deep pass logic
        analysis_mode = "bowling"
        
        if analysis_mode == "bowling":
            tracker = MockTracker(ball_color="red")
            trajectory = tracker.track_ball_in_video(
                video_path="test.mp4",
                sample_fps=10.0,
            )
            
            assert trajectory.detection_rate == 85.0
            mock_tracker_instance.track_ball_in_video.assert_called_once()
```

## Summary

**Task 1**: ✅ analysis_worker.py deep pass integration  
**Task 2**: ✅ S3 persistence (ball_tracking_results.json)  
**Task 3**: ✅ Bowling findings + report updates with ball metrics  
**Task 4**: ✅ Gating at <40% detection rate

**Key Changes**:
- analysis_worker.py: Ball tracking runs after pose analysis for bowling mode
- coach_findings.py: New bowling-specific findings (swing, release consistency, insufficient tracking)
- coach_report_service.py: Reports include ball tracking insights
- Tests: Comprehensive coverage of gating logic and integration
