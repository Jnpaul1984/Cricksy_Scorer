import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'

import BowlingCard from '@/components/BowlingCard.vue'

describe('BowlingCard.vue', () => {
  const sampleEntries = [
    {
      player_id: '1',
      player_name: 'Fast Bowler',
      balls_bowled: 24,
      maidens: 1,
      runs_conceded: 30,
      wickets_taken: 2,
    },
    {
      player_id: '2',
      player_name: 'Spin Bowler',
      balls_bowled: 18,
      maidens: 0,
      runs_conceded: 25,
      wickets_taken: 1,
    },
  ]

  it('renders bowling card with entries', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    expect(wrapper.find('.card').exists()).toBe(true)
    expect(wrapper.find('h3').text()).toBe('Bowling')
    expect(wrapper.find('table').exists()).toBe(true)
  })

  it('displays correct number of rows', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2)
  })

  it('displays player names correctly', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Fast Bowler')
    expect(rows[1].text()).toContain('Spin Bowler')
  })

  it('displays bowling statistics correctly', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('1')  // maidens
    expect(rows[0].text()).toContain('30') // runs
    expect(rows[0].text()).toContain('2')  // wickets
  })

  it('converts balls to overs format correctly', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    // 24 balls = 4.0 overs
    expect(rows[0].text()).toContain('4.0')
    // 18 balls = 3.0 overs
    expect(rows[1].text()).toContain('3.0')
  })

  it('calculates economy rate correctly', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const rows = wrapper.findAll('tbody tr')
    // Fast Bowler: 30 runs from 24 balls = 7.50 economy
    expect(rows[0].text()).toContain('7.50')
    // Spin Bowler: 25 runs from 18 balls = 8.33 economy
    expect(rows[1].text()).toContain('8.33')
  })

  it('shows empty state when no entries', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: [] }
    })

    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.find('.empty').exists()).toBe(true)
    expect(wrapper.find('.empty').text()).toBe('No bowling entries yet.')
  })

  it('handles zero balls bowled', () => {
    const entries = [{
      player_id: '3',
      player_name: 'New Bowler',
      balls_bowled: 0,
      maidens: 0,
      runs_conceded: 0,
      wickets_taken: 0,
    }]

    const wrapper = mount(BowlingCard, {
      props: { entries }
    })

    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('0.0') // overs
    expect(row.text()).toContain('0')   // maidens
    expect(row.text()).toContain('0')   // runs
    expect(row.text()).toContain('0')   // wickets
  })

  it('displays all column headers', () => {
    const wrapper = mount(BowlingCard, {
      props: { entries: sampleEntries }
    })

    const headers = wrapper.findAll('thead th')
    expect(headers[0].text()).toBe('Player')
    expect(headers[1].text()).toBe('O')
    expect(headers[2].text()).toBe('M')
    expect(headers[3].text()).toBe('R')
    expect(headers[4].text()).toBe('W')
    expect(headers[5].text()).toBe('Econ')
  })

  it('handles partial overs correctly', () => {
    const entries = [{
      player_id: '4',
      player_name: 'Partial Over Bowler',
      balls_bowled: 17, // 2.5 overs
      maidens: 0,
      runs_conceded: 20,
      wickets_taken: 1,
    }]

    const wrapper = mount(BowlingCard, {
      props: { entries }
    })

    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('2.5')
  })
})
