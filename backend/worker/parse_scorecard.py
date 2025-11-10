"""
Scorecard parser for converting OCR text to delivery data.

This is a PROTOTYPE parser using simple rule-based extraction.
In production, this should be enhanced with more sophisticated
parsing logic or ML-based extraction.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_scorecard_text(ocr_text: str) -> dict[str, Any]:
    """
    Parse OCR text and extract delivery information.
    
    This is a best-effort prototype parser that uses simple pattern
    matching to extract deliveries from scorecard text. It should be
    enhanced with more sophisticated parsing for production use.
    
    Args:
        ocr_text: Raw text from OCR engine
    
    Returns:
        Dict with 'deliveries' list and metadata
    """
    deliveries: list[dict[str, Any]] = []
    
    # Split text into lines
    lines = ocr_text.strip().split("\n")
    
    # Simple pattern matching for delivery data
    # Pattern: Over Ball Bowler Batsman Runs Wicket
    # Example: "1.1 Smith Jones 4 No"
    delivery_pattern = re.compile(
        r"(\d+)\.(\d+)\s+(\w+(?:\s+\w+)?)\s+(\w+(?:\s+\w+)?)\s+(\d+)\s+(Yes|No|wicket|out|W)?",
        re.IGNORECASE
    )
    
    for line in lines:
        match = delivery_pattern.search(line)
        if match:
            over_num = int(match.group(1))
            ball_num = int(match.group(2))
            bowler = match.group(3).strip()
            batsman = match.group(4).strip()
            runs = int(match.group(5))
            wicket_text = match.group(6) or ""
            
            is_wicket = bool(
                wicket_text and wicket_text.lower() in ["yes", "wicket", "out", "w"]
            )
            
            delivery = {
                "over": over_num,
                "ball": ball_num,
                "bowler": bowler,
                "batsman": batsman,
                "runs": runs,
                "is_wicket": is_wicket,
                "extras": 0,
            }
            
            deliveries.append(delivery)
            logger.debug(f"Parsed delivery: {delivery}")
    
    # If no deliveries found with strict pattern, try to extract some basic info
    if not deliveries:
        logger.warning("No deliveries found with pattern matching, using fallback")
        # Fallback: Look for common cricket scoring patterns
        # This is very basic and should be improved
        run_mentions = re.findall(r"(\d+)\s*runs?", ocr_text, re.IGNORECASE)
        if run_mentions:
            # Create synthetic deliveries for testing purposes
            for i, runs_str in enumerate(run_mentions[:20]):  # Limit to 20
                deliveries.append({
                    "over": (i // 6) + 1,
                    "ball": (i % 6) + 1,
                    "bowler": "Unknown Bowler",
                    "batsman": "Unknown Batsman",
                    "runs": int(runs_str),
                    "is_wicket": False,
                    "extras": 0,
                })
    
    result = {
        "deliveries": deliveries,
        "metadata": {
            "total_deliveries": len(deliveries),
            "ocr_length": len(ocr_text),
            "parser_version": "prototype_v1",
        },
    }
    
    logger.info(f"Parsed {len(deliveries)} deliveries from OCR text")
    return result


def validate_parsed_deliveries(parsed_data: dict[str, Any]) -> list[str]:
    """
    Validate parsed delivery data and return list of issues/warnings.
    
    Args:
        parsed_data: Parsed data from parse_scorecard_text
    
    Returns:
        List of validation warnings (empty if all valid)
    """
    warnings: list[str] = []
    deliveries = parsed_data.get("deliveries", [])
    
    if not deliveries:
        warnings.append("No deliveries found in parsed data")
        return warnings
    
    # Check for sequential overs
    prev_over = 0
    for i, delivery in enumerate(deliveries):
        over_num = delivery.get("over", 0)
        ball_num = delivery.get("ball", 0)
        
        # Check ball number is valid (1-6)
        if ball_num < 1 or ball_num > 6:
            warnings.append(f"Delivery {i+1}: Invalid ball number {ball_num}")
        
        # Check overs are sequential
        if over_num < prev_over:
            warnings.append(f"Delivery {i+1}: Non-sequential over number {over_num}")
        
        prev_over = over_num
        
        # Check required fields
        if not delivery.get("bowler"):
            warnings.append(f"Delivery {i+1}: Missing bowler")
        if not delivery.get("batsman"):
            warnings.append(f"Delivery {i+1}: Missing batsman")
    
    return warnings
