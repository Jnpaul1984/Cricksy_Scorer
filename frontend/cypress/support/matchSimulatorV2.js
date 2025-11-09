import * as fs from 'node:fs'
import * as path from 'node:path'

/**
 * Improved Match Simulator with Better Error Handling
 * 
 * Features:
 * - Comprehensive error handling and logging
 * - Automatic batsman selection after wickets
 * - Retry logic for transient failures
 * - Detailed progress reporting
 * - Validation at each step
 */

const API_HEADERS = {
  'Content-Type': 'application/json',
}

class MatchSimulatorError extends Error {
  constructor(message, context = {}) {
    super(message)
    this.name = 'MatchSimulatorError'
    this.context = context
  }
}

/**
 * HTTP request wrapper with better error handling
 */
async function httpRequest(base, urlPath, options = {}, retries = 2) {
  const url = `${base.replace(/\/+$/, '')}${urlPath}`
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        method: options.method || 'GET',
        headers: options.body ? API_HEADERS : {},
        body: options.body ? JSON.stringify(options.body) : undefined,
      })
      
      if (!res.ok) {
        const text = await res.text()
        let errorDetail
        try {
          const json = JSON.parse(text)
          errorDetail = json.detail || text
        } catch {
          errorDetail = text
        }
        
        // Don't retry 4xx errors (client errors)
        if (res.status >= 400 && res.status < 500) {
          throw new MatchSimulatorError(
            `${res.status} ${res.statusText}: ${errorDetail}`,
            {
              status: res.status,
              url,
              method: options.method || 'GET',
              body: options.body,
              detail: errorDetail
            }
          )
        }
        
        // Retry 5xx errors (server errors)
        if (attempt < retries) {
          console.warn(`Request failed (attempt ${attempt + 1}/${retries + 1}), retrying...`)
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
          continue
        }
        
        throw new MatchSimulatorError(
          `${res.status} ${res.statusText}: ${errorDetail}`,
          { status: res.status, url, method: options.method || 'GET' }
        )
      }
      
      if (res.status === 204) {
        return undefined
      }
      
      return await res.json()
    } catch (error) {
      if (error instanceof MatchSimulatorError) {
        throw error
      }
      
      // Retry network errors
      if (attempt < retries) {
        console.warn(`Network error (attempt ${attempt + 1}/${retries + 1}), retrying...`)
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
        continue
      }
      
      throw new MatchSimulatorError(
        `Network error: ${error.message}`,
        { url, originalError: error }
      )
    }
  }
}

/**
 * Load fixture file with validation
 */
function loadFixture(frontendDir) {
  try {
    const fixturePath = path.resolve(frontendDir, 'simulated_t20_match.json')
    const raw = fs.readFileSync(fixturePath, 'utf-8')
    const fixture = JSON.parse(raw)
    
    // Validate fixture structure
    if (!fixture.teams || fixture.teams.length !== 2) {
      throw new Error('Fixture must have exactly 2 teams')
    }
    if (!fixture.innings || fixture.innings.length !== 2) {
      throw new Error('Fixture must have exactly 2 innings')
    }
    
    return fixture
  } catch (error) {
    throw new MatchSimulatorError(
      `Failed to load fixture: ${error.message}`,
      { frontendDir, originalError: error }
    )
  }
}

/**
 * Build batting order from fixture
 */
function buildBattingOrder(innings) {
  const order = []
  const seen = new Set()
  
  // Add openers first
  order.push(innings.opening_pair.striker)
  order.push(innings.opening_pair.non_striker)
  seen.add(innings.opening_pair.striker)
  seen.add(innings.opening_pair.non_striker)
  
  // Add remaining batsmen in order of appearance
  for (const ball of innings.balls) {
    if (!seen.has(ball.batsman)) {
      order.push(ball.batsman)
      seen.add(ball.batsman)
    }
  }
  
  return order
}

/**
 * Normalize extra type from fixture format
 */
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

/**
 * Batsman Manager - handles batsman selection after wickets
 */
class BatsmanManager {
  constructor(gameData, battingTeamLetter) {
    this.gameData = gameData
    this.battingTeamLetter = battingTeamLetter
    this.battingTeamPlayers = battingTeamLetter === 'A' ? 
      gameData.team_a.players : gameData.team_b.players
    this.availableBatsmen = this.battingTeamPlayers.map(p => p.id)
    this.currentBatsmenOnField = new Set()
    this.nextBatsmanIndex = 0
  }
  
  setOpeners(strikerId, nonStrikerId) {
    this.currentBatsmenOnField.add(strikerId)
    this.currentBatsmenOnField.add(nonStrikerId)
    this.nextBatsmanIndex = 2
  }
  
  hasAvailableBatsman() {
    return this.nextBatsmanIndex < this.availableBatsmen.length
  }
  
  getNextBatsman() {
    if (!this.hasAvailableBatsman()) {
      throw new MatchSimulatorError('No more batsmen available')
    }
    
    const batsmanId = this.availableBatsmen[this.nextBatsmanIndex]
    this.nextBatsmanIndex++
    this.currentBatsmenOnField.add(batsmanId)
    return batsmanId
  }
  
  async selectNextBatsman(apiBase, gameId) {
    if (!this.hasAvailableBatsman()) {
      console.warn('No more batsmen available (all out scenario)')
      return null
    }
    
    const batsmanId = this.getNextBatsman()
    
    try {
      await httpRequest(apiBase, `/games/${gameId}/next-batter`, {
        method: 'POST',
        body: { batter_id: batsmanId }
      })
      return batsmanId
    } catch (error) {
      throw new MatchSimulatorError(
        `Failed to select next batsman: ${error.message}`,
        { batsmanId, gameId, originalError: error }
      )
    }
  }
}

/**
 * Main match seeding function with improved error handling
 */
export async function seedMatch(apiBase, frontendDir, options = {}) {
  const {
    verbose = false,
    onProgress = null
  } = options
  
  const log = (message, data = {}) => {
    if (verbose) {
      console.log(`[MatchSimulator] ${message}`, data)
    }
    if (onProgress) {
      onProgress({ message, ...data })
    }
  }
  
  try {
    // Load and validate fixture
    log('Loading fixture...')
    const fixture = loadFixture(frontendDir)
    log('Fixture loaded', { 
      teams: fixture.teams,
      innings: fixture.innings.length
    })
    
    const playerIds = new Map()
    const teamIds = new Map()
    
    // 1) Create match
    log('Creating match...')
    const matchPayload = {
      match_type: 'limited',
      overs_limit: 20,
      team_a_name: fixture.teams[0],
      team_b_name: fixture.teams[1],
      players_a: buildBattingOrder(fixture.innings[0]),
      players_b: buildBattingOrder(fixture.innings[1]),
      toss_winner_team: 'A',
      elected_to: 'bat',
    }
    
    const gameData = await httpRequest(apiBase, '/games', {
      method: 'POST',
      body: matchPayload,
    })
    
    const gameId = gameData.id
    log('Match created', { gameId })
    
    // Store team IDs
    teamIds.set(fixture.teams[0], gameData.team_a.id)
    teamIds.set(fixture.teams[1], gameData.team_b.id)
    
    // Store player IDs
    for (const player of gameData.team_a.players) {
      playerIds.set(player.name, player.id)
    }
    for (const player of gameData.team_b.players) {
      playerIds.set(player.name, player.id)
    }
    
    // 2) Play each innings
    for (let inningsIdx = 0; inningsIdx < fixture.innings.length; inningsIdx++) {
      const innings = fixture.innings[inningsIdx]
      const teamId = teamIds.get(innings.team)
      const battingTeamLetter = gameData.team_a.id === teamId ? 'A' : 'B'
      
      log(`Starting innings ${inningsIdx + 1}`, {
        team: innings.team,
        balls: innings.balls.length
      })
      
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
      
      log('Openers set', {
        striker: innings.opening_pair.striker,
        nonStriker: innings.opening_pair.non_striker
      })
      
      // Initialize batsman manager
      const batsmanManager = new BatsmanManager(gameData, battingTeamLetter)
      batsmanManager.setOpeners(strikerId, nonStrikerId)
      
      // Play each ball
      let previousBallWasWicket = false
      let ballsPlayed = 0
      let wicketsCount = 0
      
      for (let i = 0; i < innings.balls.length; i++) {
        const ball = innings.balls[i]
        
        // If previous ball was a wicket, select new batsman
        if (previousBallWasWicket) {
          try {
            const newBatsmanId = await batsmanManager.selectNextBatsman(apiBase, gameId)
            if (newBatsmanId) {
              log(`New batsman selected after wicket`, { 
                batsmanIndex: batsmanManager.nextBatsmanIndex - 1
              })
            }
            previousBallWasWicket = false
          } catch (error) {
            // If we can't select a new batsman, the innings might be over (all out)
            log('Could not select new batsman', { error: error.message })
            break
          }
        }
        
        // Prepare delivery payload
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
        
        // Post delivery
        try {
          await httpRequest(apiBase, `/games/${gameId}/deliveries`, {
            method: 'POST',
            body: deliveryPayload,
          })
          
          ballsPlayed++
          if (ball.wicket) {
            wicketsCount++
            previousBallWasWicket = true
          }
          
          // Log progress every 20 balls
          if (ballsPlayed % 20 === 0) {
            log(`Progress: ${ballsPlayed}/${innings.balls.length} balls`, {
              wickets: wicketsCount
            })
          }
        } catch (error) {
          throw new MatchSimulatorError(
            `Failed to post delivery ${i + 1}: ${error.message}`,
            {
              innings: inningsIdx + 1,
              ball: i + 1,
              deliveryPayload,
              originalError: error
            }
          )
        }
      }
      
      log(`Innings ${inningsIdx + 1} complete`, {
        balls: ballsPlayed,
        wickets: wicketsCount
      })
      
      // Start next innings if not the last one
      if (inningsIdx < fixture.innings.length - 1) {
        const nextInnings = fixture.innings[inningsIdx + 1]
        const nextStrikerId = playerIds.get(nextInnings.opening_pair.striker)
        const nextNonStrikerId = playerIds.get(nextInnings.opening_pair.non_striker)
        const nextBowlerId = playerIds.get(innings.balls[0].bowler)
        
        await httpRequest(apiBase, `/games/${gameId}/innings/start`, {
          method: 'POST',
          body: {
            striker_id: nextStrikerId,
            non_striker_id: nextNonStrikerId,
            opening_bowler_id: nextBowlerId
          }
        })
        
        log('Next innings started')
      }
    }
    
    // 3) Finalize match
    log('Finalizing match...')
    await httpRequest(apiBase, `/games/${gameId}/finalize`, { method: 'POST' })
    log('Match finalized')
    
    // Get final result
    const finalSnapshot = await httpRequest(apiBase, `/games/${gameId}/snapshot`)
    
    return {
      gameId,
      success: true,
      result: finalSnapshot.result,
      summary: finalSnapshot.first_inning_summary
    }
  } catch (error) {
    if (error instanceof MatchSimulatorError) {
      console.error('[MatchSimulator] Error:', error.message, error.context)
      throw error
    }
    
    throw new MatchSimulatorError(
      `Unexpected error: ${error.message}`,
      { originalError: error }
    )
  }
}

/**
 * Simplified version for Cypress tasks
 */
export async function seedMatchSimple(apiBase, frontendDir) {
  const result = await seedMatch(apiBase, frontendDir, { verbose: true })
  return {
    gameId: result.gameId,
    result: result.result?.result_text
  }
}

