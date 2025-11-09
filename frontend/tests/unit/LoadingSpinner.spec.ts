import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

describe('LoadingSpinner', () => {
  it('renders loading spinner', () => {
    const wrapper = mount(LoadingSpinner)
    
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.find('.loading-spinner').exists()).toBe(true)
  })

  it('displays custom message when provided', () => {
    const message = 'Loading game data...'
    const wrapper = mount(LoadingSpinner, {
      props: { message }
    })
    
    expect(wrapper.text()).toContain(message)
  })
})

