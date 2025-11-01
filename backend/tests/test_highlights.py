"""
Tests for the AI highlights feature.

Tests include:
- Event detection (boundaries, wickets, milestones)
- Highlight generation from match data
- API endpoints for highlights
- Social media sharing functionality
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure backend is on path for local runs
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app
from backend.services.highlights_service import HighlightsService
from backend.sql_app.models import HighlightEventType

client = TestClient(app)


class TestHighlightsService:
    """Test the highlights detection service."""

    def test_detect_boundary(self):
        """Test detection of a boundary (4 runs)."""
        deliveries = [
            {
                "over_number": 1,
                "ball_number": 1,
                "runs_scored": 4,
                "is_wicket": False,
                "is_extra": False,
                "striker_id": "player1",
                "bowler_id": "bowler1",
            }
        ]
        
        highlights = HighlightsService.detect_highlights(
            deliveries=deliveries,
            batting_scorecard={},
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        assert len(highlights) == 1
        assert highlights[0]["event_type"] == HighlightEventType.boundary
        assert highlights[0]["title"] == "Boundary!"
        assert highlights[0]["over_number"] == 1
        assert highlights[0]["ball_number"] == 1

    def test_detect_six(self):
        """Test detection of a six."""
        deliveries = [
            {
                "over_number": 2,
                "ball_number": 3,
                "runs_scored": 6,
                "is_wicket": False,
                "is_extra": False,
                "striker_id": "player1",
                "bowler_id": "bowler1",
            }
        ]
        
        highlights = HighlightsService.detect_highlights(
            deliveries=deliveries,
            batting_scorecard={},
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        assert len(highlights) == 1
        assert highlights[0]["event_type"] == HighlightEventType.six
        assert highlights[0]["title"] == "SIX!"
        assert highlights[0]["event_metadata"]["runs"] == 6

    def test_detect_wicket(self):
        """Test detection of a wicket."""
        deliveries = [
            {
                "over_number": 5,
                "ball_number": 4,
                "runs_scored": 0,
                "is_wicket": True,
                "is_extra": False,
                "striker_id": "player1",
                "bowler_id": "bowler1",
                "dismissed_player_id": "player1",
                "dismissal_type": "bowled",
            }
        ]
        
        highlights = HighlightsService.detect_highlights(
            deliveries=deliveries,
            batting_scorecard={},
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        assert len(highlights) == 1
        assert highlights[0]["event_type"] == HighlightEventType.wicket
        assert highlights[0]["title"] == "Wicket!"
        assert highlights[0]["description"] == "bowled"

    def test_detect_hat_trick(self):
        """Test detection of a hat-trick (3 consecutive wickets by same bowler)."""
        deliveries = [
            {
                "over_number": 10,
                "ball_number": 4,
                "runs_scored": 0,
                "is_wicket": True,
                "is_extra": False,
                "striker_id": "player1",
                "bowler_id": "bowler1",
                "dismissed_player_id": "player1",
                "dismissal_type": "bowled",
            },
            {
                "over_number": 10,
                "ball_number": 5,
                "runs_scored": 0,
                "is_wicket": True,
                "is_extra": False,
                "striker_id": "player2",
                "bowler_id": "bowler1",
                "dismissed_player_id": "player2",
                "dismissal_type": "caught",
            },
            {
                "over_number": 10,
                "ball_number": 6,
                "runs_scored": 0,
                "is_wicket": True,
                "is_extra": False,
                "striker_id": "player3",
                "bowler_id": "bowler1",
                "dismissed_player_id": "player3",
                "dismissal_type": "lbw",
            },
        ]
        
        highlights = HighlightsService.detect_highlights(
            deliveries=deliveries,
            batting_scorecard={},
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        # Should detect 3 wickets + 1 hat-trick
        wicket_highlights = [h for h in highlights if h["event_type"] == HighlightEventType.wicket]
        hat_trick_highlights = [h for h in highlights if h["event_type"] == HighlightEventType.hat_trick]
        
        assert len(wicket_highlights) == 3
        assert len(hat_trick_highlights) == 1
        assert hat_trick_highlights[0]["title"] == "Hat-trick!"

    def test_detect_milestone(self):
        """Test detection of a batting milestone (50, 100, etc.)."""
        batting_scorecard = {
            "player1": {
                "runs": 52,
                "player_name": "Test Player",
                "balls_faced": 40,
            }
        }
        
        highlights = HighlightsService.detect_highlights(
            deliveries=[],
            batting_scorecard=batting_scorecard,
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        milestone_highlights = [h for h in highlights if h["event_type"] == HighlightEventType.milestone]
        assert len(milestone_highlights) == 1
        assert milestone_highlights[0]["title"] == "50 runs!"
        assert milestone_highlights[0]["event_metadata"]["milestone"] == 50

    def test_detect_maiden_over(self):
        """Test detection of a maiden over (6 balls, no runs)."""
        deliveries = [
            {"over_number": 5, "ball_number": 1, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
            {"over_number": 5, "ball_number": 2, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
            {"over_number": 5, "ball_number": 3, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
            {"over_number": 5, "ball_number": 4, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
            {"over_number": 5, "ball_number": 5, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
            {"over_number": 5, "ball_number": 6, "runs_scored": 0, "is_wicket": False, "bowler_id": "bowler1"},
        ]
        
        highlights = HighlightsService.detect_highlights(
            deliveries=deliveries,
            batting_scorecard={},
            bowling_scorecard={},
            game_id="game1",
            current_inning=1,
        )
        
        maiden_highlights = [h for h in highlights if h["event_type"] == HighlightEventType.maiden_over]
        assert len(maiden_highlights) == 1
        assert maiden_highlights[0]["title"] == "Maiden Over!"

    def test_generate_video_url(self):
        """Test video URL generation."""
        highlight = {
            "game_id": "game123",
            "id": "highlight456",
            "event_type": HighlightEventType.six,
        }
        
        video_url = HighlightsService.generate_video_url(highlight)
        
        assert "game123" in video_url
        assert "highlight456" in video_url
        assert video_url.endswith(".mp4")

    def test_generate_share_url_twitter(self):
        """Test Twitter share URL generation."""
        url = HighlightsService.generate_share_url("highlight123", "twitter")
        
        assert "twitter.com/intent/tweet" in url
        assert "highlight123" in url

    def test_generate_share_url_facebook(self):
        """Test Facebook share URL generation."""
        url = HighlightsService.generate_share_url("highlight123", "facebook")
        
        assert "facebook.com/sharer" in url
        assert "highlight123" in url

    def test_generate_share_url_whatsapp(self):
        """Test WhatsApp share URL generation."""
        url = HighlightsService.generate_share_url("highlight123", "whatsapp")
        
        assert "wa.me" in url
        assert "highlight123" in url


class TestHighlightsAPI:
    """Test the highlights API endpoints."""

    def test_health_endpoint_accessible(self):
        """Ensure the API is running."""
        resp = client.get("/health")
        assert resp.status_code == 200

    # Note: The following tests would require a test database setup
    # For now, they are placeholders showing the test structure
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_generate_highlights_for_game(self):
        """Test generating highlights for a game."""
        # This would require creating a game with deliveries first
        pass

    @pytest.mark.skip(reason="Requires database setup")
    def test_get_game_highlights(self):
        """Test retrieving highlights for a game."""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    def test_get_single_highlight(self):
        """Test retrieving a single highlight by ID."""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    def test_share_highlight(self):
        """Test generating a share URL for a highlight."""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    def test_delete_highlight(self):
        """Test deleting a highlight."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
