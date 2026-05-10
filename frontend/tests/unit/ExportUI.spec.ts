import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ExportUI from '@/components/ExportUI.vue'
import { getAnalystExportData } from '@/services/api'

vi.mock('@/services/api', () => ({
  getAnalystExportData: vi.fn(),
}))

const BaseButtonStub = defineComponent({
  name: 'BaseButtonStub',
  emits: ['click'],
  setup(_props, { emit, slots }) {
    return () => h('button', { class: 'base-button-stub', onClick: () => emit('click') }, slots.default?.())
  },
})

const BaseCardStub = defineComponent({
  name: 'BaseCardStub',
  setup(_props, { slots }) {
    return () => h('div', { class: 'base-card-stub' }, slots.default?.())
  },
})

describe('ExportUI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls backend export API instead of generating fake rows', async () => {
    vi.mocked(getAnalystExportData).mockResolvedValue({
      rows: [],
      meta: { row_count: 0, empty_reason: 'no_rows_for_match_or_filters' },
    })

    const wrapper = mount(ExportUI, {
      props: {
        data: [{ id: 'm-1' }],
        matchId: 'm-1',
      },
      global: {
        stubs: {
          BaseButton: BaseButtonStub,
          BaseCard: BaseCardStub,
        },
      },
    })

    const buttons = wrapper.findAll('button.base-button-stub')
    await buttons[0].trigger('click')
    await wrapper.find('input[placeholder="Search by name or ID..."]').setValue('p-1')
    const actionButtons = wrapper.findAll('.export-actions button.base-button-stub')
    await actionButtons[1].trigger('click')

    expect(getAnalystExportData).toHaveBeenCalledWith(
      {
        dateFrom: undefined,
        dateTo: undefined,
        player: 'p-1',
        dismissalType: undefined,
        phase: undefined,
      },
      'm-1',
    )
  })

  it('shows a safe empty state message when export data is unavailable', async () => {
    vi.mocked(getAnalystExportData).mockResolvedValue({
      rows: [],
      meta: { row_count: 0, empty_reason: 'no_data' },
    })

    const wrapper = mount(ExportUI, {
      props: {
        data: [],
        matchId: null,
      },
      global: {
        stubs: {
          BaseButton: BaseButtonStub,
          BaseCard: BaseCardStub,
        },
      },
    })

    const buttons = wrapper.findAll('button.base-button-stub')
    await buttons[0].trigger('click')
    const actionButtons = wrapper.findAll('.export-actions button.base-button-stub')
    await actionButtons[1].trigger('click')

    expect(wrapper.text()).toContain('No export data available for the current context/filters.')
  })
})
