"""
Highlights service: AI-powered event detection and highlight generation.

This module provides functionality to:
- Detect key moments from match deliveries (boundaries, wickets, milestones)
- Generate highlight videos based on detected events
- Manage highlight metadata and storage
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from backend.sql_app.models import HighlightEventType

UTC = getattr(dt, "UTC", dt.UTC)


class HighlightsService:
    """Service for detecting and managing match highlights."""

    @staticmethod
    def detect_highlights(
        deliveries: list[dict[str, Any]],
        batting_scorecard: dict[str, Any],
        bowling_scorecard: dict[str, Any],
        game_id: str,
        current_inning: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Detect key moments from match deliveries.
        
        Args:
            deliveries: List of delivery dictionaries
            batting_scorecard: Batting scorecard dictionary
            bowling_scorecard: Bowling scorecard dictionary
            game_id: Game identifier
            current_inning: Current inning number
            
        Returns:
            List of highlight dictionaries
        """
        highlights: list[dict[str, Any]] = []

        # Track state for detection
        consecutive_wickets: list[dict[str, Any]] = []
        partnership_runs: dict[tuple[str, str], int] = {}
        current_over_runs = 0
        last_over_number = -1

        for delivery in deliveries:
            over_num = delivery.get("over_number", 0)
            ball_num = delivery.get("ball_number", 0)
            runs = delivery.get("runs_scored", 0)
            is_wicket = delivery.get("is_wicket", False)
            striker_id = delivery.get("striker_id")
            bowler_id = delivery.get("bowler_id")

            # Track current over runs
            if over_num != last_over_number:
                current_over_runs = 0
                last_over_number = over_num
            current_over_runs += runs

            # Detect boundaries (4s)
            if runs == 4 and not delivery.get("is_extra", False):
                highlights.append({
                    "game_id": game_id,
                    "event_type": HighlightEventType.boundary,
                    "over_number": over_num,
                    "ball_number": ball_num,
                    "inning": current_inning,
                    "title": "Boundary!",
                    "description": f"Four runs off the bat",
                    "player_id": striker_id,
                    "player_name": delivery.get("striker_name"),
                    "event_metadata": {
                        "runs": runs,
                        "bowler_id": bowler_id,
                        "shot_type": delivery.get("shot_map"),
                    },
                })

            # Detect sixes
            if runs == 6 and not delivery.get("is_extra", False):
                highlights.append({
                    "game_id": game_id,
                    "event_type": HighlightEventType.six,
                    "over_number": over_num,
                    "ball_number": ball_num,
                    "inning": current_inning,
                    "title": "SIX!",
                    "description": f"Maximum! Six runs",
                    "player_id": striker_id,
                    "player_name": delivery.get("striker_name"),
                    "event_metadata": {
                        "runs": runs,
                        "bowler_id": bowler_id,
                        "shot_type": delivery.get("shot_map"),
                    },
                })

            # Detect wickets
            if is_wicket:
                dismissed_id = delivery.get("dismissed_player_id")
                dismissal_type = delivery.get("dismissal_type", "out")
                
                highlights.append({
                    "game_id": game_id,
                    "event_type": HighlightEventType.wicket,
                    "over_number": over_num,
                    "ball_number": ball_num,
                    "inning": current_inning,
                    "title": "Wicket!",
                    "description": f"{dismissal_type}",
                    "player_id": dismissed_id,
                    "player_name": delivery.get("dismissed_player_name"),
                    "event_metadata": {
                        "dismissal_type": dismissal_type,
                        "bowler_id": bowler_id,
                        "fielder_id": delivery.get("fielder_id"),
                    },
                })

                # Track consecutive wickets for hat-trick detection
                consecutive_wickets.append(delivery)
                if len(consecutive_wickets) >= 3:
                    # Check if last 3 wickets are by same bowler
                    recent_bowlers = [d.get("bowler_id") for d in consecutive_wickets[-3:]]
                    if len(set(recent_bowlers)) == 1:
                        highlights.append({
                            "game_id": game_id,
                            "event_type": HighlightEventType.hat_trick,
                            "over_number": over_num,
                            "ball_number": ball_num,
                            "inning": current_inning,
                            "title": "Hat-trick!",
                            "description": f"Three wickets in consecutive balls!",
                            "player_id": bowler_id,
                            "player_name": delivery.get("bowler_name"),
                            "event_metadata": {
                                "bowler_id": bowler_id,
                            },
                        })
            else:
                consecutive_wickets.clear()

        # Detect milestones from batting scorecard
        for player_id, stats in batting_scorecard.items():
            if not isinstance(stats, dict):
                continue
            
            runs = stats.get("runs", 0)
            player_name = stats.get("player_name", "Unknown")

            # Detect 50, 100, 150, 200+ milestones
            milestones = [50, 100, 150, 200]
            for milestone in milestones:
                if runs >= milestone:
                    # Find the delivery where milestone was reached
                    # For now, we'll just add a milestone highlight
                    highlights.append({
                        "game_id": game_id,
                        "event_type": HighlightEventType.milestone,
                        "over_number": 0,  # Will be updated with actual over
                        "ball_number": 0,
                        "inning": current_inning,
                        "title": f"{milestone} runs!",
                        "description": f"{player_name} reaches {milestone}",
                        "player_id": player_id,
                        "player_name": player_name,
                        "event_metadata": {
                            "milestone": milestone,
                            "total_runs": runs,
                        },
                    })
                    break  # Only add the highest milestone reached

        # Detect maiden overs - track which overs we've already checked
        checked_overs = set()
        for delivery in deliveries:
            over_num = delivery.get("over_number", 0)
            
            # Skip if we've already checked this over
            if over_num in checked_overs:
                continue
            
            # Check if over is complete and no runs scored
            over_deliveries = [
                d for d in deliveries 
                if d.get("over_number") == over_num
            ]
            
            if len(over_deliveries) >= 6:  # Complete over
                checked_overs.add(over_num)
                total_runs = sum(d.get("runs_scored", 0) for d in over_deliveries)
                if total_runs == 0:
                    bowler_id = over_deliveries[0].get("bowler_id")
                    highlights.append({
                        "game_id": game_id,
                        "event_type": HighlightEventType.maiden_over,
                        "over_number": over_num,
                        "ball_number": 6,
                        "inning": current_inning,
                        "title": "Maiden Over!",
                        "description": f"Maiden over bowled",
                        "player_id": bowler_id,
                        "player_name": over_deliveries[0].get("bowler_name"),
                        "event_metadata": {
                            "bowler_id": bowler_id,
                        },
                    })

        return highlights

    @staticmethod
    def generate_video_url(highlight: dict[str, Any]) -> str:
        """
        Generate a video URL for a highlight.
        
        For now, this is a placeholder that returns a mock URL.
        In production, this would integrate with a video generation service.
        
        Args:
            highlight: Highlight dictionary
            
        Returns:
            Video URL string
        """
        # Mock implementation - in production, this would call a video generation service
        game_id = highlight.get("game_id")
        highlight_id = highlight.get("id", "unknown")
        event_type = highlight.get("event_type", "event")
        
        # Return a placeholder URL
        return f"/api/highlights/{game_id}/videos/{highlight_id}/{event_type}.mp4"

    @staticmethod
    def generate_share_url(highlight_id: str, platform: str) -> str:
        """
        Generate a social media share URL for a highlight.
        
        Args:
            highlight_id: Highlight identifier
            platform: Social media platform (e.g., "twitter", "facebook")
            
        Returns:
            Share URL string
        """
        base_url = "https://cricksy-scorer.com"  # Replace with actual domain
        highlight_url = f"{base_url}/highlights/{highlight_id}"
        
        if platform == "twitter":
            return f"https://twitter.com/intent/tweet?url={highlight_url}&text=Check%20out%20this%20cricket%20highlight!"
        elif platform == "facebook":
            return f"https://www.facebook.com/sharer/sharer.php?u={highlight_url}"
        elif platform == "instagram":
            # Instagram doesn't support direct web sharing, return app deep link
            return f"instagram://share?url={highlight_url}"
        elif platform == "whatsapp":
            return f"https://wa.me/?text=Check%20out%20this%20cricket%20highlight!%20{highlight_url}"
        else:
            return highlight_url
