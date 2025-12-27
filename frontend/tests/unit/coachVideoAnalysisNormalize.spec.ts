import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import { normalizeCoachVideoAnalysis } from '@/utils/coachVideoAnalysisNormalize';

describe('normalizeCoachVideoAnalysis', () => {
  it('queued job (results undefined) returns safe defaults', () => {
    const job = {
      id: 'job_1',
      session_id: 'sess_1',
      sample_fps: 10,
      include_frames: false,
      status: 'queued',
      error_message: null,
      sqs_message_id: null,
      // Intentionally simulate missing results payload
      results: undefined,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const normalized = normalizeCoachVideoAnalysis(job);

    expect(normalized.status).toBe('queued');
    expect(normalized.hasResults).toBe(false);
    expect(normalized.progress.show).toBe(true);

    expect(normalized.numbers.totalFrames).toBeNull();
    expect(normalized.numbers.sampledFrames).toBeNull();
    expect(normalized.numbers.detectionRate).toBeNull();
    expect(normalized.numbers.fps).toBeNull();
  });

  it('completed job maps nested backend schema fields', () => {
    const job = {
      id: 'job_2',
      session_id: 'sess_2',
      sample_fps: 10,
      include_frames: false,
      status: 'completed',
      error_message: null,
      sqs_message_id: 'sqs_1',
      results: {
        pose: {
          total_frames: 123,
          sampled_frames: 40,
          detected_frames: 100,
          detection_rate: 0.8,
          video_fps: 29.97,
          video_width: 1920,
          video_height: 1080,
          pose_summary: {
            frame_count: 999,
          },
        },
        metrics: {
          summary: { total_frames: 45 },
          balance: 0.82,
          alignment_score: 0.33,
        },
        findings: {
          key_findings: [
            {
              title: 'Front elbow timing',
              why: 'Helps transfer power and keep the bat path stable.',
              fix: 'Keep the front elbow high through contact.',
              drills: ['Top-hand control drill', 'Mirror swing reps'],
            },
          ],
        },
        report: {
          summary: 'Good base; focus on front elbow and balance.',
          key_issues: ['Front elbow drops early'],
          drills: [{ name: 'Top-hand control drill' }],
          one_week_plan: '3 sessions: slow reps → medium pace → match intensity.',
        },
      },
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const normalized = normalizeCoachVideoAnalysis(job);

    expect(normalized.status).toBe('completed');
    expect(normalized.hasResults).toBe(true);
    expect(normalized.progress.show).toBe(false);

    // Required mappings
    expect(normalized.numbers.totalFrames).toBe(123);
    expect(normalized.numbers.sampledFrames).toBe(45);
    expect(normalized.numbers.detectionRate).toBeCloseTo(0.8, 5);
    expect(normalized.numbers.fps).toBeCloseTo(29.97, 2);
    expect(normalized.numbers.width).toBe(1920);
    expect(normalized.numbers.height).toBe(1080);

    // Findings should be coach-friendly and non-throwing
    expect(normalized.nextWork.length).toBeGreaterThan(0);
    expect(normalized.nextWork[0]?.title).toContain('Front elbow');

    // Metrics should include friendly labels and score bands
    const balance = normalized.metrics.find((m) => m.key === 'balance');
    expect(balance?.label).toBe('Balance');
    expect(balance?.band).toBe('Strong');
  });

  it('failed job surfaces error_message and safe defaults', () => {
    const job = {
      id: 'job_3',
      session_id: 'sess_3',
      sample_fps: 10,
      include_frames: false,
      status: 'failed',
      error_message: 'Pose extraction failed',
      sqs_message_id: 'sqs_2',
      results: null,
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const normalized = normalizeCoachVideoAnalysis(job);

    expect(normalized.status).toBe('failed');
    expect(normalized.isTerminal).toBe(true);
    expect(normalized.errorMessage).toBe('Pose extraction failed');
    expect(normalized.hasResults).toBe(false);
    expect(normalized.progress.show).toBe(false);
  });
});
