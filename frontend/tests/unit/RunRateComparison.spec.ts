import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'

import RunRateComparison from '@/components/analytics/RunRateComparison.vue'

describe('RunRateComparison.vue', () => {
  const basicProps = {
    currentRunRate: 6.5,
    currentScore: 52,
    ballsBowled: 48,
    oversLimit: 20
  }

  it('renders the component', () => {
    const wrapper = mount(RunRateComparison, {
      props: basicProps
    })

    expect(wrapper.find('.run-rate-comparison').exists()).toBe(true)
  })

  it('displays current run rate', () => {
    const wrapper = mount(RunRateComparison, {
      props: basicProps
    })

    const text = wrapper.text()
    expect(text).toContain('6.50')
    expect(text).toContain('Current Run Rate')
  })

  it('does not display required run rate when not chasing', () => {
    const wrapper = mount(RunRateComparison, {
      props: basicProps
    })

    const text = wrapper.text()
    expect(text).not.toContain('Required Run Rate')
  })

  it('displays required run rate when chasing', () => {
    const chasingProps = {
      ...basicProps,
      requiredRunRate: 8.5,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: chasingProps
    })

    const text = wrapper.text()
    expect(text).toContain('8.50')
    expect(text).toContain('Required Run Rate')
  })

  it('shows difference when chasing', () => {
    const chasingProps = {
      ...basicProps,
      currentRunRate: 6.5,
      requiredRunRate: 8.5,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: chasingProps
    })

    const text = wrapper.text()
    expect(text).toContain('Difference')
    expect(text).toContain('2.00')
    expect(text).toContain('behind')
  })

  it('shows ahead when current rate exceeds required rate', () => {
    const aheadProps = {
      ...basicProps,
      currentRunRate: 9.5,
      requiredRunRate: 8.0,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: aheadProps
    })

    const text = wrapper.text()
    expect(text).toContain('ahead')
  })

  it('shows behind when current rate is less than required rate', () => {
    const behindProps = {
      ...basicProps,
      currentRunRate: 6.0,
      requiredRunRate: 8.5,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: behindProps
    })

    const text = wrapper.text()
    expect(text).toContain('behind')
  })

  it('displays empty state when no data', () => {
    const noDataProps = {
      currentRunRate: 0,
      currentScore: 0,
      ballsBowled: 0,
      oversLimit: 20
    }

    const wrapper = mount(RunRateComparison, {
      props: noDataProps
    })

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No run rate data available')
  })

  it('displays chart when data is available', () => {
    const propsWithData = {
      ...basicProps,
      oversData: [
        { over: 1, runRate: 6.0 },
        { over: 2, runRate: 6.5 },
        { over: 3, runRate: 7.0 }
      ]
    }

    const wrapper = mount(RunRateComparison, {
      props: propsWithData
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
  })

  it('displays stats summary', () => {
    const wrapper = mount(RunRateComparison, {
      props: basicProps
    })

    expect(wrapper.find('.stats-summary').exists()).toBe(true)
    expect(wrapper.findAll('.stat-item').length).toBeGreaterThan(0)
  })

  it('applies correct CSS class for ahead status', () => {
    const aheadProps = {
      ...basicProps,
      currentRunRate: 9.0,
      requiredRunRate: 7.0,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: aheadProps
    })

    const aheadValue = wrapper.find('.stat-value.ahead')
    expect(aheadValue.exists()).toBe(true)
  })

  it('applies correct CSS class for behind status', () => {
    const behindProps = {
      ...basicProps,
      currentRunRate: 6.0,
      requiredRunRate: 8.0,
      targetScore: 150
    }

    const wrapper = mount(RunRateComparison, {
      props: behindProps
    })

    const behindValue = wrapper.find('.stat-value.behind')
    expect(behindValue.exists()).toBe(true)
  })

  it('handles zero required run rate', () => {
    const zeroRRRProps = {
      ...basicProps,
      requiredRunRate: 0,
      targetScore: 50
    }

    const wrapper = mount(RunRateComparison, {
      props: zeroRRRProps
    })

    // Should not display required run rate section when RRR is 0
    const text = wrapper.text()
    expect(text).toContain('Current Run Rate')
  })

  it('handles null required run rate', () => {
    const nullRRRProps = {
      ...basicProps,
      requiredRunRate: null,
      targetScore: null
    }

    const wrapper = mount(RunRateComparison, {
      props: nullRRRProps
    })

    const text = wrapper.text()
    expect(text).not.toContain('Required Run Rate')
  })

  it('updates when props change', async () => {
    const wrapper = mount(RunRateComparison, {
      props: basicProps
    })

    expect(wrapper.text()).toContain('6.50')

    await wrapper.setProps({
      ...basicProps,
      currentRunRate: 7.5,
      currentScore: 60
    })

    expect(wrapper.text()).toContain('7.50')
  })

  it('handles high run rates', () => {
    const highRateProps = {
      ...basicProps,
      currentRunRate: 15.0,
      requiredRunRate: 12.0,
      targetScore: 200
    }

    const wrapper = mount(RunRateComparison, {
      props: highRateProps
    })

    const text = wrapper.text()
    expect(text).toContain('15.00')
    expect(text).toContain('12.00')
  })

  it('handles low run rates', () => {
    const lowRateProps = {
      ...basicProps,
      currentRunRate: 2.5,
      currentScore: 10,
      ballsBowled: 24
    }

    const wrapper = mount(RunRateComparison, {
      props: lowRateProps
    })

    const text = wrapper.text()
    expect(text).toContain('2.50')
  })

  it('displays stats in correct format', () => {
    const wrapper = mount(RunRateComparison, {
      props: {
        ...basicProps,
        currentRunRate: 6.789,
        requiredRunRate: 8.123
      }
    })

    const text = wrapper.text()
    // Should display with 2 decimal places
    expect(text).toContain('6.79')
    expect(text).toContain('8.12')
  })

  it('calculates difference correctly', () => {
    const props = {
      ...basicProps,
      currentRunRate: 6.5,
      requiredRunRate: 8.5
    }

    const wrapper = mount(RunRateComparison, {
      props
    })

    const text = wrapper.text()
    // Difference should be 2.00
    expect(text).toContain('2.00')
  })
})
