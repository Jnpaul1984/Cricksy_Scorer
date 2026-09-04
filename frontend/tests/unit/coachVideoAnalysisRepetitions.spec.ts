import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import {
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
        },
        v2: {
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
    expect(getCoachVideoJobFps(job)).toBe(30);
    expect(extractCoachVideoRepetitionSummary(job)?.repetitions_count).toBe(2);
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
    expect(getCoachVideoJobFps(job)).toBeNull();
  });
});
