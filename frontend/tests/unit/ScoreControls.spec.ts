import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ScoreControls from '@/components/scoring/ScoreControls.vue'

const scoreRuns = vi.fn().mockResolvedValue(undefined)
const scoreExtra = vi.fn().mockResolvedValue(undefined)

vi.mock('@/stores/gameStore', () => ({
  useGameStore: () => ({
    canScoreDelivery: true,
    scoreRuns,
    scoreExtra,
  }),
}))

describe('ScoreControls', () => {
  const baseProps = {
    canScore: true,
    gameId: 'game-123',
    strikerId: 'striker-1',
    nonStrikerId: 'non-striker-1',
    bowlerId: 'bowler-1',
    commentary: 'test notes',
  }

  beforeEach(() => {
    scoreRuns.mockReset().mockResolvedValue(undefined)
    scoreExtra.mockReset().mockResolvedValue(undefined)
  })

  it('disables all action buttons when scoring is blocked', () => {
    const wrapper = mount(ScoreControls, {
      props: { ...baseProps, canScore: false },
    })

    const runButtons = wrapper.findAll('.runs-grid button')
    const extras = wrapper.findAll('.extras-grid button')
    const wicket = wrapper.find('.wicket-row button')

    expect(runButtons.every((btn) => btn.attributes('disabled') !== undefined)).toBe(true)
    expect(extras.every((btn) => btn.attributes('disabled') !== undefined)).toBe(true)
    expect(wicket.attributes('disabled')).toBeDefined()
  })

  it('leaves scoring buttons enabled when allowed', () => {
    const wrapper = mount(ScoreControls, {
      props: baseProps,
    })

    const runButtons = wrapper.findAll('.runs-grid button')
    const extras = wrapper.findAll('.extras-grid button')
    const wicket = wrapper.find('.wicket-row button')

    expect(runButtons.some((btn) => btn.attributes('disabled') !== undefined)).toBe(false)
    expect(extras.some((btn) => btn.attributes('disabled') !== undefined)).toBe(false)
    expect(wicket.attributes('disabled')).toBeUndefined()
  })

  it('uses the store scoring action and emits when a run button is clicked', async () => {
    const wrapper = mount(ScoreControls, {
      props: baseProps,
    })

    const runButton = wrapper.get('[data-testid="run-1"]')
    expect(runButton).toBeDefined()

    await runButton.trigger('click')
    await flushPromises()

    expect(scoreRuns).toHaveBeenCalledTimes(1)
    expect(scoreRuns).toHaveBeenCalledWith(baseProps.gameId, 1, null)
    expect(wrapper.emitted('scored')).toBeTruthy()
  })

  it('does not trigger scoring when delivery gate is closed', async () => {
    const wrapper = mount(ScoreControls, {
      props: { ...baseProps, canScore: false },
    })

    const runButton = wrapper.get('[data-testid="run-4"]')
    expect(runButton.attributes('disabled')).toBeDefined()

    await runButton.trigger('click')
    await flushPromises()

    expect(scoreRuns).not.toHaveBeenCalled()
    expect(wrapper.emitted('scored')).toBeUndefined()
  })
})
