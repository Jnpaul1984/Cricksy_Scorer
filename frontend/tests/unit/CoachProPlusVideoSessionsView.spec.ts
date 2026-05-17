import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'

import { listVideoSessions } from '@/services/coachPlusVideoService'
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

  it('keeps the upgrade gate for users without coach access', async () => {
    const wrapper = mountView()
    await flushAsync()

    expect(wrapper.text()).toContain('Unlock Video Sessions')
  })
})
