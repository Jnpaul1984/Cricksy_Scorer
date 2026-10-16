import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import FieldSectionSelector from '@/components/scoring/FieldSectionSelector.vue'

describe('FieldSectionSelector', () => {
  it('selects a canonical regular-scorer section and clears it', async () => {
    const wrapper = mount(FieldSectionSelector, { props: { modelValue: null } })
    await wrapper.get('[data-testid="field-section-6"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[6]])
    await wrapper.setProps({ modelValue: 6 })
    await wrapper.get('[data-testid="clear-field-section"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[6], [null]])
  })

  it('does not emit a section while disabled', async () => {
    const wrapper = mount(FieldSectionSelector, { props: { modelValue: null, disabled: true } })
    expect(wrapper.get('[data-testid="field-section-2"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="field-section-2"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('renders eight distinct grid targets that receive native click events', () => {
    const wrapper = mount(FieldSectionSelector, { props: { modelValue: null } })
    const positions = [1, 2, 3, 4, 5, 6, 7, 8].map((section) => {
      const element = wrapper.get(`[data-testid="field-section-${section}"]`).element as HTMLElement
      return `${element.className}:${getComputedStyle(element).gridColumn}/${getComputedStyle(element).gridRow}`
    })
    expect(new Set(positions)).toHaveLength(8)
    for (let section = 1; section <= 8; section += 1) {
      ;(wrapper.get(`[data-testid="field-section-${section}"]`).element as HTMLButtonElement).click()
    }
    expect(wrapper.emitted('update:modelValue')).toEqual([[1], [2], [3], [4], [5], [6], [7], [8]])
  })
})
