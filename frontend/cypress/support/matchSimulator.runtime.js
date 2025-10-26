import * as fs from 'node:fs'
import * as path from 'node:path'

const API_HEADERS = {
  'Content-Type': 'application/json',
}

async function httpRequest(base, urlPath, options = {}) {
  const url = `${base.replace(/\/+$/, '')}${urlPath}`
  const init = {
    method: options.method ?? 'GET',
  }
  if (options.body !== undefined) {
    init.headers = API_HEADERS
    init.body = JSON.stringify(options.body)
  }
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  if (res.status === 204) {
    return undefined
  }
  return await res.json()
}

function loadFixture(frontendDir) {
  const fixturePath = path.resolve(frontendDir, 'simulated_t20_match.json')
  const raw = fs.readFileSync(fixturePath, 'utf-8')
  return JSON.parse(raw)
}

function buildBattingOrder(innings) {
  const order = []
  for (const ball of innings.balls) {
    if (!order.includes(ball.batsman)) {
      order.push(ball.batsman)
    }
  }
  const openerSet = new Set([innings.opening_pair.striker, innings.opening_pair.non_striker])
  const remaining = order.filter(name => !openerSet.has(name))
  return [innings.opening_pair.striker, innings.opening_pair.non_striker, ...remaining]
}

// Map fixture ball to extra code and runs for posting deliveries
function normalizeExtra(ball) {
  const extraType = ball.extraType ? String(ball.extraType).toLowerCase() : null
  if (!extraType || Number(ball.extras || 0) === 0) {
    return { code: null, runsScored: Number(ball.runs || 0), runsOffBat: undefined }
  }
  switch (extraType) {
    case 'wd':
    case 'wide':
      return { code: 'wd', runsScored: Number(ball.extras || 1), runsOffBat: undefined }
    case 'nb':
    case 'no_ball':
    case 'no-ball':
      return { code: 'nb', runsScored: 0, runsOffBat: Number(ball.runs || 0) }
    case 'b':
    case 'bye':
      return { code: 'b', runsScored: Number(ball.extras || 0), runsOffBat: undefined }
    case 'lb':
    case 'leg_bye':
    case 'leg-bye':
      return { code: 'lb', runsScored: Number(ball.extras || 0), runsOffBat: undefined }
    default:
      return { code: null, runsScored: Number((ball.runs || 0) + (ball.extras || 0)), runsOffBat: undefined }
  }
}

// Compute total runs for an innings using the same scoring semantics
function inningsTotal(innings) {
  let total = 0
  for (const ball of innings.balls) {
    const et = ball.extraType ? String(ball.extraType).toLowerCase() : null
    if (!et || Number(ball.extras || 0) === 0) {
      total += Number(ball.runs || 0)
    } else if (et === 'wd' || et === 'wide') {
      total += Number(ball.extras || 1)
    } else if (et === 'nb' || et === 'no_ball' || et === 'no-ball') {
      total += 1 + Number(ball.runs || 0)
    } else if (et === 'b' || et === 'bye' || et === 'lb' || et === 'leg_bye' || et === 'leg-bye') {
      total += Number(ball.extras || 0)
    } else {
      total += Number((ball.runs || 0) + (ball.extras || 0))
    }
  }
  return total
}

// Best-effort margin extraction from a summary like "Team Alpha won by 15 runs"
function extractMargin(summary) {
  if (!summary) return null
  const m = String(summary).match(/\bby\s+(\d+)\b/i)
  return m ? Number(m[1]) : null
}

async function startOver(apiBase, gameId, bowlerId) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/overs/start`, {
    method: 'POST',
    body: { bowler_id: bowlerId },
  })
}

async function postDelivery(apiBase, gameId, payload) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/deliveries`, {
    method: 'POST',
    body: payload,
  })
}

async function replaceBatter(apiBase, gameId, batterId) {
  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/batters/replace`, {
    method: 'POST',
    body: { new_batter_id: batterId },
  })
}

function rotateStrike(striker, nonStriker, runs, extraCode) {
  if (extraCode === 'wd') {
    return [striker, nonStriker]
  }
  if (runs % 2 === 1) {
    return [nonStriker, striker]
  }
  return [striker, nonStriker]
}

async function playInnings(apiBase, gameId, innings, battingIds, bowlingIds) {
  const deliveries = [...innings.balls].sort((a, b) => a.over - b.over || a.ball - b.ball)
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
      const missing = []
      if (!strikerId) missing.push('striker')
      if (!nonStrikerId) missing.push('non-striker')
      if (!bowlerId) missing.push('bowler')
      throw new Error(`Missing ID(s) for delivery ${ball.over}.${ball.ball}: ${missing.join(', ')}`)
    }

    const { code: extraCode, runsScored, runsOffBat } = normalizeExtra(ball)
    const payload = {
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
      const runsForRotation = extraCode === 'nb' ? (runsOffBat ?? 0) : runsScored
      ;[striker, nonStriker] = rotateStrike(striker, nonStriker, runsForRotation, extraCode)
    }

    if (ball.ball === 6) {
      ;[striker, nonStriker] = [nonStriker, striker]
    }
  }
}

function mapPlayers(players) {
  const map = new Map()
  for (const player of players) {
    map.set(player.name, player.id)
  }
  return map
}

export async function seedMatch(apiBase, frontendDir) {
  try {
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

    const game = await httpRequest(apiBase, '/games', {
      method: 'POST',
      body: createPayload,
    })
    const gameId = game.id

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

    // 1) Finalize to compute winner/target state; snapshot/UI need this
    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/finalize`, {
      method: 'POST',
    })

    // 2) Persist result explicitly so GET /games/{id}/results succeeds in any mode
    const teamAScore = inningsTotal(innings1)
    const teamBScore = inningsTotal(innings2)
    const winnerName = String(fixture?.result?.winner || teamAName) // fallback
    const resultText = String(fixture?.result?.summary || `${winnerName} won`)
    const margin = extractMargin(fixture?.result?.summary || '')

    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/results`, {
      method: 'POST',
      body: {
        match_id: gameId,
        winner: winnerName,                 // optional in schema; safe to include
        team_a_score: teamAScore,           // required by MatchResultRequest
        team_b_score: teamBScore,           // required by MatchResultRequest
        winner_team_name: winnerName,       // helps consumers
        method: 'normal',
        margin,
        result_text: resultText,
        completed_at: null,
      },
    })

    return { gameId }
  } catch (err) {
    console.error('[matchSimulator] seedMatch error', err)
    throw err
  }
}
