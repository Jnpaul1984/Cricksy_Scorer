"""Scorecard parser prototype.

This is a prototype-level parser that extracts structured data from OCR text.
Human verification is REQUIRED before applying parsed data to the delivery ledger.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_scorecard(ocr_text: str) -> dict[str, Any]:
    """Parse OCR text into structured scorecard data.

    This is a PROTOTYPE implementation that demonstrates the concept.
    Real production parsing would require much more sophisticated logic,
    machine learning models, and extensive testing.

    Args:
        ocr_text: Raw OCR text extracted from scorecard image

    Returns:
        Dictionary containing parsed scorecard data with structure:
        {
            "deliveries": [...],
            "teams": {...},
            "metadata": {...},
            "confidence": float,  # Overall confidence score
            "raw_ocr": str  # Original OCR text for reference
        }
    """
    logger.info("Parsing scorecard from OCR text")

    # Initialize result structure
    result: dict[str, Any] = {
        "deliveries": [],
        "teams": {"team_a": None, "team_b": None},
        "metadata": {
            "match_type": "unknown",
            "date": None,
            "venue": None,
        },
        "confidence": 0.0,
        "raw_ocr": ocr_text,
        "warnings": [],
    }

    # Prototype parsing logic
    # In production, this would use sophisticated NLP/ML models

    # Try to extract team names (simple pattern matching)
    team_pattern = r"(?:vs|v/s|versus)\s+([A-Za-z\s]+?)(?:\n|$)"
    team_match = re.search(team_pattern, ocr_text, re.IGNORECASE)
    if team_match:
        result["teams"]["team_b"] = team_match.group(1).strip()

    # Try to extract scores (looking for patterns like "123/4")
    score_pattern = r"(\d{1,3})/(\d{1,2})"
    score_matches = re.findall(score_pattern, ocr_text)
    if score_matches:
        for runs, wickets in score_matches:
            result["metadata"]["total_runs"] = int(runs)
            result["metadata"]["total_wickets"] = int(wickets)
            break  # Just take first match for prototype

    # Try to extract overs (looking for patterns like "20.0" or "20")
    overs_pattern = r"(?:overs?|ov)\s*[:=]?\s*(\d{1,2}(?:\.\d)?)"
    overs_match = re.search(overs_pattern, ocr_text, re.IGNORECASE)
    if overs_match:
        result["metadata"]["overs"] = float(overs_match.group(1))

    # Try to extract match type (T20, ODI, Test)
    if re.search(r"\b(T20|T-20|Twenty20)\b", ocr_text, re.IGNORECASE):
        result["metadata"]["match_type"] = "T20"
    elif re.search(r"\b(ODI|One[- ]?Day)\b", ocr_text, re.IGNORECASE):
        result["metadata"]["match_type"] = "ODI"
    elif re.search(r"\bTest\b", ocr_text, re.IGNORECASE):
        result["metadata"]["match_type"] = "Test"

    # Prototype delivery parsing
    # Look for ball-by-ball data patterns (very simplified)
    delivery_pattern = r"(\d+)\.(\d+)\s+([A-Za-z\s]+?)\s+(\d+)"
    delivery_matches = re.findall(delivery_pattern, ocr_text)

    for over, ball, batsman, runs in delivery_matches[:50]:  # Limit to 50 for safety
        delivery = {
            "over": int(over),
            "ball": int(ball),
            "batsman": batsman.strip(),
            "runs": int(runs),
            "extras": 0,
            "wicket": False,
        }
        result["deliveries"].append(delivery)

    # Calculate confidence based on what we found
    confidence = 0.0
    if result["teams"]["team_b"]:
        confidence += 0.2
    if result["metadata"]["match_type"] != "unknown":
        confidence += 0.2
    if result["metadata"].get("total_runs"):
        confidence += 0.2
    if result["metadata"].get("overs"):
        confidence += 0.2
    if len(result["deliveries"]) > 0:
        confidence += 0.2

    result["confidence"] = round(confidence, 2)

    # Add warnings if confidence is low
    if confidence < 0.4:
        result["warnings"].append("Low confidence parse - manual review strongly recommended")
    if len(result["deliveries"]) == 0:
        result["warnings"].append("No deliveries detected - manual entry may be required")
    if not result["teams"]["team_b"]:
        result["warnings"].append("Could not detect team names")

    logger.info(
        f"Parsed scorecard with confidence {confidence:.2f}, "
        f"{len(result['deliveries'])} deliveries, "
        f"{len(result['warnings'])} warnings"
    )

    return result


def validate_parsed_data(parsed_data: dict[str, Any]) -> list[str]:
    """Validate parsed scorecard data for completeness and consistency.

    Args:
        parsed_data: Parsed scorecard dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "deliveries" not in parsed_data:
        errors.append("Missing 'deliveries' field")
    elif not isinstance(parsed_data["deliveries"], list):
        errors.append("'deliveries' must be a list")

    if "teams" not in parsed_data:
        errors.append("Missing 'teams' field")

    if "metadata" not in parsed_data:
        errors.append("Missing 'metadata' field")

    # Check confidence threshold
    confidence = parsed_data.get("confidence", 0.0)
    if confidence < 0.3:
        errors.append(f"Confidence too low ({confidence:.2f}) - manual review required")

    # Validate deliveries structure
    if "deliveries" in parsed_data and isinstance(parsed_data["deliveries"], list):
        for i, delivery in enumerate(parsed_data["deliveries"]):
            if not isinstance(delivery, dict):
                errors.append(f"Delivery {i} is not a dictionary")
                continue

            required_fields = ["over", "ball", "runs"]
            for field in required_fields:
                if field not in delivery:
                    errors.append(f"Delivery {i} missing required field '{field}'")

    return errors
