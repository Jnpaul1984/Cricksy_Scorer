import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import { buildCoachNarrative } from '@/utils/coachVideoAnalysisNarrative';

describe('buildCoachNarrative', () => {
  it('queued job returns coach-safe summary strings and no priorities', () => {
    const job = {
      id: 'job_q',
      session_id: 'sess_q',
      sample_fps: 10,
      include_frames: false,
      status: 'queued',
      error_message: null,
      sqs_message_id: null,
      results: undefined,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const narrative = buildCoachNarrative(job);

    expect(narrative.summary.rating).toBe('Solid');
    expect(narrative.summary.confidenceText).toContain('Analysis is running');
    expect(narrative.summary.coverageText.length).toBeGreaterThan(0);
    expect(narrative.summary.coachSummaryText.length).toBeGreaterThan(0);
    expect(narrative.priorities).toEqual([]);

    // Coach should never see undefined/null
    expect(JSON.stringify(narrative)).not.toContain('undefined');
    expect(JSON.stringify(narrative)).not.toContain('null');
  });

  it('completed job maps findings severity into rating and priorities ordering', () => {
    const job = {
      id: 'job_c',
      session_id: 'sess_c',
      sample_fps: 10,
      include_frames: false,
      status: 'completed',
      error_message: null,
      sqs_message_id: 'sqs_1',
      results: {
        pose: {
          total_frames: 120,
          detected_frames: 90,
          detection_rate: 0.75,
        },
        findings: {
          key_findings: [
            {
              key: 'front_elbow',
              title: 'Front elbow timing',
              severity: 'high',
              why: 'Helps transfer power and keep the bat path stable.',
              fix: 'Keep the front elbow high through contact.',
              drills: ['Top-hand control drill'],
            },
            {
              key: 'balance',
              title: 'Balance at contact',
              severity: 'low',
              why: 'Better balance improves repeatability.',
              fix: 'Finish tall with stable head position.',
              drills: ['Mirror swing reps'],
            },
          ],
        },
        report: {
          summary: 'Strong base. Focus first on front elbow timing.',
        },
      },
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const narrative = buildCoachNarrative(job);

    expect(narrative.summary.rating).toBe('High Risk');
    expect(narrative.priorities.length).toBe(2);
    expect(narrative.priorities[0].severity).toBe('high');
    expect(narrative.priorities[0].title).toContain('Front elbow');
    expect(narrative.priorities[0].drills.length).toBeGreaterThan(0);
  });

  it('completed job with missing metrics still returns readable summary and safe coverage', () => {
    const job = {
      id: 'job_partial',
      session_id: 'sess_partial',
      sample_fps: 10,
      include_frames: false,
      status: 'completed',
      error_message: null,
      sqs_message_id: 'sqs_2',
      results: {
        pose: {
          total_frames: 100,
          // detection_rate intentionally missing
        },
        // findings + metrics missing
      },
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob;

    const narrative = buildCoachNarrative(job);

    expect(narrative.summary.rating).toBe('Solid');
    expect(narrative.summary.coverageText).toContain('Frames analyzed');
    expect(narrative.summary.coachSummaryText.length).toBeGreaterThan(0);

    // No undefined/null for coaches
    expect(JSON.stringify(narrative)).not.toContain('undefined');
    expect(JSON.stringify(narrative)).not.toContain('null');
  });
});
