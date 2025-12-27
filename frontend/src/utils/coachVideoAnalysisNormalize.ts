import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';

type AnalysisJob = VideoAnalysisJob;

export type CoachFriendlyMetricBand = 'Needs work' | 'Improving' | 'Strong';

export type CoachFriendlyMetric = {
  key: string;
  label: string;
  value: number | null;
  band: CoachFriendlyMetricBand | null;
};

export type CoachFriendlyFinding = {
  title: string;
  whyItMatters: string;
  whatToFix: string;
  drillSuggestions: string[];
};

export type CoachFriendlyNumbers = {
  totalFrames: number | null;
  sampledFrames: number | null;
  detectionRate: number | null; // 0..1
  fps: number | null;
  width: number | null;
  height: number | null;
};

export type CoachFriendlyAnalysis = {
  status: string;
  isTerminal: boolean;
  hasResults: boolean;
  sessionId: string | null;
  jobId: string | null;
  errorMessage: string | null;

  coachSummary: {
    overallLevel: CoachFriendlyMetricBand | '—';
    takeaways: string[];
  };

  nextWork: CoachFriendlyFinding[];
  numbers: CoachFriendlyNumbers;
  metrics: CoachFriendlyMetric[];

  progress: {
    show: boolean;
    steps: string[];
  };
};

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function normalizeRateTo01(value: number): number {
  // Heuristic: treat 0..1 as already normalized; treat >1 and <=100 as percent.
  if (value <= 1) return clamp01(value);
  if (value <= 100) return clamp01(value / 100);
  return 1;
}

function pickFirstNumber(...values: unknown[]): number | null {
  for (const v of values) {
    const n = toNumberOrNull(v);
    if (n !== null) return n;
  }
  return null;
}

function pickFirstObject(...values: unknown[]): Record<string, unknown> | null {
  for (const v of values) {
    if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>;
  }
  return null;
}

function titleCaseFromKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\bscore\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function metricLabelForKey(key: string): string {
  const known: Record<string, string> = {
    balance: 'Balance',
    balance_score: 'Balance',
    alignment: 'Alignment',
    alignment_score: 'Alignment',
    stability: 'Stability',
    stability_score: 'Stability',
    head_position: 'Head Position',
    head_position_score: 'Head Position',
    front_elbow: 'Front Elbow',
    front_elbow_score: 'Front Elbow',
    stride_length: 'Stride Length',
    stride_length_score: 'Stride Length',
    hip_rotation: 'Hip Rotation',
    hip_rotation_score: 'Hip Rotation',
    shoulder_rotation: 'Shoulder Rotation',
    shoulder_rotation_score: 'Shoulder Rotation',
  };
  return known[key] ?? titleCaseFromKey(key);
}

function bandForScore(score01: number | null): CoachFriendlyMetricBand | null {
  if (score01 === null) return null;
  if (score01 <= 0.39) return 'Needs work';
  if (score01 <= 0.69) return 'Improving';
  return 'Strong';
}

function coerceMetricValueTo01(value: unknown): number | null {
  const n = toNumberOrNull(value);
  if (n === null) return null;
  if (n >= 0 && n <= 1) return n;
  if (n > 1 && n <= 100) return n / 100;
  return null;
}

function extractTopFindings(findingsRaw: unknown, reportRaw: unknown): CoachFriendlyFinding[] {
  const findings: CoachFriendlyFinding[] = [];

  const report = pickFirstObject(reportRaw);
  const reportIssues = Array.isArray(report?.key_issues) ? (report?.key_issues as unknown[]) : [];
  const reportDrills = Array.isArray(report?.drills) ? (report?.drills as unknown[]) : [];

  const drillNames: string[] = reportDrills
    .map((d) => (d && typeof d === 'object' ? (d as Record<string, unknown>).name : null))
    .map((n) => (typeof n === 'string' ? n : null))
    .filter((n): n is string => !!n);

  // If findings is an array of strings
  if (Array.isArray(findingsRaw)) {
    for (const item of findingsRaw) {
      if (typeof item !== 'string') continue;
      findings.push({
        title: item,
        whyItMatters: 'Why it matters: Small inefficiencies add up across innings.',
        whatToFix: 'What to fix: Pick one clear cue and repeat it consistently.',
        drillSuggestions: drillNames.slice(0, 3),
      });
      if (findings.length >= 3) return findings;
    }
  }

  // If findings is an object with common keys
  const findingsObj = pickFirstObject(findingsRaw);
  const strengthAreas = Array.isArray(findingsObj?.strength_areas)
    ? (findingsObj?.strength_areas as unknown[])
    : [];
  const keyFindings = Array.isArray(findingsObj?.key_findings)
    ? (findingsObj?.key_findings as unknown[])
    : [];

  for (const f of keyFindings) {
    if (!f || typeof f !== 'object') continue;
    const fo = f as Record<string, unknown>;
    const title =
      (typeof fo.title === 'string' && fo.title.trim()) ||
      (typeof fo.name === 'string' && fo.name.trim());
    if (!title) continue;

    const why = typeof fo.why === 'string' ? fo.why : null;
    const fix = typeof fo.fix === 'string' ? fo.fix : null;
    const drills = Array.isArray(fo.drills) ? (fo.drills as unknown[]) : [];
    const drillSuggestions = drills
      .map((d) => (typeof d === 'string' ? d : null))
      .filter((d): d is string => !!d);

    findings.push({
      title,
      whyItMatters: why
        ? `Why it matters: ${why}`
        : 'Why it matters: This impacts consistency and control.',
      whatToFix: fix ? `What to fix: ${fix}` : 'What to fix: Focus on a simple cue during reps.',
      drillSuggestions: (drillSuggestions.length ? drillSuggestions : drillNames).slice(0, 3),
    });

    if (findings.length >= 3) return findings;
  }

  // Fallback to report key issues
  for (const issue of reportIssues) {
    if (typeof issue !== 'string' || !issue.trim()) continue;
    findings.push({
      title: issue,
      whyItMatters: 'Why it matters: This can reduce power, timing, or repeatability.',
      whatToFix: 'What to fix: Slow down, isolate the movement, and rebuild clean reps.',
      drillSuggestions: drillNames.slice(0, 3),
    });
    if (findings.length >= 3) return findings;
  }

  // If nothing actionable, add a gentle default
  if (strengthAreas.length > 0) {
    findings.push({
      title: 'Build on your strengths',
      whyItMatters:
        'Why it matters: Reinforcing strengths makes your base more reliable under pressure.',
      whatToFix: 'What to fix: Keep your best cue consistent across all reps.',
      drillSuggestions: drillNames.slice(0, 3),
    });
  }

  return findings.slice(0, 3);
}

function buildTakeaways(
  numbers: CoachFriendlyNumbers,
  findings: CoachFriendlyFinding[],
  reportRaw: unknown,
): string[] {
  const takeaways: string[] = [];

  const report = pickFirstObject(reportRaw);
  const summary = typeof report?.summary === 'string' ? report.summary.trim() : '';
  if (summary) takeaways.push(summary);

  if (numbers.detectionRate !== null) {
    const pct = Math.round(numbers.detectionRate * 100);
    takeaways.push(`Pose detection coverage: ${pct}% of frames.`);
  }

  if (numbers.totalFrames !== null && numbers.sampledFrames !== null) {
    takeaways.push(`Analyzed ${numbers.sampledFrames} of ${numbers.totalFrames} frames.`);
  }

  for (const f of findings.slice(0, 2)) {
    takeaways.push(f.title);
  }

  // Keep 2–4 takeaways, stable.
  return takeaways.filter(Boolean).slice(0, 4);
}

function overallLevelFromMetrics(metrics: CoachFriendlyMetric[]): CoachFriendlyMetricBand | '—' {
  const values = metrics.map((m) => m.value).filter((v): v is number => typeof v === 'number');
  if (values.length === 0) return '—';
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return bandForScore(avg) ?? '—';
}

export function normalizeCoachVideoAnalysis(
  job: AnalysisJob | null | undefined,
): CoachFriendlyAnalysis {
  const status = job?.status ?? 'unknown';
  const isTerminal = status === 'completed' || status === 'failed';

  const results = (job?.results ?? null) as unknown;
  const resultsObj = pickFirstObject(results);

  const pose = pickFirstObject(resultsObj?.pose);
  const poseSummaryLegacy = pickFirstObject(resultsObj?.pose_summary);
  const poseSummaryNested = pickFirstObject(pose?.pose_summary);

  const metricsRaw = pickFirstObject(resultsObj?.metrics);
  const metricsSummary = pickFirstObject(metricsRaw?.summary);

  const totalFrames = pickFirstNumber(
    pose?.total_frames,
    poseSummaryNested?.frame_count,
    poseSummaryLegacy?.total_frames,
  );

  const sampledFrames = pickFirstNumber(
    metricsSummary?.total_frames,
    pose?.sampled_frames,
    poseSummaryLegacy?.sampled_frames,
  );

  const detectedFrames = pickFirstNumber(
    pose?.detected_frames,
    poseSummaryLegacy?.frames_with_pose,
  );

  const detectionRateRaw = pickFirstNumber(
    pose?.detection_rate,
    poseSummaryLegacy?.detection_rate_percent,
  );

  let detectionRate: number | null = null;
  if (detectionRateRaw !== null) {
    detectionRate = normalizeRateTo01(detectionRateRaw);
  } else if (detectedFrames !== null && totalFrames !== null && totalFrames > 0) {
    detectionRate = clamp01(detectedFrames / totalFrames);
  }

  const fps = pickFirstNumber(pose?.video_fps, poseSummaryLegacy?.video_fps);
  const width = pickFirstNumber(pose?.video_width);
  const height = pickFirstNumber(pose?.video_height);

  const findingsRaw = (resultsObj?.findings ?? resultsObj?.coach?.findings ?? null) as unknown;
  const reportRaw = (resultsObj?.report ?? resultsObj?.coach?.report ?? null) as unknown;

  const nextWork = extractTopFindings(findingsRaw, reportRaw);

  // Metrics: flatten metrics.* (ignore summary + non-number)
  const metricEntries: CoachFriendlyMetric[] = [];
  if (metricsRaw) {
    for (const [key, value] of Object.entries(metricsRaw)) {
      if (key === 'summary') continue;
      const score01 = coerceMetricValueTo01(value);
      if (score01 === null) continue;
      const label = metricLabelForKey(key);
      metricEntries.push({
        key,
        label,
        value: clamp01(score01),
        band: bandForScore(clamp01(score01)),
      });
    }
  }

  metricEntries.sort((a, b) => {
    const av = a.value ?? -1;
    const bv = b.value ?? -1;
    return bv - av;
  });

  const numbers: CoachFriendlyNumbers = {
    totalFrames,
    sampledFrames,
    detectionRate,
    fps,
    width,
    height,
  };

  const takeaways = buildTakeaways(numbers, nextWork, reportRaw);

  const hasResults = !!resultsObj;

  return {
    status,
    isTerminal,
    hasResults,
    sessionId: job?.session_id ?? null,
    jobId: job?.id ?? null,
    errorMessage: job?.error_message ?? null,

    coachSummary: {
      overallLevel: overallLevelFromMetrics(metricEntries),
      takeaways: takeaways.length ? takeaways : ['—'],
    },

    nextWork,
    numbers,
    metrics: metricEntries,

    progress: {
      show: (status === 'queued' || status === 'processing') && !hasResults,
      steps: ['Extract pose', 'Compute metrics', 'Generate findings', 'Generate report'],
    },
  };
}
