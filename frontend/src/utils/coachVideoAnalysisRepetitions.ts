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

export type CoachVideoV2Metric = {
  metricId: string;
  discipline: string | null;
  phase: string | null;
  rawValue: number | null;
  unit: string | null;
  confidenceScore: number | null;
  validityState: string;
  classificationStatus: string | null;
  unavailableReason: string | null;
  limitations: string[];
  repetitionValues: number[];
  consistency: {
    status: string | null;
    method: string | null;
    classification: string | null;
    value: number | null;
    validSampleCount: number | null;
    excludedRepetitionCount: number | null;
    limitations: string[];
  } | null;
};

export type CoachVideoBattingMetric = CoachVideoV2Metric;

export type CoachVideoSessionSignal = {
  metricId: string;
  discipline: string | null;
  phase: string | null;
  severity: string | null;
  confidenceScore: number | null;
  validSampleCount: number | null;
  summary: string;
  supportingRepetitionIds: string[];
  limitations: string[];
};

export type CoachVideoConsistencyObservation = {
  metricId: string;
  discipline: string | null;
  phase: string | null;
  method: string | null;
  classification: string | null;
  value: number | null;
  confidenceScore: number | null;
  validSampleCount: number | null;
  excludedRepetitionCount: number | null;
  limitations: string[];
};

export type CoachVideoRepetitionSelection = {
  available: boolean;
  repetitionId: string | null;
  rationale: string | null;
  confidenceScore: number | null;
  supportingMetrics: string[];
};

export type CoachVideoSessionAnalysis = {
  strengths: CoachVideoSessionSignal[];
  recurringConcerns: CoachVideoSessionSignal[];
  consistencyObservations: CoachVideoConsistencyObservation[];
  bestRepetition: CoachVideoRepetitionSelection | null;
  needsWorkRepetition: CoachVideoRepetitionSelection | null;
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

function toStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
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

export function extractCoachVideoDisciplineV2Metrics(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoV2Metric[] {
  const results = pickBestCoachVideoResults(analysisJob);
  const rawMetricResults = results?.v2?.metric_results;
  if (!Array.isArray(rawMetricResults)) return [];

  return rawMetricResults
    .map((item) => (isObject(item) ? item : null))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .filter(
      (item) =>
        typeof item.metric_id === 'string' &&
        ['batting_', 'pace_bowling_', 'spin_bowling_', 'wicketkeeping_', 'fielding_'].some((prefix) =>
          item.metric_id.startsWith(prefix),
        ),
    )
    .map((item) => ({
      metricId: String(item.metric_id),
      discipline: typeof item.discipline === 'string' ? item.discipline : null,
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
      consistency: isObject(item.consistency)
        ? {
            status: typeof item.consistency.status === 'string' ? item.consistency.status : null,
            method: typeof item.consistency.method === 'string' ? item.consistency.method : null,
            classification:
              typeof item.consistency.classification === 'string' ? item.consistency.classification : null,
            value: toNumber(item.consistency.value),
            validSampleCount: toNumber(item.consistency.valid_sample_count),
            excludedRepetitionCount: toNumber(item.consistency.excluded_repetition_count),
            limitations: toStringArray(item.consistency.limitations),
          }
        : null,
    }))
    .sort((left, right) => left.metricId.localeCompare(right.metricId));
}

export function extractCoachVideoBattingMetrics(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoBattingMetric[] {
  return extractCoachVideoDisciplineV2Metrics(analysisJob).filter((item) =>
    item.metricId.startsWith('batting_'),
  );
}

export function extractCoachVideoSessionAnalysis(
  analysisJob: VideoAnalysisJob | null | undefined,
): CoachVideoSessionAnalysis | null {
  const results = pickBestCoachVideoResults(analysisJob);
  const source =
    (isObject(results?.findings) && isObject(results?.findings['v2_session_analysis'])
      ? results?.findings['v2_session_analysis']
      : null) ??
    (isObject(results?.report) && isObject(results?.report['v2_session_analysis'])
      ? results?.report['v2_session_analysis']
      : null);
  if (!isObject(source)) return null;

  const mapSignal = (item: unknown): CoachVideoSessionSignal | null => {
    if (!isObject(item)) return null;
    return {
      metricId: typeof item.metric_id === 'string' ? item.metric_id : '',
      discipline: typeof item.discipline === 'string' ? item.discipline : null,
      phase: typeof item.phase === 'string' ? item.phase : null,
      severity: typeof item.severity === 'string' ? item.severity : null,
      confidenceScore: toNumber(item.confidence_score),
      validSampleCount: toNumber(item.valid_sample_count),
      summary: typeof item.summary === 'string' ? item.summary : '',
      supportingRepetitionIds: toStringArray(item.supporting_repetition_ids),
      limitations: toStringArray(item.limitations),
    };
  };

  const mapObservation = (item: unknown): CoachVideoConsistencyObservation | null => {
    if (!isObject(item)) return null;
    return {
      metricId: typeof item.metric_id === 'string' ? item.metric_id : '',
      discipline: typeof item.discipline === 'string' ? item.discipline : null,
      phase: typeof item.phase === 'string' ? item.phase : null,
      method: typeof item.method === 'string' ? item.method : null,
      classification: typeof item.classification === 'string' ? item.classification : null,
      value: toNumber(item.value),
      confidenceScore: toNumber(item.confidence_score),
      validSampleCount: toNumber(item.valid_sample_count),
      excludedRepetitionCount: toNumber(item.excluded_repetition_count),
      limitations: toStringArray(item.limitations),
    };
  };

  const mapSelection = (item: unknown): CoachVideoRepetitionSelection | null => {
    if (!isObject(item)) return null;
    return {
      available: Boolean(item.available),
      repetitionId: typeof item.repetition_id === 'string' ? item.repetition_id : null,
      rationale: typeof item.rationale === 'string' ? item.rationale : typeof item.reason === 'string' ? item.reason : null,
      confidenceScore: toNumber(item.confidence_score),
      supportingMetrics: toStringArray(item.supporting_metrics),
    };
  };

  return {
    strengths: Array.isArray(source.strengths)
      ? source.strengths.map(mapSignal).filter((item): item is CoachVideoSessionSignal => Boolean(item?.metricId))
      : [],
    recurringConcerns: Array.isArray(source.recurring_concerns)
      ? source.recurring_concerns
          .map(mapSignal)
          .filter((item): item is CoachVideoSessionSignal => Boolean(item?.metricId))
      : [],
    consistencyObservations: Array.isArray(source.consistency_observations)
      ? source.consistency_observations
          .map(mapObservation)
          .filter((item): item is CoachVideoConsistencyObservation => Boolean(item?.metricId))
      : [],
    bestRepetition: mapSelection(source.best_repetition),
    needsWorkRepetition: mapSelection(source.needs_work_repetition),
  };
}
