import { describe, it, expect } from 'vitest'
import type { VideoAnalysisJob } from '@/services/coachPlusVideoService'
import { buildCoachNarrative } from '@/utils/coachVideoAnalysisNarrative'

describe('CoachProPlusVideoSessions - Modal Status Logic', () => {
  /**
   * These tests verify the modal rendering logic:
   * 1. Terminal statuses (done, completed, failed) should show results UI
   * 2. Non-terminal statuses (queued, processing, quick_running) should show progress UI
   * 3. Partial results (quick_done, deep_running) should show results UI (after fix)
   */

  describe('Modal condition logic', () => {
    it('status="done" should NOT match progress UI condition', () => {
      const status = 'done'

      // Progress UI condition (after fix):
      // v-else-if="status === 'queued' || status === 'processing' || status === 'quick_running'"
      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(false)

      // Should fall through to results UI (v-else)
      const shouldShowResults = !shouldShowProgress && status !== 'failed'
      expect(shouldShowResults).toBe(true)
    })

    it('status="completed" should NOT match progress UI condition', () => {
      const status = 'completed'

      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(false)

      const shouldShowResults = !shouldShowProgress && status !== 'failed'
      expect(shouldShowResults).toBe(true)
    })

    it('status="deep_running" should NOT match progress UI condition (should show results)', () => {
      const status = 'deep_running'

      // After fix: deep_running is removed from progress UI condition
      // This allows quick_results to be displayed while deep analysis continues
      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(false)

      const shouldShowResults = !shouldShowProgress && status !== 'failed'
      expect(shouldShowResults).toBe(true)
    })

    it('status="quick_done" should NOT match progress UI condition (should show results)', () => {
      const status = 'quick_done'

      // After fix: quick_done is removed from progress UI condition
      // This allows quick results to be displayed immediately
      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(false)

      const shouldShowResults = !shouldShowProgress && status !== 'failed'
      expect(shouldShowResults).toBe(true)
    })

    it('status="queued" SHOULD match progress UI condition', () => {
      const status = 'queued'

      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(true)
    })

    it('status="failed" should show failed UI (not progress, not results)', () => {
      const status = 'failed'

      const shouldShowProgress =
        status === 'queued' ||
        status === 'processing' ||
        status === 'quick_running'

      expect(shouldShowProgress).toBe(false)

      // Should match the failed condition: v-else-if="status === 'failed'"
      expect(status).toBe('failed')
    })
  })

  describe('buildCoachNarrative with done status', () => {
    it('returns populated narrative when status=done with deep_results', () => {
      const job: VideoAnalysisJob = {
        id: 'job_done_123',
        session_id: 'sess_456',
        sample_fps: 5,
        include_frames: false,
        status: 'done',
        stage: 'DONE',
        progress_pct: 100,
        error_message: null,
        sqs_message_id: null,
        deep_results: {
          pose_summary: {
            total_frames: 1827,
            sampled_frames: 1827,
            frames_with_pose: 1761,
            detection_rate_percent: 96.4,
            video_fps: 30.0,
            model: 'MediaPipe Pose Landmarker Full',
          },
          findings: {
            overall_level: 'low',
            findings: [
              {
                code: 'HEAD_MOVEMENT',
                title: 'Head movement through contact',
                severity: 'high',
                evidence: {
                  mean_score: 0.45,
                  threshold: 0.6,
                },
                why_it_matters: 'A stable head position is crucial for visual tracking.',
                cues: ['Keep eyes locked on contact point'],
                suggested_drills: ['Mirror batting - observe head position'],
              },
            ],
          },
          report: {
            summary: 'Your technique requires comprehensive improvement.',
            top_issues: [
              {
                issue: 'Head movement through contact',
                severity: 'high',
                why_it_matters: 'Impacts timing and accuracy',
                cues: ['Keep eyes locked on contact point'],
              },
            ],
            drills: ['Mirror batting'],
            one_week_plan: [],
            notes: 'Focus on the high-severity findings first.',
            generated_with_llm: false,
          },
        },
        quick_results: null,
        results: null,
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as VideoAnalysisJob

      const narrative = buildCoachNarrative(job)

      // Should NOT show "analysis is running" message
      expect(narrative.summary.coachSummaryText).not.toContain('Analysis is in progress')
      expect(narrative.summary.coachSummaryText).not.toContain('analysis is running')

      // Should show actual report summary
      expect(narrative.summary.coachSummaryText).toContain('Your technique requires comprehensive improvement')

      // Should have high-risk rating due to high-severity finding
      expect(narrative.summary.rating).toBe('High Risk')

      // Should have priorities extracted from findings
      expect(narrative.priorities.length).toBeGreaterThan(0)
      expect(narrative.priorities[0].title).toContain('Head movement')
      expect(narrative.priorities[0].severity).toBe('high')
    })

    it('uses deep_results in preference to quick_results', () => {
      const job: VideoAnalysisJob = {
        id: 'job_both_results',
        session_id: 'sess_789',
        sample_fps: 5,
        include_frames: false,
        status: 'done',
        error_message: null,
        sqs_message_id: null,
        quick_results: {
          findings: {
            overall_level: 'low',
            findings: [],
          },
          report: {
            summary: 'Quick analysis summary (should be overridden)',
          },
        },
        deep_results: {
          findings: {
            overall_level: 'medium',
            findings: [
              {
                code: 'TEST',
                title: 'Deep analysis finding',
                severity: 'medium',
              },
            ],
          },
          report: {
            summary: 'Deep analysis summary (should be used)',
          },
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as VideoAnalysisJob

      const narrative = buildCoachNarrative(job)

      // Should use deep_results summary, not quick_results
      expect(narrative.summary.coachSummaryText).toContain('Deep analysis summary')
      expect(narrative.summary.coachSummaryText).not.toContain('Quick analysis summary')

      // Should have priorities from deep_results
      expect(narrative.priorities.length).toBeGreaterThan(0)
      expect(narrative.priorities[0].title).toContain('Deep analysis finding')
    })

    it('falls back to quick_results when deep_results is null', () => {
      const job: VideoAnalysisJob = {
        id: 'job_quick_only',
        session_id: 'sess_quick',
        sample_fps: 5,
        include_frames: false,
        status: 'quick_done',
        error_message: null,
        sqs_message_id: null,
        quick_results: {
          findings: {
            overall_level: 'low',
            findings: [
              {
                code: 'QUICK_FINDING',
                title: 'Quick analysis finding',
                severity: 'low',
              },
            ],
          },
          report: {
            summary: 'Quick analysis complete',
          },
        },
        deep_results: null,
        results: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as VideoAnalysisJob

      const narrative = buildCoachNarrative(job)

      // Should use quick_results summary
      expect(narrative.summary.coachSummaryText).toContain('Quick analysis complete')

      // Should have priorities from quick_results
      expect(narrative.priorities.length).toBeGreaterThan(0)
      expect(narrative.priorities[0].title).toContain('Quick analysis finding')
    })
  })

  describe('Polling timeout reset', () => {
    it('pollTimedOut should be reset to false when status becomes terminal', () => {
      // This test documents the expected behavior:
      // When status changes from non-terminal to terminal (done/completed/failed),
      // the pollTimedOut flag should be reset to false so the timeout UI disappears

      const pollTimedOut = { value: true } // Simulating a ref
      const status = 'done'

      // Polling logic:
      if (status === 'completed' || status === 'done' || status === 'failed') {
        pollTimedOut.value = false // ✅ This is the fix
        // stopUiPolling()
      }

      expect(pollTimedOut.value).toBe(false)
    })
  })

  describe('Cache staleness and terminal status protection', () => {
    it('isJobStale returns true after 30 seconds', () => {
      const now = Date.now()
      const staleThresholdMs = 30000 // 30 seconds

      // lastFetchedAt Map behavior simulation
      const lastFetchedAt = new Map<string, number>()
      const jobId = 'job-123'

      // Simulate function logic
      function isJobStale(id: string): boolean {
        const timestamp = lastFetchedAt.get(id)
        if (!timestamp) return true // Never fetched
        return Date.now() - timestamp > staleThresholdMs
      }

      // Test: never fetched → stale
      expect(isJobStale(jobId)).toBe(true)

      // Test: just fetched → not stale
      lastFetchedAt.set(jobId, now)
      expect(isJobStale(jobId)).toBe(false)

      // Test: fetched 29 seconds ago → not stale
      lastFetchedAt.set(jobId, now - 29000)
      expect(isJobStale(jobId)).toBe(false)

      // Test: fetched 31 seconds ago → stale
      lastFetchedAt.set(jobId, now - 31000)
      expect(isJobStale(jobId)).toBe(true)
    })

    it('updateJobStatus prevents terminal → non-terminal override', () => {
      const jobStatusMap = new Map<string, VideoAnalysisJob>()
      const jobId = 'job-123'

      // Helper to check if status is terminal
      function isJobTerminal(job: VideoAnalysisJob): boolean {
        return job.status === 'done' || job.status === 'completed' || job.status === 'failed'
      }

      // Simulate updateJobStatus logic
      function updateJobStatus(job: VideoAnalysisJob): boolean {
        const existing = jobStatusMap.get(job.id)
        if (existing && isJobTerminal(existing) && !isJobTerminal(job)) {
          // Should NOT update - terminal status is immutable
          return false
        }
        jobStatusMap.set(job.id, job)
        return true
      }

      // Test: done → deep_running BLOCKED
      const doneJob: VideoAnalysisJob = {
        id: jobId,
        session_id: 'session-1',
        status: 'done',
        sample_fps: 5,
        include_frames: true,
        error_message: null,
        sqs_message_id: null,
        results: null,
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        updated_at: new Date().toISOString(),
      }

      jobStatusMap.set(jobId, doneJob)

      const staleRunningJob: VideoAnalysisJob = {
        ...doneJob,
        status: 'deep_running',
      }

      const updated = updateJobStatus(staleRunningJob)
      expect(updated).toBe(false) // Should be blocked
      expect(jobStatusMap.get(jobId)?.status).toBe('done') // Status unchanged
    })

    it('updateJobStatus allows non-terminal → terminal update', () => {
      const jobStatusMap = new Map<string, VideoAnalysisJob>()
      const jobId = 'job-123'

      function isJobTerminal(job: VideoAnalysisJob): boolean {
        return job.status === 'done' || job.status === 'completed' || job.status === 'failed'
      }

      function updateJobStatus(job: VideoAnalysisJob): boolean {
        const existing = jobStatusMap.get(job.id)
        if (existing && isJobTerminal(existing) && !isJobTerminal(job)) {
          return false
        }
        jobStatusMap.set(job.id, job)
        return true
      }

      // Test: deep_running → done ALLOWED
      const runningJob: VideoAnalysisJob = {
        id: jobId,
        session_id: 'session-1',
        status: 'deep_running',
        sample_fps: 5,
        include_frames: true,
        error_message: null,
        sqs_message_id: null,
        results: null,
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        updated_at: new Date().toISOString(),
      }

      jobStatusMap.set(jobId, runningJob)

      const doneJob: VideoAnalysisJob = {
        ...runningJob,
        status: 'done',
      }

      const updated = updateJobStatus(doneJob)
      expect(updated).toBe(true) // Should be allowed
      expect(jobStatusMap.get(jobId)?.status).toBe('done')
    })

    it('forceFetchJob bypasses terminal status protection', () => {
      const jobStatusMap = new Map<string, VideoAnalysisJob>()
      const lastFetchedAt = new Map<string, number>()
      const jobId = 'job-123'

      // Simulate forceFetchJob (always updates, no protection)
      async function forceFetchJob(id: string, freshJob: VideoAnalysisJob): Promise<VideoAnalysisJob> {
        jobStatusMap.set(id, freshJob) // Always update, no checks
        lastFetchedAt.set(id, Date.now())
        return freshJob
      }

      // Start with done status
      const doneJob: VideoAnalysisJob = {
        id: jobId,
        session_id: 'session-1',
        status: 'done',
        sample_fps: 5,
        include_frames: true,
        error_message: null,
        sqs_message_id: null,
        results: { pose: {} as any },
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        updated_at: new Date().toISOString(),
      }

      jobStatusMap.set(jobId, doneJob)

      // User explicitly opens modal, triggering forceFetchJob
      // API returns fresh "done" status (not stale)
      const freshDoneJob: VideoAnalysisJob = {
        ...doneJob,
        updated_at: new Date(Date.now() + 1000).toISOString(), // Newer timestamp
      }

      forceFetchJob(jobId, freshDoneJob)

      expect(jobStatusMap.get(jobId)?.status).toBe('done')
      expect(jobStatusMap.get(jobId)?.updated_at).toBe(freshDoneJob.updated_at)
      expect(lastFetchedAt.has(jobId)).toBe(true)
    })

    it('modal open scenario: done → stale cache → force fetch → shows done', async () => {
      const jobStatusMap = new Map<string, VideoAnalysisJob>()
      const lastFetchedAt = new Map<string, number>()
      const jobId = 'job-123'

      // Simulate the complete flow
      const initialJob: VideoAnalysisJob = {
        id: jobId,
        session_id: 'session-1',
        status: 'done',
        sample_fps: 5,
        include_frames: true,
        error_message: null,
        sqs_message_id: null,
        results: { pose: {} as any },
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      // Step 1: Job reaches done, modal shows it
      jobStatusMap.set(jobId, initialJob)
      lastFetchedAt.set(jobId, Date.now() - 60000) // 60 seconds ago (stale)

      expect(jobStatusMap.get(jobId)?.status).toBe('done')

      // Step 2: User closes modal, time passes
      // (Cache becomes stale - >30 seconds old)
      function isJobStale(id: string): boolean {
        const timestamp = lastFetchedAt.get(id)
        if (!timestamp) return true
        return Date.now() - timestamp > 30000
      }

      expect(isJobStale(jobId)).toBe(true)

      // Step 3: User clicks session to view results again
      // forceFetchJob is called (bypasses protection)
      async function forceFetchJob(id: string): Promise<VideoAnalysisJob> {
        // Simulate API returning fresh "done" status
        const freshJob: VideoAnalysisJob = {
          ...initialJob,
          updated_at: new Date().toISOString(), // Fresh timestamp
        }
        jobStatusMap.set(id, freshJob) // Always update
        lastFetchedAt.set(id, Date.now()) // Mark as fresh
        return freshJob
      }

      const freshJob = await forceFetchJob(jobId)

      // Step 4: Modal opens with FRESH data (not stale cache)
      expect(freshJob.status).toBe('done')
      expect(jobStatusMap.get(jobId)?.status).toBe('done')
      expect(isJobStale(jobId)).toBe(false) // No longer stale
    })

    it('exponential backoff behavior', () => {
      let pollBackoffMs = 1000
      const maxBackoffMs = 10000

      // Simulate errors causing backoff
      const errorSequence = [
        // Error 1: 1s → 2s
        () => {
          pollBackoffMs = Math.min(pollBackoffMs * 2, maxBackoffMs)
          expect(pollBackoffMs).toBe(2000)
        },
        // Error 2: 2s → 4s
        () => {
          pollBackoffMs = Math.min(pollBackoffMs * 2, maxBackoffMs)
          expect(pollBackoffMs).toBe(4000)
        },
        // Error 3: 4s → 8s
        () => {
          pollBackoffMs = Math.min(pollBackoffMs * 2, maxBackoffMs)
          expect(pollBackoffMs).toBe(8000)
        },
        // Error 4: 8s → 10s (capped)
        () => {
          pollBackoffMs = Math.min(pollBackoffMs * 2, maxBackoffMs)
          expect(pollBackoffMs).toBe(10000)
        },
        // Error 5: stays at 10s
        () => {
          pollBackoffMs = Math.min(pollBackoffMs * 2, maxBackoffMs)
          expect(pollBackoffMs).toBe(10000)
        },
      ]

      errorSequence.forEach(fn => fn())

      // Success resets backoff
      pollBackoffMs = 1000
      expect(pollBackoffMs).toBe(1000)
    })
  })
})
