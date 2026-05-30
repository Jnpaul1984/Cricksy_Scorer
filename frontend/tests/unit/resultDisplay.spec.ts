import { describe, expect, it } from 'vitest'

import { normalizeResultDisplayText } from '@/utils/resultDisplay'

describe('normalizeResultDisplayText', () => {
  it('normalizes singular run and wicket grammar', () => {
    expect(normalizeResultDisplayText('Durham won by 1 runs')).toBe('Durham won by 1 run')
    expect(normalizeResultDisplayText('Falcons won by 1 wickets')).toBe('Falcons won by 1 wicket')
  })

  it('normalizes run(s)/wicket(s) tokens based on count', () => {
    expect(normalizeResultDisplayText('won by 1 run(s)')).toBe('won by 1 run')
    expect(normalizeResultDisplayText('won by 2 run(s)')).toBe('won by 2 runs')
    expect(normalizeResultDisplayText('won by 1 wicket(s)')).toBe('won by 1 wicket')
    expect(normalizeResultDisplayText('won by 2 wicket(s)')).toBe('won by 2 wickets')
  })

  it('preserves correct plural results', () => {
    expect(normalizeResultDisplayText('Team A won by 2 runs')).toBe('Team A won by 2 runs')
    expect(normalizeResultDisplayText('Team B won by 3 wickets')).toBe('Team B won by 3 wickets')
    expect(normalizeResultDisplayText('Team C won by 10 wickets')).toBe('Team C won by 10 wickets')
  })

  it('does not mutate source objects', () => {
    const payload = { result: 'Durham won by 1 runs' }
    const display = normalizeResultDisplayText(payload.result)

    expect(display).toBe('Durham won by 1 run')
    expect(payload.result).toBe('Durham won by 1 runs')
  })
})
