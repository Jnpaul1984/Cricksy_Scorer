"""Prototype scorecard parser for OCR output.

This is a prototype-level parser that extracts basic scorecard information.
The output requires human verification before being applied to the delivery ledger.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_scorecard(ocr_text: str) -> dict[str, Any]:
    """
    Parse OCR text into structured scorecard data.

    This is a PROTOTYPE parser with limited accuracy. The output must be
    reviewed and confirmed by a human before being applied to the ledger.

    Args:
        ocr_text: Raw OCR text from Tesseract

    Returns:
        dict with parsed scorecard data:
        {
            "teams": {"team_a": str, "team_b": str},
            "players": [{"name": str, "runs": int, "balls": int, "wickets": int}, ...],
            "total_runs": int,
            "total_wickets": int,
            "overs": float,
            "confidence": str (low/medium/high),
            "raw_text": str
        }
    """
    result: dict[str, Any] = {
        "teams": {},
        "players": [],
        "total_runs": 0,
        "total_wickets": 0,
        "overs": 0.0,
        "confidence": "low",
        "raw_text": ocr_text,
    }

    # Try to extract team names (look for "vs" or "v" between team names)
    team_pattern = r"([A-Za-z\s]+)\s+(?:vs?\.?)\s+([A-Za-z\s]+)"
    team_match = re.search(team_pattern, ocr_text, re.IGNORECASE)
    if team_match:
        result["teams"]["team_a"] = team_match.group(1).strip()
        result["teams"]["team_b"] = team_match.group(2).strip()

    # Try to extract total score (e.g., "123/4" or "123-4")
    score_pattern = r"(\d{1,3})[\s]*[/-][\s]*(\d{1,2})"
    score_match = re.search(score_pattern, ocr_text)
    if score_match:
        result["total_runs"] = int(score_match.group(1))
        result["total_wickets"] = int(score_match.group(2))

    # Try to extract overs (e.g., "20.0 overs" or "(20 ov)")
    overs_pattern = r"(\d{1,3}\.?\d*)\s*(?:overs?|ov)"
    overs_match = re.search(overs_pattern, ocr_text, re.IGNORECASE)
    if overs_match:
        result["overs"] = float(overs_match.group(1))

    # Try to extract player scores (name followed by runs)
    # This is very simplistic and will need improvement
    player_pattern = r"([A-Za-z][A-Za-z\s\.]{2,30})\s+(\d{1,3})\*?\s*(?:\((\d+)\))?"
    for match in re.finditer(player_pattern, ocr_text):
        name = match.group(1).strip()
        runs = int(match.group(2))
        balls = int(match.group(3)) if match.group(3) else 0

        # Basic filtering to avoid false matches
        if len(name) > 3 and runs <= 500:  # Sanity checks
            result["players"].append({
                "name": name,
                "runs": runs,
                "balls": balls,
                "wickets": 0,
            })

    # Assess confidence based on what we found
    confidence_score = 0
    if result["teams"].get("team_a"):
        confidence_score += 1
    if result["total_runs"] > 0:
        confidence_score += 1
    if result["overs"] > 0:
        confidence_score += 1
    if len(result["players"]) > 0:
        confidence_score += 1

    if confidence_score >= 3:
        result["confidence"] = "medium"
    elif confidence_score >= 2:
        result["confidence"] = "low"
    else:
        result["confidence"] = "very_low"

    logger.info(
        f"Parsed scorecard: {len(result['players'])} players, "
        f"{result['total_runs']}/{result['total_wickets']}, "
        f"confidence={result['confidence']}"
    )

    return result


def validate_parsed_data(parsed_data: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate parsed scorecard data.

    Args:
        parsed_data: Parsed data from parse_scorecard()

    Returns:
        (is_valid, error_message)
    """
    # Check required fields
    if not isinstance(parsed_data, dict):
        return False, "Parsed data must be a dictionary"

    if "teams" not in parsed_data or not isinstance(parsed_data["teams"], dict):
        return False, "Missing or invalid teams data"

    if "total_runs" not in parsed_data or not isinstance(parsed_data["total_runs"], (int, float)):
        return False, "Missing or invalid total_runs"

    if "total_wickets" not in parsed_data or not isinstance(parsed_data["total_wickets"], (int, float)):
        return False, "Missing or invalid total_wickets"

    # Validate ranges
    if parsed_data["total_runs"] < 0 or parsed_data["total_runs"] > 1000:
        return False, "Invalid total_runs value (must be 0-1000)"

    if parsed_data["total_wickets"] < 0 or parsed_data["total_wickets"] > 10:
        return False, "Invalid total_wickets value (must be 0-10)"

    if parsed_data.get("overs", 0) < 0 or parsed_data.get("overs", 0) > 100:
        return False, "Invalid overs value (must be 0-100)"

    # Validate players if present
    if "players" in parsed_data:
        if not isinstance(parsed_data["players"], list):
            return False, "Players must be a list"

        for player in parsed_data["players"]:
            if not isinstance(player, dict):
                return False, "Each player must be a dictionary"
            if "name" not in player or not player["name"]:
                return False, "Each player must have a name"

    return True, None
