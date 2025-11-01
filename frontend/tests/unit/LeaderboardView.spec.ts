import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import LeaderboardView from '@/views/LeaderboardView.vue'
import * as playerApi from '@/services/playerApi'

// Mock the playerApi module
vi.mock('@/services/playerApi')

describe('LeaderboardView', () => {
  const mockLeaderboard = {
    metric: 'total_runs',
    entries: [
      {
        rank: 1,
        player_id: 'player-1',
        player_name: 'Top Player',
        value: 1000,
        additional_stats: {
          batting_average: 55.5,
          strike_rate: 145.0,
        },
      },
      {
        rank: 2,
        player_id: 'player-2',
        player_name: 'Second Player',
        value: 850,
        additional_stats: {
          batting_average: 50.0,
          strike_rate: 140.0,
        },
      },
      {
        rank: 3,
        player_id: 'player-3',
        player_name: 'Third Player',
        value: 750,
        additional_stats: {
          batting_average: 48.0,
          strike_rate: 135.0,
        },
      },
    ],
    updated_at: '2025-01-15T12:00:00Z',
  }

  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('displays loading state initially', () => {
    vi.mocked(playerApi.getLeaderboard).mockImplementation(
      () => new Promise(() => {}), // Never resolves
    )

    const wrapper = mount(LeaderboardView)
    expect(wrapper.text()).toContain('Loading leaderboard')
  })

  it('displays leaderboard title and header', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Leaderboards')
    expect(wrapper.text()).toContain('Most Runs Scored')
  })

  it('displays all leaderboard entries', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Top Player')
    expect(wrapper.text()).toContain('Second Player')
    expect(wrapper.text()).toContain('Third Player')
  })

  it('displays correct rank badges for top 3', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    // Check for medal emojis
    expect(wrapper.text()).toContain('🥇')
    expect(wrapper.text()).toContain('🥈')
    expect(wrapper.text()).toContain('🥉')
  })

  it('displays player values correctly', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('1000.00') // Top player runs
    expect(wrapper.text()).toContain('850.00') // Second player runs
  })

  it('displays additional statistics', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Batting Average')
    expect(wrapper.text()).toContain('Strike Rate')
  })

  it('changes leaderboard when metric is changed', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    const wicketsLeaderboard = {
      ...mockLeaderboard,
      metric: 'total_wickets',
      entries: [
        {
          rank: 1,
          player_id: 'bowler-1',
          player_name: 'Top Bowler',
          value: 50,
          additional_stats: {
            bowling_average: 18.5,
            economy_rate: 6.5,
          },
        },
      ],
    }

    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(wicketsLeaderboard)

    // Change the select value
    const select = wrapper.find('select')
    await select.setValue('total_wickets')

    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Top Bowler')
  })

  it('displays error message when loading fails', async () => {
    vi.mocked(playerApi.getLeaderboard).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Network error')
  })

  it('displays message when no data available', async () => {
    const emptyLeaderboard = {
      ...mockLeaderboard,
      entries: [],
    }
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(emptyLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No data available')
  })

  it('has all metric options in select', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()

    const select = wrapper.find('select')
    const options = select.findAll('option')

    expect(options).toHaveLength(8)
    expect(options[0].text()).toContain('Most Runs')
    expect(options[1].text()).toContain('Best Batting Average')
    expect(options[4].text()).toContain('Most Wickets')
  })

  it('formats updated timestamp correctly', async () => {
    vi.mocked(playerApi.getLeaderboard).mockResolvedValue(mockLeaderboard)

    const wrapper = mount(LeaderboardView)
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toMatch(/Updated:.*Jan.*2025/)
  })
})
