import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import WinProbabilityWidget from '@/components/WinProbabilityWidget.vue'

describe('WinProbabilityWidget', () => {
  const samplePrediction = {
    batting_team_win_prob: 65.5,
    bowling_team_win_prob: 34.5,
    confidence: 75.0,
    batting_team: 'Team A',
    bowling_team: 'Team B',
    factors: {
      runs_needed: 45,
      balls_remaining: 30,
      required_run_rate: 9.0,
      wickets_remaining: 6,
    },
  }

  it('renders prediction when provided', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        battingTeam: 'Team A',
        bowlingTeam: 'Team B',
      },
    })

    expect(wrapper.text()).toContain('Win Probability')
    expect(wrapper.text()).toContain('65.5%')
    expect(wrapper.text()).toContain('34.5%')
    expect(wrapper.text()).toContain('Confidence: 75%')
  })

  it('displays team names from prediction when available', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        battingTeam: 'Custom Batting Team',
        bowlingTeam: 'Custom Bowling Team',
      },
    })

    // Prediction team names take priority
    expect(wrapper.text()).toContain('Team A')
    expect(wrapper.text()).toContain('Team B')
  })

  it('shows factors when not in compact mode', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        compact: false,
      },
    })

    expect(wrapper.text()).toContain('Runs Needed')
    expect(wrapper.text()).toContain('45')
    expect(wrapper.text()).toContain('Balls Remaining')
    expect(wrapper.text()).toContain('30')
    expect(wrapper.text()).toContain('Required RR')
    expect(wrapper.text()).toContain('9.00')
  })

  it('hides factors in compact mode', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        compact: true,
      },
    })

    expect(wrapper.text()).not.toContain('Runs Needed')
    expect(wrapper.text()).not.toContain('Balls Remaining')
  })

  it('shows placeholder when no prediction provided', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: null,
      },
    })

    expect(wrapper.text()).toContain('AI predictions will appear')
  })

  it('shows placeholder when confidence is zero', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: {
          ...samplePrediction,
          confidence: 0,
        },
      },
    })

    expect(wrapper.text()).toContain('AI predictions will appear')
  })

  it('renders probability bars with correct widths', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
      },
    })

    const bars = wrapper.findAll('.bar')
    expect(bars.length).toBe(2)
    
    // Check batting bar width
    expect(bars[0].attributes('style')).toContain('width: 65.5%')
    
    // Check bowling bar width
    expect(bars[1].attributes('style')).toContain('width: 34.5%')
  })

  it('applies correct theme', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        theme: 'dark',
      },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('hides chart when showChart is false', () => {
    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: samplePrediction,
        showChart: false,
      },
    })

    // Chart component should not be rendered
    expect(wrapper.findComponent({ name: 'WinProbabilityChart' }).exists()).toBe(false)
  })

  it('renders with different probability values', () => {
    const highProbPrediction = {
      ...samplePrediction,
      batting_team_win_prob: 85.0,
      bowling_team_win_prob: 15.0,
    }

    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: highProbPrediction,
      },
    })

    expect(wrapper.text()).toContain('85.0%')
    expect(wrapper.text()).toContain('15.0%')
  })

  it('handles missing factors gracefully', () => {
    const predictionWithoutFactors = {
      batting_team_win_prob: 50.0,
      bowling_team_win_prob: 50.0,
      confidence: 25.0,
    }

    const wrapper = mount(WinProbabilityWidget, {
      props: {
        prediction: predictionWithoutFactors,
      },
    })

    expect(wrapper.text()).toContain('50.0%')
    expect(wrapper.text()).not.toContain('Runs Needed')
  })
})
