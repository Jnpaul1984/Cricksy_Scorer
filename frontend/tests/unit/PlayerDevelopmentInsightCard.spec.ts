import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PlayerDevelopmentInsightCard from '@/components/PlayerDevelopmentInsightCard.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  getAiInsightReviewState: vi.fn(),
  submitAiInsightReview: vi.fn(),
}))

const insightFixture = {
  player_id: 'player-1',
  summary: 'Player is developing confidence across middle overs.',
  strengths: ['Strong off-side stroke play under pressure.'],
  weaknesses: ['Strike rotation can improve against spin.'],
  recent_form: { label: 'Developing', trend: [0.41, 0.52, 0.63] },
  role_tags: ['batter'],
  recommendations: [
    'Focus on controlled sweep and late-cut technique in spin drills.',
    'Build innings tempo by rotating strike in middle-over scenarios.',
  ],
  ai_metadata: {
    output_type: 'insight',
    is_official_truth: false,
    confidence_score: 0.62,
    limitations: ['Small sample size from recent matches.'],
    source_refs: [{ type: 'player', id: 'player-1', label: 'Player form profile' }],
  },
}

describe('PlayerDevelopmentInsightCard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.getAiInsightReviewState).mockResolvedValue({
      insight_type: 'insight',
      insight_id: 'player-1',
      current_state: 'approved',
      latest_review: null,
      total_reviews: 1,
      is_advisory_only: true,
    })
  })

  it('renders development sections with provided insight data', async () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: insightFixture,
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Main strength')
    expect(wrapper.text()).toContain('Strong off-side stroke play under pressure.')
    expect(wrapper.text()).toContain('Main improvement area')
    expect(wrapper.text()).toContain('Strike rotation can improve against spin.')
    expect(wrapper.text()).toContain('Technical focus')
    expect(wrapper.text()).toContain('Tactical focus')
    expect(wrapper.text()).toContain('Recommended drill category')
    expect(wrapper.find('[data-testid="player-dev-confidence"]').text()).toContain('62%')
    expect(wrapper.find('[data-testid="player-dev-sample-warning"]').text())
      .toContain('Small sample size')
    expect(wrapper.find('[data-testid="player-dev-source-refs"]').text())
      .toContain('Player form profile')
  })

  it('renders review status when review metadata is available', async () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: insightFixture,
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Coach review status')
    expect(wrapper.text()).toContain('Approved')
  })

  it('renders empty state when no insight exists', async () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: null,
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="player-dev-empty"]').exists()).toBe(true)
  })

  it('renders loading state while insight is loading', () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: null,
        loading: true,
      },
    })

    expect(wrapper.find('[data-testid="player-dev-loading"]').exists()).toBe(true)
  })

  it('renders error state when insight request fails', () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: null,
        error: 'Request failed',
      },
    })

    expect(wrapper.find('[data-testid="player-dev-error"]').text()).toContain('Request failed')
  })

  it('shows low-confidence insights as early signals', async () => {
    const wrapper = mount(PlayerDevelopmentInsightCard, {
      props: {
        playerName: 'Test Player',
        playerRole: 'Batter',
        insights: {
          ...insightFixture,
          ai_metadata: {
            ...insightFixture.ai_metadata,
            confidence_score: 0.21,
            limitations: [],
          },
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="player-dev-confidence"]').text())
      .toContain('Low confidence (early signal)')
  })
})
