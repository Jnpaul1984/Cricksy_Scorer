import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach } from 'vitest'

import { useGameStore } from '@/stores/gameStore'

describe('gameStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initialization', () => {
    it('initializes with default state', () => {
      const store = useGameStore()

      expect(store.currentGame).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('isGameActive returns false when no game loaded', () => {
      const store = useGameStore()
      expect(store.isGameActive).toBe(false)
    })

    it('isGameActive returns true when game is in progress', () => {
      const store = useGameStore()

      store.snapshot = { status: 'GAMESTATUS.IN_PROGRESS' } as any
      expect(store.isGameActive).toBe(true)

      store.snapshot = { status: 'IN_PROGRESS' } as any
      expect(store.isGameActive).toBe(true)
    })

    it('isGameCompleted returns true for completed status', () => {
      const store = useGameStore()
      store.currentGame = {
        id: 'test-game',
        status: 'completed',
      } as any

      expect(store.isGameCompleted).toBe(true)
    })

    it('isFirstInnings returns true for first innings', () => {
      const store = useGameStore()
      store.currentGame = {
        id: 'test-game',
        current_inning: 1,
      } as any

      expect(store.isFirstInnings).toBe(true)
    })

    it('isSecondInnings returns true for second innings', () => {
      const store = useGameStore()
      store.currentGame = {
        id: 'test-game',
        current_inning: 2,
      } as any

      expect(store.isSecondInnings).toBe(true)
    })
  })

  describe('score computed property', () => {
    it('returns default score when no game loaded', () => {
      const store = useGameStore()

      const score = store.score
      expect(score.runs).toBe(0)
      expect(score.wickets).toBe(0)
    })

    it('returns current score when game is loaded', () => {
      const store = useGameStore()
      store.currentGame = {
        id: 'test-game',
        total_runs: 120,
        total_wickets: 5,
      } as any

      const score = store.score
      expect(score.runs).toBe(120)
      expect(score.wickets).toBe(5)
    })
  })

  describe('team computed properties', () => {
    it('battingTeam returns null when no game loaded', () => {
      const store = useGameStore()
      expect(store.battingTeam).toBeNull()
    })

    it('bowlingTeam returns null when no game loaded', () => {
      const store = useGameStore()
      expect(store.bowlingTeam).toBeNull()
    })

    it('battingTeam returns team_a when batting_team_name matches team_a.name', () => {
      const store = useGameStore()
      const teamA = { name: 'Team A', players: [] }
      store.currentGame = {
        id: 'test-game',
        team_a: teamA,
        team_b: { name: 'Team B', players: [] },
        batting_team_name: 'Team A',
      } as any

      expect(store.battingTeam).toEqual(teamA)
    })

    it('battingTeam returns team_b when batting_team_name matches team_b.name', () => {
      const store = useGameStore()
      const teamB = { name: 'Team B', players: [] }
      store.currentGame = {
        id: 'test-game',
        team_a: { name: 'Team A', players: [] },
        team_b: teamB,
        batting_team_name: 'Team B',
      } as any

      expect(store.battingTeam).toEqual(teamB)
    })
  })

  describe('canScore / canScoreDelivery backend gating', () => {
    type GameStore = ReturnType<typeof useGameStore>

    const setValidSelection = (store: GameStore) => {
      store.setSelectedStriker('striker-1')
      store.setSelectedNonStriker('non-striker-1')
      store.setSelectedBowler('bowler-1')
    }

    it('backend says no -> cannot score', () => {
      const store = useGameStore()
      store.snapshot = {
        status: 'GAMESTATUS.IN_PROGRESS',
        canScore: false,
      } as any
      setValidSelection(store)

      expect(store.canScoreDelivery).toBe(false)
    })

    it('backend says yes + valid selection -> can score', () => {
      const store = useGameStore()
      store.snapshot = {
        status: 'GAMESTATUS.IN_PROGRESS',
        canScore: true,
      } as any
      setValidSelection(store)

      expect(store.isGameActive).toBe(true)
      expect(store.canScoreDelivery).toBe(true)
    })

    it('no backend flag -> defaults to legacy canScore', () => {
      const store = useGameStore()
      store.snapshot = {
        status: 'GAMESTATUS.IN_PROGRESS',
      } as any
      setValidSelection(store)

      expect(store.isGameActive).toBe(true)
      expect(store.canScoreDelivery).toBe(true)
      expect(store.canScoreDelivery).toBe(store.canScore)
    })

    it('backend says yes but striker not selected -> blocked', () => {
      const store = useGameStore()
      store.snapshot = {
        status: 'GAMESTATUS.IN_PROGRESS',
        canScore: true,
      } as any
      setValidSelection(store)
      store.setSelectedStriker(null)
      store.setSelectedNonStriker(null)
      store.liveSnapshot = { canScore: true } as any

      expect(store.canScoreDelivery).toBe(false)
    })
  })
})
