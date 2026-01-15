"""Session comparison service for Coach Phase 2.

Compares multiple analysis jobs within a session to show progress trends.
"""

from typing import Any


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
        for metric_name, metric_val in metrics.items():
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
        }
    
    # Build timeline
    timeline = []
    for job in job_rows:
        timestamp = job.completed_at or job.created_at
        metric_scores = extract_metric_scores(job.deep_findings)
        
        timeline.append({
            "timestamp": timestamp.isoformat() if timestamp else None,
            "job_id": job.id,
            "analysis_mode": job.analysis_mode,
            "metric_scores": metric_scores,
        })
    
    # Calculate deltas between consecutive jobs
    deltas = []
    for i in range(len(timeline) - 1):
        from_job = timeline[i]
        to_job = timeline[i + 1]
        
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
                improvements.append({
                    "code": code,
                    "from_score": round(from_score, 3),
                    "to_score": round(to_score, 3),
                    "delta": round(delta, 3),
                })
            elif delta < -0.05:  # Threshold for meaningful regression
                regressions.append({
                    "code": code,
                    "from_score": round(from_score, 3),
                    "to_score": round(to_score, 3),
                    "delta": round(delta, 3),
                })
        
        deltas.append({
            "from_job_id": from_job["job_id"],
            "to_job_id": to_job["job_id"],
            "improvements": improvements,
            "regressions": regressions,
        })
    
    # Identify persistent issues
    # Metrics that appear in ALL jobs with consistently low scores
    persistent_issues: list[dict[str, Any]] = []
    if len(timeline) >= 2:
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
                
                persistent_issues.append({
                    "code": code,
                    "title": code.replace("_", " ").title(),
                    "avg_score": round(avg_score, 3),
                    "trend": trend,
                    "occurrences": len(scores),
                })
    
    return {
        "timeline": timeline,
        "deltas": deltas,
        "persistent_issues": persistent_issues,
    }
