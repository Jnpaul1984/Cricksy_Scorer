import type { VideoAnalysisJob, VideoAnalysisResults } from '@/services/coachPlusVideoService';

export type CoachVideoRepetition = {
  repetitionId: string;
  discipline: string;
  actionType: string;
  startFrame: number | null;
  endFrame: number | null;
  startSeconds: number | null;
  endSeconds: number | null;
  segmentationMethod: string | null;
  segmentationConfidence: number | null;
  validityState: string;
  insufficientReason: string | null;
};

export type CoachVideoRepetitionSummary = {
  enabled?: boolean;
  discipline?: string;
  segmentation_method?: string;
  validity_state?: string;
  segmentation_confidence?: number;
  repetitions_count?: number;
  insufficient_reason?: string | null;
} | null;

export type CoachVideoPhase = {
  phaseId: string;
  repetitionId: string;
  phaseName: string;
  startFrame: number | null;
  endFrame: number | null;
  startSeconds: number | null;
  endSeconds: number | null;
  confidence: number | null;
  validityState: string;
  detectionMethod: string | null;
  requiresObjectEvidence: boolean;
  limitations: string[];
};

export type CoachVideoPhaseSummary = {
  enabled?: boolean;
  discipline?: string;
  detection_method?: string;
  validity_state?: string;
  phases_count?: number;
  recognized_repetitions?: number;
  insufficient_reason?: string | null;
} | null;

export type CoachVideoBattingMetric = {
  metricId: string;
  phase: string | null;
  rawValue: number | null;
  unit: string | null;
  confidenceScore: number | null;
  validityState: string;
  classificationStatus: string | null;
  unavailableReason: string | null;
  limitations: string[];
  repetitionValues: number[];
};

type AnyObj = Record<string, unknown>;

function isObject(value: unknown): value is AnyObj {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function asResults(value: unknown): VideoAnalysisResults | null {
  return isObject(value) ? (value as VideoAnalysisResults) : null;
}

function toNumber(value: unknown): number | null {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function pickBestCoachVideoResults(
  analysisJob: VideoAnalysisJob | null | undefined,
): VideoAnalysisResults | null {
  const direct = analysisJob?.deep_results ?? analysisJob?.quick_results ?? null;
  if (direct && isObject(direct)) return direct;

  const combined = analysisJob?.results;
  if (!isObject(combined)) return asResults(combined);
  const combinedObj = combined as AnyObj;

  return (
    asResults(combinedObj['deep']) ??
    asResults(combinedObj['quick']) ??
    asResults(combinedObj)
  );
}

export function getCoachVideoJobFps(analysisJob: VideoAnalysisJob | null | undefined): number | null {
  const results = pickBestCoachVideoResults(analysisJob);
  if (!results) return null;
  return (
    toNumber(results.pose_summary?.video_fps) ??
    toNumber(results.video_fps) ??
    toNumber(results.pose?.video_fps) ??
    toNumber((results.pose as Record<string, unknown> | undefined)?.fps) ??
    null
  );
}

export function extractCoachVideoRepetitionSummary(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoRepetitionSummary {
  const results = pickBestCoachVideoResults(analysisJob);
  const summary = results?.meta?.repetition_segmentation;
  return summary && isObject(summary) ? summary : null;
}

export function extractCoachVideoPhaseSummary(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoPhaseSummary {
  const results = pickBestCoachVideoResults(analysisJob);
  const summary = results?.meta?.phase_recognition;
  return summary && isObject(summary) ? summary : null;
}

export function extractCoachVideoRepetitions(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoRepetition[] {
  const results = pickBestCoachVideoResults(analysisJob);
  const rawRepetitions = results?.v2?.repetitions;
  if (!Array.isArray(rawRepetitions)) return [];

  return rawRepetitions
    .map((item) => (isObject(item) ? item : null))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .map((item) => ({
      repetitionId: String(item.repetition_id ?? ''),
      discipline: typeof item.discipline === 'string' ? item.discipline : 'unknown',
      actionType:
        typeof item.action_type === 'string' && item.action_type.trim().length > 0
          ? item.action_type
          : 'repetition',
      startFrame: toNumber(item.start_frame),
      endFrame: toNumber(item.end_frame),
      startSeconds: toNumber(item.start_ts),
      endSeconds: toNumber(item.end_ts),
      segmentationMethod:
        typeof item.segmentation_method === 'string' ? item.segmentation_method : null,
      segmentationConfidence: toNumber(item.segmentation_confidence),
      validityState:
        typeof item.validity_state === 'string' ? item.validity_state : 'NOT_MEASURABLE',
      insufficientReason:
        typeof item.insufficient_reason === 'string' ? item.insufficient_reason : null,
    }))
    .filter((item) => item.repetitionId.length > 0)
    .sort((left, right) => {
      const leftStart = left.startSeconds ?? Number.MAX_SAFE_INTEGER;
      const rightStart = right.startSeconds ?? Number.MAX_SAFE_INTEGER;
      if (leftStart !== rightStart) return leftStart - rightStart;
      const leftFrame = left.startFrame ?? Number.MAX_SAFE_INTEGER;
      const rightFrame = right.startFrame ?? Number.MAX_SAFE_INTEGER;
      return leftFrame - rightFrame;
    });
}

export function extractCoachVideoPhases(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoPhase[] {
  const results = pickBestCoachVideoResults(analysisJob);
  const rawPhases = results?.v2?.phases;
  if (!Array.isArray(rawPhases)) return [];

  return rawPhases
    .map((item) => (isObject(item) ? item : null))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .map((item) => ({
      phaseId: String(item.phase_id ?? ''),
      repetitionId: String(item.repetition_id ?? ''),
      phaseName:
        typeof item.phase_name === 'string' && item.phase_name.trim().length > 0
          ? item.phase_name
          : 'phase',
      startFrame: toNumber(item.start_frame),
      endFrame: toNumber(item.end_frame),
      startSeconds: toNumber(item.start_ts),
      endSeconds: toNumber(item.end_ts),
      confidence: toNumber(item.confidence),
      validityState: typeof item.validity_state === 'string' ? item.validity_state : 'NOT_MEASURABLE',
      detectionMethod: typeof item.detection_method === 'string' ? item.detection_method : null,
      requiresObjectEvidence: Boolean(item.requires_object_evidence),
      limitations: Array.isArray(item.limitations)
        ? item.limitations.filter((entry): entry is string => typeof entry === 'string')
        : [],
    }))
    .filter((item) => item.phaseId.length > 0 && item.repetitionId.length > 0)
    .sort((left, right) => {
      const leftStart = left.startSeconds ?? Number.MAX_SAFE_INTEGER;
      const rightStart = right.startSeconds ?? Number.MAX_SAFE_INTEGER;
      if (leftStart !== rightStart) return leftStart - rightStart;
      const leftFrame = left.startFrame ?? Number.MAX_SAFE_INTEGER;
      const rightFrame = right.startFrame ?? Number.MAX_SAFE_INTEGER;
      return leftFrame - rightFrame;
    });
}

export function extractCoachVideoBattingMetrics(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoBattingMetric[] {
  const results = pickBestCoachVideoResults(analysisJob);
  const rawMetricResults = results?.v2?.metric_results;
  if (!Array.isArray(rawMetricResults)) return [];

  return rawMetricResults
    .map((item) => (isObject(item) ? item : null))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .filter((item) => typeof item.metric_id === 'string' && item.metric_id.startsWith('batting_'))
    .map((item) => ({
      metricId: String(item.metric_id),
      phase: typeof item.phase === 'string' ? item.phase : null,
      rawValue: toNumber(item.raw_value),
      unit: typeof item.unit === 'string' ? item.unit : null,
      confidenceScore: toNumber(item.confidence_score),
      validityState: typeof item.validity_state === 'string' ? item.validity_state : 'NOT_MEASURABLE',
      classificationStatus:
        typeof item.classification_status === 'string' ? item.classification_status : null,
      unavailableReason:
        typeof item.unavailable_reason === 'string' ? item.unavailable_reason : null,
      limitations: Array.isArray(item.limitations)
        ? item.limitations.filter((entry): entry is string => typeof entry === 'string')
        : [],
      repetitionValues: Array.isArray(item.repetition_values)
        ? item.repetition_values.map((value) => toNumber(value)).filter((value): value is number => value !== null)
        : [],
    }))
    .sort((left, right) => left.metricId.localeCompare(right.metricId));
}
