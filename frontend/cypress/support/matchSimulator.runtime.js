import * as fs from 'node:fs'
import * as path from 'node:path'

const API_HEADERS = { 'Content-Type': 'application/json' }

async function httpRequest(base, urlPath, options = {}) {
  const url = `${base.replace(/\/+$/, '')}${urlPath}`
  const init = { method: options.method ?? 'GET' }
  if (options.body !== undefined) {
    init.headers = API_HEADERS
    init.body = JSON.stringify(options.body)
  }
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  if (res.status === 204) return undefined
  return await res.json()
}

function loadFixture(frontendDir) {
  const p = path.resolve(frontendDir, 'simulated_t20_match.json')
  const raw = fs.readFileSync(p, 'utf-8')
  return JSON.parse(raw)
}

function buildBattingOrder(inn) {
  const order = []
  for (const ball of inn.balls) {
    if (!order.includes(ball.batsman)) order.push(ball.batsman)
  }
  const open = inn.opening_pair
  const set = new Set([open.striker, open.non_striker])
  const rest = order.filter((n) => !set.has(n))
  return [open.striker, open.non_striker, ...rest]
}

function normalizeExtra(ball) {
  const et = ball.extraType ? String(ball.extraType).toLowerCase() : null
  if (!et || Number(ball.extras || 0) === 0) {
    return { code: null, runsScored: Number(ball.runs || 0), runsOffBat: undefined }
  }
  switch (et) {
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
      return {
        code: null,
        runsScored: Number((ball.runs || 0) + (ball.extras || 0)),
        runsOffBat: undefined,
      }
  }
}

function inningsTotal(inn) {
  let total = 0
  for (const b of inn.balls) {
    const et = b.extraType ? String(b.extraType).toLowerCase() : null
    const r = Number(b.runs || 0)
    const x = Number(b.extras || 0)
    if (!et || x === 0) total += r
    else if (et === 'wd' || et === 'wide') total += (x || 1)
    else if (et === 'nb' || et === 'no_ball' || et === 'no-ball') total += 1 + r
    else if (et === 'b' || et === 'bye' || et === 'lb' || et === 'leg_bye' || et === 'leg-bye')
      total += x
    else total += r + x
  }
  return total
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
  if (extraCode === 'wd') return [striker, nonStriker]
  return runs % 2 === 1 ? [nonStriker, striker] : [striker, nonStriker]
}

async function playInnings(apiBase, gameId, inn, batIds, bowlIds) {
  const delivs = [...inn.balls].sort((a, b) => a.over - b.over || a.ball - b.ball)
  const order = buildBattingOrder(inn)
  let striker = inn.opening_pair.striker
  let nonStriker = inn.opening_pair.non_striker
  const queue = order.filter((n) => n !== striker && n !== nonStriker)
  let curOver = -1

  for (const ball of delivs) {
    if (ball.over !== curOver) {
      curOver = ball.over
      const bowlerId = bowlIds.get(ball.bowler)
      if (!bowlerId) throw new Error(`Unknown bowler "${ball.bowler}"`)
      await startOver(apiBase, gameId, bowlerId)
    }

    const sId = batIds.get(striker)
    const nId = batIds.get(nonStriker)
    const bowId = bowlIds.get(ball.bowler)
    if (!sId || !nId || !bowId) {
      const miss = []
      if (!sId) miss.push('striker')
      if (!nId) miss.push('non-striker')
      if (!bowId) miss.push('bowler')
      throw new Error(`Missing IDs for ${ball.over}.${ball.ball}: ${miss.join(', ')}`)
    }

    const { code, runsScored, runsOffBat } = normalizeExtra(ball)
    const payload = {
      striker_id: sId,
      non_striker_id: nId,
      bowler_id: bowId,
      is_wicket: Boolean(ball.wicket),
    }
    if (code) {
      payload.extra = code
      if (code === 'nb') payload.runs_off_bat = runsOffBat ?? 0
      else payload.runs_scored = runsScored
    } else {
      payload.runs_scored = runsScored
    }

    if (ball.wicketType) payload.dismissal_type = ball.wicketType
    if (ball.fielder) {
      const fid = bowlIds.get(ball.fielder)
      if (fid) payload.fielder_id = fid
    }

    await postDelivery(apiBase, gameId, payload)

    if (ball.wicket) {
      const next = queue.shift()
      if (!next) throw new Error('Ran out of batters to replace wicket')
      const id = batIds.get(next)
      if (!id) throw new Error(`Unknown batter ${next}`)
      await replaceBatter(apiBase, gameId, id)
      striker = next
    } else {
      const r = code === 'nb' ? (runsOffBat ?? 0) : runsScored
      ;[striker, nonStriker] = rotateStrike(striker, nonStriker, r, code)
    }

    if (ball.ball === 6) [striker, nonStriker] = [nonStriker, striker]
  }
}

function mapPlayers(players) {
  const m = new Map()
  for (const p of players) m.set(p.name, p.id)
  return m
}

async function createLiveGame(apiBase, { oversLimit = 2 } = {}) {
  const teamAName = `Cypress A ${Date.now()}`
  const teamBName = `Cypress B ${Date.now()}`
  const playersA = Array.from({ length: 11 }, (_, i) => `A Player ${i + 1}`)
  const playersB = Array.from({ length: 11 }, (_, i) => `B Player ${i + 1}`)

  const game = await httpRequest(apiBase, '/games', {
    method: 'POST',
    body: {
      team_a_name: teamAName,
      team_b_name: teamBName,
      players_a: playersA,
      players_b: playersB,
      match_type: 'limited',
      overs_limit: oversLimit,
      toss_winner_team: teamAName,
      decision: 'bat',
    },
  })

  const gameId = game.id
  const teamAPlayers = game?.team_a?.players || []
  const teamBPlayers = game?.team_b?.players || []

  const strikerId = teamAPlayers[0]?.id
  const nonStrikerId = teamAPlayers[1]?.id
  const bowlerId = teamBPlayers[0]?.id

  if (!strikerId || !nonStrikerId || !bowlerId) {
    throw new Error('Missing player ids to start live game')
  }

  await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/innings/start`, {
    method: 'POST',
    body: {
      striker_id: strikerId,
      non_striker_id: nonStrikerId,
      opening_bowler_id: bowlerId,
    },
  })

  // await startOver(apiBase, gameId, bowlerId)

  return {
    gameId,
    strikerId,
    nonStrikerId,
    bowlerId,
    teamAPlayers,
    teamBPlayers,
    teamAName,
    teamBName,
    nextBowlerId: teamBPlayers[1]?.id ?? null,
  }
}

async function bowlLegalBalls(apiBase, gameId, ctx, count = 6) {
  let striker = ctx.strikerId
  let nonStriker = ctx.nonStrikerId
  for (let i = 0; i < count; i += 1) {
    await postDelivery(apiBase, gameId, {
      striker_id: striker,
      non_striker_id: nonStriker,
      bowler_id: ctx.bowlerId,
      runs_scored: (i % 2) + 1,
      is_wicket: false,
    })
    // rotate on odd runs
    if (((i % 2) + 1) % 2 === 1) {
      ;[striker, nonStriker] = [nonStriker, striker]
    }
  }
  return { striker, nonStriker }
}

async function seedOverComplete(apiBase, opts = {}) {
  const live = await createLiveGame(apiBase, opts)
  await bowlLegalBalls(apiBase, live.gameId, live, 6)
  return live
}

async function seedInningsBreak(apiBase, opts = {}) {
  const live = await createLiveGame(apiBase, { oversLimit: 1, ...opts })
  await bowlLegalBalls(apiBase, live.gameId, live, 6)
  // Best-effort nudge backend into innings break if supported
  try {
    await httpRequest(apiBase, `/games/${encodeURIComponent(live.gameId)}/innings/end`, {
      method: 'POST',
    })
  } catch {
    /* ignore if endpoint not supported */
  }
  return live
}

async function seedWeatherDelay(apiBase, opts = {}) {
  const live = await createLiveGame(apiBase, opts)
  try {
    await httpRequest(apiBase, `/games/${encodeURIComponent(live.gameId)}/interruptions/start`, {
      method: 'POST',
      body: { kind: 'weather', note: 'Cypress weather pause' },
    })
  } catch {
    /* non-fatal; interruption banner may not show */
  }
  return live
}

export async function seedMatch(apiBase, frontendDir) {
  try {
    const fx = loadFixture(frontendDir)
    const [teamAName, teamBName] = fx.teams
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

    const [inn1, inn2] = fx.innings

    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/innings/start`, {
      method: 'POST',
      body: {
        striker_id: teamAIds.get(inn1.opening_pair.striker),
        non_striker_id: teamAIds.get(inn1.opening_pair.non_striker),
        opening_bowler_id: teamBIds.get((inn1.balls[0] || {}).bowler),
      },
    })

    await playInnings(apiBase, gameId, inn1, teamAIds, teamBIds)

    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/innings/start`, {
      method: 'POST',
      body: {
        striker_id: teamBIds.get(inn2.opening_pair.striker),
        non_striker_id: teamBIds.get(inn2.opening_pair.non_striker),
        opening_bowler_id: teamAIds.get((inn2.balls[0] || {}).bowler),
      },
    })

    await playInnings(apiBase, gameId, inn2, teamBIds, teamAIds)

    // Finalize server state for the match
    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/finalize`, {
      method: 'POST',
    })

    // Persist an explicit result so /games/{id}/results is never null
    const aScore = inningsTotal(inn1)
    const bScore = inningsTotal(inn2)
    const tie = aScore === bScore
    const margin = Math.abs(aScore - bScore)
    const winner = tie ? '' : (aScore > bScore ? teamAName : teamBName)
    const text = tie ? 'Match tied' : `${winner} won by ${margin} runs`

    const body = {
      match_id: gameId,
      winner: tie ? null : winner,
      team_a_score: aScore,
      team_b_score: bScore,
      winner_team_name: tie ? null : winner,
      method: tie ? 'tie' : 'by runs',
      margin: tie ? 0 : margin,
      result_text: text,
      completed_at: null,
    }

    await httpRequest(apiBase, `/games/${encodeURIComponent(gameId)}/results`, {
      method: 'POST',
      body,
    })

    return { gameId }
  } catch (err) {
    console.error('[matchSimulator] seedMatch error', err)
    throw err
  }
}

export {
  createLiveGame,
  seedOverComplete,
  seedInningsBreak,
  seedWeatherDelay,
}
