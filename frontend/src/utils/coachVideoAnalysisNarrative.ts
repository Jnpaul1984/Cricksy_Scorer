import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import { normalizeCoachVideoAnalysis } from '@/utils/coachVideoAnalysisNormalize';

export type CoachNarrativeRating = 'Needs Improvement' | 'Solid' | 'High Risk';
export type CoachNarrativeSeverity = 'low' | 'medium' | 'high';

export type CoachNarrative = {
  summary: {
    rating: CoachNarrativeRating;
    confidenceText: string;
    coverageText: string;
    coachSummaryText: string;
  };
  priorities: Array<{
    key: string;
    title: string;
    severity: CoachNarrativeSeverity;
    explanation: string;
    impact: string;
    drills: string[];
  }>;
  metrics: {
    framesAnalyzed?: number;
    totalFrames?: number;
    detectionRate?: number;
  };
};

type AnyObj = Record<string, unknown>;

function isObject(value: unknown): value is AnyObj {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function pickFirstObject(...values: unknown[]): AnyObj | null {
  for (const v of values) {
    if (isObject(v)) return v;
  }
  return null;
}

function toNonEmptyString(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function safeText(value: unknown, fallback: string): string {
  return toNonEmptyString(value) ?? fallback;
}

function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function coerceSeverity(value: unknown): CoachNarrativeSeverity {
  const v = toNonEmptyString(value)?.toLowerCase() ?? '';
  if (
    v === 'high' ||
    v === 'critical' ||
    v === 'severe' ||
    v === 'danger' ||
    v === 'error'
  ) {
    return 'high';
  }
  if (v === 'medium' || v === 'moderate' || v === 'warning' || v === 'warn') {
    return 'medium';
  }
  return 'low';
}

function ratingFromSeverities(severities: CoachNarrativeSeverity[], jobStatus: string): CoachNarrativeRating {
  if (jobStatus === 'failed') return 'High Risk';
  if (severities.includes('high')) return 'High Risk';
  if (severities.includes('medium')) return 'Needs Improvement';
  return 'Solid';
}

function impactTextForSeverity(severity: CoachNarrativeSeverity): string {
  if (severity === 'high') {
    return 'Impact: High — this can significantly reduce consistency and control under pressure.';
  }
  if (severity === 'medium') {
    return 'Impact: Medium — fixing this should improve repeatability and timing.';
  }
  return 'Impact: Low — a small improvement that can add polish and efficiency.';
}

function confidenceText(jobStatus: string, detectionRate01: number | undefined, framesAnalyzed: number | undefined): string {
  if (jobStatus === 'queued' || jobStatus === 'processing') {
    return 'Confidence: Analysis is running — results will update automatically.';
  }
  if (jobStatus === 'failed') {
    return 'Confidence: Not available — analysis did not complete successfully.';
  }
  if (detectionRate01 == null || framesAnalyzed == null) {
    return 'Confidence: Limited — not enough data was returned to judge reliability.';
  }

  const dr = clamp01(detectionRate01);
  if (framesAnalyzed >= 60 && dr >= 0.8) return 'Confidence: High — strong coverage and a good sample size.';
  if (framesAnalyzed >= 30 && dr >= 0.65) return 'Confidence: Medium — good signal, but more data improves certainty.';
  return 'Confidence: Low — coverage/sample size is limited; interpret carefully.';
}

function coverageText(jobStatus: string, detectionRate01: number | undefined, framesAnalyzed: number | undefined, totalFrames: number | undefined): string {
  if (jobStatus === 'queued' || jobStatus === 'processing') {
    return 'Coverage: Not available yet (analysis in progress).';
  }
  if (jobStatus === 'failed') {
    return 'Coverage: Not available (analysis failed).';
  }

  const parts: string[] = [];
  if (typeof framesAnalyzed === 'number') {
    if (typeof totalFrames === 'number') {
      parts.push(`Frames analyzed: ${framesAnalyzed} of ${totalFrames}.`);
    } else {
      parts.push(`Frames analyzed: ${framesAnalyzed}.`);
    }
  } else {
    parts.push('Frames analyzed: —.');
  }

  if (typeof detectionRate01 === 'number') {
    const pct = Math.round(clamp01(detectionRate01) * 100);
    parts.push(`Pose detection coverage: ~${pct}%.`);
  } else {
    parts.push('Pose detection coverage: —.');
  }

  return parts.join(' ');
}

function uniqueStrings(values: unknown[], limit: number): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const v of values) {
    const s = toNonEmptyString(v);
    if (!s) continue;
    if (seen.has(s)) continue;
    seen.add(s);
    out.push(s);
    if (out.length >= limit) break;
  }
  return out;
}

function extractPriorities(resultsObj: AnyObj | null): CoachNarrative['priorities'] {
  if (!resultsObj) return [];

  const coachObj = pickFirstObject(resultsObj['coach']);
  const findingsRaw = (resultsObj['findings'] ?? coachObj?.['findings'] ?? null) as unknown;

  const priorities: CoachNarrative['priorities'] = [];

  // Supported shape: { key_findings: [{ title, why, fix, drills, severity }] }
  const findingsObj = pickFirstObject(findingsRaw);
  const keyFindings = Array.isArray(findingsObj?.['key_findings'])
    ? (findingsObj?.['key_findings'] as unknown[])
    : [];

  for (const f of keyFindings) {
    if (!isObject(f)) continue;

    const title = safeText(f['title'] ?? f['name'], 'Technique priority');
    const key = safeText(f['key'], title.toLowerCase().replace(/\s+/g, '_'));
    const severity = coerceSeverity(f['severity'] ?? f['level'] ?? f['priority']);

    const explanation =
      toNonEmptyString(f['explanation']) ??
      (toNonEmptyString(f['why']) ? `Why it matters: ${String(f['why'])}` : null) ??
      'Why it matters: Improving this will help you repeat your best movement more often.';

    const whatToFix = toNonEmptyString(f['fix'])
      ? `What to do: ${String(f['fix'])}`
      : 'What to do: Use one simple cue and repeat it consistently in practice.';

    const drills = Array.isArray(f['drills']) ? uniqueStrings(f['drills'] as unknown[], 5) : [];

    priorities.push({
      key,
      title,
      severity,
      explanation: `${explanation} ${whatToFix}`,
      impact: impactTextForSeverity(severity),
      drills,
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
        explanation:
          'Why it matters: Small inefficiencies add up across innings. What to do: Pick one clear cue and repeat it consistently.',
        impact: impactTextForSeverity('medium'),
        drills: [],
      });
    }
  }

  // Order: high → medium → low
  const rank: Record<CoachNarrativeSeverity, number> = { high: 0, medium: 1, low: 2 };
  priorities.sort((a, b) => rank[a.severity] - rank[b.severity]);

  return priorities;
}

function extractCoachSummaryText(resultsObj: AnyObj | null, jobStatus: string, errorMessage: string | null): string {
  if (jobStatus === 'queued' || jobStatus === 'processing') {
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

export function buildCoachNarrative(analysisJob: VideoAnalysisJob | null | undefined): CoachNarrative {
  const jobStatus = analysisJob?.status ?? 'unknown';
  const errorMessage = toNonEmptyString(analysisJob?.error_message) ?? null;

  // Reuse the existing normalizer for stable numeric extraction.
  const normalized = normalizeCoachVideoAnalysis(analysisJob);

  const totalFrames = normalized.numbers.totalFrames ?? undefined;
  const framesAnalyzed = normalized.numbers.sampledFrames ?? undefined;
  const detectionRate = normalized.numbers.detectionRate ?? undefined;

  const resultsObj = pickFirstObject((analysisJob?.results ?? null) as unknown);

  const priorities = extractPriorities(resultsObj);
  const rating = ratingFromSeverities(
    priorities.map((p) => p.severity),
    jobStatus,
  );

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
