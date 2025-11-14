import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'

import WagonWheel from '@/components/analytics/WagonWheel.vue'

describe('WagonWheel.vue', () => {
  const sampleStrokes = [
    { angleDeg: 0, runs: 4, kind: '4' as const },
    { angleDeg: 45, runs: 6, kind: '6' as const },
    { angleDeg: 90, runs: 2, kind: 'other' as const },
    { angleDeg: 180, runs: 1, kind: 'other' as const },
    { angleDeg: 270, runs: 4, kind: '4' as const },
  ]

  it('renders wagon wheel SVG', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('.wagon-wheel-svg').exists()).toBe(true)
  })

  it('uses default size when not specified', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('220')
    expect(svg.attributes('height')).toBe('220')
  })

  it('uses custom size when specified', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes, size: 300 }
    })

    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('300')
    expect(svg.attributes('height')).toBe('300')
  })

  it('renders outer circle', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const circles = wrapper.findAll('circle')
    expect(circles.length).toBeGreaterThan(0)
    expect(circles[0].attributes('fill')).toBe('#fafafa')
  })

  it('renders guidelines for field', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const lines = wrapper.findAll('line')
    // Should have 12 guidelines + strokes
    expect(lines.length).toBeGreaterThanOrEqual(12)
  })

  it('renders correct number of stroke lines', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const lines = wrapper.findAll('line.stroke-line')
    expect(lines.length).toBe(sampleStrokes.length)
  })

  it('applies correct colors to strokes', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const strokeLines = wrapper.findAll('line.stroke-line')

    // First stroke is a four (blue)
    expect(strokeLines[0].attributes('stroke')).toBe('#2563eb')

    // Second stroke is a six (green)
    expect(strokeLines[1].attributes('stroke')).toBe('#22c55e')

    // Third stroke is other (gray)
    expect(strokeLines[2].attributes('stroke')).toBe('#94a3b8')
  })

  it('renders container with default props', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    expect(wrapper.find('.wagon-wheel-container').exists()).toBe(true)
    expect(wrapper.find('.wagon-wheel-svg').exists()).toBe(true)
  })

  it('hides legend when showLegend is false', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes, showLegend: false }
    })

    expect(wrapper.props('showLegend')).toBe(false)
  })

  it('calculates stroke counts correctly', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    // Verify strokes are rendered
    const strokeLines = wrapper.findAll('line.stroke-line')
    expect(strokeLines.length).toBe(5)

    // Count strokes by type
    const sixes = sampleStrokes.filter(s => s.kind === '6').length
    const fours = sampleStrokes.filter(s => s.kind === '4').length
    const others = sampleStrokes.filter(s => s.kind === 'other').length

    expect(sixes).toBe(1)
    expect(fours).toBe(2)
    expect(others).toBe(2)
  })

  it('adds tooltip to stroke lines', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const strokeLines = wrapper.findAll('line.stroke-line')
    const firstTitle = strokeLines[0].find('title')

    expect(firstTitle.exists()).toBe(true)
    expect(firstTitle.text()).toContain('4 runs')
    expect(firstTitle.text()).toContain('0°')
  })

  it('handles empty strokes array', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: [] }
    })

    expect(wrapper.find('svg').exists()).toBe(true)
    const strokeLines = wrapper.findAll('line.stroke-line')
    expect(strokeLines.length).toBe(0)
  })

  it('handles single run correctly in tooltip', () => {
    const wrapper = mount(WagonWheel, {
      props: {
        strokes: [{ angleDeg: 0, runs: 1, kind: 'other' as const }]
      }
    })

    const strokeLine = wrapper.find('line.stroke-line')
    const title = strokeLine.find('title')

    expect(title.text()).toContain('1 run')
    expect(title.text()).not.toContain('runs')
  })

  it('applies hover styles to stroke lines', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const strokeLine = wrapper.find('line.stroke-line')
    expect(strokeLine.classes()).toContain('stroke-line')
  })

  it('component has correct container structure', () => {
    const wrapper = mount(WagonWheel, {
      props: { strokes: sampleStrokes }
    })

    const container = wrapper.find('.wagon-wheel-container')
    expect(container.exists()).toBe(true)

    const svg = wrapper.find('.wagon-wheel-svg')
    expect(svg.exists()).toBe(true)
  })

  it('handles strokes at various angles', () => {
    const allAngles = [
      { angleDeg: 0, runs: 4, kind: '4' as const },
      { angleDeg: 90, runs: 6, kind: '6' as const },
      { angleDeg: 180, runs: 4, kind: '4' as const },
      { angleDeg: 270, runs: 6, kind: '6' as const },
    ]

    const wrapper = mount(WagonWheel, {
      props: { strokes: allAngles }
    })

    const strokeLines = wrapper.findAll('line.stroke-line')
    expect(strokeLines.length).toBe(4)
  })
})
