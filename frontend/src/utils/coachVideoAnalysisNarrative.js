import { normalizeCoachVideoAnalysis } from '@/utils/coachVideoAnalysisNormalize';
function isObject(value) {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}
function pickFirstObject(...values) {
    for (const v of values) {
        if (isObject(v))
            return v;
    }
    return null;
}
function toNonEmptyString(value) {
    if (typeof value !== 'string')
        return null;
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
}
function safeText(value, fallback) {
    return toNonEmptyString(value) ?? fallback;
}
function clamp01(value) {
    if (value < 0)
        return 0;
    if (value > 1)
        return 1;
    return value;
}
function coerceSeverity(value) {
    const v = toNonEmptyString(value)?.toLowerCase() ?? '';
    if (v === 'high' ||
        v === 'critical' ||
        v === 'severe' ||
        v === 'danger' ||
        v === 'error') {
        return 'high';
    }
    if (v === 'medium' || v === 'moderate' || v === 'warning' || v === 'warn') {
        return 'medium';
    }
    return 'low';
}
function ratingFromSeverities(severities, jobStatus) {
    if (jobStatus === 'failed')
        return 'High Risk';
    if (severities.includes('high'))
        return 'High Risk';
    if (severities.includes('medium'))
        return 'Needs Improvement';
    return 'Solid';
}
function impactTextForSeverity(severity) {
    if (severity === 'high') {
        return 'Impact: High — this can significantly reduce consistency and control under pressure.';
    }
    if (severity === 'medium') {
        return 'Impact: Medium — fixing this should improve repeatability and timing.';
    }
    return 'Impact: Low — a small improvement that can add polish and efficiency.';
}
function confidenceText(jobStatus, detectionRate01, framesAnalyzed) {
    if (jobStatus === 'queued' ||
        jobStatus === 'processing' ||
        jobStatus === 'quick_running' ||
        jobStatus === 'quick_done' ||
        jobStatus === 'deep_running') {
        return 'Confidence: Analysis is running — results will update automatically.';
    }
    if (jobStatus === 'failed') {
        return 'Confidence: Not available — analysis did not complete successfully.';
    }
    if (detectionRate01 == null || framesAnalyzed == null) {
        return 'Confidence: Limited — not enough data was returned to judge reliability.';
    }
    const dr = clamp01(detectionRate01);
    if (framesAnalyzed >= 60 && dr >= 0.8)
        return 'Confidence: High — strong coverage and a good sample size.';
    if (framesAnalyzed >= 30 && dr >= 0.65)
        return 'Confidence: Medium — good signal, but more data improves certainty.';
    return 'Confidence: Low — coverage/sample size is limited; interpret carefully.';
}
function coverageText(jobStatus, detectionRate01, framesAnalyzed, totalFrames) {
    if (jobStatus === 'queued' ||
        jobStatus === 'processing' ||
        jobStatus === 'quick_running' ||
        jobStatus === 'quick_done' ||
        jobStatus === 'deep_running') {
        return 'Coverage: Not available yet (analysis in progress).';
    }
    if (jobStatus === 'failed') {
        return 'Coverage: Not available (analysis failed).';
    }
    const parts = [];
    if (typeof framesAnalyzed === 'number') {
        if (typeof totalFrames === 'number') {
            parts.push(`Frames analyzed: ${framesAnalyzed} of ${totalFrames}.`);
        }
        else {
            parts.push(`Frames analyzed: ${framesAnalyzed}.`);
        }
    }
    else {
        parts.push('Frames analyzed: —.');
    }
    if (typeof detectionRate01 === 'number') {
        const pct = Math.round(clamp01(detectionRate01) * 100);
        parts.push(`Pose detection coverage: ~${pct}%.`);
    }
    else {
        parts.push('Pose detection coverage: —.');
    }
    return parts.join(' ');
}
function uniqueStrings(values, limit) {
    const out = [];
    const seen = new Set();
    for (const v of values) {
        const s = toNonEmptyString(v);
        if (!s)
            continue;
        if (seen.has(s))
            continue;
        seen.add(s);
        out.push(s);
        if (out.length >= limit)
            break;
    }
    return out;
}
function extractPriorities(resultsObj) {
    if (!resultsObj)
        return [];
    const coachObj = pickFirstObject(resultsObj['coach']);
    const findingsRaw = (resultsObj['findings'] ?? coachObj?.['findings'] ?? null);
    const evidenceRaw = (resultsObj['evidence'] ?? resultsObj?.metrics?.['evidence'] ?? null);
    const evidenceObj = pickFirstObject(evidenceRaw);
    const priorities = [];
    // Backend MVP shape: { findings: [{ code, title, severity, why_it_matters, cues, suggested_drills, evidence? }] }
    const findingsObjBackend = pickFirstObject(findingsRaw);
    const findingsList = Array.isArray(findingsObjBackend?.['findings'])
        ? findingsObjBackend?.['findings']
        : [];
    const codeToMetricKey = {
        HEAD_MOVEMENT: 'head_stability_score',
        BALANCE_DRIFT: 'balance_drift_score',
        KNEE_COLLAPSE: 'front_knee_brace_score',
        ROTATION_TIMING: 'hip_shoulder_separation_timing',
        ELBOW_DROP: 'elbow_drop_score',
    };
    if (findingsList.length) {
        for (const f of findingsList) {
            if (!isObject(f))
                continue;
            const code = safeText(f['code'], 'TECHNIQUE');
            const metricKey = codeToMetricKey[code] ?? code.toLowerCase();
            const title = safeText(f['title'], 'Technique priority');
            const severity = coerceSeverity(f['severity']);
            const why = toNonEmptyString(f['why_it_matters']);
            const cues = Array.isArray(f['cues']) ? uniqueStrings(f['cues'], 3) : [];
            const drills = Array.isArray(f['suggested_drills'])
                ? uniqueStrings(f['suggested_drills'], 5)
                : [];
            const explanationParts = [];
            if (why)
                explanationParts.push(`Why it matters: ${why}`);
            if (cues.length)
                explanationParts.push(`What to do: ${cues.join(' ')}.`);
            if (!explanationParts.length) {
                explanationParts.push('Why it matters: Improving this will help you repeat your best movement more often. What to do: Pick one clear cue and repeat it consistently.');
            }
            const evidenceForMetric = pickFirstObject(evidenceObj?.[metricKey]);
            const worstFramesRaw = Array.isArray(evidenceForMetric?.['worst_frames'])
                ? evidenceForMetric?.['worst_frames']
                : [];
            const badSegmentsRaw = Array.isArray(evidenceForMetric?.['bad_segments'])
                ? evidenceForMetric?.['bad_segments']
                : [];
            const worstFrames = worstFramesRaw
                .map((w) => (isObject(w) ? w : null))
                .filter((w) => !!w)
                .map((w) => {
                const frameNum = typeof w['frame_num'] === 'number' ? w['frame_num'] : Number(w['frame_num']);
                const timeSeconds = typeof w['timestamp_s'] === 'number' ? w['timestamp_s'] : Number(w['timestamp_s']);
                const score = typeof w['score'] === 'number' ? w['score'] : Number(w['score']);
                return {
                    frameNum: Number.isFinite(frameNum) ? Math.round(frameNum) : 0,
                    ...(Number.isFinite(timeSeconds) ? { timeSeconds } : {}),
                    ...(Number.isFinite(score) ? { score } : {}),
                };
            })
                .filter((w) => w.frameNum > 0);
            const badSegments = badSegmentsRaw
                .map((s) => (isObject(s) ? s : null))
                .filter((s) => !!s)
                .map((s) => {
                const startFrame = typeof s['start_frame'] === 'number' ? s['start_frame'] : Number(s['start_frame']);
                const endFrame = typeof s['end_frame'] === 'number' ? s['end_frame'] : Number(s['end_frame']);
                const startSeconds = typeof s['start_timestamp_s'] === 'number' ? s['start_timestamp_s'] : Number(s['start_timestamp_s']);
                const endSeconds = typeof s['end_timestamp_s'] === 'number' ? s['end_timestamp_s'] : Number(s['end_timestamp_s']);
                const minScore = typeof s['min_score'] === 'number' ? s['min_score'] : Number(s['min_score']);
                return {
                    startFrame: Number.isFinite(startFrame) ? Math.round(startFrame) : 0,
                    endFrame: Number.isFinite(endFrame) ? Math.round(endFrame) : 0,
                    ...(Number.isFinite(startSeconds) ? { startSeconds } : {}),
                    ...(Number.isFinite(endSeconds) ? { endSeconds } : {}),
                    ...(Number.isFinite(minScore) ? { minScore } : {}),
                };
            })
                .filter((s) => s.startFrame > 0 && s.endFrame > 0);
            const threshold = typeof evidenceForMetric?.['threshold'] === 'number'
                ? evidenceForMetric?.['threshold']
                : undefined;
            priorities.push({
                key: metricKey,
                title,
                severity,
                explanation: explanationParts.join(' '),
                impact: impactTextForSeverity(severity),
                drills,
                ...(worstFrames.length || badSegments.length
                    ? {
                        evidence: {
                            ...(typeof threshold === 'number' ? { threshold } : {}),
                            worstFrames,
                            badSegments,
                        },
                    }
                    : {}),
            });
        }
        // Order: high → medium → low
        const rank = { high: 0, medium: 1, low: 2 };
        priorities.sort((a, b) => rank[a.severity] - rank[b.severity]);
        return priorities;
    }
    // Supported shape: { key_findings: [{ title, why, fix, drills, severity }] }
    const findingsObj = pickFirstObject(findingsRaw);
    const keyFindings = Array.isArray(findingsObj?.['key_findings'])
        ? findingsObj?.['key_findings']
        : [];
    for (const f of keyFindings) {
        if (!isObject(f))
            continue;
        const title = safeText(f['title'] ?? f['name'], 'Technique priority');
        const key = safeText(f['key'], title.toLowerCase().replace(/\s+/g, '_'));
        const severity = coerceSeverity(f['severity'] ?? f['level'] ?? f['priority']);
        const explanation = toNonEmptyString(f['explanation']) ??
            (toNonEmptyString(f['why']) ? `Why it matters: ${String(f['why'])}` : null) ??
            'Why it matters: Improving this will help you repeat your best movement more often.';
        const whatToFix = toNonEmptyString(f['fix'])
            ? `What to do: ${String(f['fix'])}`
            : 'What to do: Use one simple cue and repeat it consistently in practice.';
        const drills = Array.isArray(f['drills']) ? uniqueStrings(f['drills'], 5) : [];
        const evidenceForMetric = pickFirstObject(evidenceObj?.[key]);
        const worstFramesRaw = Array.isArray(evidenceForMetric?.['worst_frames'])
            ? evidenceForMetric?.['worst_frames']
            : [];
        const badSegmentsRaw = Array.isArray(evidenceForMetric?.['bad_segments'])
            ? evidenceForMetric?.['bad_segments']
            : [];
        const worstFrames = worstFramesRaw
            .map((w) => (isObject(w) ? w : null))
            .filter((w) => !!w)
            .map((w) => {
            const frameNum = typeof w['frame_num'] === 'number' ? w['frame_num'] : Number(w['frame_num']);
            const timeSeconds = typeof w['timestamp_s'] === 'number' ? w['timestamp_s'] : Number(w['timestamp_s']);
            const score = typeof w['score'] === 'number' ? w['score'] : Number(w['score']);
            return {
                frameNum: Number.isFinite(frameNum) ? Math.round(frameNum) : 0,
                ...(Number.isFinite(timeSeconds) ? { timeSeconds } : {}),
                ...(Number.isFinite(score) ? { score } : {}),
            };
        })
            .filter((w) => w.frameNum > 0);
        const badSegments = badSegmentsRaw
            .map((s) => (isObject(s) ? s : null))
            .filter((s) => !!s)
            .map((s) => {
            const startFrame = typeof s['start_frame'] === 'number' ? s['start_frame'] : Number(s['start_frame']);
            const endFrame = typeof s['end_frame'] === 'number' ? s['end_frame'] : Number(s['end_frame']);
            const startSeconds = typeof s['start_timestamp_s'] === 'number' ? s['start_timestamp_s'] : Number(s['start_timestamp_s']);
            const endSeconds = typeof s['end_timestamp_s'] === 'number' ? s['end_timestamp_s'] : Number(s['end_timestamp_s']);
            const minScore = typeof s['min_score'] === 'number' ? s['min_score'] : Number(s['min_score']);
            return {
                startFrame: Number.isFinite(startFrame) ? Math.round(startFrame) : 0,
                endFrame: Number.isFinite(endFrame) ? Math.round(endFrame) : 0,
                ...(Number.isFinite(startSeconds) ? { startSeconds } : {}),
                ...(Number.isFinite(endSeconds) ? { endSeconds } : {}),
                ...(Number.isFinite(minScore) ? { minScore } : {}),
            };
        })
            .filter((s) => s.startFrame > 0 && s.endFrame > 0);
        const threshold = typeof evidenceForMetric?.['threshold'] === 'number'
            ? evidenceForMetric?.['threshold']
            : undefined;
        priorities.push({
            key,
            title,
            severity,
            explanation: `${explanation} ${whatToFix}`,
            impact: impactTextForSeverity(severity),
            drills,
            ...(worstFrames.length || badSegments.length
                ? {
                    evidence: {
                        ...(typeof threshold === 'number' ? { threshold } : {}),
                        worstFrames,
                        badSegments,
                    },
                }
                : {}),
        });
    }
    // Fallback: if findings is an array of strings, treat as medium priorities.
    if (priorities.length === 0 && Array.isArray(findingsRaw)) {
        const items = uniqueStrings(findingsRaw, 3);
        for (const item of items) {
            priorities.push({
                key: item.toLowerCase().replace(/\s+/g, '_'),
                title: item,
                severity: 'medium',
                explanation: 'Why it matters: Small inefficiencies add up across innings. What to do: Pick one clear cue and repeat it consistently.',
                impact: impactTextForSeverity('medium'),
                drills: [],
            });
        }
    }
    // Order: high → medium → low
    const rank = { high: 0, medium: 1, low: 2 };
    priorities.sort((a, b) => rank[a.severity] - rank[b.severity]);
    return priorities;
}
function extractCoachSummaryText(resultsObj, jobStatus, errorMessage) {
    if (jobStatus === 'queued' ||
        jobStatus === 'processing' ||
        jobStatus === 'quick_running' ||
        jobStatus === 'quick_done' ||
        jobStatus === 'deep_running') {
        return 'Analysis is in progress. Keep this screen open — results will populate automatically.';
    }
    if (jobStatus === 'failed') {
        const err = errorMessage ? ` Reason: ${errorMessage}` : '';
        return `Analysis failed to complete.${err} You can retry the upload or try a shorter clip.`;
    }
    if (!resultsObj) {
        return 'Analysis completed, but no results were returned. You can retry or check back later.';
    }
    const coachObj = pickFirstObject(resultsObj['coach']);
    const reportObj = pickFirstObject(resultsObj['report'], coachObj?.['report']);
    const summary = toNonEmptyString(reportObj?.['summary']);
    return summary ?? 'Summary: Review priorities below and focus on one cue at a time.';
}
export function buildCoachNarrative(analysisJob) {
    const jobStatus = analysisJob?.status ?? 'unknown';
    const errorMessage = toNonEmptyString(analysisJob?.error_message) ?? null;
    // Reuse the existing normalizer for stable numeric extraction.
    const normalized = normalizeCoachVideoAnalysis(analysisJob);
    const totalFrames = normalized.numbers.totalFrames ?? undefined;
    const framesAnalyzed = normalized.numbers.sampledFrames ?? undefined;
    const detectionRate = normalized.numbers.detectionRate ?? undefined;
    const bestResults = (analysisJob?.deep_results ?? analysisJob?.quick_results ?? analysisJob?.results ?? null);
    const resultsObj = pickFirstObject(bestResults);
    const priorities = extractPriorities(resultsObj);
    const rating = ratingFromSeverities(priorities.map((p) => p.severity), jobStatus);
    const summaryText = extractCoachSummaryText(resultsObj, jobStatus, errorMessage);
    return {
        summary: {
            rating,
            confidenceText: confidenceText(jobStatus, detectionRate, framesAnalyzed),
            coverageText: coverageText(jobStatus, detectionRate, framesAnalyzed, totalFrames),
            coachSummaryText: summaryText,
        },
        priorities,
        metrics: {
            ...(typeof framesAnalyzed === 'number' ? { framesAnalyzed } : {}),
            ...(typeof totalFrames === 'number' ? { totalFrames } : {}),
            ...(typeof detectionRate === 'number' ? { detectionRate: clamp01(detectionRate) } : {}),
        },
    };
}
