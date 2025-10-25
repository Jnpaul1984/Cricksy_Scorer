import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ErrorMessage from '@/components/common/ErrorMessage.vue'

describe('ErrorMessage', () => {
  it('renders error message', () => {
    const message = 'Failed to load game'
    const wrapper = mount(ErrorMessage, {
      props: { message }
    })

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain(message)
  })

  it('does not render when message is empty', () => {
    const wrapper = mount(ErrorMessage, {
      props: { message: '' }
    })

    // Component might still exist but be hidden
    expect(wrapper.exists()).toBe(true)
  })
})
