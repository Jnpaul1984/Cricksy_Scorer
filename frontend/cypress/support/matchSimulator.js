import * as fs from 'node:fs'
import * as path from 'node:path'

const API_HEADERS = {
  'Content-Type': 'application/json',
}

async function httpRequest(base, urlPath, options = {}) {
  const url = `${base.replace(/\/+$/, '')}${urlPath}`
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
  // Ensure openers are at the front
  const openerSet = new Set([innings.opening_pair.striker, innings.opening_pair.non_striker])
  const remaining = order.filter((name) => !openerSet.has(name))
  return [innings.opening_pair.striker, innings.opening_pair.non_striker, ...remaining]
}

function normalizeExtra(ball) {
  const extraType = ball.extraType ? ball.extraType.toLowerCase() : null
  if (!extraType || ball.extras === 0) {
    return { code: null, runsScored: ball.runs, runsOffBat: undefined }
  }
  switch (extraType) {
    case 'wd':
    case 'wide':
      return { code: 'wd', runsScored: ball.extras || 1, runsOffBat: undefined }
    case 'nb':
    case 'noball':
      return { code: 'nb', runsScored: ball.extras || 1, runsOffBat: ball.runs }
    case 'b':
    case 'bye':
      return { code: 'b', runsScored: ball.extras, runsOffBat: undefined }
    case 'lb':
    case 'legbye':
      return { code: 'lb', runsScored: ball.extras, runsOffBat: undefined }
    default:
      return { code: null, runsScored: ball.runs, runsOffBat: undefined }
  }
}

export async function seedMatch(apiBase, frontendDir) {
  const fixture = loadFixture(frontendDir)
  const playerIds = new Map()
  const teamIds = new Map()

  // 1) Create match
  const matchPayload = {
    match_type: 'limited',
    overs_limit: 20,
    team_a_name: fixture.teams[0],
    team_b_name: fixture.teams[1],
    players_a: buildBattingOrder(fixture.innings[0]),
    players_b: buildBattingOrder(fixture.innings[1]),
    toss_winner_team: 'A',
    decision: 'bat',
  }
  const gameData = await httpRequest(apiBase, '/games', {
    method: 'POST',
    body: matchPayload,
  })
  const gameId = gameData.id
  teamIds.set(fixture.teams[0], gameData.team_a.id)
  teamIds.set(fixture.teams[1], gameData.team_b.id)
  for (const p of gameData.team_a.players) {
    playerIds.set(p.name, p.id)
  }
  for (const p of gameData.team_b.players) {
    playerIds.set(p.name, p.id)
  }

  // 2) First innings starts automatically, no need to call innings/start

  // 3) Play innings
  for (let inningsIdx = 0; inningsIdx < fixture.innings.length; inningsIdx++) {
    const innings = fixture.innings[inningsIdx]
    const teamId = teamIds.get(innings.team)
    const battingTeamLetter = gameData.team_a.id === teamId ? 'A' : 'B'

    // Set openers
    const strikerId = playerIds.get(innings.opening_pair.striker)
    const nonStrikerId = playerIds.get(innings.opening_pair.non_striker)
    await httpRequest(apiBase, `/games/${gameId}/openers`, {
      method: 'POST',
      body: {
        striker_id: strikerId,
        non_striker_id: nonStrikerId,
        team: battingTeamLetter,
      },
    })

    // Set bowling order if provided
    // Note: bowling order endpoint may not exist in API, skipping
    // if (innings.bowling_order && innings.bowling_order.length > 0) {
    //   const bowlerIds = innings.bowling_order.map((name) => playerIds.get(name))
    //   await httpRequest(apiBase, `/games/${gameId}/set_bowling_order`, {
    //     method: 'POST',
    //     body: {
    //       bowler_ids: bowlerIds,
    //       team: battingTeamLetter === 'A' ? 'B' : 'A',
    //     },
    //   })
    // }

    // Track batting order - get all batsmen from this team
    const battingTeamPlayers = battingTeamLetter === 'A' ? gameData.team_a.players : gameData.team_b.players
    const availableBatsmen = battingTeamPlayers.map(p => p.id)
    let currentBatsmenOnField = new Set([strikerId, nonStrikerId])
    let nextBatsmanIndex = 2 // Start from 3rd batsman (0-indexed)

    // Play each ball
    let previousBallWasWicket = false
    for (let i = 0; i < innings.balls.length; i++) {
      const ball = innings.balls[i]

      // If previous ball was a wicket, select new batsman before this delivery
      if (previousBallWasWicket && nextBatsmanIndex < availableBatsmen.length) {
        const newBatsmanId = availableBatsmen[nextBatsmanIndex]
        nextBatsmanIndex++

        await httpRequest(apiBase, `/games/${gameId}/next-batter`, {
          method: 'POST',
          body: {
            batter_id: newBatsmanId
          }
        })

        currentBatsmenOnField.add(newBatsmanId)
        previousBallWasWicket = false
      }
      const batsmanId = playerIds.get(ball.batsman)
      const bowlerId = playerIds.get(ball.bowler)
      const extra = normalizeExtra(ball)

      const deliveryPayload = {
        batsman_id: batsmanId,
        bowler_id: bowlerId,
        runs_scored: extra.runsScored,
      }
      if (extra.code) {
        deliveryPayload.extra_type = extra.code
      }
      if (extra.runsOffBat !== undefined) {
        deliveryPayload.runs_off_bat = extra.runsOffBat
      }
      if (ball.wicket) {
        deliveryPayload.is_wicket = true
        deliveryPayload.dismissal_type = ball.wicketType || 'bowled'
        if (ball.fielder) {
          const fielderId = playerIds.get(ball.fielder)
          if (fielderId) {
            deliveryPayload.fielder_id = fielderId
          }
        }
      }

      await httpRequest(apiBase, `/games/${gameId}/deliveries`, {
        method: 'POST',
        body: deliveryPayload,
      })

      // Mark if this was a wicket for next iteration
      if (ball.wicket) {
        previousBallWasWicket = true
      }
    }

    // Start next innings if not the last one
    if (inningsIdx < fixture.innings.length - 1) {
      const nextInnings = fixture.innings[inningsIdx + 1]
      const nextStrikerId = playerIds.get(nextInnings.opening_pair.striker)
      const nextNonStrikerId = playerIds.get(nextInnings.opening_pair.non_striker)
      // Get first bowler from previous innings (now bowling team)
      const nextBowlerId = playerIds.get(innings.balls[0].bowler)

      await httpRequest(apiBase, `/games/${gameId}/innings/start`, {
        method: 'POST',
        body: {
          striker_id: nextStrikerId,
          non_striker_id: nextNonStrikerId,
          opening_bowler_id: nextBowlerId
        }
      })
    }
  }

  // 4) Finalize match
  await httpRequest(apiBase, `/games/${gameId}/finalize`, { method: 'POST' })

  return { gameId, success: true }
}
