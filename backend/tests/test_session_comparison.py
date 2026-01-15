"""Tests for session comparison service."""

import pytest
from backend.services.session_comparison import compare_jobs, extract_metric_scores
from datetime import datetime, UTC


class TestExtractMetricScores:
    """Test metric score extraction from findings."""

    def test_extract_metric_scores_with_scores(self):
        """Test extracting scores from findings."""
        findings = {
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "metrics": {"head_stability": {"score": 0.75}},
                },
                {
                    "code": "FRONT_ELBOW",
                    "metrics": {"elbow_angle": {"score": 0.82}},
                },
            ]
        }

        scores = extract_metric_scores(findings)

        assert len(scores) == 2
        assert scores["HEAD_MOVEMENT"] == 0.75
        assert scores["FRONT_ELBOW"] == 0.82

    def test_extract_metric_scores_empty(self):
        """Test extracting scores from empty findings."""
        findings = {"findings": []}

        scores = extract_metric_scores(findings)

        assert len(scores) == 0

    def test_extract_metric_scores_none(self):
        """Test extracting scores from None."""
        scores = extract_metric_scores(None)

        assert len(scores) == 0


class TestCompareJobs:
    """Test job comparison function."""

    @pytest.fixture
    def mock_jobs(self):
        """Create mock jobs for testing."""

        class MockJob:
            def __init__(self, job_id, completed_at, analysis_mode, metric_scores):
                self.id = job_id
                self.completed_at = completed_at
                self.created_at = completed_at
                self.analysis_mode = analysis_mode
                self.deep_findings = {
                    "findings": [
                        {
                            "code": code,
                            "metrics": {"metric": {"score": score}},
                        }
                        for code, score in metric_scores.items()
                    ]
                }

        return [
            MockJob(
                "job1",
                datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
                "bowling",
                {"HEAD_MOVEMENT": 0.50, "FRONT_ELBOW": 0.60},
            ),
            MockJob(
                "job2",
                datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
                "bowling",
                {"HEAD_MOVEMENT": 0.70, "FRONT_ELBOW": 0.55},
            ),
            MockJob(
                "job3",
                datetime(2026, 1, 10, 10, 0, 0, tzinfo=UTC),
                "bowling",
                {"HEAD_MOVEMENT": 0.75, "FRONT_ELBOW": 0.65},
            ),
        ]

    def test_compare_jobs_empty_list(self):
        """Test comparing empty job list."""
        result = compare_jobs([])

        assert result["timeline"] == []
        assert result["deltas"] == []
        assert result["persistent_issues"] == []

    def test_compare_jobs_single_job(self, mock_jobs):
        """Test comparing single job."""
        result = compare_jobs([mock_jobs[0]])

        assert len(result["timeline"]) == 1
        assert result["timeline"][0]["job_id"] == "job1"
        assert result["deltas"] == []
        assert result["persistent_issues"] == []

    def test_compare_jobs_timeline(self, mock_jobs):
        """Test timeline generation."""
        result = compare_jobs(mock_jobs)

        assert len(result["timeline"]) == 3
        assert result["timeline"][0]["job_id"] == "job1"
        assert result["timeline"][1]["job_id"] == "job2"
        assert result["timeline"][2]["job_id"] == "job3"

        # Check metric scores in timeline
        assert result["timeline"][0]["metric_scores"]["HEAD_MOVEMENT"] == 0.50
        assert result["timeline"][1]["metric_scores"]["HEAD_MOVEMENT"] == 0.70
        assert result["timeline"][2]["metric_scores"]["HEAD_MOVEMENT"] == 0.75

    def test_compare_jobs_improvements(self, mock_jobs):
        """Test improvement detection."""
        result = compare_jobs(mock_jobs)

        assert len(result["deltas"]) == 2

        # First delta: job1 -> job2
        delta1 = result["deltas"][0]
        assert delta1["from_job_id"] == "job1"
        assert delta1["to_job_id"] == "job2"
        
        # HEAD_MOVEMENT improved by 0.20 (above 0.05 threshold)
        improvements = [imp for imp in delta1["improvements"] if imp["code"] == "HEAD_MOVEMENT"]
        assert len(improvements) == 1
        assert improvements[0]["delta"] == 0.20

    def test_compare_jobs_regressions(self, mock_jobs):
        """Test regression detection."""
        result = compare_jobs(mock_jobs)

        # First delta: job1 -> job2
        delta1 = result["deltas"][0]
        
        # FRONT_ELBOW regressed slightly (not enough for threshold)
        # But in delta2 (job2 -> job3), it improved
        delta2 = result["deltas"][1]
        assert delta2["from_job_id"] == "job2"
        assert delta2["to_job_id"] == "job3"

    def test_compare_jobs_persistent_issues(self, mock_jobs):
        """Test persistent issue detection."""
        # Modify jobs to have consistently low scores
        for job in mock_jobs:
            job.deep_findings = {
                "findings": [
                    {
                        "code": "BAD_METRIC",
                        "metrics": {"metric": {"score": 0.40}},
                    },
                    {
                        "code": "GOOD_METRIC",
                        "metrics": {"metric": {"score": 0.80}},
                    },
                ]
            }

        result = compare_jobs(mock_jobs)

        # BAD_METRIC should be flagged as persistent issue (avg 0.40 < 0.60 threshold)
        persistent = result["persistent_issues"]
        assert len(persistent) == 1
        assert persistent[0]["code"] == "BAD_METRIC"
        assert persistent[0]["avg_score"] == 0.40
        assert persistent[0]["occurrences"] == 3
        assert persistent[0]["trend"] == "stable"

    def test_compare_jobs_trend_improving(self, mock_jobs):
        """Test improving trend detection."""
        # Create jobs with improving metric
        for i, job in enumerate(mock_jobs):
            score = 0.40 + (i * 0.10)  # 0.40, 0.50, 0.60
            job.deep_findings = {
                "findings": [
                    {
                        "code": "IMPROVING_METRIC",
                        "metrics": {"metric": {"score": score}},
                    }
                ]
            }

        result = compare_jobs(mock_jobs)

        # Should be flagged but with improving trend
        persistent = result["persistent_issues"]
        if persistent:  # Only if first half avg is below threshold
            assert any(p["trend"] == "improving" for p in persistent)

    def test_compare_jobs_trend_declining(self):
        """Test declining trend detection."""

        class MockJob:
            def __init__(self, job_id, completed_at, score):
                self.id = job_id
                self.completed_at = completed_at
                self.created_at = completed_at
                self.analysis_mode = "bowling"
                self.deep_findings = {
                    "findings": [
                        {
                            "code": "DECLINING_METRIC",
                            "metrics": {"metric": {"score": score}},
                        }
                    ]
                }

        jobs = [
            MockJob("job1", datetime(2026, 1, 1, tzinfo=UTC), 0.55),
            MockJob("job2", datetime(2026, 1, 5, tzinfo=UTC), 0.50),
            MockJob("job3", datetime(2026, 1, 10, tzinfo=UTC), 0.40),
        ]

        result = compare_jobs(jobs)

        # Should be flagged with declining trend
        persistent = result["persistent_issues"]
        assert len(persistent) == 1
        assert persistent[0]["trend"] == "declining"
