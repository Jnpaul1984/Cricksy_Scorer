import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import {
  extractCoachVideoBattingMetrics,
  extractCoachVideoPhases,
  extractCoachVideoPhaseSummary,
  extractCoachVideoRepetitions,
  extractCoachVideoRepetitionSummary,
  getCoachVideoJobFps,
} from '@/utils/coachVideoAnalysisRepetitions';

describe('coachVideoAnalysisRepetitions', () => {
  it('prefers deep_results and returns sorted repetition windows', () => {
    const job = {
      id: 'job-1',
      session_id: 'session-1',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      deep_results: {
        pose_summary: { video_fps: 30 },
        meta: {
          repetition_segmentation: {
            enabled: true,
            validity_state: 'VALID',
            repetitions_count: 2,
          },
          phase_recognition: {
            enabled: true,
            validity_state: 'LOW_CONFIDENCE',
            phases_count: 2,
          },
        },
        v2: {
          metric_results: [
            {
              metric_id: 'batting_setup_stance_width_ratio',
              phase: 'setup',
              raw_value: 1.1,
              unit: 'ratio',
              confidence_score: 0.8,
              classification_status: 'STRONG',
              validity_state: 'VALID',
              repetition_values: [1.0, 1.2],
            },
            {
              metric_id: 'head_stability_score',
              raw_value: 0.75,
              unit: 'score',
              validity_state: 'VALID',
            },
          ],
          repetitions: [
            {
              repetition_id: 'rep-2',
              discipline: 'batting',
              action_type: 'batting_shot',
              start_ts: 1.4,
              end_ts: 1.9,
              start_frame: 42,
              end_frame: 57,
              validity_state: 'VALID',
            },
            {
              repetition_id: 'rep-1',
              discipline: 'batting',
              action_type: 'batting_shot',
              start_ts: 0.4,
              end_ts: 0.9,
              start_frame: 12,
              end_frame: 27,
              validity_state: 'VALID',
            },
          ],
          phases: [
            {
              phase_id: 'rep-1:phase:1',
              repetition_id: 'rep-1',
              phase_name: 'setup',
              start_ts: 0.4,
              end_ts: 0.6,
              start_frame: 12,
              end_frame: 18,
              confidence: 0.7,
              validity_state: 'VALID',
              requires_object_evidence: false,
              limitations: [],
            },
            {
              phase_id: 'rep-2:phase:1',
              repetition_id: 'rep-2',
              phase_name: 'contact_proxy_window',
              start_ts: 1.7,
              end_ts: 1.8,
              start_frame: 51,
              end_frame: 54,
              confidence: 0.58,
              validity_state: 'LOW_CONFIDENCE',
              requires_object_evidence: true,
              limitations: ['proxy only'],
            },
          ],
        },
      },
      quick_results: {
        pose_summary: { video_fps: 24 },
      },
      results: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const repetitions = extractCoachVideoRepetitions(job);

    expect(repetitions).toHaveLength(2);
    expect(repetitions[0]?.repetitionId).toBe('rep-1');
    expect(repetitions[1]?.repetitionId).toBe('rep-2');
    const phases = extractCoachVideoPhases(job);
    expect(phases).toHaveLength(2);
    expect(phases[0]?.repetitionId).toBe('rep-1');
    expect(phases[1]?.phaseName).toBe('contact_proxy_window');
    expect(getCoachVideoJobFps(job)).toBe(30);
    expect(extractCoachVideoRepetitionSummary(job)?.repetitions_count).toBe(2);
    expect(extractCoachVideoPhaseSummary(job)?.phases_count).toBe(2);
    const battingMetrics = extractCoachVideoBattingMetrics(job);
    expect(battingMetrics).toHaveLength(1);
    expect(battingMetrics[0]?.metricId).toBe('batting_setup_stance_width_ratio');
    expect(battingMetrics[0]?.repetitionValues).toEqual([1.0, 1.2]);
  });

  it('keeps legacy jobs safe when repetition data is absent', () => {
    const job = {
      id: 'job-legacy',
      session_id: 'session-legacy',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      results: {
        quick: {
          report: { summary: 'legacy' },
        },
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    expect(extractCoachVideoRepetitions(job)).toEqual([]);
    expect(extractCoachVideoRepetitionSummary(job)).toBeNull();
    expect(extractCoachVideoPhases(job)).toEqual([]);
    expect(extractCoachVideoPhaseSummary(job)).toBeNull();
    expect(getCoachVideoJobFps(job)).toBeNull();
  });
});
