import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'

import {
  createCoachPrivatePlayer,
  listCoachPlayers,
  listVideoSessions,
  type VideoAnalysisJob,
} from '@/services/coachPlusVideoService'
import CoachProPlusVideoSessionsView from '@/views/CoachProPlusVideoSessionsView.vue'

const authStoreMock = reactive({
  canCoach: false,
  isCoach: false,
  isCoachPro: false,
  isCoachProPlus: false,
  isSuperuser: false,
  currentUser: null,
  planName: 'free',
  role: 'free',
})

const videoStoreCleanup = vi.fn()
const videoStoreCreateSession = vi.fn()
const videoStoreMock = reactive({
  error: null as string | null,
  uploading: null as { status: string } | null,
  uploadProgress: 0,
  cleanup: videoStoreCleanup,
  createSession: videoStoreCreateSession,
})

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => authStoreMock,
}))

vi.mock('@/stores/coachPlusVideoStore', () => ({
  useCoachPlusVideoStore: () => videoStoreMock,
}))

vi.mock('@/services/coachPlusVideoService', () => ({
  ApiError: class ApiError extends Error {},
  listVideoSessions: vi.fn(),
  listCoachPlayers: vi.fn(),
  createCoachPrivatePlayer: vi.fn(),
  getVideoStreamUrl: vi.fn(),
  calculateCompliance: vi.fn(),
  getJobOutcomes: vi.fn(),
  generateCoachSuggestions: vi.fn(),
  getCoachSuggestions: vi.fn(),
}))

vi.mock('@/services/playerDevelopmentApi', () => ({
  PlayerDevelopmentApiError: class PlayerDevelopmentApiError extends Error {
    isUnauthorized() {
      return false
    }

    isNotFound() {
      return false
    }

    isConflict() {
      return false
    }

    isValidationError() {
      return false
    }
  },
  listPlayerDevelopmentPlans: vi.fn(),
  reviewPlayerDevelopmentPlan: vi.fn(),
}))

async function flushAsync() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

function mountView() {
  return mount(CoachProPlusVideoSessionsView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        GoalsPanel: true,
        SessionComparison: true,
        CoachSuggestionsPanel: true,
        CoachingSkillRecommendationReviewCard: true,
        PlayerSummaryCard: true,
      },
    },
  })
}

describe('CoachProPlusVideoSessionsView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    authStoreMock.canCoach = false
    authStoreMock.isCoach = false
    authStoreMock.isCoachPro = false
    authStoreMock.isCoachProPlus = false
    authStoreMock.isSuperuser = false
    authStoreMock.currentUser = null
    authStoreMock.planName = 'free'
    authStoreMock.role = 'free'
    videoStoreMock.error = null
    videoStoreMock.uploading = null
    videoStoreMock.uploadProgress = 0
    videoStoreMock.cleanup = videoStoreCleanup
    videoStoreMock.createSession = videoStoreCreateSession
    vi.mocked(listVideoSessions).mockResolvedValue([])
    vi.mocked(listCoachPlayers).mockResolvedValue([])
  })

  it('shows the video sessions workspace for authorized org pro reviewers', async () => {
    authStoreMock.canCoach = true
    authStoreMock.isCoachProPlus = true
    authStoreMock.role = 'org_pro'

    const wrapper = mountView()
    await flushAsync()

    expect(wrapper.text()).toContain('Video Sessions')
    expect(wrapper.text()).not.toContain('Unlock Video Sessions')
  })

  it('uses player-centered create form fields instead of manual player ID textarea', async () => {
    authStoreMock.canCoach = true
    authStoreMock.isCoachProPlus = true
    authStoreMock.role = 'coach_pro_plus'

    vi.mocked(listCoachPlayers).mockResolvedValue([
      {
        player_id: 'player-1',
        player_name: 'Player One',
        date_of_birth: null,
        assignment_active: true,
      },
    ])

    const wrapper = mountView()
    await flushAsync()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushAsync()

    expect(wrapper.text()).toContain('Discipline')
    expect(wrapper.text()).toContain('Add coaching player')
    expect(wrapper.text()).not.toContain('existing Match Setup workflow')
    expect(wrapper.text()).not.toContain('Player IDs (comma-separated)')
  })

  it('creates a private coaching player and immediately selects it', async () => {
    authStoreMock.canCoach = true
    authStoreMock.isCoachProPlus = true
    authStoreMock.role = 'coach_pro_plus'

    const createdPlayer = {
      player_id: 'coach-player-new',
      player_name: 'Private Player',
      date_of_birth: '2010-06-15',
      assignment_active: true,
    }
    vi.mocked(listCoachPlayers)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdPlayer])
    vi.mocked(createCoachPrivatePlayer).mockResolvedValue(createdPlayer)

    const wrapper = mountView()
    await flushAsync()
    await wrapper.find('button.btn-primary').trigger('click')
    await flushAsync()
    await wrapper.find('.btn-link-inline').trigger('click')
    await wrapper.find('#new-player-name').setValue('Private Player')
    await wrapper.find('#new-player-dob').setValue('2010-06-15')
    await wrapper.find('.player-create-panel .btn-primary').trigger('click')
    await flushAsync()

    expect(createCoachPrivatePlayer).toHaveBeenCalledWith({
      player_name: 'Private Player',
      date_of_birth: '2010-06-15',
    })
    expect((wrapper.find('#primary-player').element as HTMLSelectElement).value).toBe(
      'coach-player-new',
    )
    expect(wrapper.findAll('#primary-player option[value="coach-player-new"]')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Quick add coaching player')
  })

  it('preserves a created player when refresh fails and reconciles it without duplicates later', async () => {
    authStoreMock.canCoach = true
    authStoreMock.isCoachProPlus = true
    authStoreMock.role = 'coach_pro_plus'

    const createdPlayer = {
      player_id: 'coach-player-preserved',
      player_name: 'Preserved Player',
      date_of_birth: null,
      assignment_active: true,
    }
    vi.mocked(listCoachPlayers)
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('Temporary player refresh failure'))
      .mockResolvedValueOnce([createdPlayer])
    vi.mocked(createCoachPrivatePlayer).mockResolvedValue(createdPlayer)

    const wrapper = mountView()
    await flushAsync()
    await wrapper.find('button.btn-primary').trigger('click')
    await flushAsync()
    await wrapper.find('.btn-link-inline').trigger('click')
    await wrapper.find('#new-player-name').setValue('Preserved Player')
    await wrapper.find('.player-create-panel .btn-primary').trigger('click')
    await flushAsync()

    const selector = wrapper.find('#primary-player')
    expect((selector.element as HTMLSelectElement).value).toBe('coach-player-preserved')
    expect(wrapper.findAll('#primary-player option[value="coach-player-preserved"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('Temporary player refresh failure')
    expect(wrapper.text()).not.toContain('Quick add coaching player')
    expect(createCoachPrivatePlayer).toHaveBeenCalledTimes(1)

    await (wrapper.vm as unknown as { fetchAssignedPlayers: () => Promise<void> }).fetchAssignedPlayers()
    await flushAsync()

    expect(wrapper.findAll('#primary-player option[value="coach-player-preserved"]')).toHaveLength(1)
    expect((wrapper.find('#primary-player').element as HTMLSelectElement).value).toBe(
      'coach-player-preserved',
    )
    expect(wrapper.text()).not.toContain('Temporary player refresh failure')
    expect(createCoachPrivatePlayer).toHaveBeenCalledTimes(1)
  })

  it('keeps the upgrade gate for users without coach access', async () => {
    const wrapper = mountView()
    await flushAsync()

    expect(wrapper.text()).toContain('Unlock Video Sessions')
  })

  it('renders repetition windows in the results modal when V2 repetitions are present', async () => {
    authStoreMock.canCoach = true
    authStoreMock.isCoachPro = true
    authStoreMock.role = 'coach_pro'

    const wrapper = mountView()
    await flushAsync()

    const vm = wrapper.vm as unknown as {
      showResultsModal: boolean
      selectedJob: VideoAnalysisJob | null
    }

    vm.selectedJob = {
      id: 'job-reps',
      session_id: 'session-reps',
      sample_fps: 10,
      include_frames: false,
      status: 'done',
      error_message: null,
      sqs_message_id: null,
      deep_results: {
        pose_summary: { total_frames: 120, sampled_frames: 30, frames_with_pose: 28, detection_rate_percent: 93, video_fps: 30 },
        report: {
          summary: 'Done',
          v2_session_analysis: {
            strengths: [
              {
                metric_id: 'bowling_release_height_ratio',
                discipline: 'bowling',
                severity: 'medium',
                confidence_score: 0.84,
                valid_sample_count: 3,
                summary: 'Repeated strong release height evidence.',
                supporting_repetition_ids: ['rep-1'],
                limitations: [],
              },
            ],
            recurring_concerns: [
              {
                metric_id: 'bowling_head_alignment_ratio',
                discipline: 'bowling',
                severity: 'low',
                confidence_score: 0.71,
                valid_sample_count: 3,
                summary: 'Repeated needs-attention head alignment evidence.',
                supporting_repetition_ids: ['rep-1'],
                limitations: [],
              },
            ],
            consistency_observations: [
              {
                metric_id: 'bowling_release_height_ratio',
                discipline: 'bowling',
                phase: 'release',
                method: 'normalized_spread',
                classification: 'high',
                value: 0.03,
                confidence_score: 0.84,
                valid_sample_count: 3,
                excluded_repetition_count: 0,
                limitations: [],
              },
            ],
            best_repetition: {
              available: true,
              repetition_id: 'rep-1',
              rationale: 'Selected because this repetition had 2 strong metric signals and 0 needs-attention signals.',
              confidence_score: 0.84,
              supporting_metrics: ['bowling_release_height_ratio'],
            },
            needs_work_repetition: {
              available: false,
              reason: 'No repetition had enough negative metric evidence for needs-work selection.',
              supporting_metrics: [],
            },
          },
        },
        findings: { findings: [] },
        meta: {
          repetition_segmentation: {
            enabled: true,
            validity_state: 'VALID',
            repetitions_count: 1,
          },
          phase_recognition: {
            enabled: true,
            validity_state: 'LOW_CONFIDENCE',
            phases_count: 1,
          },
        },
        v2: {
          repetitions: [
            {
              repetition_id: 'rep-1',
              discipline: 'bowling',
              action_type: 'bowling_delivery',
              start_ts: 0.5,
              end_ts: 1.1,
              start_frame: 15,
              end_frame: 33,
              segmentation_confidence: 0.84,
              validity_state: 'VALID',
            },
          ],
          phases: [
            {
              phase_id: 'rep-1:phase:1',
              repetition_id: 'rep-1',
              phase_name: 'contact_proxy_window',
              start_ts: 0.8,
              end_ts: 0.9,
              start_frame: 24,
              end_frame: 27,
              confidence: 0.58,
              validity_state: 'LOW_CONFIDENCE',
              requires_object_evidence: true,
              limitations: ['proxy only'],
            },
          ],
        },
      },
      results: null,
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    } as unknown as VideoAnalysisJob
    vm.showResultsModal = true
    await flushAsync()

    expect(wrapper.text()).toContain('Repetitions')
    expect(wrapper.text()).toContain('Rep 1 — Bowling Delivery')
    expect(wrapper.text()).toContain('Valid')
    expect(wrapper.text()).toContain('Contact Proxy Window')
    expect(wrapper.text()).toContain('object evidence')
    expect(wrapper.text()).toContain('Technical strengths')
    expect(wrapper.text()).toContain('Repeated strong release height evidence.')
    expect(wrapper.text()).toContain('Recurring concerns')
    expect(wrapper.text()).toContain('Consistency & repeatability')
    expect(wrapper.text()).toContain('Representative repetitions')
  })
})
