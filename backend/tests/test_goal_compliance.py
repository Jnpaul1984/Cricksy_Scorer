"""Tests for goal compliance service."""

import pytest
from backend.services.goal_compliance import (
    calculate_compliance,
    calculate_metric_compliance,
    calculate_zone_compliance,
    is_point_in_circle,
    is_point_in_rect,
)


class TestPointInShape:
    """Test point-in-shape detection functions."""

    def test_point_in_rect_inside(self):
        """Test point inside rectangle."""
        rect = {"x": 0.2, "y": 0.3, "width": 0.5, "height": 0.4}
        assert is_point_in_rect(0.4, 0.5, rect) is True

    def test_point_in_rect_outside(self):
        """Test point outside rectangle."""
        rect = {"x": 0.2, "y": 0.3, "width": 0.5, "height": 0.4}
        assert is_point_in_rect(0.1, 0.5, rect) is False

    def test_point_in_circle_inside(self):
        """Test point inside circle."""
        circle = {"cx": 0.5, "cy": 0.5, "r": 0.2}
        assert is_point_in_circle(0.6, 0.6, circle) is True

    def test_point_in_circle_outside(self):
        """Test point outside circle."""
        circle = {"cx": 0.5, "cy": 0.5, "r": 0.2}
        assert is_point_in_circle(0.9, 0.9, circle) is False


class TestZoneCompliance:
    """Test zone compliance calculation."""

    def test_calculate_zone_compliance_no_bounces(self):
        """Test zone compliance with no ball bounces detected."""
        deep_results = {"ball_tracking": {"bounces": []}}
        goals = {"zones": [{"zone_id": "zone1", "target_accuracy": 0.8}]}
        zones_lookup = {
            "zone1": {
                "id": "zone1",
                "name": "Test Zone",
                "shape": "rect",
                "definition_json": {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        }

        results = calculate_zone_compliance(deep_results, goals, zones_lookup)

        assert len(results) == 1
        assert results[0]["zone_id"] == "zone1"
        assert results[0]["actual_accuracy"] == 0.0
        assert results[0]["pass"] is False
        assert results[0]["delta"] == -0.8

    def test_calculate_zone_compliance_perfect_accuracy(self):
        """Test zone compliance with 100% accuracy."""
        deep_results = {
            "ball_tracking": {
                "bounces": [
                    {"x_normalized": 0.4, "y_normalized": 0.5},
                    {"x_normalized": 0.45, "y_normalized": 0.55},
                ]
            }
        }
        goals = {"zones": [{"zone_id": "zone1", "target_accuracy": 0.8}]}
        zones_lookup = {
            "zone1": {
                "id": "zone1",
                "name": "Test Zone",
                "shape": "rect",
                "definition_json": {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        }

        results = calculate_zone_compliance(deep_results, goals, zones_lookup)

        assert len(results) == 1
        assert results[0]["actual_accuracy"] == 1.0
        assert results[0]["pass"] is True
        assert results[0]["delta"] == 0.2

    def test_calculate_zone_compliance_partial_accuracy(self):
        """Test zone compliance with partial accuracy."""
        deep_results = {
            "ball_tracking": {
                "bounces": [
                    {"x_normalized": 0.4, "y_normalized": 0.5},  # Inside
                    {"x_normalized": 0.1, "y_normalized": 0.1},  # Outside
                ]
            }
        }
        goals = {"zones": [{"zone_id": "zone1", "target_accuracy": 0.8}]}
        zones_lookup = {
            "zone1": {
                "id": "zone1",
                "name": "Test Zone",
                "shape": "rect",
                "definition_json": {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        }

        results = calculate_zone_compliance(deep_results, goals, zones_lookup)

        assert len(results) == 1
        assert results[0]["actual_accuracy"] == 0.5
        assert results[0]["pass"] is False
        assert results[0]["delta"] == -0.3


class TestMetricCompliance:
    """Test metric compliance calculation."""

    def test_calculate_metric_compliance_pass(self):
        """Test metric compliance when target is met."""
        findings = {
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "title": "Head Stability",
                    "metrics": {"head_stability": {"score": 0.75}},
                }
            ]
        }
        goals = {"metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]}

        results = calculate_metric_compliance(findings, goals)

        assert len(results) == 1
        assert results[0]["code"] == "HEAD_MOVEMENT"
        assert results[0]["actual_score"] == 0.75
        assert results[0]["pass"] is True
        assert results[0]["delta"] == 0.05

    def test_calculate_metric_compliance_fail(self):
        """Test metric compliance when target is not met."""
        findings = {
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "title": "Head Stability",
                    "metrics": {"head_stability": {"score": 0.40}},
                }
            ]
        }
        goals = {"metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]}

        results = calculate_metric_compliance(findings, goals)

        assert len(results) == 1
        assert results[0]["actual_score"] == 0.40
        assert results[0]["pass"] is False
        assert results[0]["delta"] == -0.30

    def test_calculate_metric_compliance_missing_finding(self):
        """Test metric compliance when finding is not present."""
        findings = {"findings": []}
        goals = {"metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]}

        results = calculate_metric_compliance(findings, goals)

        assert len(results) == 1
        assert results[0]["actual_score"] == 0.0
        assert results[0]["pass"] is False


class TestOverallCompliance:
    """Test overall compliance calculation."""

    @pytest.fixture
    def mock_job(self):
        """Mock job with goals and results."""

        class MockJob:
            def __init__(self):
                self.coach_goals = {
                    "zones": [{"zone_id": "zone1", "target_accuracy": 0.8}],
                    "metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}],
                }
                self.deep_results = {
                    "ball_tracking": {
                        "bounces": [
                            {"x_normalized": 0.4, "y_normalized": 0.5},
                            {"x_normalized": 0.45, "y_normalized": 0.55},
                        ]
                    }
                }
                self.deep_findings = {
                    "findings": [
                        {
                            "code": "HEAD_MOVEMENT",
                            "title": "Head Stability",
                            "metrics": {"head_stability": {"score": 0.75}},
                        }
                    ]
                }

        return MockJob()

    def test_calculate_compliance_all_pass(self, mock_job):
        """Test overall compliance when all goals are met."""
        zones_lookup = {
            "zone1": {
                "id": "zone1",
                "name": "Test Zone",
                "shape": "rect",
                "definition_json": {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        }

        outcomes = calculate_compliance(mock_job, zones_lookup)

        assert len(outcomes["zones"]) == 1
        assert len(outcomes["metrics"]) == 1
        assert outcomes["zones"][0]["pass"] is True
        assert outcomes["metrics"][0]["pass"] is True
        assert outcomes["overall_compliance_pct"] == 100.0

    def test_calculate_compliance_partial_pass(self, mock_job):
        """Test overall compliance when some goals are met."""
        # Modify job to have failing metric
        mock_job.deep_findings = {
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "title": "Head Stability",
                    "metrics": {"head_stability": {"score": 0.40}},
                }
            ]
        }

        zones_lookup = {
            "zone1": {
                "id": "zone1",
                "name": "Test Zone",
                "shape": "rect",
                "definition_json": {"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        }

        outcomes = calculate_compliance(mock_job, zones_lookup)

        assert outcomes["zones"][0]["pass"] is True
        assert outcomes["metrics"][0]["pass"] is False
        assert outcomes["overall_compliance_pct"] == 50.0
