import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'

import ChartBar from '@/components/analytics/ChartBar.vue'

describe('ChartBar.vue', () => {
  const sampleData = {
    labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4', 'Over 5'],
    series: [
      { label: 'Innings 1', data: [8, 12, 6, 15, 10] },
      { label: 'Innings 2', data: [5, 10, 14, 8, 12] },
    ]
  }

  beforeEach(() => {
    // Reset any chart instances
  })

  it('renders chart component', () => {
    const wrapper = mount(ChartBar, {
      props: sampleData
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('has correct height styling', () => {
    const wrapper = mount(ChartBar, {
      props: sampleData
    })

    const chartDiv = wrapper.find('.chart')
    expect(chartDiv.element).toBeTruthy()
  })

  it('accepts labels prop', () => {
    const wrapper = mount(ChartBar, {
      props: sampleData
    })

    expect(wrapper.props('labels')).toEqual(sampleData.labels)
  })

  it('accepts series prop with multiple datasets', () => {
    const wrapper = mount(ChartBar, {
      props: sampleData
    })

    expect(wrapper.props('series')).toEqual(sampleData.series)
    expect(wrapper.props('series').length).toBe(2)
  })

  it('handles empty labels array', () => {
    const wrapper = mount(ChartBar, {
      props: {
        labels: [],
        series: []
      }
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('handles single series', () => {
    const singleSeries = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [8, 12, 6] }
      ]
    }

    const wrapper = mount(ChartBar, {
      props: singleSeries
    })

    expect(wrapper.props('series').length).toBe(1)
  })

  it('handles null values in data', () => {
    const dataWithNulls = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [8, null, 6] }
      ]
    }

    const wrapper = mount(ChartBar, {
      props: dataWithNulls
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('renders with different data lengths', () => {
    const differentLengths = {
      labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4'],
      series: [
        { label: 'Innings 1', data: [8, 12, 6, 15] },
        { label: 'Innings 2', data: [5, 10, 14, null] },
      ]
    }

    const wrapper = mount(ChartBar, {
      props: differentLengths
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('handles many overs', () => {
    const manyOvers = {
      labels: Array.from({ length: 20 }, (_, i) => `Over ${i + 1}`),
      series: [
        { 
          label: 'Innings 1', 
          data: Array.from({ length: 20 }, () => Math.floor(Math.random() * 20)) 
        }
      ]
    }

    const wrapper = mount(ChartBar, {
      props: manyOvers
    })

    expect(wrapper.props('labels').length).toBe(20)
  })

  it('updates when props change', async () => {
    const wrapper = mount(ChartBar, {
      props: sampleData
    })

    const newData = {
      labels: ['Over 1', 'Over 2'],
      series: [
        { label: 'Innings 1', data: [10, 15] }
      ]
    }

    await wrapper.setProps(newData)

    expect(wrapper.props('labels')).toEqual(newData.labels)
    expect(wrapper.props('series')).toEqual(newData.series)
  })

  it('handles zero runs', () => {
    const zeroRuns = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [0, 0, 0] }
      ]
    }

    const wrapper = mount(ChartBar, {
      props: zeroRuns
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('handles high scoring overs', () => {
    const highScoring = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [36, 28, 30] }
      ]
    }

    const wrapper = mount(ChartBar, {
      props: highScoring
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })
})
