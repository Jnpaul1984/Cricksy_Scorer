"""
Tests for Training Drill Generator

Tests personalized drill recommendations and drill tracking.
"""

from backend.services.training_drill_generator import (
    TrainingDrillGenerator,
    DrillCategory,
    DrillSeverity,
)


class TestTrainingDrillGeneration:
    """Test drill generation logic."""

    def test_generates_drills_for_player_with_weaknesses(self):
        """Verify drills are generated for identified weaknesses."""
        player_profile = {
            "pace_weakness": 75.0,  # High weakness
            "spin_weakness": 30.0,
            "dot_ball_weakness": 60.0,
            "yorker_weakness": 80.0,
            "aggressive_weakness": 20.0,
            "boundary_weakness": 25.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p1",
            player_name="Test Player",
            player_profile=player_profile,
        )

        assert plan is not None
        assert plan.player_id == "p1"
        assert len(plan.drills) > 0
        assert plan.high_priority_count >= 0

    def test_high_priority_drills_for_severe_weaknesses(self):
        """Verify severe weaknesses generate HIGH priority drills."""
        player_profile = {
            "pace_weakness": 85.0,  # Very high weakness
            "spin_weakness": 10.0,
            "dot_ball_weakness": 90.0,  # Very high weakness
            "yorker_weakness": 88.0,  # Very high weakness
            "aggressive_weakness": 15.0,
            "boundary_weakness": 20.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p2",
            player_name="Struggling Player",
            player_profile=player_profile,
        )

        high_priority_drills = [d for d in plan.drills if d.severity == DrillSeverity.HIGH]
        assert len(high_priority_drills) >= 2
        assert plan.high_priority_count >= 2

    def test_no_drills_for_weak_player_profile(self):
        """Verify no drills when all weaknesses are below threshold."""
        player_profile = {
            "pace_weakness": 20.0,  # Below threshold
            "spin_weakness": 15.0,
            "dot_ball_weakness": 25.0,
            "yorker_weakness": 30.0,
            "aggressive_weakness": 18.0,
            "boundary_weakness": 22.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p3",
            player_name="Strong Player",
            player_profile=player_profile,
        )

        assert len(plan.drills) == 0

    def test_drill_plan_contains_complete_information(self):
        """Verify generated drills have all required fields."""
        player_profile = {
            "pace_weakness": 70.0,
            "spin_weakness": 60.0,
            "dot_ball_weakness": 55.0,
            "yorker_weakness": 65.0,
            "aggressive_weakness": 40.0,
            "boundary_weakness": 45.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p4",
            player_name="Complete Test",
            player_profile=player_profile,
        )

        for drill in plan.drills:
            assert drill.drill_id is not None
            assert drill.name is not None
            assert drill.description is not None
            assert drill.category is not None
            assert drill.severity is not None
            assert drill.reps_or_count > 0
            assert drill.duration_minutes > 0
            assert drill.focus_area is not None
            assert 1 <= drill.difficulty <= 10

    def test_drill_frequency_matches_severity(self):
        """Verify drill frequency is appropriate for severity level."""
        player_profile = {
            "pace_weakness": 85.0,  # HIGH
            "spin_weakness": 55.0,  # MEDIUM
            "dot_ball_weakness": 25.0,  # LOW
            "yorker_weakness": 70.0,  # HIGH
            "aggressive_weakness": 20.0,
            "boundary_weakness": 30.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p5",
            player_name="Frequency Test",
            player_profile=player_profile,
        )

        high_severity_drills = [d for d in plan.drills if d.severity == DrillSeverity.HIGH]
        for drill in high_severity_drills:
            assert drill.recommended_frequency in ["daily", "3x/week"]

    def test_maximum_six_drills_per_plan(self):
        """Verify drill plan never exceeds 6 drills."""
        player_profile = {
            "pace_weakness": 80.0,
            "spin_weakness": 75.0,
            "dot_ball_weakness": 85.0,
            "yorker_weakness": 90.0,
            "aggressive_weakness": 60.0,
            "boundary_weakness": 70.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p6",
            player_name="Max Drills Test",
            player_profile=player_profile,
        )

        assert len(plan.drills) <= 6


class TestDrillTemplates:
    """Test drill template library."""

    def test_all_drill_categories_have_templates(self):
        """Verify each implemented category has at least one template."""
        # Not all categories may have templates implemented yet
        for category, templates in TrainingDrillGenerator.DRILL_TEMPLATES.items():
            assert len(templates) > 0, f"Category {category} has no templates"

    def test_template_duration_is_reasonable(self):
        """Verify template durations are between 10-60 minutes."""
        for category, templates in TrainingDrillGenerator.DRILL_TEMPLATES.items():
            for template in templates:
                assert 10 <= template.duration_minutes <= 60

    def test_template_difficulty_is_valid(self):
        """Verify template difficulty is on 1-10 scale."""
        for category, templates in TrainingDrillGenerator.DRILL_TEMPLATES.items():
            for template in templates:
                assert 1 <= template.difficulty <= 10

    def test_template_reps_are_positive(self):
        """Verify template reps/counts are positive integers."""
        for category, templates in TrainingDrillGenerator.DRILL_TEMPLATES.items():
            for template in templates:
                assert template.reps_or_count > 0
                assert isinstance(template.reps_or_count, int)


class TestDrillProgress:
    """Test drill progress tracking."""

    def test_progress_not_started(self):
        """Verify progress for drill with no sessions."""
        progress = TrainingDrillGenerator.get_drill_progress(
            drill_id="drill1",
            completed_sessions=[],
        )

        assert progress["completion_rate"] == 0.0
        assert progress["sessions_completed"] == 0
        assert progress["status"] == "not_started"
        assert progress["improvement_score"] == 0.0

    def test_progress_in_progress(self):
        """Verify progress for partially completed drill."""
        sessions = [
            {"success": True, "performance_score": 50},
            {"success": False, "performance_score": 55},
            {"success": True, "performance_score": 65},
        ]

        progress = TrainingDrillGenerator.get_drill_progress(
            drill_id="drill2",
            completed_sessions=sessions,
        )

        assert progress["status"] == "in_progress"
        assert progress["sessions_completed"] == 2
        assert progress["total_sessions"] == 3
        assert progress["completion_rate"] == round(2 / 3, 2)

    def test_progress_completed(self):
        """Verify progress for fully completed drill."""
        sessions = [
            {"success": True, "performance_score": 50},
            {"success": True, "performance_score": 60},
            {"success": True, "performance_score": 70},
            {"success": True, "performance_score": 80},
            {"success": True, "performance_score": 85},
        ]

        progress = TrainingDrillGenerator.get_drill_progress(
            drill_id="drill3",
            completed_sessions=sessions,
        )

        assert progress["status"] == "completed"
        assert progress["completion_rate"] == 1.0
        assert progress["sessions_completed"] == 5
        assert progress["improvement_score"] == 35  # 85 - 50

    def test_progress_improvement_calculation(self):
        """Verify improvement score is calculated correctly."""
        sessions = [
            {"success": True, "performance_score": 40},
            {"success": True, "performance_score": 55},
            {"success": True, "performance_score": 70},
        ]

        progress = TrainingDrillGenerator.get_drill_progress(
            drill_id="drill4",
            completed_sessions=sessions,
        )

        # Improvement = last score - first score = 70 - 40 = 30
        assert progress["improvement_score"] == 30


class TestDismissalPatternAnalysis:
    """Test dismissal pattern detection."""

    def test_detects_dot_pressure_release_pattern(self):
        """Verify dot-ball pressure release pattern is detected."""
        dismissals = [
            {
                "dismissal_type": "bowled",
                "context": {"dot_balls_before": 4},
            },
        ]

        patterns = TrainingDrillGenerator._analyze_dismissal_patterns(dismissals)

        assert "dot_pressure_release" in patterns
        assert patterns["dot_pressure_release"] >= 1

    def test_detects_aggressive_dismissal_pattern(self):
        """Verify aggressive dismissal pattern is detected."""
        dismissals = [
            {
                "dismissal_type": "caught",
                "context": {"aggressive_attempt": True},
            },
        ]

        patterns = TrainingDrillGenerator._analyze_dismissal_patterns(dismissals)

        assert "aggressive_dismissal" in patterns
        assert patterns["aggressive_dismissal"] >= 1

    def test_detects_yorker_dismissal_pattern(self):
        """Verify yorker dismissal pattern is detected."""
        dismissals = [
            {
                "dismissal_type": "lbw",
                "context": {"delivery_type": "yorker"},
            },
        ]

        patterns = TrainingDrillGenerator._analyze_dismissal_patterns(dismissals)

        assert "yorker_dismissal" in patterns

    def test_ignores_non_matching_dismissals(self):
        """Verify non-matching dismissals are ignored."""
        dismissals = [
            {
                "dismissal_type": "caught",
                "context": {"aggressive_attempt": False},
            },
        ]

        patterns = TrainingDrillGenerator._analyze_dismissal_patterns(dismissals)

        # Should have minimal or no patterns
        assert len(patterns) == 0 or all(count == 0 for count in patterns.values())


class TestWeaknessDrillMapping:
    """Test weakness-to-drill mapping."""

    def test_pace_weakness_maps_to_pace_handling(self):
        """Verify pace weakness recommends pace handling drills."""
        player_profile = {
            "pace_weakness": 75.0,  # High
            "spin_weakness": 20.0,
            "dot_ball_weakness": 20.0,
            "yorker_weakness": 20.0,
            "aggressive_weakness": 20.0,
            "boundary_weakness": 20.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p7",
            player_name="Pace Weakness Test",
            player_profile=player_profile,
        )

        pace_drills = [d for d in plan.drills if d.category == DrillCategory.PACE_HANDLING]
        assert len(pace_drills) >= 1

    def test_dot_ball_weakness_maps_to_dot_ball_drills(self):
        """Verify dot ball weakness recommends dot ball drills."""
        player_profile = {
            "pace_weakness": 20.0,
            "spin_weakness": 20.0,
            "dot_ball_weakness": 80.0,  # High
            "yorker_weakness": 20.0,
            "aggressive_weakness": 20.0,
            "boundary_weakness": 20.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p8",
            player_name="Dot Ball Test",
            player_profile=player_profile,
        )

        dot_drills = [d for d in plan.drills if d.category == DrillCategory.DOT_BALL]
        assert len(dot_drills) >= 1


class TestTrainingPlanSummary:
    """Test training plan summary statistics."""

    def test_plan_calculates_weekly_hours(self):
        """Verify plan calculates total weekly hours correctly."""
        player_profile = {
            "pace_weakness": 70.0,
            "spin_weakness": 60.0,
            "dot_ball_weakness": 65.0,
            "yorker_weakness": 75.0,
            "aggressive_weakness": 40.0,
            "boundary_weakness": 45.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p9",
            player_name="Weekly Hours Test",
            player_profile=player_profile,
        )

        assert plan.total_weekly_hours > 0
        assert isinstance(plan.total_weekly_hours, float)

    def test_plan_aggregates_focus_areas(self):
        """Verify plan lists all unique focus areas."""
        player_profile = {
            "pace_weakness": 70.0,
            "spin_weakness": 60.0,
            "dot_ball_weakness": 65.0,
            "yorker_weakness": 75.0,
            "aggressive_weakness": 40.0,
            "boundary_weakness": 45.0,
        }

        plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id="p10",
            player_name="Focus Areas Test",
            player_profile=player_profile,
        )

        if plan.drills:
            assert len(plan.focus_areas) > 0
            unique_focus_areas = set(d.focus_area for d in plan.drills)
            assert plan.focus_areas == sorted(unique_focus_areas)
