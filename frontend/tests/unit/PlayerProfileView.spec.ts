import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

import * as playerApi from '@/services/playerApi'
import PlayerProfileView from '@/views/PlayerProfileView.vue'

// Mock the router
vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { playerId: 'test-player-123' },
  }),
}))

// Mock the playerApi module
vi.mock('@/services/playerApi')

describe('PlayerProfileView', () => {
  const mockProfile = {
    player_id: 'test-player-123',
    player_name: 'Test Player',
    total_matches: 10,
    total_innings_batted: 10,
    total_runs_scored: 450,
    total_balls_faced: 300,
    total_fours: 35,
    total_sixes: 12,
    times_out: 8,
    highest_score: 95,
    centuries: 0,
    half_centuries: 4,
    batting_average: 56.25,
    strike_rate: 150.0,
    total_innings_bowled: 8,
    total_overs_bowled: 30.0,
    total_runs_conceded: 240,
    total_wickets: 12,
    best_bowling_figures: '3/25',
    five_wicket_hauls: 0,
    maidens: 2,
    bowling_average: 20.0,
    economy_rate: 8.0,
    catches: 5,
    stumpings: 0,
    run_outs: 2,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-15T00:00:00Z',
    achievements: [
      {
        id: 1,
        player_id: 'test-player-123',
        game_id: 'game-456',
        achievement_type: 'half_century',
        title: 'Half Century Hero',
        description: 'Scored 50 runs',
        badge_icon: '🏏',
        earned_at: '2025-01-10T00:00:00Z',
        metadata: {},
      },
    ],
  }

  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('displays loading state initially', () => {
    vi.mocked(playerApi.getPlayerProfile).mockImplementation(
      () => new Promise(() => {}), // Never resolves
    )

    const wrapper = mount(PlayerProfileView)
    expect(wrapper.text()).toContain('Loading player profile')
  })

  it('displays player profile data when loaded', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick() // Wait for async load

    expect(wrapper.text()).toContain('Test Player')
    expect(wrapper.text()).toContain('test-player-123')
  })

  it('displays batting statistics correctly', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('450') // Total runs
    expect(wrapper.text()).toContain('56.25') // Batting average
    expect(wrapper.text()).toContain('150.00') // Strike rate
  })

  it('displays bowling statistics correctly', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('12') // Wickets
    expect(wrapper.text()).toContain('20.00') // Bowling average
    expect(wrapper.text()).toContain('8.00') // Economy rate
    expect(wrapper.text()).toContain('3/25') // Best figures
  })

  it('displays fielding statistics correctly', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('5') // Catches
    expect(wrapper.text()).toContain('2') // Run outs
  })

  it('displays achievements when present', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Half Century Hero')
    expect(wrapper.text()).toContain('Scored 50 runs')
    expect(wrapper.text()).toContain('🏏')
  })

  it('displays message when no achievements', async () => {
    const profileWithoutAchievements = { ...mockProfile, achievements: [] }
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(profileWithoutAchievements)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No achievements yet')
  })

  it('displays error message when loading fails', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Network error')
  })

  it('formats dates correctly', async () => {
    vi.mocked(playerApi.getPlayerProfile).mockResolvedValue(mockProfile)

    const wrapper = mount(PlayerProfileView)
    await nextTick()
    await nextTick()

    // Achievement date should be formatted
    const achievementText = wrapper.text()
    expect(achievementText).toMatch(/Earned:.*Jan.*2025/)
  })
})
