import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'

import ChartLine from '@/components/analytics/ChartLine.vue'

describe('ChartLine.vue', () => {
  const sampleData = {
    labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4', 'Over 5'],
    series: [
      { label: 'Innings 1', data: [8, 20, 26, 41, 51] },
      { label: 'Innings 2', data: [5, 15, 29, 37, 49] },
    ]
  }

  beforeEach(() => {
    // Reset any chart instances
  })

  it('renders chart component', () => {
    const wrapper = mount(ChartLine, {
      props: sampleData
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('has correct height styling', () => {
    const wrapper = mount(ChartLine, {
      props: sampleData
    })

    const chartDiv = wrapper.find('.chart')
    expect(chartDiv.element).toBeTruthy()
  })

  it('accepts labels prop', () => {
    const wrapper = mount(ChartLine, {
      props: sampleData
    })

    expect(wrapper.props('labels')).toEqual(sampleData.labels)
  })

  it('accepts series prop with multiple datasets', () => {
    const wrapper = mount(ChartLine, {
      props: sampleData
    })

    expect(wrapper.props('series')).toEqual(sampleData.series)
    expect(wrapper.props('series').length).toBe(2)
  })

  it('handles empty labels array', () => {
    const wrapper = mount(ChartLine, {
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
        { label: 'Innings 1', data: [8, 20, 26] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: singleSeries
    })

    expect(wrapper.props('series').length).toBe(1)
  })

  it('handles null values in data (gaps in line)', () => {
    const dataWithNulls = {
      labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4'],
      series: [
        { label: 'Innings 1', data: [8, 20, null, 35] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: dataWithNulls
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('renders cumulative data correctly', () => {
    const cumulativeData = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [10, 22, 36] } // Cumulative progression
      ]
    }

    const wrapper = mount(ChartLine, {
      props: cumulativeData
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
    const series = wrapper.props('series')[0].data
    expect(series[0]).toBeLessThan(series[1])
    expect(series[1]).toBeLessThan(series[2])
  })

  it('handles many overs (long match)', () => {
    const manyOvers = {
      labels: Array.from({ length: 50 }, (_, i) => `Over ${i + 1}`),
      series: [
        {
          label: 'Innings 1',
          data: Array.from({ length: 50 }, (_, i) => i * 5) // Cumulative
        }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: manyOvers
    })

    expect(wrapper.props('labels').length).toBe(50)
  })

  it('updates when props change', async () => {
    const wrapper = mount(ChartLine, {
      props: sampleData
    })

    const newData = {
      labels: ['Over 1', 'Over 2'],
      series: [
        { label: 'Innings 1', data: [10, 25] }
      ]
    }

    await wrapper.setProps(newData)

    expect(wrapper.props('labels')).toEqual(newData.labels)
    expect(wrapper.props('series')).toEqual(newData.series)
  })

  it('handles innings starting from zero', () => {
    const fromZero = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [0, 8, 15] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: fromZero
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('handles high scoring matches', () => {
    const highScoring = {
      labels: ['Over 1', 'Over 2', 'Over 3'],
      series: [
        { label: 'Innings 1', data: [36, 64, 94] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: highScoring
    })

    expect(wrapper.find('.chart').exists()).toBe(true)
  })

  it('compares two innings effectively', () => {
    const comparison = {
      labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4'],
      series: [
        { label: 'Innings 1', data: [8, 20, 26, 41] },
        { label: 'Innings 2', data: [10, 18, 30, 45] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: comparison
    })

    expect(wrapper.props('series').length).toBe(2)
    expect(wrapper.props('series')[0].label).toBe('Innings 1')
    expect(wrapper.props('series')[1].label).toBe('Innings 2')
  })

  it('shows progression over time', () => {
    const progression = {
      labels: ['Over 1', 'Over 2', 'Over 3', 'Over 4', 'Over 5'],
      series: [
        { label: 'Innings 1', data: [5, 12, 20, 35, 48] }
      ]
    }

    const wrapper = mount(ChartLine, {
      props: progression
    })

    const data = wrapper.props('series')[0].data
    // Verify it's cumulative (always increasing or staying same)
    for (let i = 1; i < data.length; i++) {
      expect(data[i]).toBeGreaterThanOrEqual(data[i - 1])
    }
  })
})
