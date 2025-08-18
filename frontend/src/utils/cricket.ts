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

// -----------------------------------------------------------------------------
// Optional tiny helpers you *may* find handy elsewhere
// -----------------------------------------------------------------------------

/** True if this delivery should count as a legal ball (increments ball count). */
export function isLegalBall(d: { is_extra?: boolean; extra_type?: 'wd' | 'nb' | 'b' | 'lb' | string } | Record<string, any>): boolean {
  // If your API provides d.legal, prefer that.
  if ('legal' in (d as any)) return Boolean((d as any).legal)
  // Otherwise, wides & no-balls do not increment balls; byes/leg-byes do.
  const isExtra = Boolean((d as any).is_extra)
  if (!isExtra) return true
  const t = String((d as any).extra_type ?? '')
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

/** Sum bowling figures (runs & legal balls) from a list of deliveries for one bowler. */
export function accumulateBowling(deliveries: Array<Record<string, any>>, bowlerId: string): { runs: number; balls: number } {
  let runs = 0, balls = 0
  for (const d of deliveries) {
    if (String(d.bowler_id || '') !== String(bowlerId)) continue
    const offBat = Number(d.runs_scored ?? d.runs_off_bat ?? d.runs ?? 0)
    const extrasTotal = Number((d.extras && d.extras.total) ?? 0)
    runs += offBat + extrasTotal
    if (isLegalBall(d)) balls += 1
  }
  return { runs, balls }
}

export default {
  fmtSR,
  ballsToOversFloat,
  fmtEconomy,
  oversDisplayFromBalls,
  isLegalBall,
  accumulateBowling,
}
