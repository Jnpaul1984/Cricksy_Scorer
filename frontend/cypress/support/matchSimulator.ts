import fs from 'node:fs'
import path from 'node:path'

type FixtureDelivery = {
  over: number
  ball: number
  bowler: string
  batsman: string
  runs: number
  extras: number
  extraType?: string
  wicket?: boolean
  wicketType?: string
  fielder?: string
}

type FixtureInnings = {
  team: string
  runs: number
  wickets: number
  balls: FixtureDelivery[]
  opening_pair: { striker: string; non_striker: string }
  bowling_order?: string[]
}

type Fixture = {
  matchType: string
  teams: [string, string]
  venue: string
  innings: [FixtureInnings, FixtureInnings]
  result: { winner: string; summary: string }
}

type IdMap = Map<string, string>

const API_HEADERS = {
  'Content-Type': 'application/json',
}

async function httpRequest<T>(
  base: string,
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const url = `${base.replace(/\/+$/, '')}${path}`
  const res = await fetch(url, {
    method: options.method || 'GET',
    headers: options.body ? API_HEADERS : {},
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return (await res.json()) as T
}

function loadFixture(frontendDir: string): Fixture {
  const fixturePath = path.resolve(frontendDir, 'simulated_t20_match.json')
  const raw = fs.readFileSync(fixturePath, 'utf-8')
  return JSON.parse(raw) as Fixture
}

function buildBattingOrder(innings: FixtureInnings): string[] {
  const order: string[] = []
  for (const ball of innings.balls) {
    if (!order.includes(ball.batsman)) {
      order.push(ball.batsman)
    }
  }
  // Ensure openers are at the front
  const openerSet = new Set([innings.opening_pair.striker, innings.opening_pair.non_striker])
  const remaining = order.filter(name => !openerSet.has(name))
  return [innings.opening_pair.striker, innings.opening_pair.non_striker, ...remaining]
}

function normalizeExtra(ball: FixtureDelivery): {
  code: string | null
  runsScored: number
  runsOffBat: number | undefined
} {
  const extraType = ball.extraType ? ball.extraType.toLowerCase() : null
  if (!extraType || ball.extras === 0) {
    return { code: null, runsScored: ball.runs, runsOffBat: undefined }
  }
  switch (extraType) {
    case 'wd':
    case 'wide':
      return { code: 'wd', runsScored: ball.extras || 1, runsOffBat: undefined }
    case 'nb':
    case 'no_ball':
    case 'no-ball':
      return { code: 'nb', runsScored: 0, runsOffBat: ball.runs }
    case 'b':
    case 'bye':
      return { code: 'b', runsScored: ball.extras, runsOffBat: undefined }
    case 'lb':
    case 'leg_bye':
    case 'leg-bye':
      return { code: 'lb', runsScored: ball.extras, runsOffBat: undefined }
    default:
      return { code: null, runsScored: ball.runs + ball.extras, runsOffBat: undefined }
  }
}

async function startOver(apiBase: string, gameId: string, bowlerId: string) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/overs/start`, {
    method: 'POST',
    body: { bowler_id: bowlerId },
  })
}

async function postDelivery(
  apiBase: string,
  gameId: string,
  payload: Record<string, unknown>,
) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/deliveries`, {
    method: 'POST',
    body: payload,
  })
}

async function replaceBatter(apiBase: string, gameId: string, batterId: string) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/batters/replace`, {
    method: 'POST',
    body: { new_batter_id: batterId },
  })
}

function rotateStrike(
  striker: string,
  nonStriker: string,
  runs: number,
  extraCode: string | null,
): [string, string] {
  if (extraCode === 'wd') {
    return [striker, nonStriker]
  }
  if (runs % 2 === 1) {
    return [nonStriker, striker]
  }
  return [striker, nonStriker]
}

async function playInnings(
  apiBase: string,
  gameId: string,
  innings: FixtureInnings,
  battingIds: IdMap,
  bowlingIds: IdMap,
) {
  const deliveries = [...innings.balls].sort(
    (a, b) => a.over - b.over || a.ball - b.ball,
  )
  const order = buildBattingOrder(innings)
  let striker = innings.opening_pair.striker
  let nonStriker = innings.opening_pair.non_striker
  const queue = order.filter(name => name !== striker && name !== nonStriker)
  let currentOver = -1

  for (const ball of deliveries) {
    if (ball.over !== currentOver) {
      currentOver = ball.over
      const bowlerId = bowlingIds.get(ball.bowler)
      if (!bowlerId) {
        throw new Error(`Unknown bowler "${ball.bowler}" (not found in bowlingIds map)`)
      }
      await startOver(apiBase, gameId, bowlerId)
    }

    const strikerId = battingIds.get(striker)
    const nonStrikerId = battingIds.get(nonStriker)
    const bowlerId = bowlingIds.get(ball.bowler)
    if (!strikerId || !nonStrikerId || !bowlerId) {
      const missing: string[] = []
      if (!strikerId) missing.push('striker')
      if (!nonStrikerId) missing.push('non-striker')
      if (!bowlerId) missing.push('bowler')
      throw new Error(
        `Missing ID(s) for delivery ${ball.over}.${ball.ball}: ${missing.join(', ')}`
      )
    }

    const { code: extraCode, runsScored, runsOffBat } = normalizeExtra(ball)
    const payload: Record<string, unknown> = {
      striker_id: strikerId,
      non_striker_id: nonStrikerId,
      bowler_id: bowlerId,
      is_wicket: Boolean(ball.wicket),
    }
    if (extraCode) {
      payload.extra = extraCode
      if (extraCode === 'nb') {
        payload.runs_off_bat = runsOffBat ?? 0
      } else {
        payload.runs_scored = runsScored
      }
    } else {
      payload.runs_scored = runsScored
    }

    if (ball.wicketType) {
      payload.dismissal_type = ball.wicketType
    }
    if (ball.fielder) {
      const fid = bowlingIds.get(ball.fielder)
      if (fid) payload.fielder_id = fid
    }

    await postDelivery(apiBase, gameId, payload)

    if (ball.wicket) {
      const nextBatter = queue.shift()
      if (!nextBatter) {
        throw new Error('Ran out of batters to replace wicket')
      }
      const nextId = battingIds.get(nextBatter)
      if (!nextId) {
        throw new Error(`Unknown batter ${nextBatter}`)
      }
      await replaceBatter(apiBase, gameId, nextId)
      striker = nextBatter
    } else {
      const runsForRotation = extraCode === 'nb' ? runsOffBat ?? 0 : runsScored
      ;[striker, nonStriker] = rotateStrike(striker, nonStriker, runsForRotation, extraCode)
    }

    if (ball.ball === 6) {
      ;[striker, nonStriker] = [nonStriker, striker]
    }
  }
}

function mapPlayers(players: Array<{ id: string; name: string }>): IdMap {
  const map = new Map<string, string>()
  for (const player of players) {
    map.set(player.name, player.id)
  }
  return map
}

export async function seedMatch(apiBase: string, frontendDir: string): Promise<{ gameId: string }> {
  const fixture = loadFixture(frontendDir)
  const [teamAName, teamBName] = fixture.teams
  const playersA = Array.from({ length: 11 }, (_, i) => `Alpha Player ${i + 1}`)
  const playersB = Array.from({ length: 11 }, (_, i) => `Beta Player ${i + 1}`)

  const createPayload = {
    team_a_name: teamAName,
    team_b_name: teamBName,
    players_a: playersA,
    players_b: playersB,
    match_type: 'limited',
    overs_limit: 20,
    dls_enabled: true,
    toss_winner_team: teamAName,
    decision: 'bat',
  }

  interface GameCreationResponse {
    id: string
    team_a: { players: Array<{ id: string; name: string }> }
    team_b: { players: Array<{ id: string; name: string }> }
  }

  const game = await httpRequest<GameCreationResponse>(apiBase, '/games', {
    method: 'POST',
    body: createPayload,
  })
  const gameId: string = game.id

  const teamAIds = mapPlayers(game.team_a.players || [])
  const teamBIds = mapPlayers(game.team_b.players || [])

  const [innings1, innings2] = fixture.innings

  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/openers`, {
    method: 'POST',
    body: {
      striker_id: teamAIds.get(innings1.opening_pair.striker),
      non_striker_id: teamAIds.get(innings1.opening_pair.non_striker),
    },
  })

  await playInnings(apiBase, gameId, innings1, teamAIds, teamBIds)

  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/innings/start`, {
    method: 'POST',
    body: {
      striker_id: teamBIds.get(innings2.opening_pair.striker),
      non_striker_id: teamBIds.get(innings2.opening_pair.non_striker),
      opening_bowler_id: teamAIds.get((innings2.balls[0] || {}).bowler),
    },
  })

  await playInnings(apiBase, gameId, innings2, teamBIds, teamAIds)

  return { gameId }
}
