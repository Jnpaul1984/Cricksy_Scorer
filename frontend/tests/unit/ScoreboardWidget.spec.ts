import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

import simulatedMatch from '../../../simulated_t20_match.json'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { useGameStore } from '@/stores/gameStore'

describe('ScoreboardWidget', () => {
  it('displays the winner and match result', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(ScoreboardWidget, {
      global: { plugins: [pinia] },
      props: {
        gameId: 'test-game-id'
      }
    })

    const store = useGameStore()
    // Stub networked methods
    ;(store as any).loadGame = vi.fn().mockResolvedValue(undefined)
    ;(store as any).refreshInterruptions = vi.fn().mockResolvedValue(undefined)
    ;(store as any).initLive = vi.fn().mockResolvedValue(undefined)
    ;(store as any).stopLive = vi.fn()

    // Seed minimal game state so result banner is shown
    store.currentGame = {
      id: 'test-game-id',
      team_a: { name: simulatedMatch.teams[0], players: [] },
      team_b: { name: simulatedMatch.teams[1], players: [] },
      status: 'completed',
      current_inning: 2,
      result: { result_text: simulatedMatch.result.summary } as any,
    } as any

    await nextTick()

    expect(wrapper.text()).toContain(simulatedMatch.result.winner)
    expect(wrapper.text()).toContain(simulatedMatch.result.summary)
  })
})
