import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'

import { listVideoSessions, type VideoAnalysisJob } from '@/services/coachPlusVideoService'
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
const videoStoreMock = reactive({
  error: null as string | null,
  uploading: null as { status: string } | null,
  uploadProgress: 0,
  cleanup: videoStoreCleanup,
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
  listCoachAssignedPlayers: vi.fn(),
  listPlayerDevelopmentPlans: vi.fn(),
  reviewPlayerDevelopmentPlan: vi.fn(),
}))

vi.mock('@/services/playerApi', () => ({
  getPlayerProfile: vi.fn(),
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
    vi.mocked(listVideoSessions).mockResolvedValue([])
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

    const playerDevApi = await import('@/services/playerDevelopmentApi')
    const playerApi = await import('@/services/playerApi')
    vi.mocked(playerDevApi.listCoachAssignedPlayers).mockResolvedValue([
      {
        id: 'assign-1',
        coach_user_id: 'coach-1',
        player_profile_id: 'player-1',
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ])
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue({
      player_id: 'player-1',
      player_name: 'Player One',
    } as any)

    const wrapper = mountView()
    await flushAsync()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushAsync()

    expect(wrapper.text()).toContain('Discipline')
    expect(wrapper.text()).toContain('Create new player')
    expect(wrapper.text()).not.toContain('Player IDs (comma-separated)')
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
        report: { summary: 'Done' },
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
  })
})
