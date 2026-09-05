"""Session comparison service for Coach Phase 2.

Compares multiple analysis jobs within a session to show progress trends.
"""

from typing import Any

from backend.services.coach_analysis_v2_compatibility import compare_metric_results


def extract_metric_scores(findings: dict[str, Any] | None) -> dict[str, float]:
    """Extract metric scores from findings for comparison.

    Args:
        findings: Job findings with findings: [{code, metrics: {...}}, ...]

    Returns:
        Map of metric_code -> score
    """
    if not findings:
        return {}

    findings_list = findings.get("findings", [])
    if not findings_list:
        return {}

    scores = {}
    for finding in findings_list:
        code = finding.get("code")
        if not code:
            continue

        metrics = finding.get("metrics", {})

        # Try to extract a score from metrics
        for _metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict):
                if "score" in metric_val:
                    scores[code] = float(metric_val["score"])
                    break
                elif "value" in metric_val:
                    try:
                        scores[code] = float(metric_val["value"])
                        break
                    except (ValueError, TypeError):
                        pass

    return scores


def compare_jobs(job_rows: list[Any]) -> dict[str, Any]:
    """Compare multiple analysis jobs to show trends and improvements.

    Args:
        job_rows: List of VideoAnalysisJob objects sorted by completed_at/created_at

    Returns:
        Comparison payload: {
            timeline: [{timestamp, job_id, metric_scores: {code: score}}],
            deltas: [{from_job_id, to_job_id, improvements: [...], regressions: [...]}],
            persistent_issues: [{code, title, avg_score, trend: "declining"|"stable"|"improving"}]
        }
    """
    if not job_rows:
        return {
            "timeline": [],
            "deltas": [],
            "persistent_issues": [],
            "comparability": {
                "comparable": False,
                "state": "UNAVAILABLE",
                "reasons": ["No analysis jobs were supplied for comparison."],
                "comparable_metric_ids": [],
            },
        }

    # Build timeline
    timeline = []
    for job in job_rows:
        timestamp = job.completed_at or job.created_at
        metric_scores = extract_metric_scores(job.deep_findings)
        v2_metrics = _extract_v2_metrics(job)

        timeline.append(
            {
                "timestamp": timestamp.isoformat() if timestamp else None,
                "job_id": job.id,
                "analysis_mode": job.analysis_mode,
                "metric_scores": metric_scores,
                "comparability": {
                    "has_v2_metrics": bool(v2_metrics),
                    "metric_ids": sorted(v2_metrics.keys()),
                },
            }
        )

    # Calculate deltas between consecutive jobs
    deltas = []
    for i in range(len(timeline) - 1):
        from_job = timeline[i]
        to_job = timeline[i + 1]
        pair_comparability = _evaluate_job_pair_comparability(job_rows[i], job_rows[i + 1])

        if not pair_comparability["comparable"]:
            deltas.append(
                {
                    "from_job_id": from_job["job_id"],
                    "to_job_id": to_job["job_id"],
                    "improvements": [],
                    "regressions": [],
                    "comparability": pair_comparability,
                }
            )
            continue

        from_scores = from_job["metric_scores"]
        to_scores = to_job["metric_scores"]

        # Find common metrics
        common_codes = set(from_scores.keys()) & set(to_scores.keys())

        improvements = []
        regressions = []

        for code in common_codes:
            from_score = from_scores[code]
            to_score = to_scores[code]
            delta = to_score - from_score

            if delta > 0.05:  # Threshold for meaningful improvement
                improvements.append(
                    {
                        "code": code,
                        "from_score": round(from_score, 3),
                        "to_score": round(to_score, 3),
                        "delta": round(delta, 3),
                    }
                )
            elif delta < -0.05:  # Threshold for meaningful regression
                regressions.append(
                    {
                        "code": code,
                        "from_score": round(from_score, 3),
                        "to_score": round(to_score, 3),
                        "delta": round(delta, 3),
                    }
                )

        deltas.append(
            {
                "from_job_id": from_job["job_id"],
                "to_job_id": to_job["job_id"],
                "improvements": improvements,
                "regressions": regressions,
                "comparability": pair_comparability,
            }
        )

    # Identify persistent issues
    # Metrics that appear in ALL jobs with consistently low scores
    persistent_issues: list[dict[str, Any]] = []
    overall_comparability = _evaluate_job_series_comparability(job_rows)
    if len(timeline) >= 2 and overall_comparability["comparable"]:
        # Find codes that appear in all jobs
        all_codes_sets = [set(t["metric_scores"].keys()) for t in timeline]
        common_codes_all = set.intersection(*all_codes_sets) if all_codes_sets else set()

        for code in common_codes_all:
            scores = [t["metric_scores"][code] for t in timeline]
            avg_score = sum(scores) / len(scores)

            # Only flag as persistent if avg score is below threshold
            if avg_score < 0.60:  # Below "acceptable" threshold
                # Determine trend
                if len(scores) >= 2:
                    first_half_avg = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
                    second_half_avg = sum(scores[len(scores) // 2 :]) / (
                        len(scores) - len(scores) // 2
                    )

                    if second_half_avg > first_half_avg + 0.05:
                        trend = "improving"
                    elif second_half_avg < first_half_avg - 0.05:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"

                persistent_issues.append(
                    {
                        "code": code,
                        "title": code.replace("_", " ").title(),
                        "avg_score": round(avg_score, 3),
                        "trend": trend,
                        "occurrences": len(scores),
                    }
                )

    return {
        "timeline": timeline,
        "deltas": deltas,
        "persistent_issues": persistent_issues,
        "comparability": overall_comparability,
    }


def _extract_v2_metrics(job: Any) -> dict[str, dict[str, Any]]:
    payloads = [
        getattr(job, "deep_results", None),
        getattr(job, "quick_results", None),
        getattr(job, "results", None),
    ]
    for payload in payloads:
        candidate = payload
        if isinstance(candidate, dict) and isinstance(candidate.get("deep"), dict):
            candidate = candidate["deep"]
        elif isinstance(candidate, dict) and isinstance(candidate.get("quick"), dict):
            candidate = candidate["quick"]
        if not isinstance(candidate, dict):
            continue
        metric_results = candidate.get("v2", {}).get("metric_results")
        if not isinstance(metric_results, list):
            continue
        metrics = {
            str(item.get("metric_id")): item
            for item in metric_results
            if isinstance(item, dict) and isinstance(item.get("metric_id"), str)
        }
        if metrics:
            return metrics
    return {}


def _evaluate_job_pair_comparability(left_job: Any, right_job: Any) -> dict[str, Any]:
    if getattr(left_job, "analysis_mode", None) != getattr(right_job, "analysis_mode", None):
        return {
            "comparable": False,
            "state": "NON_COMPARABLE",
            "reasons": ["Analysis modes do not match."],
            "comparable_metric_ids": [],
        }

    left_metrics = _extract_v2_metrics(left_job)
    right_metrics = _extract_v2_metrics(right_job)
    if not left_metrics or not right_metrics:
        return {
            "comparable": False,
            "state": "UNKNOWN",
            "reasons": [
                "V2 metric metadata is unavailable, so safe comparison could not be established."
            ],
            "comparable_metric_ids": [],
        }

    comparable_metric_ids: list[str] = []
    reasons: list[str] = []
    for metric_id in sorted(set(left_metrics) & set(right_metrics)):
        eligibility = compare_metric_results(
            left_metrics[metric_id],
            right_metrics[metric_id],
            player_id_left=getattr(left_job, "player_id", None),
            player_id_right=getattr(right_job, "player_id", None),
        )
        if eligibility.comparable:
            comparable_metric_ids.append(metric_id)
            continue
        for reason in eligibility.reasons:
            if reason not in reasons:
                reasons.append(reason)

    return {
        "comparable": bool(comparable_metric_ids),
        "state": "COMPARABLE" if comparable_metric_ids else "NON_COMPARABLE",
        "reasons": reasons or (["No directly comparable V2 metrics were shared across both jobs."]),
        "comparable_metric_ids": comparable_metric_ids,
    }


def _evaluate_job_series_comparability(job_rows: list[Any]) -> dict[str, Any]:
    if len(job_rows) < 2:
        return {
            "comparable": False,
            "state": "UNAVAILABLE",
            "reasons": ["At least two jobs are required for comparison."],
            "comparable_metric_ids": [],
        }

    pair_results = [
        _evaluate_job_pair_comparability(job_rows[index], job_rows[index + 1])
        for index in range(len(job_rows) - 1)
    ]
    comparable_metric_ids = sorted(
        {metric_id for pair in pair_results for metric_id in pair.get("comparable_metric_ids", [])}
    )
    reasons: list[str] = []
    for pair in pair_results:
        for reason in pair.get("reasons", []):
            if reason not in reasons:
                reasons.append(reason)
    return {
        "comparable": all(pair.get("comparable", False) for pair in pair_results),
        "state": (
            "COMPARABLE"
            if pair_results and all(pair.get("comparable", False) for pair in pair_results)
            else "NON_COMPARABLE"
        ),
        "reasons": reasons,
        "comparable_metric_ids": comparable_metric_ids,
    }
