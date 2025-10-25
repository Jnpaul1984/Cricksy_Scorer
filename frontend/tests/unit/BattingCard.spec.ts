import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BattingCard from '@/components/BattingCard.vue'

describe('BattingCard.vue', () => {
  const sampleEntries = [
    {
      player_id: '1',
      player_name: 'John Doe',
      runs: 45,
      balls_faced: 30,
      fours: 5,
      sixes: 2,
      is_out: false,
    },
    {
      player_id: '2',
      player_name: 'Jane Smith',
      runs: 23,
      balls_faced: 18,
      fours: 3,
      sixes: 0,
      is_out: true,
      how_out: 'caught',
    },
  ]

  it('renders batting card with entries', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    expect(wrapper.find('.card').exists()).toBe(true)
    expect(wrapper.find('h3').text()).toBe('Batting')
    expect(wrapper.find('table').exists()).toBe(true)
  })

  it('displays correct number of rows', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2)
  })

  it('displays player names correctly', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('John Doe')
    expect(rows[1].text()).toContain('Jane Smith')
  })

  it('displays player statistics correctly', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('45') // runs
    expect(rows[0].text()).toContain('30') // balls
    expect(rows[0].text()).toContain('5')  // fours
    expect(rows[0].text()).toContain('2')  // sixes
  })

  it('highlights striker with dot indicator', () => {
    const wrapper = mount(BattingCard, {
      props: {
        entries: sampleEntries,
        strikerId: '1'
      }
    })

    const strikerRow = wrapper.findAll('tbody tr')[0]
    expect(strikerRow.classes()).toContain('striker')
    expect(strikerRow.find('.dot').exists()).toBe(true)
  })

  it('highlights non-striker', () => {
    const wrapper = mount(BattingCard, {
      props: {
        entries: sampleEntries,
        nonStrikerId: '2'
      }
    })

    const nonStrikerRow = wrapper.findAll('tbody tr')[1]
    expect(nonStrikerRow.classes()).toContain('nonStriker')
  })

  it('marks out players with out class', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const outRow = wrapper.findAll('tbody tr')[1]
    expect(outRow.classes()).toContain('out')
    expect(outRow.text()).toContain('Out (caught)')
  })

  it('displays "Not out" for active players', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const activeRow = wrapper.findAll('tbody tr')[0]
    expect(activeRow.text()).toContain('Not out')
  })

  it('shows empty state when no entries', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: [] }
    })

    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.find('.empty').exists()).toBe(true)
    expect(wrapper.find('.empty').text()).toBe('No batting entries yet.')
  })

  it('calculates strike rate correctly', () => {
    const wrapper = mount(BattingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    // John Doe: 45 runs from 30 balls = 150.0 SR
    expect(rows[0].text()).toContain('150.0')
  })

  it('handles zero balls faced for strike rate', () => {
    const entries = [{
      player_id: '3',
      player_name: 'New Player',
      runs: 0,
      balls_faced: 0,
      fours: 0,
      sixes: 0,
      is_out: false,
    }]

    const wrapper = mount(BattingCard, {
      props: { entries }
    })

    const row = wrapper.find('tbody tr')
    // Should show em dash '—' for zero balls (from fmtSR utility)
    expect(row.text()).toContain('—')
  })
})
