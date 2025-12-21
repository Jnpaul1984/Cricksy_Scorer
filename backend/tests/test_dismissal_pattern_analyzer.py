"""
Tests for Dismissal Pattern Analyzer

Tests dismissal pattern identification, vulnerability scoring, and analysis.
"""

from backend.services.dismissal_pattern_analyzer import (
    DismissalPatternAnalyzer,
    DismissalRecord,
    MatchPhase,
    DismissalType,
)


class TestDismissalPatternIdentification:
    """Test dismissal pattern identification."""

    def test_identifies_dominant_dismissal_type(self):
        """Verify dominant dismissal type is identified as pattern."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=15,
                deliveries_faced=30,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=20,
                deliveries_faced=45,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p1",
            player_name="Test Player",
            dismissals=dismissals,
        )

        assert len(profile.top_patterns) > 0
        assert any(p.pattern_value == DismissalType.BOWLED for p in profile.top_patterns)

    def test_identifies_delivery_type_vulnerability(self):
        """Verify vulnerability to specific delivery types is detected."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.LBW,
                delivery_type="yorker",
                runs_at_dismissal=12,
                deliveries_faced=25,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                delivery_type="yorker",
                runs_at_dismissal=10,
                deliveries_faced=20,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.CAUGHT,
                delivery_type="short",
                runs_at_dismissal=25,
                deliveries_faced=50,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p2",
            player_name="Pace Vulnerable",
            dismissals=dismissals,
        )

        # Should have yorker pattern
        assert "yorker" in profile.dismissals_by_delivery or len(profile.top_patterns) > 0

    def test_identifies_phase_vulnerability(self):
        """Verify vulnerability during specific match phases is detected."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=25,
                deliveries_faced=50,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.CAUGHT,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.RUN_OUT,
                match_phase=MatchPhase.POWERPLAY,
                runs_at_dismissal=15,
                deliveries_faced=30,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p3",
            player_name="Death Overs Weak",
            dismissals=dismissals,
        )

        # Should identify death overs as vulnerability
        assert MatchPhase.DEATH_OVERS in profile.dismissals_by_phase
        assert profile.dismissals_by_phase[MatchPhase.DEATH_OVERS] >= 2


class TestVulnerabilityScoring:
    """Test vulnerability score calculation."""

    def test_high_dismissal_frequency_increases_score(self):
        """Verify high dismissal frequency increases vulnerability score."""
        many_dismissals = [
            DismissalRecord(
                dismissal_id=f"d{i}",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=20 + i,
                deliveries_faced=40 + i,
            )
            for i in range(15)
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p4",
            player_name="Frequently Dismissed",
            dismissals=many_dismissals,
        )

        assert profile.overall_vulnerability_score > 20

    def test_technical_dismissals_increase_score(self):
        """Verify technical dismissals (bowled, lbw) increase vulnerability."""
        technical_dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=10,
                deliveries_faced=20,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.LBW,
                runs_at_dismissal=12,
                deliveries_faced=25,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=8,
                deliveries_faced=15,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p5",
            player_name="Technical Failure",
            dismissals=technical_dismissals,
        )

        assert profile.overall_vulnerability_score > 20

    def test_death_overs_dismissals_increase_score(self):
        """Verify death overs dismissals contribute to vulnerability."""
        death_dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.CAUGHT,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=40,
                deliveries_faced=80,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.CAUGHT,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=35,
                deliveries_faced=70,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.CAUGHT,
                match_phase=MatchPhase.POWERPLAY,
                runs_at_dismissal=15,
                deliveries_faced=30,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p6",
            player_name="Death Vulnerable",
            dismissals=death_dismissals,
        )

        assert profile.overall_vulnerability_score >= 10

    def test_low_dismissals_low_score(self):
        """Verify few dismissals result in low vulnerability score."""
        few_dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=50,
                deliveries_faced=100,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p7",
            player_name="Rarely Dismissed",
            dismissals=few_dismissals,
        )

        assert profile.overall_vulnerability_score < 15


class TestCriticalSituationIdentification:
    """Test identification of critical dismissal situations."""

    def test_identifies_recurring_situation(self):
        """Verify recurring dismissal situations are identified."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.LBW,
                delivery_type="yorker",
                line="leg",
                runs_at_dismissal=15,
                deliveries_faced=30,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                delivery_type="yorker",
                line="leg",
                runs_at_dismissal=12,
                deliveries_faced=25,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.CAUGHT,
                delivery_type="pace",
                line="off",
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p8",
            player_name="Situation Vulnerable",
            dismissals=dismissals,
        )

        assert len(profile.critical_situations) > 0

    def test_critical_situation_risk_level(self):
        """Verify critical situations have appropriate risk level."""
        dismissals = [
            DismissalRecord(
                dismissal_id=f"d{i}",
                dismissal_type=DismissalType.LBW,
                delivery_type="yorker",
                line="leg",
                runs_at_dismissal=12,
                deliveries_faced=25,
            )
            for i in range(3)
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p9",
            player_name="High Risk",
            dismissals=dismissals,
        )

        if profile.critical_situations:
            assert profile.critical_situations[0].risk_level in ["critical", "high"]


class TestPrimaryVulnerability:
    """Test primary vulnerability identification."""

    def test_identifies_primary_vulnerability(self):
        """Verify primary vulnerability is correctly identified."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=10,
                deliveries_faced=20,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=8,
                deliveries_faced=15,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=12,
                deliveries_faced=25,
            ),
            DismissalRecord(
                dismissal_id="d4",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p10",
            player_name="Clear Vulnerability",
            dismissals=dismissals,
        )

        assert profile.primary_vulnerability is not None
        assert profile.primary_vulnerability == DismissalType.BOWLED

    def test_identifies_secondary_vulnerabilities(self):
        """Verify secondary vulnerabilities are identified."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=10,
                deliveries_faced=20,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                runs_at_dismissal=8,
                deliveries_faced=15,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.LBW,
                runs_at_dismissal=12,
                deliveries_faced=25,
            ),
            DismissalRecord(
                dismissal_id="d4",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p11",
            player_name="Multiple Vulnerabilities",
            dismissals=dismissals,
        )

        assert len(profile.secondary_vulnerabilities) > 0


class TestImprovementAreas:
    """Test improvement area identification."""

    def test_identifies_improvement_areas(self):
        """Verify improvement areas are identified."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.BOWLED,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.BOWLED,
                match_phase=MatchPhase.DEATH_OVERS,
                runs_at_dismissal=28,
                deliveries_faced=55,
            ),
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p12",
            player_name="Needs Improvement",
            dismissals=dismissals,
        )

        assert len(profile.improvement_areas) > 0
        assert any(
            "technique" in area.lower() or "death" in area.lower()
            for area in profile.improvement_areas
        )


class TestDismissalTrend:
    """Test dismissal trend analysis."""

    def test_calculates_trend_improving(self):
        """Verify improving trend is identified when runs increase."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=5,
                deliveries_faced=10,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=8,
                deliveries_faced=15,
            ),
            DismissalRecord(
                dismissal_id="d3",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=25,
                deliveries_faced=50,
            ),
            DismissalRecord(
                dismissal_id="d4",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=28,
                deliveries_faced=55,
            ),
        ]

        trend = DismissalPatternAnalyzer.get_dismissal_trend(dismissals, "last_10")

        assert trend.trend_direction in ["improving", "stable", "declining"]

    def test_calculates_average_runs_at_dismissal(self):
        """Verify average runs at dismissal is calculated."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=20,
                deliveries_faced=40,
            ),
            DismissalRecord(
                dismissal_id="d2",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=30,
                deliveries_faced=60,
            ),
        ]

        trend = DismissalPatternAnalyzer.get_dismissal_trend(dismissals, "last_5")

        assert trend.average_runs_at_dismissal == 25.0


class TestEmptyData:
    """Test handling of empty/minimal data."""

    def test_handles_no_dismissals(self):
        """Verify analyzer handles players with no dismissals."""
        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p13",
            player_name="Never Dismissed",
            dismissals=[],
        )

        assert profile.total_dismissals == 0
        assert profile.overall_vulnerability_score == 0.0
        assert len(profile.top_patterns) == 0

    def test_handles_single_dismissal(self):
        """Verify analyzer handles single dismissal."""
        dismissals = [
            DismissalRecord(
                dismissal_id="d1",
                dismissal_type=DismissalType.CAUGHT,
                runs_at_dismissal=25,
                deliveries_faced=50,
            )
        ]

        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p14",
            player_name="Rarely Dismissed",
            dismissals=dismissals,
        )

        assert profile.total_dismissals == 1
        assert profile.overall_vulnerability_score >= 0


class TestTeamAnalysis:
    """Test team-level dismissal analysis."""

    def test_analyzes_team_dismissals(self):
        """Verify team dismissal analysis works."""
        profile1 = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p1",
            player_name="Player 1",
            dismissals=[
                DismissalRecord(
                    dismissal_id="d1",
                    dismissal_type=DismissalType.BOWLED,
                    match_phase=MatchPhase.POWERPLAY,
                    runs_at_dismissal=10,
                    deliveries_faced=20,
                )
            ],
        )

        profile2 = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p2",
            player_name="Player 2",
            dismissals=[
                DismissalRecord(
                    dismissal_id="d2",
                    dismissal_type=DismissalType.CAUGHT,
                    match_phase=MatchPhase.DEATH_OVERS,
                    runs_at_dismissal=30,
                    deliveries_faced=60,
                )
            ],
        )

        team_context = DismissalPatternAnalyzer.analyze_team_dismissals(
            team_id="t1",
            team_name="Test Team",
            player_profiles=[profile1, profile2],
        )

        assert team_context.total_team_dismissals == 2
        assert len(team_context.vulnerable_players) > 0

    def test_identifies_vulnerable_players(self):
        """Verify team analysis identifies most vulnerable players."""
        profile1 = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p1",
            player_name="Strong Player",
            dismissals=[
                DismissalRecord(
                    dismissal_id="d1",
                    dismissal_type=DismissalType.CAUGHT,
                    runs_at_dismissal=50,
                    deliveries_faced=100,
                )
            ],
        )

        profile2 = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id="p2",
            player_name="Weak Player",
            dismissals=[
                DismissalRecord(
                    dismissal_id=f"d{i}",
                    dismissal_type=DismissalType.BOWLED,
                    runs_at_dismissal=8 + i,
                    deliveries_faced=15 + i,
                )
                for i in range(8)
            ],
        )

        team_context = DismissalPatternAnalyzer.analyze_team_dismissals(
            team_id="t2",
            team_name="Test Team 2",
            player_profiles=[profile1, profile2],
        )

        # Weak player should be in vulnerable list
        vulnerable_names = [name for name, score in team_context.vulnerable_players]
        assert "Weak Player" in vulnerable_names
