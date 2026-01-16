// frontend/src/composables/useCanonicalMetrics.ts
/**
 * Canonical Metrics Composable
 * 
 * Single source of truth for all scoreboard-critical metrics.
 * Primary data source: Pinia gameStore.liveSnapshot (real-time Socket.IO)
 * Fallback: GET /games/{gameId} API call
 * 
 * NON-NEGOTIABLE RULE:
 * All UI scoreboard values MUST use this composable.
 * No local CRR/RRR/balls_remaining calculations allowed.
 */

import { computed, ref, watch, type Ref } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import { apiRequest } from '@/services/api'
import type { GameState } from '@/types'

export interface ExtrasBreakdown {
  total: number
  wides: number
  noBalls: number
  byes: number
  legByes: number
}

export interface CanonicalMetrics {
  // Core scoreboard
  score: number | null
  wickets: number | null
  overs: string  // "12.3" format
  ballsRemaining: number | null
  
  // Run rates
  crr: number | null
  rrr: number | null
  
  // Extras breakdown
  extras: ExtrasBreakdown
  
  // Meta
  updatedAt: Date | null
  isStale: boolean  // > 30s since last update
}

export function useCanonicalMetrics(gameIdInput: Ref<string> | string) {
  const gameStore = useGameStore()
  const gameId = typeof gameIdInput === 'string' ? ref(gameIdInput) : gameIdInput
  
  const isRefreshing = ref(false)
  const lastError = ref<string | null>(null)
  
  // Primary source: liveSnapshot from Socket.IO
  const snapshot = computed(() => gameStore.liveSnapshot)
  
  // Core scoreboard values
  const score = computed(() => snapshot.value?.total_runs ?? null)
  
  const wickets = computed(() => snapshot.value?.total_wickets ?? null)
  
  const overs = computed(() => {
    const oversCompleted = snapshot.value?.overs_completed ?? 0
    const ballsThisOver = snapshot.value?.balls_this_over ?? 0
    return `${oversCompleted}.${ballsThisOver}`
  })
  
  const ballsRemaining = computed(() => {
    // ALWAYS use backend-calculated value
    return snapshot.value?.balls_remaining ?? null
  })
  
  // Run rates - BACKEND ONLY
  const crr = computed(() => {
    // NO local fallback calculation allowed
    return snapshot.value?.current_run_rate ?? null
  })
  
  const rrr = computed(() => {
    // NO local fallback calculation allowed
    return snapshot.value?.required_run_rate ?? null
  })
  
  // Extras breakdown
  const extras = computed<ExtrasBreakdown>(() => {
    const extrasData = snapshot.value?.extras
    
    if (extrasData && typeof extrasData === 'object') {
      return {
        total: extrasData.total ?? 0,
        wides: extrasData.wides ?? 0,
        noBalls: extrasData.no_balls ?? 0,
        byes: extrasData.byes ?? 0,
        legByes: extrasData.leg_byes ?? 0,
      }
    }
    
    // If backend doesn't provide extras breakdown, return zeros
    return {
      total: 0,
      wides: 0,
      noBalls: 0,
      byes: 0,
      legByes: 0,
    }
  })
  
  // Meta information
  const updatedAt = computed(() => {
    const timestamp = snapshot.value?.last_updated
    return timestamp ? new Date(timestamp) : null
  })
  
  const isStale = computed(() => {
    const updated = updatedAt.value
    if (!updated) return true
    
    const now = new Date()
    const ageMs = now.getTime() - updated.getTime()
    return ageMs > 30000 // 30 seconds
  })
  
  // Refresh from API (fallback when socket data missing)
  async function refresh() {
    if (!gameId.value || isRefreshing.value) return
    
    try {
      isRefreshing.value = true
      lastError.value = null
      
      const game = await apiRequest<GameState>(`/games/${gameId.value}`)
      
      // Store will be updated via normal mechanisms
      // This is just to trigger a fresh fetch
      console.info('[useCanonicalMetrics] Refreshed from API:', game.id)
    } catch (err) {
      lastError.value = err instanceof Error ? err.message : 'Failed to refresh metrics'
      console.error('[useCanonicalMetrics] Refresh failed:', lastError.value)
    } finally {
      isRefreshing.value = false
    }
  }
  
  // Auto-refresh when snapshot becomes stale
  watch(isStale, (stale) => {
    if (stale && !isRefreshing.value) {
      console.warn('[useCanonicalMetrics] Snapshot is stale, refreshing...')
      refresh()
    }
  })
  
  // Composable return object
  return {
    // Core metrics
    score,
    wickets,
    overs,
    ballsRemaining,
    
    // Run rates
    crr,
    rrr,
    
    // Extras
    extras,
    
    // Meta
    updatedAt,
    isStale,
    
    // Methods
    refresh,
    isRefreshing: computed(() => isRefreshing.value),
    lastError: computed(() => lastError.value),
  }
}

/**
 * Helper to format CRR/RRR for display
 */
export function formatRunRate(rate: number | null, decimals = 2): string {
  if (rate === null || rate === undefined) return '—'
  return rate.toFixed(decimals)
}

/**
 * Helper to format balls remaining as overs
 */
export function formatBallsAsOvers(balls: number | null): string {
  if (balls === null || balls === undefined) return '—'
  const overs = Math.floor(balls / 6)
  const remainingBalls = balls % 6
  return remainingBalls > 0 ? `${overs}.${remainingBalls}` : `${overs}`
}
