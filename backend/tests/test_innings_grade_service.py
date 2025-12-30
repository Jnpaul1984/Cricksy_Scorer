"""
Unit tests for the innings grade calculation service.
"""

from backend.services.innings_grade_service import InningsGradeCalculator, get_innings_grade


class TestInningsGradeCalculator:
    """Tests for InningsGradeCalculator class"""

    def test_a_plus_grade_exceptional_innings(self):
        """Test A+ grade for exceptional innings (>150% of par)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=250,  # Much higher than par to compensate for adjustments
            total_wickets=2,  # Very few wickets lost
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        assert result["grade"] == "A+"
        assert result["total_runs"] == 250
        assert result["par_score"] == 160  # T20 par
        assert result["score_percentage"] > 150  # 250/160 = 156.25%
        assert result["wicket_efficiency"] > 0.8  # Lost only 2 wickets

    def test_a_grade_very_good_innings(self):
        """Test A grade for very good innings (130-150% of par)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=220,
            total_wickets=5,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # 220/160 = 137.5%
        assert result["grade"] in ["A", "A+"]
        assert result["total_runs"] == 220
        assert 130 <= result["score_percentage"] <= 150

    def test_b_grade_good_innings(self):
        """Test B grade for good innings (100-130% of par)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=165,
            total_wickets=6,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # 165/160 = 103%
        assert result["grade"] == "B"
        assert 100 <= result["score_percentage"] <= 130

    def test_c_grade_average_innings(self):
        """Test C grade for average innings (70-100% of par)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=130,
            total_wickets=7,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # 130/160 = 81.25%
        assert result["grade"] == "C"
        assert 70 <= result["score_percentage"] <= 100

    def test_d_grade_below_average_innings(self):
        """Test D grade for below average innings (<70% of par)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=95,
            total_wickets=8,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # 95/160 = 59.4%
        assert result["grade"] == "D"
        assert result["score_percentage"] < 70

    def test_partial_innings_grade(self):
        """Test grade calculation for partial innings"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=75,
            total_wickets=2,
            overs_completed=10,
            balls_this_over=3,
            overs_limit=20,
            batting_team_size=11,
            is_completed=False,
        )

        assert "grade" in result
        assert result["total_runs"] == 75
        assert result["wickets_lost"] == 2
        assert result["overs_played"] > 10  # 10.5 overs

    def test_wicket_efficiency_calculation(self):
        """Test wicket efficiency metric"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=160,
            total_wickets=2,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # Lost 2 wickets, preserved 9
        expected_efficiency = 9 / 11  # ~0.82
        assert abs(result["wicket_efficiency"] - expected_efficiency) < 0.01

    def test_run_rate_calculation(self):
        """Test run rate calculation"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=180,
            total_wickets=5,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # 180 runs in 20 overs = 9.0 run rate
        assert result["run_rate"] == 9.0

    def test_deliveries_analysis_boundaries(self):
        """Test boundary counting from deliveries"""
        deliveries = [
            {"runs_scored": 4, "is_extra": False},
            {"runs_scored": 6, "is_extra": False},
            {"runs_scored": 1, "is_extra": False},
            {"runs_scored": 4, "is_extra": False},
            {"runs_scored": 2, "is_extra": False},
        ]

        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=17,
            total_wickets=0,
            overs_completed=0,
            balls_this_over=5,
            overs_limit=20,
            deliveries=deliveries,
            is_completed=False,
        )

        # 3 boundaries (4+6+4 = 14 runs from boundaries)
        assert result["boundary_count"] == 3
        assert abs(result["boundary_percentage"] - (14 / 17 * 100)) < 0.1

    def test_deliveries_analysis_dot_balls(self):
        """Test dot ball ratio from deliveries"""
        deliveries = [
            {"runs_scored": 0, "is_extra": False},
            {"runs_scored": 0, "is_extra": False},
            {"runs_scored": 1, "is_extra": False},
            {"runs_scored": 0, "is_extra": False},
            {"runs_scored": 2, "is_extra": False},
            {"runs_scored": 0, "is_extra": False},
        ]

        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=3,
            total_wickets=0,
            overs_completed=1,
            balls_this_over=0,
            overs_limit=20,
            deliveries=deliveries,
            is_completed=False,
        )

        # 4 dot balls out of 6 legal deliveries = 0.67
        assert abs(result["dot_ball_ratio"] - 0.67) < 0.01

    def test_grade_factors_breakdown(self):
        """Test grade factors breakdown is present"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=160,
            total_wickets=5,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        assert "grade_factors" in result
        assert "score_percentage_contribution" in result["grade_factors"]
        assert "wicket_efficiency_contribution" in result["grade_factors"]
        assert "strike_rotation_contribution" in result["grade_factors"]
        assert "boundary_efficiency_contribution" in result["grade_factors"]

    def test_par_score_t20(self):
        """Test par score for T20 format"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=160,
            total_wickets=5,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        assert result["par_score"] == 160

    def test_par_score_odi(self):
        """Test par score for ODI format"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=280,
            total_wickets=6,
            overs_completed=50,
            balls_this_over=0,
            overs_limit=50,
            batting_team_size=11,
            is_completed=True,
        )

        assert result["par_score"] == 270

    def test_par_score_custom_overs(self):
        """Test par score for custom overs (e.g., 15 overs)"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=120,
            total_wickets=4,
            overs_completed=15,
            balls_this_over=0,
            overs_limit=15,
            batting_team_size=11,
            is_completed=True,
        )

        # Custom format: 15 * 7.5 = 112.5 = 112 (int)
        assert result["par_score"] == 112

    def test_convenience_function(self):
        """Test get_innings_grade convenience function"""
        game_state = {
            "total_runs": 160,
            "total_wickets": 5,
            "overs_completed": 20,
            "balls_this_over": 0,
            "overs_limit": 20,
            "is_completed": True,
        }

        result = get_innings_grade(game_state)

        assert "grade" in result
        assert result["total_runs"] == 160

    def test_high_boundary_percentage_bonus(self):
        """Test that high boundary percentage contributes positively to grade"""
        deliveries = [{"runs_scored": 4 if i % 2 == 0 else 6, "is_extra": False} for i in range(20)]

        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=100,  # All from boundaries
            total_wickets=2,
            overs_completed=3,
            balls_this_over=2,
            overs_limit=20,
            deliveries=deliveries,
            is_completed=False,
        )

        # All runs from boundaries should have 100% boundary percentage
        assert result["boundary_percentage"] == 100.0

    def test_wicket_preservation_penalty(self):
        """Test that losing many wickets reduces grade"""
        # Same runs, different wicket losses
        result_few_wickets = InningsGradeCalculator.calculate_innings_grade(
            total_runs=160,
            total_wickets=3,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        result_many_wickets = InningsGradeCalculator.calculate_innings_grade(
            total_runs=160,
            total_wickets=8,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        # Fewer wickets should have higher wicket efficiency
        assert result_few_wickets["wicket_efficiency"] > result_many_wickets["wicket_efficiency"]

    def test_edge_case_zero_runs(self):
        """Test grade when no runs scored"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=0,
            total_wickets=10,
            overs_completed=10,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        assert result["grade"] == "D"
        assert result["total_runs"] == 0
        assert result["score_percentage"] == 0.0

    def test_edge_case_no_wickets_lost(self):
        """Test grade when no wickets lost"""
        result = InningsGradeCalculator.calculate_innings_grade(
            total_runs=180,
            total_wickets=0,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            batting_team_size=11,
            is_completed=True,
        )

        assert result["wicket_efficiency"] == 1.0  # Perfect wicket preservation
        assert result["wickets_lost"] == 0
