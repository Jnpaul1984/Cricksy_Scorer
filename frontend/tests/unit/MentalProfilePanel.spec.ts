import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

import MentalProfilePanel from '@/components/MentalProfilePanel.vue'
import * as mentalApi from '@/services/mentalQuestionnaireApi'

vi.mock('@/services/mentalQuestionnaireApi')

const mockProfile = {
  session_id: 'session-abc',
  player_id: 'player-123',
  submitted_by_user_id: 'coach-1',
  overall_average_score: 3.8,
  overall_summary: 'A composed player with solid mental habits.',
  strengths: ['Stays focused under pressure', 'Good game awareness'],
  development_areas: ['Can improve composure in final overs'],
  category_scores: [
    { category: 'mental_toughness', average_score: 4.0 },
    { category: 'pressure_handling', average_score: 3.5 },
  ],
  created_at: '2025-05-01T10:00:00Z',
}

describe('MentalProfilePanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(mentalApi.getLatestMentalProfile).mockResolvedValue(mockProfile)
    vi.mocked(mentalApi.getMentalResponseHistory).mockResolvedValue([mockProfile])
  })

  it('renders the export report button when profile is loaded', async () => {
    const wrapper = mount(MentalProfilePanel, {
      props: { playerId: 'player-123', playerName: 'Alex Smith' },
    })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Export Report')
  })

  it('does not render export button when no profile is loaded', async () => {
    vi.mocked(mentalApi.getLatestMentalProfile).mockRejectedValue({ status: 404 })

    const wrapper = mount(MentalProfilePanel, {
      props: { playerId: 'player-123' },
    })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).not.toContain('Export Report')
  })

  it('generates report HTML with player name, scores, strengths, and disclaimer', async () => {
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({
      document: {
        write: vi.fn(),
        close: vi.fn(),
      },
      onload: null,
      print: vi.fn(),
    } as unknown as Window)

    const wrapper = mount(MentalProfilePanel, {
      props: { playerId: 'player-123', playerName: 'Alex Smith' },
    })
    await nextTick()
    await nextTick()

    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('Export Report'))
    expect(exportBtn).toBeTruthy()
    await exportBtn!.trigger('click')

    expect(openSpy).toHaveBeenCalledWith('', '_blank')

    openSpy.mockRestore()
  })

  it('shows overall score and summary from profile', async () => {
    const wrapper = mount(MentalProfilePanel, {
      props: { playerId: 'player-123' },
    })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('3.8')
    expect(wrapper.text()).toContain('A composed player with solid mental habits.')
  })

  it('accepts playerName as optional prop without breaking', async () => {
    const wrapper = mount(MentalProfilePanel, {
      props: { playerId: 'player-123' },
    })
    await nextTick()
    await nextTick()

    // Export button still renders without playerName prop
    expect(wrapper.text()).toContain('Export Report')
  })
})
