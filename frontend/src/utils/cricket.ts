// utils/cricket.ts
// Small, framework-agnostic helpers for cricket math/formatting.
// Keep this file free of Vue/Pinia imports so it can be reused on server or client.

/** Formats Strike Rate as a string with 1 decimal place. Returns '—' if balls = 0. */
export function fmtSR(runs: number, balls: number): string {
  const r = Number.isFinite(runs) ? Number(runs) : 0
  const b = Number.isFinite(balls) ? Number(balls) : 0
  if (!b) return '—'
  return ((r * 100) / b).toFixed(1)
}

/** Convert number of balls to decimal overs (e.g., 22 balls -> 3.666…, not 3.4). */
export function ballsToOversFloat(balls: number): number {
  const b = Math.max(0, Math.trunc(Number(balls) || 0))
  return b / 6
}

export function oversNotationToFloat(ov: number | string | undefined): number {
  if (ov == null) return 0
  const n = typeof ov === 'number' ? ov : Number(ov)
  if (!Number.isFinite(n)) return 0
  const whole = Math.trunc(n)
  const balls = Math.round((n - whole) * 10)
  return whole + balls / 6
}

// A minimal shape we can safely accept from anywhere in the app
export type Delivery = {
  bowler_id?: string | number
  over_number?: number | string
  ball_number?: number
  extra?: 'wd' | 'nb' | 'b' | 'lb' | string | null
  extra_runs?: number
  runs_off_bat?: number
  runs_scored?: number
}

/** Formats Economy Rate as a string with 2 decimals. Returns '—' if ballsBowled = 0. */
export function fmtEconomy(runsConceded: number, ballsBowled: number): string {
  const r = Number.isFinite(runsConceded) ? Number(runsConceded) : 0
  const b = Math.max(0, Math.trunc(Number(ballsBowled) || 0))
  if (!b) return '—'
  const overs = b / 6
  if (!overs) return '—'
  return (r / overs).toFixed(2)
}

/** Formats balls as the conventional overs display "O.R" (e.g., 3.4 means 3 overs + 4 balls). */
export function oversDisplayFromBalls(balls: number): string {
  const b = Math.max(0, Math.trunc(Number(balls) || 0))
  const overs = Math.floor(b / 6)
  const rem = b % 6
  return `${overs}.${rem}`
}

/** Formats overs from whichever field is available.
 *  Prefers integer balls (authoritative) if present, else derives from X.Y notation.
 *  Accepts either a number of balls, a legacy overs number/string, or a bowler-like object.
 */
export function oversDisplayFromAny(
  src:
    | number
    | string
    | { balls_bowled?: number; overs_bowled?: number | string; overs?: number | string }
    | Record<string, any>
): string {
  // If they passed a plain number, assume it's BALLS
  if (typeof src === 'number' && Number.isFinite(src)) {
    return oversDisplayFromBalls(src as number)
  }
  // If they passed a string, assume it's legacy overs X.Y (e.g., "3.4")
  if (typeof src === 'string') {
    return oversDisplayFromBalls(ballsFromOversNotation(src))
  }

  const obj = src as Record<string, any>
  const balls = Number.isFinite(obj?.balls_bowled) ? Math.trunc(Number(obj.balls_bowled)) : null
  if (balls != null && balls >= 0) {
    return oversDisplayFromBalls(balls)
  }

  // Fallback to legacy fields (overs_bowled or overs) in decimal-notation X.Y
  const ov = obj?.overs_bowled ?? obj?.overs
  return oversDisplayFromBalls(ballsFromOversNotation(ov))
}

// -----------------------------------------------------------------------------
// Optional tiny helpers you *may* find handy elsewhere
// -----------------------------------------------------------------------------

/** True if this delivery should count as a legal ball (increments ball count). */
export function isLegalBall(
  d: { is_extra?: boolean; extra?: string; extra_type?: 'wd' | 'nb' | 'b' | 'lb' | string } | Record<string, any>
): boolean {
  // If your API provides d.legal, prefer that.
  if ('legal' in (d as any)) return Boolean((d as any).legal)

  // Otherwise, wides/no-balls do NOT increment balls; byes/leg-byes DO.
  const t = String((d as any).extra_type ?? (d as any).extra ?? '')
  if (!t) return true          // no extra => legal ball
  return t === 'b' || t === 'lb'
}


export function ballsFromOversNotation(ov: number | string | undefined): number {
  if (ov == null) return 0
  const n = typeof ov === 'number' ? ov : Number(ov)
  if (!Number.isFinite(n)) return 0
  const whole = Math.trunc(n)
  const balls = Math.max(0, Math.round((n - whole) * 10))
  return whole * 6 + balls
}

/** Sum bowling figures (runs to bowler & legal balls) for one bowler. */
export function accumulateBowling(deliveries: Array<Record<string, any>>, bowlerId: string): { runs: number; balls: number } {
  let runs = 0, balls = 0
  const pid = String(bowlerId)

  for (const d of deliveries) {
    if (String(d.bowler_id || '') !== pid) continue
    const x  = String(d.extra_type ?? d.extra ?? '')
    const ob = Number(d.runs_off_bat ?? d.runs_scored ?? d.runs ?? 0)

    if (x === 'wd') {
      // wides: all wides charged to bowler; do NOT consume a ball
      runs += Math.max(0, Number(d.extra_runs ?? 0))
    } else if (x === 'nb') {
      // no-ball: 1 penalty + any off-bat runs; does NOT consume a ball
      runs += 1 + Math.max(0, ob)
    } else if (x === 'b' || x === 'lb') {
      // byes/leg-byes: NOT charged to bowler; DO consume a ball
      balls += 1
    } else {
      // legal delivery: off-bat runs; consumes a ball
      runs += Math.max(0, ob)
      balls += 1
    }
  }
  return { runs, balls }
}

/** Derive full figures for a bowler from deliveries (runs/balls/maidens/overs/econ). */
export function deriveBowlerFigures(deliveries: Delivery[], bowlerId: string | number): {
  runs: number
  balls: number
  maidens: number
  oversText: string
  econText: string | '—'
} {
  let runs = 0
  let balls = 0
  let maidens = 0
  const pid = String(bowlerId)

  // Track over totals for maiden detection: key = `${pid}:${overNumber}`
  const overRuns: Record<string, number> = {}

  const overNum = (d: Delivery): number => {
    const o = d.over_number
    if (typeof o === 'number') return Math.floor(o)
    if (typeof o === 'string') return Number(o.split('.')[0] || 0) || 0
    return 0
  }

  for (const d of deliveries) {
    if (String(d.bowler_id || '') !== pid) continue
    const x  = String(d.extra ?? '')
    const ob = Number(d.runs_off_bat ?? d.runs_scored ?? 0)

    if (x === 'wd') {
      const w = Math.max(0, Number(d.extra_runs ?? 0))
      runs += w
      // ball does NOT count
      const k = `${pid}:${overNum(d)}`
      overRuns[k] = (overRuns[k] || 0) + w
    } else if (x === 'nb') {
      const add = 1 + Math.max(0, ob)
      runs += add
      // ball does NOT count
      const k = `${pid}:${overNum(d)}`
      overRuns[k] = (overRuns[k] || 0) + add
    } else if (x === 'b' || x === 'lb') {
      // byes/leg-byes: not to bowler, but DO consume a ball
      balls += 1
      const add = Math.max(0, Number(d.runs_scored ?? d.extra_runs ?? 0))
      const k = `${pid}:${overNum(d)}`
      overRuns[k] = (overRuns[k] || 0) + add
    } else {
      // legal delivery: off-bat, consumes a ball
      runs += Math.max(0, ob)
      balls += 1
      const k = `${pid}:${overNum(d)}`
      overRuns[k] = (overRuns[k] || 0) + Math.max(0, ob)
    }
  }

  // maidens = completed overs (6 legal balls) with zero over total
  for (const key of Object.keys(overRuns)) {
    if (!key.startsWith(pid + ':')) continue
    const over = Number(key.split(':')[1] || 0)
    const legalBallsInOver = deliveries.filter(d =>
      String(d.bowler_id || '') === pid &&
      overNum(d) === over &&
      (d.extra !== 'wd' && d.extra !== 'nb')
    ).length
    if (legalBallsInOver === 6 && overRuns[key] === 0) maidens += 1
  }

  const oversText = oversDisplayFromBalls(balls)
  const econText = balls ? (runs / (balls / 6)).toFixed(2) : '—'
  return { runs, balls, maidens, oversText, econText }
}


export default {
  fmtSR,
  ballsToOversFloat,
  fmtEconomy,
  oversDisplayFromBalls,
  oversDisplayFromAny,
  isLegalBall,
  ballsFromOversNotation,
  accumulateBowling,     // now corrected
  deriveBowlerFigures,   // <-- new
}


