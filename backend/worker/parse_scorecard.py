"""Prototype rule-based parser for scorecard OCR text.

This is a prototype-level parser that converts OCR text into delivery objects.
It uses simple pattern matching and heuristics. All results require human verification.
"""
from __future__ import annotations

import re
from typing import Any


def parse_scorecard(ocr_text: str) -> dict[str, Any]:
    """
    Parse OCR text from a scorecard into delivery objects.
    
    This is a prototype parser using simple rules. It attempts to extract:
    - Batsman names
    - Bowler names
    - Runs scored
    - Wickets
    - Extras
    
    Args:
        ocr_text: Raw text extracted from OCR
    
    Returns:
        Dictionary with deliveries and metadata
        {
            "deliveries": [...],
            "metadata": {
                "confidence": 0.0-1.0,
                "parser": "rule_based_v1",
                "warnings": [...]
            }
        }
    """
    deliveries: list[dict[str, Any]] = []
    warnings: list[str] = []
    
    # Clean and normalize text
    text = ocr_text.strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    if not lines:
        return {
            "deliveries": [],
            "metadata": {
                "confidence": 0.0,
                "parser": "rule_based_v1",
                "warnings": ["No text found in OCR output"]
            }
        }
    
    # Try to detect innings structure
    current_over = 1
    current_ball = 1
    current_batsman = "Unknown Batsman"
    current_bowler = "Unknown Bowler"
    
    # Pattern for scoreboard entries like "J Smith 24 (18)"
    batsman_pattern = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*\((\d+)\)")
    
    # Pattern for bowler figures like "M Jones 3-0-12-1"
    bowler_pattern = re.compile(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)-(\d+)-(\d+)-(\d+)")
    
    # Pattern for delivery notation like "1.2 runs 4" or "2.3 W" or "3.4 wd 1"
    delivery_pattern = re.compile(r"(\d+)\.(\d+)\s+(?:runs?\s+)?(\d+|W|wd|nb|b|lb)", re.IGNORECASE)
    
    # Attempt to extract team names
    team_names = []
    for line in lines[:5]:  # Check first 5 lines for team names
        if "vs" in line.lower() or "v" in line:
            parts = re.split(r"\s+vs?\s+", line, flags=re.IGNORECASE)
            if len(parts) == 2:
                team_names = [p.strip() for p in parts]
                break
    
    # Parse lines looking for delivery information
    for line_idx, line in enumerate(lines):
        # Try to match batsman entry
        batsman_match = batsman_pattern.search(line)
        if batsman_match:
            current_batsman = batsman_match.group(1)
            continue
        
        # Try to match bowler entry
        bowler_match = bowler_pattern.search(line)
        if bowler_match:
            current_bowler = bowler_match.group(1)
            continue
        
        # Try to match delivery notation
        delivery_match = delivery_pattern.search(line)
        if delivery_match:
            over = int(delivery_match.group(1))
            ball = int(delivery_match.group(2))
            outcome = delivery_match.group(3)
            
            delivery = {
                "over": over,
                "ball": ball,
                "batsman": current_batsman,
                "bowler": current_bowler,
                "runs": 0,
                "is_wicket": False,
                "is_extra": False,
                "extra_type": None,
            }
            
            if outcome.upper() == "W":
                delivery["is_wicket"] = True
            elif outcome.lower() in ["wd", "nb", "b", "lb"]:
                delivery["is_extra"] = True
                delivery["extra_type"] = outcome.lower()
                # Try to find runs after the extra
                runs_match = re.search(r"\d+", line[delivery_match.end():])
                if runs_match:
                    delivery["runs"] = int(runs_match.group())
            else:
                try:
                    delivery["runs"] = int(outcome)
                except ValueError:
                    warnings.append(f"Could not parse runs from '{outcome}' on line {line_idx + 1}")
            
            deliveries.append(delivery)
    
    # If we couldn't parse any deliveries, try a simpler approach
    if not deliveries:
        warnings.append("Primary parser found no deliveries, attempting fallback")
        deliveries = _fallback_parse(lines, warnings)
    
    # Calculate confidence based on how much we parsed
    confidence = 0.0
    if deliveries:
        # Base confidence on having deliveries
        confidence = 0.3
        
        # Boost if we found team names
        if team_names:
            confidence += 0.1
        
        # Boost if we found batsmen/bowler names that aren't "Unknown"
        named_deliveries = sum(
            1 for d in deliveries
            if d.get("batsman", "Unknown") != "Unknown Batsman"
        )
        if named_deliveries > 0:
            confidence += 0.2 * (named_deliveries / len(deliveries))
        
        # Boost if overs/balls seem sequential
        sequential = sum(
            1 for i in range(1, len(deliveries))
            if _is_sequential_delivery(deliveries[i-1], deliveries[i])
        )
        if len(deliveries) > 1:
            confidence += 0.2 * (sequential / (len(deliveries) - 1))
        
        # Cap at 0.85 since this is a prototype parser
        confidence = min(confidence, 0.85)
    
    return {
        "deliveries": deliveries,
        "metadata": {
            "confidence": round(confidence, 2),
            "parser": "rule_based_v1",
            "warnings": warnings,
            "team_names": team_names if team_names else None,
            "lines_processed": len(lines),
            "deliveries_found": len(deliveries)
        }
    }


def _fallback_parse(lines: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    """
    Fallback parser that looks for any numbers that might be runs.
    
    This is very basic and will produce low-quality results.
    """
    deliveries = []
    
    # Look for lines with numbers that might be runs
    runs_pattern = re.compile(r"\b([0-6]|W)\b")
    
    over = 1
    ball = 1
    
    for line in lines:
        matches = runs_pattern.findall(line)
        for match in matches:
            delivery = {
                "over": over,
                "ball": ball,
                "batsman": "Unknown Batsman",
                "bowler": "Unknown Bowler",
                "runs": 0,
                "is_wicket": False,
                "is_extra": False,
                "extra_type": None,
            }
            
            if match.upper() == "W":
                delivery["is_wicket"] = True
            else:
                try:
                    delivery["runs"] = int(match)
                except ValueError:
                    continue
            
            deliveries.append(delivery)
            
            # Increment ball counter
            ball += 1
            if ball > 6:
                ball = 1
                over += 1
    
    if deliveries:
        warnings.append(f"Fallback parser found {len(deliveries)} potential deliveries - HIGH UNCERTAINTY")
    
    return deliveries


def _is_sequential_delivery(prev: dict[str, Any], curr: dict[str, Any]) -> bool:
    """Check if two deliveries are sequential."""
    prev_over = prev.get("over", 0)
    prev_ball = prev.get("ball", 0)
    curr_over = curr.get("over", 0)
    curr_ball = curr.get("ball", 0)
    
    # Same over, next ball
    if curr_over == prev_over and curr_ball == prev_ball + 1:
        return True
    
    # Next over, ball 1
    if curr_over == prev_over + 1 and curr_ball == 1:
        return True
    
    return False


def validate_parsed_deliveries(deliveries: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """
    Validate a list of parsed deliveries.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if not deliveries:
        errors.append("No deliveries to validate")
        return False, errors
    
    for i, delivery in enumerate(deliveries):
        # Check required fields
        required = ["over", "ball", "batsman", "bowler", "runs", "is_wicket"]
        for field in required:
            if field not in delivery:
                errors.append(f"Delivery {i+1}: Missing required field '{field}'")
        
        # Validate over/ball numbers
        if "over" in delivery and delivery["over"] < 1:
            errors.append(f"Delivery {i+1}: Invalid over number {delivery['over']}")
        
        if "ball" in delivery and not (1 <= delivery["ball"] <= 6):
            errors.append(f"Delivery {i+1}: Invalid ball number {delivery['ball']}")
        
        # Validate runs
        if "runs" in delivery and not isinstance(delivery["runs"], int):
            errors.append(f"Delivery {i+1}: Runs must be an integer")
        
        if "runs" in delivery and delivery["runs"] < 0:
            errors.append(f"Delivery {i+1}: Negative runs not allowed")
    
    return len(errors) == 0, errors
