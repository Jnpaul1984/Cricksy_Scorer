"""Goal compliance calculation service for Coach Phase 2.

Compares coach-defined goals against actual analysis outcomes.
Supports zone accuracy goals and metric performance goals across all analysis modes.
"""

from typing import Any


def is_point_in_rect(x: float, y: float, rect: dict[str, float]) -> bool:
    """Check if normalized point (x,y) is inside rectangle."""
    x_min = rect.get("x", 0.0)
    y_min = rect.get("y", 0.0)
    width = rect.get("width", 0.0)
    height = rect.get("height", 0.0)

    return x_min <= x <= (x_min + width) and y_min <= y <= (y_min + height)


def is_point_in_circle(x: float, y: float, circle: dict[str, float]) -> bool:
    """Check if normalized point (x,y) is inside circle."""
    cx = circle.get("cx", 0.5)
    cy = circle.get("cy", 0.5)
    r = circle.get("r", 0.1)

    dx = x - cx
    dy = y - cy
    dist_sq = dx * dx + dy * dy
    return dist_sq <= (r * r)


def is_point_in_polygon(x: float, y: float, polygon: dict[str, Any]) -> bool:
    """Check if normalized point (x,y) is inside polygon using ray casting."""
    points = polygon.get("points", [])
    if len(points) < 3:
        return False

    n = len(points)
    inside = False

    p1x, p1y = points[0]["x"], points[0]["y"]
    for i in range(1, n + 1):
        p2x, p2y = points[i % n]["x"], points[i % n]["y"]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def is_point_in_zone(x: float, y: float, zone: dict[str, Any]) -> bool:
    """Check if normalized point (x,y) is inside a target zone."""
    shape = zone.get("shape", "rect")
    definition = zone.get("definition_json", {})

    if shape == "rect":
        return is_point_in_rect(x, y, definition)
    elif shape == "circle":
        return is_point_in_circle(x, y, definition)
    elif shape == "polygon":
        return is_point_in_polygon(x, y, definition)
    else:
        return False


def calculate_zone_compliance(
    deep_results: dict[str, Any] | None,
    goals: dict[str, Any],
    zones_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calculate zone accuracy compliance for bowling analysis.

    Args:
        deep_results: Deep analysis results with ball_tracking.bounces
        goals: Coach goals with zones: [{zone_id, target_accuracy}, ...]
        zones_lookup: Map of zone_id -> {id, name, shape, definition_json}

    Returns:
        List of zone compliance results:
        [{zone_id, zone_name, target_accuracy, actual_accuracy, pass, delta}, ...]
    """
    zone_goals = goals.get("zones", [])
    if not zone_goals or not deep_results:
        return []

    # Extract ball bounces from deep_results
    ball_tracking = deep_results.get("ball_tracking", {})
    bounces = ball_tracking.get("bounces", [])

    if not bounces:
        # No bounces detected - all zones fail
        return [
            {
                "zone_id": zg["zone_id"],
                "zone_name": zones_lookup.get(zg["zone_id"], {}).get("name", "Unknown"),
                "target_accuracy": zg["target_accuracy"],
                "actual_accuracy": 0.0,
                "pass": False,
                "delta": -zg["target_accuracy"],
            }
            for zg in zone_goals
        ]

    results = []
    for zone_goal in zone_goals:
        zone_id = zone_goal["zone_id"]
        target_accuracy = zone_goal["target_accuracy"]

        zone_def = zones_lookup.get(zone_id)
        if not zone_def:
            # Zone not found - skip
            continue

        # Count bounces in this zone
        hits = 0
        for bounce in bounces:
            x_norm = bounce.get("x_normalized", bounce.get("x", 0.5))
            y_norm = bounce.get("y_normalized", bounce.get("y", 0.5))

            if is_point_in_zone(x_norm, y_norm, zone_def):
                hits += 1

        actual_accuracy = hits / len(bounces) if bounces else 0.0
        passed = actual_accuracy >= target_accuracy
        delta = actual_accuracy - target_accuracy

        results.append(
            {
                "zone_id": zone_id,
                "zone_name": zone_def.get("name", "Unknown"),
                "target_accuracy": target_accuracy,
                "actual_accuracy": round(actual_accuracy, 3),
                "pass": passed,
                "delta": round(delta, 3),
            }
        )

    return results


def calculate_metric_compliance(
    findings: dict[str, Any] | None, goals: dict[str, Any]
) -> list[dict[str, Any]]:
    """Calculate metric performance compliance.

    Args:
        findings: Deep findings with findings: [{code, title, metrics: {...}}, ...]
        goals: Coach goals with metrics: [{code, target_score}, ...]

    Returns:
        List of metric compliance results:
        [{code, title, target_score, actual_score, pass, delta}, ...]
    """
    metric_goals = goals.get("metrics", [])
    if not metric_goals:
        return []

    findings_list = findings.get("findings", []) if findings else []

    # Build lookup from findings: code -> finding
    findings_map = {f["code"]: f for f in findings_list if "code" in f}

    results = []
    for metric_goal in metric_goals:
        code = metric_goal["code"]
        target_score = metric_goal["target_score"]

        finding = findings_map.get(code)
        if not finding:
            # Finding not present - treat as 0 score (failure)
            results.append(
                {
                    "code": code,
                    "title": code.replace("_", " ").title(),
                    "target_score": target_score,
                    "actual_score": 0.0,
                    "pass": False,
                    "delta": -target_score,
                }
            )
            continue

        # Extract score from finding.metrics
        # Metrics structure: {metric_name: {score, ...}, ...}
        metrics = finding.get("metrics", {})

        # Try to find a score value - check first metric or use detection_rate
        actual_score = 0.0

        # Strategy 1: Look for explicit score key in any metric
        for _metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict) and "score" in metric_val:
                actual_score = float(metric_val["score"])
                break
            elif isinstance(metric_val, dict) and "value" in metric_val:
                # Some metrics use "value" instead
                try:
                    actual_score = float(metric_val["value"])
                    break
                except (ValueError, TypeError):
                    pass

        # Strategy 2: If no score found, try detection_rate from findings root
        if actual_score == 0.0 and findings is not None:
            detection_rate = findings.get("detection_rate", 0.0)
            if detection_rate > 0.0:
                actual_score = detection_rate

        passed = actual_score >= target_score
        delta = actual_score - target_score

        results.append(
            {
                "code": code,
                "title": finding.get("title", code.replace("_", " ").title()),
                "target_score": target_score,
                "actual_score": round(actual_score, 3),
                "pass": passed,
                "delta": round(delta, 3),
            }
        )

    return results


def calculate_compliance(job: Any, zones_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Calculate overall compliance for a job with goals.

    Args:
        job: VideoAnalysisJob with coach_goals, deep_results, deep_findings
        zones_lookup: Map of zone_id -> zone definition

    Returns:
        Outcomes dict: {
            zones: [...],
            metrics: [...],
            overall_compliance_pct: float
        }
    """
    coach_goals = job.coach_goals
    if not coach_goals:
        return {"zones": [], "metrics": [], "overall_compliance_pct": 0.0}

    # Calculate zone compliance
    zone_results = calculate_zone_compliance(job.deep_results, coach_goals, zones_lookup)

    # Calculate metric compliance
    metric_results = calculate_metric_compliance(job.deep_findings, coach_goals)

    # Calculate overall compliance percentage
    total_goals = len(zone_results) + len(metric_results)
    if total_goals == 0:
        overall_pct = 0.0
    else:
        passed_goals = sum(1 for zr in zone_results if zr["pass"]) + sum(
            1 for mr in metric_results if mr["pass"]
        )
        overall_pct = (passed_goals / total_goals) * 100.0

    return {
        "zones": zone_results,
        "metrics": metric_results,
        "overall_compliance_pct": round(overall_pct, 1),
    }
