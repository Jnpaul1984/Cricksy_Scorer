<script setup lang="ts">
/* eslint-disable */
/* --- Vue & Router --- */

/* --- Stores --- */
import { storeToRefs } from 'pinia'
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'

/* --- UI Components --- */
import BattingCard from '@/components/BattingCard.vue'
import BowlingCard from '@/components/BowlingCard.vue'
import DeliveryTable from '@/components/DeliveryTable.vue'
import PresenceBar from '@/components/PresenceBar.vue'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import ShotMapCanvas from '@/components/scoring/ShotMapCanvas.vue'
import { useRoleBadge } from '@/composables/useRoleBadge'
import { apiService } from '@/services/api'
import { generateAICommentary, type AICommentaryRequest, fetchMatchAiCommentary, type MatchAiCommentaryItem } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import { useGameStore } from '@/stores/gameStore'
import { isValidUUID } from '@/utils'
import legacyApiService, { API_BASE, apiRequest } from '@/utils/api'

const isDev = import.meta.env.DEV
const normId = (v: unknown) => String(v ?? '').trim()
// ================== Local domain types (narrow) ==================
type UUID = string
type Player = { id: UUID; name: string }
type Team = { name: string; players: Player[]; playing_xi?: UUID[] }
type BatCardEntry = {
  player_id: UUID; player_name: string; runs: number; balls_faced: number;
  fours: number; sixes: number; strike_rate: number; how_out?: string; is_out: boolean
}
type BowlCardEntry = {
  player_id: UUID; player_name: string; overs_bowled: number; maidens: number;
  runs_conceded: number; wickets_taken: number; economy: number
}
type DeliveryRowForTable = {
  over_number: number; ball_number: number; runs_scored: number;
  striker_id: UUID; non_striker_id: UUID; bowler_id: UUID;
  extra?: 'wd' | 'nb' | 'b' | 'lb'; is_wicket?: boolean; commentary?: string;
  dismissed_player_id?: UUID | null; at_utc?: string
  extra_runs?: number
  runs_off_bat?: number
  shot_map?: string | null
}

// ================== Single-panel state ==================
type ExtraOpt = 'none' | 'nb' | 'wd' | 'b' | 'lb'

const extra = ref<ExtraOpt>('none')
const offBat = ref<number>(0)
const extraRuns = ref<number>(1)
const isWicket = ref<boolean>(false)
const dismissal = ref<string | null>(null)
const dismissedName = ref<string | null>(null)
const shotMap = ref<string | null>(null)
if (import.meta.env?.DEV) {
  console.info('GameScoringView setup refs', { isWicket, extra })
}

// ================== AI Commentary state ==================
const aiCommentary = ref<string | null>(null)
const aiLoading = ref(false)
const aiError = ref<string | null>(null)

// ================== Match AI Commentary state (toggle & panel) ==================
const matchAiEnabled = ref(false)
const matchAiCommentary = ref<MatchAiCommentaryItem[]>([])
const matchAiLoading = ref(false)
const matchAiError = ref<string | null>(null)

async function loadMatchAiCommentary() {
  if (!gameId.value) return
  matchAiLoading.value = true
  matchAiError.value = null
  try {
    const resp = await fetchMatchAiCommentary(gameId.value)
    matchAiCommentary.value = resp.commentary
  } catch (err: unknown) {
    matchAiError.value = err instanceof Error ? err.message : 'Failed to load match AI commentary'
  } finally {
    matchAiLoading.value = false
  }
}

// Watch toggle – fetch when enabled
watch(matchAiEnabled, (enabled) => {
  if (enabled) {
    loadMatchAiCommentary()
  }
})

// --- Fielder (XI + subs) for wicket events ---
const selectedFielderId = ref<UUID>('' as UUID)
const inningsStartIso = ref<string | null>(null)
// Does this dismissal type require a fielder?
const needsFielder = computed<boolean>(() => {
  const t = (dismissal.value || '').toLowerCase()
  return t === 'caught' || t === 'run_out' || t === 'stumped'
})

// Mark which ids belong to the XI so we can label subs in the dropdown
const bowlingXIIds = computed<Set<UUID>>(() => new Set(bowlingRosterXI.value.map(p => p.id)))

// Reset fielder when wicket toggled off / dismissal changes to a non-fielder type
watch(isWicket, (on) => {
  if (!on) { dismissal.value = null; selectedFielderId.value = '' as UUID }
})
watch(dismissal, (t) => {
  if (!needsFielder.value) selectedFielderId.value = '' as UUID
})
watch(extra, (t) => {
  if (t === 'wd') { extraRuns.value = 1; offBat.value = 0 }
  else if (t === 'b' || t === 'lb') { extraRuns.value = 0; offBat.value = 0 }
  else if (t === 'none') { offBat.value = 0 }
  if (t !== 'none' && t !== 'nb') {
    shotMap.value = null
  }
})


const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const authStore = useAuthStore()

// Captain/Keeper badge composable
const currentGame = computed(() => gameStore.currentGame as any)
const teamAName = computed(() => String(currentGame.value?.team_a?.name ?? ''))
// Derive batting team name from liveSnapshot (updates on innings change)
const battingTeamName = computed(() => {
  const g = currentGame.value
  if (!g) return ''
  // Use liveSnapshot's batting_team_name if available, otherwise fall back to game's
  const snap = liveSnapshot.value as any
  return snap?.batting_team_name ?? g.batting_team_name ?? ''
})
const isBattingTeamA = computed(() => battingTeamName.value === teamAName.value)
const { roleBadge, bowlerRoleBadge } = useRoleBadge({ currentGame, isBattingTeamA })

// Reactive refs from the stores
const { liveSnapshot } = storeToRefs(gameStore)
const { needsNewBatter, needsNewOver } = storeToRefs(gameStore)
const { extrasBreakdown } = storeToRefs(gameStore)
const { dlsKind } = storeToRefs(gameStore)
const { runsRequired, targetSafe, requiredRunRate, ballsBowledTotal } = storeToRefs(gameStore)
const {
  canScore: roleCanScore,
  isFreeUser,
  isPlayerPro,
  role: authRole,
} = storeToRefs(authStore)
const storeCanScore = computed(() => {
  if ('canScore' in gameStore) {
    // @ts-ignore  using store getter
    return gameStore.canScore
  }
  if ('canScoreDelivery' in gameStore) {
    // @ts-ignore  using store getter
    return gameStore.canScoreDelivery
  }
  return true
})
const canScore = computed(() => Boolean(storeCanScore.value && roleCanScore.value))
const proTooltip = 'Requires Coach Pro or Organization Pro'
const showScoringUpsell = computed(
  () => !roleCanScore.value && (!authRole.value || isFreeUser.value || isPlayerPro.value),
)
const showAnalystReadOnly = computed(
  () => !roleCanScore.value && authRole.value === 'analyst_pro',
)
// Allow a manual start even if the server gate didn't flip yet
const canForceStartInnings = computed(() =>
  Boolean(gameId.value) &&
  !isStartingInnings.value &&
  pendingCount.value === 0
)

function forceStartInnings(): void {
  if (!roleCanScore.value) return
  if (!canForceStartInnings.value) return

  // If the normal conditions aren't met, warn before proceeding
  const safeToStart = needsNewInningsLive.value || allOut.value || oversExhausted.value
  if (!safeToStart) {
    const ok = window.confirm(
      'It looks like the current innings may not be finished yet.\n\nStart the next innings anyway?'
    )
    if (!ok) return
  }

  // Reuse the same picker modal for openers & (optional) opening bowler
  openStartInnings()
}

// Current gameId (param or ?id=)
const gameId = computed<string>(() => (route.params.gameId as string) || (route.query.id as string) || '')

const canSubmitSimple = computed(() => {
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (!gameId.value || needsNewBatterLive.value) return false
  // Allow submit if it's the first ball and a bowler is chosen
  if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) return false
  if (!selectedStriker.value || !selectedNonStriker.value || !selectedBowler.value) return false
  if (needsNewInningsLive.value) return false
  if (isStartingInnings.value) return false
  // If it's a wicket that needs a fielder, require one
  if (isWicket.value && needsFielder.value && !selectedFielderId.value) return false

  if (extra.value === 'nb') return offBat.value >= 0
  if (extra.value === 'wd') return extraRuns.value >= 1
  if (extra.value === 'b' || extra.value === 'lb') return extraRuns.value >= 0
  return offBat.value >= 0 // legal
})


async function submitSimple() {
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) {
    openStartOver(); onError('Start the next over first'); return
  }
  if (needsNewBatterLive.value) { openSelectBatter(); onError('Select the next batter first'); return }

  try {
    const anyStore: any = gameStore as any
    const unifiedPossible = typeof anyStore.scoreDelivery === 'function'

    if (unifiedPossible) {
      const payload: Record<string, unknown> = {}

      if (extra.value === 'wd') {
        payload.extra_type = 'wd'
        payload.extra_runs = extraRuns.value
      } else if (extra.value === 'nb') {
        payload.extra_type = 'nb'
        payload.runs_off_bat = offBat.value
      } else if (extra.value === 'b' || extra.value === 'lb') {
        payload.extra_type = extra.value
        payload.extra_runs = extraRuns.value
      } else {
        payload.runs_off_bat = offBat.value
      }
      payload.shot_map = (extra.value === 'none' || extra.value === 'nb') ? (shotMap.value ?? null) : null

      if (isWicket.value) {
        payload.is_wicket = true
        payload.dismissal_type = (dismissal.value || 'bowled')
        payload.dismissed_player_name = (dismissedName.value || null)
        payload.fielder_id = needsFielder.value ? (selectedFielderId.value || null) : null
      }

      await anyStore.scoreDelivery(gameId.value, payload)
    } else {
      if (isWicket.value && extra.value === 'none') {
        await gameStore.scoreWicket(
          gameId.value,
          (dismissal.value || 'bowled'),
          undefined,
          undefined,
          (needsFielder.value ? (selectedFielderId.value || undefined) : undefined)
        )
      } else if (!isWicket.value && extra.value === 'nb') {
        await gameStore.scoreExtra(gameId.value, 'nb', offBat.value, shotMap.value ?? null)
      } else if (!isWicket.value && extra.value === 'wd') {
        await gameStore.scoreExtra(gameId.value, 'wd', extraRuns.value)
      } else if (!isWicket.value && (extra.value === 'b' || extra.value === 'lb')) {
        await gameStore.scoreExtra(gameId.value, extra.value, extraRuns.value)
      } else if (!isWicket.value && extra.value === 'none') {
        await gameStore.scoreRuns(gameId.value, offBat.value, shotMap.value ?? null)
      } else {
        const payload = {
          extra_type: extra.value !== 'none' ? extra.value : null,
          extra_runs: extra.value === 'wd'
            ? extraRuns.value
            : (extra.value === 'b' || extra.value === 'lb')
              ? extraRuns.value
              : undefined,
          runs_off_bat: extra.value === 'nb'
            ? offBat.value
            : extra.value === 'none'
              ? offBat.value
              : undefined,
          is_wicket: true,
          dismissal_type: (dismissal.value || 'bowled'),
          dismissed_player_name: (dismissedName.value || null),
          shot_map: (extra.value === 'none' || extra.value === 'nb') ? (shotMap.value ?? null) : null,
          fielder_id: needsFielder.value ? (selectedFielderId.value || null) : null,
        }
        await apiRequest(`/games/${encodeURIComponent(gameId.value)}/deliveries`, {
          method: 'POST',
          body: JSON.stringify(payload),
        })
      }
    }

    extra.value = 'none'
    offBat.value = 0
    extraRuns.value = 1
    isWicket.value = false
    dismissal.value = null
    dismissedName.value = null
    selectedFielderId.value = '' as UUID
    shotMap.value = null
    onScored()

    // Generate AI commentary (non-blocking)
    generateCommentary().catch(() => { /* ignore AI errors */ })

    // Refresh match AI commentary if enabled (non-blocking)
    if (matchAiEnabled.value) {
      loadMatchAiCommentary().catch(() => { /* ignore match AI errors */ })
    }

    await nextTick()
    maybeRotateFromLastDelivery()
  } catch (e: any) {
    onError(e?.message || 'Scoring failed')
  }
}

// ================== AI Commentary ==================
async function generateCommentary(): Promise<void> {
  if (!gameId.value) return

  // Gather current delivery context
  const snap = liveSnapshot.value as any
  const last = snap?.last_delivery ?? lastDelivery.value
  if (!last && !selectedStriker.value) return

  // Determine over/ball from last delivery or current state
  const overNum = last?.over_number ?? Math.floor(legalBallsBowled.value / 6)
  const ballNum = last?.ball_number ?? (legalBallsBowled.value % 6)

  // Calculate total runs for this delivery
  let totalRuns = 0
  if (extra.value === 'wd') {
    totalRuns = extraRuns.value
  } else if (extra.value === 'nb') {
    totalRuns = 1 + offBat.value
  } else if (extra.value === 'b' || extra.value === 'lb') {
    totalRuns = extraRuns.value
  } else {
    totalRuns = offBat.value
  }

  // Use last delivery data if available (after submit)
  if (last) {
    totalRuns = Number(last.runs_scored ?? last.runs_off_bat ?? 0) +
                Number(last.extra_runs ?? 0)
  }

  const payload: AICommentaryRequest = {
    match_id: gameId.value,
    over: overNum,
    ball: ballNum,
    runs: totalRuns,
    wicket: last?.is_wicket ?? isWicket.value,
    batter: selectedStrikerName.value || last?.striker_name || 'Batter',
    bowler: selectedBowlerName.value || last?.bowler_name || 'Bowler',
    context: {
      innings: currentInnings.value,
      total_runs: inningsScore.value.runs,
      total_wickets: inningsScore.value.wickets,
      overs: oversDisplay.value,
      extra_type: last?.extra_type ?? (extra.value !== 'none' ? extra.value : null),
      dismissal_type: last?.dismissal_type ?? dismissal.value,
      batting_team: battingTeamName.value,
    },
  }

  aiLoading.value = true
  aiError.value = null

  try {
    const response = await generateAICommentary(payload)
    aiCommentary.value = response.commentary
  } catch (e: any) {
    aiError.value = e?.message || 'Failed to generate commentary'
    console.error('AI Commentary error:', e)
  } finally {
    aiLoading.value = false
  }
}

// Clear AI state when input changes
watch([extra, offBat, extraRuns, isWicket], () => {
  aiError.value = null
})

// --- Delete last delivery ------------------------------
const deletingLast = ref(false)

const lastDelivery = computed<any | null>(() =>
  // Prefer live snapshot (if your store fills it), else fall back to the game object
  (gameStore as any)?.state?.last_delivery ??
  (gameStore.currentGame as any)?.last_delivery ??
  (rawDeliveries.value.length ? rawDeliveries.value[rawDeliveries.value.length - 1] : null)
)

// Block when: there is no ball yet, an innings gate is up, or you still have queued actions
const canDeleteLast = computed<boolean>(() =>
  Boolean(lastDelivery.value) &&
  !needsNewInningsLive.value &&
  !isStartingInnings.value &&        // â† add this guard
  pendingCount.value === 0
)


async function deleteLastDelivery(): Promise<void> {
  const id = gameId.value
  if (!id || !canDeleteLast.value || deletingLast.value) return
  deletingLast.value = true
  try {
    const anyStore: any = gameStore as any
    if (typeof anyStore.deleteLastDelivery === 'function') {
      await anyStore.deleteLastDelivery(id)
    } else if (typeof anyStore.undoLastDelivery === 'function') {
      await anyStore.undoLastDelivery(id)
    } else {
        await legacyApiService.undoLast(id)
    }
    showToast('Last delivery deleted', 'success')

    // Ensure local UI refreshes even if the socket message arrives slowly
    await gameStore.loadGame(id)
  } catch (e:any) {
    onError(e?.message || 'Failed to delete last delivery')
  } finally {
    deletingLast.value = false
  }
}

// --- DLS panel state ---
const G50 = ref(245)
const dls = computed(() => gameStore.dlsPreview)
const canShowDls = computed(() => Boolean(gameId.value) && !!(gameStore.currentGame as any)?.dls_enabled)
const loadingDls = ref(false)
const applyingDls = ref(false)

async function refreshDls() {
  if (!gameId.value) return
  loadingDls.value = true
  try {
    await gameStore.fetchDlsPreview(gameId.value, G50.value)
  } catch (e: any) {
    onError(e?.message || 'DLS preview failed')
  } finally {
    loadingDls.value = false
  }
}

async function applyDls() {
  if (!gameId.value) return
  applyingDls.value = true
  try {
    await gameStore.applyDls(gameId.value, G50.value)
    onScored()
  } catch (e:any) {
    onError(e?.message || 'Apply DLS failed')
  } finally {
    applyingDls.value = false
  }
}

// --- Reduce Overs & Live Par ---
const oversLimit = computed<number>(() => Number((gameStore.currentGame as any)?.overs_limit ?? 0))
const currentInnings = computed<1 | 2>(() => Number((gameStore.currentGame as any)?.current_inning ?? 1) as 1 | 2)
// Balls & overs remaining in the chase (defensive if not a chase or no limit)
const ballsRemaining = computed<number>(() => {
  const limit = oversLimit.value ? Number(oversLimit.value) * 6 : 0
  return Math.max(0, limit - Number(ballsBowledTotal.value || 0))
})
const oversRemainingDisplay = computed<string>(() => {
  const balls = ballsRemaining.value
  const ov = Math.floor(balls / 6)
  const rem = balls % 6
  return `${ov}.${rem}`
})

const reduceScope = ref<'match' | 'innings'>('match')
const reduceInnings = ref<1 | 2>(currentInnings.value)
const oversNew = ref<number | null>(null)
const reducingOvers = ref(false)
const computingPar = ref(false)
// --- Optional "Fielding subs" management card ---
const showSubsCard = ref<boolean>(false)
const SUBS_CARD_KEY = 'cricksy.ui.showSubsCard'

onMounted(() => {
  try {
    const saved = localStorage.getItem(SUBS_CARD_KEY)
    if (saved != null) showSubsCard.value = saved === '1'
  } catch {}
})
watch(showSubsCard, (v) => {
  try { localStorage.setItem(SUBS_CARD_KEY, v ? '1' : '0') } catch {}
})

const canReduce = computed(() => oversNew.value != null && oversNew.value! > 0)

async function doReduceOvers() {
  if (!gameId.value || !canReduce.value) return
  reducingOvers.value = true
  try {
    if (reduceScope.value === 'innings') {
      await gameStore.reduceOversForInnings(gameId.value, reduceInnings.value, oversNew.value as number)
    } else {
      await gameStore.reduceOvers(gameId.value, oversNew.value as number)
    }
    showToast('Overs limit updated', 'success')
    try { await refreshDls() } catch {}
  } catch (e:any) {
    onError(e?.message || 'Failed to reduce overs')
  } finally {
    reducingOvers.value = false
  }
}

async function updateParNow() {
  if (!gameId.value) return
  computingPar.value = true
  try {
    await gameStore.dlsParNow(gameId.value, dlsKind.value, currentInnings.value)
    showToast('Par updated', 'success')
  } catch (e:any) {
    onError(e?.message || 'Par calc failed')
  } finally {
    computingPar.value = false
  }
}

// prime input with current limit when game loads
watch(() => oversLimit.value, (v) => { if (v && !oversNew.value) oversNew.value = v })

// --- Match controls: Weather + Reduce Overs quick actions ---
const weatherDlgOpen = ref(false)
const weatherNote = ref<string>('')

function openWeather() { weatherDlgOpen.value = true }
function closeWeather() { weatherDlgOpen.value = false }

const apiBase =
  (API_BASE || (typeof window !== 'undefined' ? window.location.origin : '')).replace(/\/$/, '')

// Store is the single writer; no manual refresh calls here.
async function startWeatherDelay() {
  const id = gameId.value
  if (!id) return
  if (!roleCanScore.value) return
  try {
    await gameStore.startInterruption('weather', weatherNote.value || undefined)
    showToast('Weather delay started', 'success')
    closeWeather()
    await nextTick()
  } catch (e:any) {
    onError(e?.message || 'Failed to start interruption')
  }
}

async function resumeAfterWeather() {
  const id = gameId.value
  if (!id) return
  if (!roleCanScore.value) return
  try {
    await gameStore.stopInterruption('weather')
    showToast('Play resumed', 'success')
    closeWeather()
    await nextTick()
  } catch (e:any) {
    onError(e?.message || 'Failed to resume')
  }
}

// Smooth jump to the existing "Reduce Overs" card
const reduceOversCardRef = ref<HTMLElement | null>(null)
function jumpToReduceOvers() {
  reduceOversCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ================== XI LOCAL STORAGE ==================
type XI = { team_a_xi: UUID[]; team_b_xi: UUID[] }
const XI_KEY = (id: string) => `cricksy.xi.${id}`
const xiA = ref<Set<UUID> | null>(null)
const xiB = ref<Set<UUID> | null>(null)
const xiLoaded = ref<boolean>(false)

function loadXIForGame(id: string): void {
  xiA.value = xiB.value = null
  xiLoaded.value = false
  try {
    const raw = localStorage.getItem(XI_KEY(id))
    if (raw) {
      const parsed = JSON.parse(raw) as XI
      if (Array.isArray(parsed.team_a_xi)) xiA.value = new Set(parsed.team_a_xi)
      if (Array.isArray(parsed.team_b_xi)) xiB.value = new Set(parsed.team_b_xi)
    }
  } catch { /* ignore */ }
  xiLoaded.value = true
}

// ================== SELECTION STATE ==================
const selectedStriker = computed<string>({
  get: () => (gameStore.uiState.selectedStrikerId || '') as string,
  set: (v) => gameStore.setSelectedStriker(normId(v) || null),
})
const selectedNonStriker = computed<string>({
  get: () => (gameStore.uiState.selectedNonStrikerId || '') as string,
  set: (v) => gameStore.setSelectedNonStriker(normId(v) || null),
})
const selectedBowler = computed<string>({
  get: () => (gameStore.uiState.selectedBowlerId || '') as string,
  set: (v) => gameStore.setSelectedBowler(normId(v) || null),
})


// ================== CONNECTION / OFFLINE QUEUE ==================
const liveReady = computed<boolean>(() => gameStore.connectionStatus === 'connected')
const pendingForThisGame = computed(() => gameStore.offlineQueue.filter(q => q.gameId === gameId.value && q.status !== 'flushing'))
const pendingCount = computed<number>(() => pendingForThisGame.value.length)


// ================== ROSTERS (FILTERED BY XI) ==================


// Names for status text
const selectedStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedStriker.value)?.name || '')
const selectedNonStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedNonStriker.value)?.name || '')
const selectedBowlerName = computed<string>(() => bowlingPlayers.value.find((p) => p.id === selectedBowler.value)?.name || '')

// Dismissed dropdown: limit to current batters to avoid ambiguity
const dismissedOptions = computed<Player[]>(() => {
  const list = battingPlayers.value
  const s = list.find(p => p.id === selectedStriker.value)
  const ns = list.find(p => p.id === selectedNonStriker.value)
  const out: Player[] = []
  if (s) out.push(s)
  if (ns && (!s || ns.id !== s.id)) out.push(ns)
  return out
})

watch([isWicket, selectedStriker, selectedNonStriker], () => {
  if (isWicket.value && !dismissedName.value && dismissedOptions.value.length > 0) {
    dismissedName.value = dismissedOptions.value[0].name
  }
})
const {
  battingRosterXI,
  bowlingRosterXI,
  battingRowsXI,       // NEW: stat rows for current batting XI
  bowlingRowsXI,       // NEW: stat rows for current bowling XI
  fieldingSubs,
  fielderRosterAll,
} = storeToRefs(gameStore)

// selectors:
const battingPlayers = computed(() => battingRosterXI.value)
const bowlingPlayers = computed(() => bowlingRosterXI.value)
const fielderOptions = computed(() => [
  ...bowlingRosterXI.value,     // XI
  ...fieldingSubs.value,        // subs
])

const nextBattingXI = computed<Player[]>(() => {
  if (needsNewInningsLive.value) {
    const isInnings1Break = currentInnings.value === 1 && ballsBowledTotal.value > 0
    return isInnings1Break ? bowlingRosterXI.value : battingRosterXI.value
  }
  return battingRosterXI.value
})
const nextBowlingXI = computed<Player[]>(() => {
  if (needsNewInningsLive.value) {
    const isInnings1Break = currentInnings.value === 1 && ballsBowledTotal.value > 0
    return isInnings1Break ? battingRosterXI.value : bowlingRosterXI.value
  }
  return bowlingRosterXI.value
})
// ================== SCORECARDS (from store) ==================
// Preferred order from the store if available
const storeBattingOrderIds = computed<string[] | null>(() => {
  const ids = (stateAny.value?.batting_order_ids as string[] | undefined) ||
              ((gameStore.currentGame as any)?.batting_order_ids as string[] | undefined)
  return Array.isArray(ids) ? ids.map(normId) : null
})

// Fallback: infer order from first appearance **in this innings** only
const battingAppearanceOrder = computed<string[]>(() => {
  if (storeBattingOrderIds.value && storeBattingOrderIds.value.length) return storeBattingOrderIds.value
  const seen = new Set<string>()
  const order: string[] = []
  for (const d of deliveriesThisInnings.value) {
    for (const id of [d.striker_id, d.non_striker_id]) {
      const nid = normId(id)
      if (nid && !seen.has(nid)) { seen.add(nid); order.push(nid) }
    }
  }
  return order
})

const battingEntries = computed(() => {
  const rows = (battingRowsXI.value || []).map((r: any) => ({
    player_id: r.id,
    player_name: String(r.name),
    runs: Number(r.runs),
    balls_faced: Number(r.balls),
    fours: Number(r.fours),
    sixes: Number(r.sixes),
    strike_rate: Number(r.sr),
    how_out: r.howOut,
    is_out: Boolean(r.isOut),
    // optional: if your row has a batting position/index, keep it for tie-breaks
    _pos: typeof r.pos === 'number' ? r.pos : undefined
  }))

  const order = battingAppearanceOrder.value
  const rank = new Map(order.map((id, i) => [id, i]))

  rows.sort((a, b) => {
    const ra = rank.get(normId(a.player_id)) ?? 9999
    const rb = rank.get(normId(b.player_id)) ?? 9999
    if (ra !== rb) return ra - rb
    // tie-breaker: explicit position if present
    if (a._pos != null && b._pos != null) return a._pos - b._pos
    return String(a.player_name).localeCompare(String(b.player_name))
  })

  return rows as unknown as BatCardEntry[]
})


const bowlingEntries = computed(() =>
  (bowlingRowsXI.value || []).map((r: any) => {
    const pid = String(r.id)
    const derived = bowlingDerivedByPlayer.value[pid]
    const balls = derived ? derived.balls : 0
    const runsToBowler = derived ? derived.runs : Number(r.runs ?? r.runs_conceded ?? 0)
    const maidens = derived ? derived.maidens : Number(r.maidens ?? 0)
    const oversTxt = balls ? oversDisplayFromBalls(balls) : String(r.overs ?? r.overs_bowled ?? '0.0')
    const econTxt = balls ? econ(runsToBowler, balls) : (typeof r.econ === 'number' ? r.econ.toFixed(2) : (Number(r.econ || 0)).toFixed(2))

    return {
      player_id: pid,
      player_name: String(r.name),
      overs_bowled: oversTxt,
      maidens,
      runs_conceded: runsToBowler,
      wickets_taken: Number(r.wkts ?? r.wickets_taken ?? 0),
      economy: Number(econTxt),
    }
  })
)



// ================== Deliveries (DEDUPE) ==================
// normalize over/ball before keying
function obOf(d:any){
  const overLike = d.over_number ?? d.over
  const ballLike = d.ball_number ?? d.ball
  if (typeof ballLike === 'number' && typeof overLike === 'number') {
    return { over: Math.max(0, Math.floor(overLike)), ball: Math.max(0, ballLike) }
  }
  if (typeof overLike === 'string') {
    const [o,b] = overLike.split('.')
    return { over: Number(o)||0, ball: Number(b)||0 }
  }
  if (typeof overLike === 'number') {
    const whole = Math.floor(overLike)
    const tenth = Math.round((overLike - whole) * 10)
    return { over: whole, ball: Math.max(0, Math.min(5, tenth)) }
  }
  return { over: 0, ball: 0 }
}

// âœ… stable identity: innings + over + ball only
function makeKey(d:any): string {
  const inn = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number ?? 0)
  const { over, ball } = obOf(d)
  return `${inn}:${over}:${ball}`
}


const rawDeliveries = computed<any[]>(() => {
  const g = gameStore.currentGame as any
  return Array.isArray(g?.deliveries) ? g.deliveries : []
})

const dedupedDeliveries = computed<DeliveryRowForTable[]>(() => {
  const byKey = new Map<string, any>()
  for (const d of rawDeliveries.value) byKey.set(makeKey(d), d) // last one wins
  const parseOverBall = (overLike: unknown, ballLike: unknown) => {
    if (typeof ballLike === 'number') return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: ballLike }
    if (typeof overLike === 'string') { const [o, b] = overLike.split('.'); return { over: Number(o) || 0, ball: Number(b) || 0 } }
    if (typeof overLike === 'number') { const over = Math.floor(overLike); const ball = Math.max(0, Math.round((overLike - over) * 10)); return { over, ball } }
    return { over: 0, ball: 0 }
  }
  return Array.from(byKey.values()).map((d: any) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      over_number: over,
      ball_number: ball,
      runs_scored: Number(d.runs_scored ?? d.runs) || 0,
      striker_id: normId(d.striker_id),
      non_striker_id: normId(d.non_striker_id),
      bowler_id: normId(d.bowler_id),
      extra: (d.extra ?? d.extra_type ?? undefined) as DeliveryRowForTable['extra'] | undefined,
      extra_runs: Number(d.extra_runs ?? 0),
      runs_off_bat: Number(d.runs_off_bat ?? d.runs ?? 0),
      is_wicket: Boolean(d.is_wicket),
      commentary: d.commentary as string | undefined,
      dismissed_player_id: (d.dismissed_player_id ? normId(d.dismissed_player_id) : null) as UUID | null,
      at_utc: d.at_utc as string | undefined,
      shot_map: typeof d.shot_map === 'string' ? d.shot_map : null,
    }
  }).sort((a, b) => (a.over_number - b.over_number) || (a.ball_number - b.ball_number))
})

// ðŸ”§ NEW: helpers to scope deliveries to the current innings
function inningsOf(d:any): number | null {
  const v = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number)
  return Number.isFinite(v) ? v : null
}

const deliveriesThisInningsRaw = computed<any[]>(() => {
  const cur = currentInnings.value
  const arr = rawDeliveries.value
  const hasInnings = arr.some(d => inningsOf(d) != null)
  if (hasInnings) return arr.filter(d => inningsOf(d) === cur)

  // Fallback only if absolutely no innings markers exist (old data)
  if (cur === 1) return arr
  if (inningsStartIso.value) {
    // strict: only include items with a timestamp after start
    return arr.filter(d => d.at_utc && String(d.at_utc) >= inningsStartIso.value!)
  }
  return [] // no markers, no timestamps â€” donâ€™t risk mixing innings
})



function dedupeByKey(arr:any[]) {
  const byKey = new Map<string, any>()
  for (const d of arr) byKey.set(makeKey(d), d)
  return Array.from(byKey.values())
}

const deliveriesThisInnings = computed<DeliveryRowForTable[]>(() => {
  const parseOverBall = (overLike: unknown, ballLike: unknown) => {
    if (typeof ballLike === 'number') return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: ballLike }
    if (typeof overLike === 'string') { const [o, b] = overLike.split('.'); return { over: Number(o) || 0, ball: Number(b) || 0 } }
    if (typeof overLike === 'number') { const over = Math.floor(overLike); const ball = Math.max(0, Math.round((overLike - over) * 10)); return { over, ball } }
    return { over: 0, ball: 0 }
  }
  return dedupeByKey(deliveriesThisInningsRaw.value).map((d: any) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      over_number: over,
      ball_number: ball,
      runs_scored: Number(d.runs_scored ?? d.runs) || 0,
      striker_id: normId(d.striker_id),
      non_striker_id: normId(d.non_striker_id),
      bowler_id: normId(d.bowler_id),
      extra: (d.extra ?? d.extra_type ?? undefined) as DeliveryRowForTable['extra'] | undefined,
      extra_runs: Number(d.extra_runs ?? 0),                       // âœ… added
      runs_off_bat: Number(d.runs_off_bat ?? d.runs ?? 0),        // âœ… added
      is_wicket: Boolean(d.is_wicket),
      commentary: d.commentary as string | undefined,
      dismissed_player_id: (d.dismissed_player_id ? normId(d.dismissed_player_id) : null) as UUID | null,
      at_utc: d.at_utc as string | undefined,
      shot_map: typeof d.shot_map === 'string' ? d.shot_map : null,
    }
  }).sort((a, b) => (a.over_number - b.over_number) || (a.ball_number - b.ball_number))
})

// == Derived bowling figures from deliveries in *this innings* ==
const bowlingDerivedByPlayer = computed<Record<string, { balls: number; runs: number; maidens: number }>>(() => {
  const out: Record<string, { balls: number; runs: number; maidens: number }> = {}
  // group per over for maiden detection
  const overRuns: Record<string, number> = {}

  const add = (pid: string) => (out[pid] ||= { balls: 0, runs: 0, maidens: 0 })

  for (const d of deliveriesThisInnings.value) {
    const pid = String(d.bowler_id || '')
    if (!pid) continue
    const rec = add(pid)

    // Runs conceded to bowler
    if (d.extra === 'wd') {
      rec.runs += Number(d.extra_runs || 0)               // wides: all wides to bowler
    } else if (d.extra === 'nb') {
      rec.runs += 1 + Number(d.runs_off_bat || 0)         // no-ball: 1 penalty + off-bat
      // ball does NOT count
    } else if (d.extra === 'b' || d.extra === 'lb') {
      // byes/leg-byes: NO runs to bowler, but DO consume a ball
      rec.balls += 1
    } else {
      // legal: off-bat runs to bowler, consumes a ball
      rec.runs += Number(d.runs_off_bat ?? d.runs_scored ?? 0)
      rec.balls += 1
    }

    // Track runs in the *over* to compute maidens later (legal extras still count to over total)
    const overKey = `${d.bowler_id}:${d.over_number}`
    let totalThisBall = 0
    if (d.extra === 'wd') totalThisBall = Number(d.extra_runs || 0)
    else if (d.extra === 'nb') totalThisBall = 1 + Number(d.runs_off_bat || 0)
    else if (d.extra === 'b' || d.extra === 'lb') totalThisBall = Number(d.runs_scored || d.extra_runs || 0)
    else totalThisBall = Number(d.runs_off_bat ?? d.runs_scored ?? 0)
    overRuns[overKey] = (overRuns[overKey] || 0) + totalThisBall
  }

  // Maidens: any completed over with 0 runs
  for (const key of Object.keys(overRuns)) {
    const [pid, overStr] = key.split(':')
    const over = Number(overStr)
    // count legal balls in that over
    const legalBallsInOver = deliveriesThisInnings.value.filter(d =>
      String(d.bowler_id) === pid &&
      d.over_number === over &&
      (d.extra !== 'wd' && d.extra !== 'nb')
    ).length
    if (legalBallsInOver === 6 && overRuns[key] === 0) {
      add(pid).maidens += 1
    }
  }

  return out
})

// === Current bowler figures (match the scorecardâ€™s logic) ====================
const currentBowlerDerived = computed(() => {
  const id = currentBowlerId.value
  if (!id) return null

  // Derived balls/runs/maidens for this innings
  const base = bowlingDerivedByPlayer.value[id]

  // Get wickets from the live XI rows (authoritative wicket tally)
  const r = (bowlingRowsXI.value || []).find((p: any) => String(p.id) === String(id)) as any
  const wkts = Number(r?.wkts ?? r?.wickets_taken ?? 0)

  const balls = Number(base?.balls || 0)
  const runs  = Number(base?.runs  || 0)

  return {
    wkts,
    runs,
    balls,
    oversText: oversDisplayFromBalls(balls),
    econText: econ(runs, balls),
  }
})

// Name lookup for DeliveryTable
function playerNameById(id?: UUID | null): string {
  const nid = normId(id)
  if (!nid) return ''
  const g = gameStore.currentGame as unknown as { team_a: Team; team_b: Team } | null
  if (!g) return ''
  return (
    g.team_a.players.find(p => normId(p.id) === nid)?.name ??
    g.team_b.players.find(p => normId(p.id) === nid)?.name ??
    ''
  )
}


// ================== Helpers: SR and Economy (local) ==================
function oversDisplayFromBalls(balls: number): string {
  const ov = Math.floor(balls / 6)
  const rem = balls % 6
  return `${ov}.${rem}`
}
function econ(runsConceded: number, ballsBowled: number): string {
  if (!ballsBowled) return 'â€”'
  const overs = ballsBowled / 6
  return (runsConceded / overs).toFixed(2)
}

const cantScoreReasons = computed(() => {
  const rs:string[] = []
  if (!roleCanScore.value) rs.push(proTooltip)
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (!gameStore.currentGame) rs.push('No game loaded')
  else {
    const status = String((gameStore.currentGame as any).status || '').toLowerCase()
    if (!['in_progress','live','started'].includes(status)) {
      rs.push(`Game is ${(gameStore.currentGame as any).status}`)
    }
  }

  if (!selectedStriker.value) rs.push('Select striker')
  if (!selectedNonStriker.value) rs.push('Select non-striker')
  if (selectedStriker.value && selectedStriker.value === selectedNonStriker.value)
    rs.push('Striker and non-striker cannot be the same')

  if (!currentBowlerId.value && !(needsNewOverLive.value && firstBall && !!selectedBowler.value)) {
    rs.push('Start next over / choose bowler')
  }
  if (!selectedBowler.value) rs.push('Choose bowler')
  if (needsNewOver.value && !(firstBall && !!selectedBowler.value)) rs.push('Start next over')
  if (needsNewBatter.value) rs.push('Select next batter')
  if (needsNewInningsLive.value) rs.push('Start next innings')

  return rs
})

function clearQueuedDeliveriesForThisGame(): void {
  const id = gameId.value
  if (!id) return
  ;(gameStore as any).offlineQueue = (gameStore as any).offlineQueue.filter((q: any) => q.gameId !== id)
  console.info('Cleared offlineQueue for game', id)
}

// ================== Live strip data (current bowler / over) ==================
// ================== Live strip data (current bowler / over) ==================
const stateAny = computed(() => gameStore.state as any)
const isStartingInnings = ref(false)
// First-innings summary captured locally when we flip to innings 2
const firstInnings = ref<{ runs: number; wickets: number; overs: string } | null>(null)

// ðŸ”§ NEW: if backend publishes an innings start, adopt it
watch(() => (stateAny.value?.innings_start_at as string | undefined), (t) => {
  if (t) inningsStartIso.value = String(t)
}, { immediate: true })

// Count legal balls in *this* innings (wides/no-balls don't consume a ball)
const legalBallsBowled = computed(() =>
  deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length
)


// NEW: wickets directly from deliveries (robust even before store catches up)
const wicketsFromDeliveries = computed(() => {
  const battingIds = new Set(battingPlayers.value.map(p => normId(p.id)))
  const dismissed = new Set<string>()
  for (const d of deliveriesThisInnings.value) {
    const did = normId(d.dismissed_player_id)
    if (d.is_wicket && did && battingIds.has(did)) dismissed.add(did)
  }
  return dismissed.size
})

// All-out fallback (use XI size if available; cricket all-out threshold is 10)
const allOut = computed(() => {
  const xiSize = battingPlayers.value?.length || 11
  const maxOut = Math.max(10, xiSize - 1)
  const wicketsFromScore = Number((gameStore as any).score?.wickets ?? 0)
  const wicketsFromRows  = battingEntries.value.filter(b => b.is_out).length
  const wickets = Math.max(wicketsFromScore, wicketsFromRows, wicketsFromDeliveries.value)
  return wickets >= maxOut
})

// Overs exhausted fallback â€” IMPORTANT: use current_over_balls (your storeâ€™s field)
const ballsThisOver = computed(() => Number(stateAny.value?.current_over_balls ?? 0))
const ballsPerInningsLimit = computed(() =>
  (oversLimit.value ? oversLimit.value * 6 : Infinity)
)
const oversExhausted = computed(() =>
  legalBallsBowled.value >= ballsPerInningsLimit.value && ballsThisOver.value === 0
)

// Track last time the innings number changed
const inningsFlipAt = ref<number>(0)
watch(() => (gameStore.currentGame as any)?.current_inning, () => {
  inningsFlipAt.value = Date.now()
})

// Small suppression window after flip (ms)
const SUPPRESS_DERIVED_MS = 10000

const needsNewInningsLive = computed<boolean>(() => {
  const statusRaw = String((gameStore.currentGame as any)?.status || '')
  const status = statusRaw.toLowerCase()
  const serverGate =
    Boolean(stateAny.value?.needs_new_innings) ||
    status === 'innings_break'

  // If server says the gate is up, respect it.
  if (serverGate) return true

  // While server says we're in progress, don't re-raise the gate locally.
  if (status === 'in_progress') return false

  // Right after an innings flip, ignore local "allOut/oversExhausted" noise.
  if (Date.now() - inningsFlipAt.value < SUPPRESS_DERIVED_MS) return false

  // Otherwise, the local fallbacks can raise the gate.
  return allOut.value || oversExhausted.value
})




const needsNewOverLive   = computed<boolean>(() => Boolean(stateAny.value?.needs_new_over))
const needsNewBatterLive = computed<boolean>(() => Boolean(stateAny.value?.needs_new_batter))
const currentBowlerId   = computed<UUID | null>(() => (stateAny.value?.current_bowler_id ?? null) as UUID | null)
const lastBallBowlerId  = computed<UUID | null>(() => (stateAny.value?.last_ball_bowler_id ?? null) as UUID | null)
const currentOverBalls  = computed<number>(() => Number(stateAny.value?.current_over_balls ?? 0))
const midOverChangeUsed = computed<boolean>(() => Boolean(stateAny.value?.mid_over_change_used))

const currentBowler = computed<Player | null>(() => {
  const id = currentBowlerId.value
  if (!id) return null
  return bowlingPlayers.value.find(p => p.id === id) || null
})

const currentBowlerStats = computed<{ runs: number; balls: number }>(() => {
  const id = currentBowlerId.value
  if (!id) return { runs: 0, balls: 0 }

  // Prefer precomputed store stats if available
  const sAny = (gameStore as any).bowlingStatsByPlayer as
    | Record<string, { runsConceded: number; balls: number }>
    | undefined
  const s = sAny?.[id]
  if (s) return { runs: Number(s.runsConceded), balls: Number(s.balls) }

  // Fallback: derive from deliveries (per your backend semantics)
  const filtered = deliveriesThisInnings.value.filter(d => d.bowler_id === id)

  const addRuns = (d: DeliveryRowForTable) => {
    if (d.extra === 'wd') return Number(d.extra_runs || 0)            // all wides to bowler
    if (d.extra === 'nb') return 1 + Number(d.runs_off_bat || 0)      // penalty + off bat
    if (d.extra === 'b' || d.extra === 'lb') return 0                  // byes: none to bowler
    return Number(d.runs_off_bat ?? d.runs_scored ?? 0)                // legal: off bat
  }

  const runs = filtered.reduce((sum, d) => sum + addRuns(d), 0)

  // Legal balls: byes/leg-byes DO consume a ball; wides/nb do not
  const isLegal = (d: DeliveryRowForTable) => !d.extra || d.extra === 'b' || d.extra === 'lb'
  const balls = filtered.filter(isLegal).length

  return { runs, balls }
})


function parseOversNotation(s?: string | number | null) {
  if (s == null) return { oc: 0, ob: 0 }
  const str = String(s)
  const [o, b] = str.split('.')
  const oc = Number(o) || 0
  let ob = Number(b) || 0
  if (ob < 0) ob = 0
  if (ob > 5) ob = 5
  return { oc, ob }
}

const oversDisplay = computed<string>(() => {
  const legal = deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length
  const ov = Math.floor(legal / 6)
  const rem = legal % 6
  return `${ov}.${rem}`
})


const eligibleNextOverBowlers = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== lastBallBowlerId.value))
const replacementOptions = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== currentBowlerId.value))
const canUseMidOverChange = computed(() => currentOverBalls.value < 6 && !midOverChangeUsed.value)
const overInProgress = computed<boolean>(() => Number((stateAny.value?.balls_this_over ?? 0)) > 0)

const inningsScore = computed<{ runs: number; wickets: number }>(() => ({
  runs: Number((gameStore as any).score?.runs ?? 0),
  wickets: Number((gameStore as any).score?.wickets ?? 0),
}))

// Target shown during the chase (if server provided)
const target = computed<number | null>(() => {
  const t = (gameStore.currentGame as any)?.target
  return typeof t === 'number' ? t : null
})

// Legal balls in the *current* (latest) over
const legalBallsThisOver = computed(() => {
  const arr = deliveriesThisInnings.value
  if (!arr.length) return 0
  const lastOver = Math.max(...arr.map(d => d.over_number))
  return arr.filter(d =>
    d.over_number === lastOver && (d.extra !== 'wd' && d.extra !== 'nb')
  ).length
})

// Local fallback: if weâ€™ve bowled 6 legal balls and no innings gate is up, prompt next over.
const needsNewOverDerived = computed(() =>
  legalBallsThisOver.value === 6 && !needsNewInningsLive.value
)

// ---- Start Next Innings ----
const startInningsDlgOpen = ref(false)
const nextStrikerId = ref<UUID>('' as UUID)
const nextNonStrikerId = ref<UUID>('' as UUID)
const openingBowlerId = ref<UUID>('' as UUID)

function openStartInnings(): void {
  if (!roleCanScore.value) return
  // sensible defaults
  const bat = nextBattingXI.value
  const bowl = nextBowlingXI.value
  nextStrikerId.value = (bat[0]?.id ?? '') as UUID
  nextNonStrikerId.value = (bat[1]?.id ?? '') as UUID
  openingBowlerId.value = (bowl[0]?.id ?? '') as UUID
  startInningsDlgOpen.value = true
}
function closeStartInnings(): void { startInningsDlgOpen.value = false }

async function confirmStartInnings(): Promise<void> {
  if (!roleCanScore.value) return
  console.log('[confirmStartInnings] clicked');
  const id = gameId.value
  if (!id) return
  try {
    inningsStartIso.value = new Date().toISOString()
    isStartingInnings.value = true

    // Cache the first-innings summary locally (runs/wkts/overs) before we flip
    try {
      firstInnings.value = {
        runs: inningsScore.value.runs,
        wickets: inningsScore.value.wickets,
        overs: oversDisplay.value,
      }
    } catch { /* noop */ }

    const strikerId = normId(nextStrikerId.value)
    const nonStrikerId = normId(nextNonStrikerId.value)
    const openingBowler = normId(openingBowlerId.value)

    // Guard: we never want to send null/empty IDs to the API
    if (!strikerId || !nonStrikerId || !openingBowler) {
      console.warn('[confirmStartInnings] missing opener selection', {
        strikerId,
        nonStrikerId,
        openingBowler,
      })
      isStartingInnings.value = false
      return
    }

    const payload = {
      striker_id:        strikerId,
      non_striker_id:    nonStrikerId,
      opening_bowler_id: openingBowler,
    } as const

    await apiService.setOpeners(id, {
      striker_id:     payload.striker_id,
      non_striker_id: payload.non_striker_id,
    })

    const anyStore: any = gameStore as any
    if (typeof anyStore.startNextInnings === 'function') {
      await anyStore.startNextInnings(id, payload)
    } else {
      await legacyApiService.startNextInnings(id, payload)
      await gameStore.loadGame(id)
    }

    // ðŸ”§ Optimistic local clear so the dialog actually goes away now
    // (server snapshot will arrive and confirm shortly)
    gameStore.mergeGamePatch({ status: 'in_progress' } as any)
    inningsFlipAt.value = Date.now()
    if (liveSnapshot.value) {
      liveSnapshot.value = {
        ...liveSnapshot.value,
        needs_new_innings: false,
        current_bowler_id: openingBowler,
        current_striker_id: strikerId,
        current_non_striker_id: nonStrikerId
      } as any
    }

    // Optimistic selections
    selectedStriker.value = normId(nextStrikerId.value) as string
    selectedNonStriker.value = normId(nextNonStrikerId.value) as string
    if (openingBowlerId.value) selectedBowler.value = normId(openingBowlerId.value) as string


    isStartingInnings.value = false
    showToast('Next innings started', 'success')
    closeStartInnings()
  } catch (e:any) {
    isStartingInnings.value = false
    onError(e?.message || 'Failed to start next innings')
    // (Optional) console for quick visibility:
    console.error('startNextInnings error:', e)
  }
}


// ================== EMBED / SHARE PANEL ==================
const theme = ref<'auto' | 'dark' | 'light'>('dark')
const title = ref<string>('Live Scoreboard')
const logo = ref<string>('')
const height = ref<number>(180)

// script setup

const sponsorsUrl = ref<string>(`${apiBase}/sponsors/cricksy/sponsors.json`)


const embedUrl = computed<string>(() => {
  const routerMode = (import.meta as any).env?.VITE_ROUTER_MODE ?? 'history'
  const useHash = routerMode === 'hash'
  const base = window.location.origin + (useHash ? '/#' : '')
  const path = `/embed/${encodeURIComponent(gameId.value)}`
  const qs = new URLSearchParams()
  if (theme.value && theme.value !== 'auto') qs.set('theme', theme.value)
  if (title.value) qs.set('title', title.value)
  if (logo.value) qs.set('logo', logo.value)
  if (sponsorsUrl.value) qs.set('sponsorsUrl', sponsorsUrl.value)
  const q = qs.toString()
  return q ? `${base}${path}?${q}` : `${base}${path}`
})

const iframeCode = computed<string>(() => `<iframe src="${embedUrl.value}" width="100%" height="${height.value}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`)

const shareOpen = ref<boolean>(false)
const copied = ref<boolean>(false)
const codeRef = ref<HTMLTextAreaElement | null>(null)

function closeShare(): void { shareOpen.value = false; copied.value = false }
async function copyEmbed(): Promise<void> {
  const txt = iframeCode.value
  try {
    await navigator.clipboard.writeText(txt)
    copied.value = true
  } catch {
    const el = codeRef.value
    if (el) {
      el.focus()
      el.select()
      try { document.execCommand('copy') } catch { /* ignore */ }
      copied.value = true
    }
  }
  window.setTimeout(() => (copied.value = false), 1600)
}
watch(shareOpen, (o) => { if (o) setTimeout(() => codeRef.value?.select(), 75) })

// ================== Tiny toast ==================
type ToastType = 'success' | 'error' | 'info'
const toast = ref<{ message: string; type: ToastType } | null>(null)
let toastTimer: number | null = null
function showToast(message: string, type: ToastType = 'success', ms = 1800): void {
  toast.value = { message, type }
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = null), ms) as unknown as number
}
function onScored(): void { showToast(pendingCount.value > 0 ? 'Saved (queued) âœ“' : 'Saved âœ“', 'success') }
function onError(message: string): void { showToast(message || 'Something went wrong', 'error', 3000) }

// ================== Lifecycle ==================
onMounted(async () => {
  const id = gameId.value
  if (!id) { void router.replace('/'); return }

  try {
    await gameStore.loadGame(id)
    loadXIForGame(id)
    gameStore.initLive(id)
    clearQueuedDeliveriesForThisGame()

    // Gate prompts after initial load
    if (liveSnapshot.value) syncBattersFromSnapshot(liveSnapshot.value as any)
    if (currentBowlerId.value) selectedBowler.value = currentBowlerId.value as UUID
    if (roleCanScore.value && needsNewBatterLive.value) openSelectBatter()
    if (roleCanScore.value && needsNewOverLive.value)  openStartOver()
  } catch (e) {
    showToast('Failed to load or connect', 'error', 3000)
    console.error('load/init failed:', e)
  }
})

onUnmounted(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
  gameStore.stopLive()
})

// --- Client fallback: derive striker/non-striker from the last delivery when snapshot is odd ---
function maybeRotateFromLastDelivery() {
  const last: any =
    (liveSnapshot.value as any)?.last_delivery ??
    (gameStore.currentGame as any)?.last_delivery
  if (!last) return

  const prevS = normId(selectedStriker.value)
  const prevNS = normId(selectedNonStriker.value)
  if (!prevS || !prevNS) return

  const x = (last.extra_type as DeliveryRowForTable['extra'] | null) || null
  const legal = !x || x === 'b' || x === 'lb'
  let swap = false

  if (legal) {
    // On legal balls, parity of off-the-bat runs decides strike
    const offBat = Number(last.runs_off_bat ?? last.runs_scored ?? 0)
    swap = (offBat % 2) === 1
  } else if (x === 'wd') {
    // wides: total includes automatic 1; only the *run(s) actually run* flip strike
    const totalWides = Math.max(1, Number(last.extra_runs ?? 1))
    const runsRun = totalWides - 1
    swap = (runsRun % 2) === 1
  } else if (x === 'nb') {
    // no-balls: penalty 1 plus *additional* runs (off bat or nb-byes if you add them later)
    const offBat = Number(last.runs_off_bat ?? 0)
    const extraBeyondPenalty = Math.max(0, Number(last.extra_runs ?? 1) - 1)
    swap = ((offBat + extraBeyondPenalty) % 2) === 1
  }

  if (swap) {
    const s = selectedStriker.value
    selectedStriker.value = selectedNonStriker.value
    selectedNonStriker.value = s
  }
}

// Keep UI batters in lockstep with server, but fix snapshot oddities locally.
function syncBattersFromSnapshot(snap: any): void {
  if (!snap) return
  const sId  = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '')
  const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '')

  if (sId)  selectedStriker.value = sId as string
  if (nsId) selectedNonStriker.value = nsId as string

  // Guard: snapshot sometimes sends SAME id for both ends; fix using last delivery parity.
  if (sId && nsId && sId === nsId) {
    maybeRotateFromLastDelivery()
  }
}

watch(liveSnapshot, (snap) => syncBattersFromSnapshot(snap))

// Keep selections valid when innings flips or XI loads
watch(currentBowlerId, (id) => { selectedBowler.value = id ? (id as UUID) : '' as unknown as UUID })
watch([bowlingPlayers, xiLoaded, currentBowlerId], () => {
  const id = selectedBowler.value
  if (id && !bowlingPlayers.value.some(p => p.id === id) && id !== currentBowlerId.value) selectedBowler.value = '' as unknown as UUID
})
watch(needsNewInningsLive, (v) => {
  if (!roleCanScore.value) return
  if (!v) return
  if (isStartingInnings.value) return               // don't pop while we're starting
  if (startInningsDlgOpen.value) return             // already open
  if (v) {
    selectedBowler.value = '' as any   // force explicit choice for the new innings
  }
  startOverDlgOpen.value = false
  selectBatterDlgOpen.value = false
  nextTick().then(() => openStartInnings())
})



watch(() => stateAny.value?.needs_new_innings, (v) => {
  if (!v) isStartingInnings.value = false
})


// Only open these gates if an innings is NOT required
watch(needsNewBatterLive, (v) => {
  if (!roleCanScore.value) return
  if (v && !needsNewInningsLive.value) openSelectBatter()
})
watch([needsNewOverLive, needsNewOverDerived], ([serverGate, localGate]) => {
  if (!roleCanScore.value) return
  if ((serverGate || localGate) && !needsNewInningsLive.value) {
    // Keep any user-chosen next bowler; just nudge the dialog if you want.
    if (!selectedBowler.value) {
      selectedBowler.value = (eligibleNextOverBowlers.value[0]?.id || '') as UUID
    }
    selectedNextOverBowlerId.value = selectedBowler.value as UUID
    openStartOver()
  }
})

watch([battingPlayers, needsNewInningsLive], ([list]) => {
  const ids = new Set(list.map(p => p.id))
  if (selectedStriker.value && !ids.has(selectedStriker.value)) {
    selectedStriker.value = '' as any
  }
  if (selectedNonStriker.value && !ids.has(selectedNonStriker.value)) {
    selectedNonStriker.value = '' as any
  }
})

watch([bowlingPlayers, needsNewInningsLive], ([list]) => {
  const ids = new Set(list.map(p => p.id))
  if (selectedBowler.value && !ids.has(selectedBowler.value)) {
    selectedBowler.value = '' as any
  }
})


// Reconnect + flush controls
function reconnect(): void {
  const id = gameId.value
  if (!id) return
  try {
    gameStore.initLive(id)
    showToast('Reconnectingâ€¦', 'info')
  } catch {
    showToast('Reconnect failed', 'error', 2500)
  }
}
function flushNow(): void {
  const id = gameId.value
  if (!id) return
  gameStore.flushQueue(id)
  showToast('Flushing queueâ€¦', 'info')
}

// ================== Start Over & Mid-over Change ==================
const startOverDlgOpen = ref(false)
const changeBowlerDlgOpen = ref(false)
const selectedNextOverBowlerId = ref<UUID>('' as UUID)
const selectedReplacementBowlerId = ref<UUID>('' as UUID)
const selectBatterDlgOpen = ref(false)
const selectedNextBatterId = ref<UUID>('' as UUID)
const canStartOverNow = computed(() => needsNewOverLive.value || !currentBowlerId.value)
const candidateBatters = computed<Player[]>(() => {
  const anyStore = gameStore as any
  if (Array.isArray(anyStore.availableBatsmen) && anyStore.availableBatsmen.length) {
    return anyStore.availableBatsmen as Player[]
  }
  const outSet = new Set(battingEntries.value.filter(b => b.is_out).map(b => b.player_id))
  return battingPlayers.value.filter(p => !outSet.has(p.id))
})



function openSelectBatter(): void {
  if (!roleCanScore.value) return
  selectedNextBatterId.value = '' as UUID
  selectBatterDlgOpen.value = true
}
function closeSelectBatter(): void { selectBatterDlgOpen.value = false }

async function confirmSelectBatter() {
  if (!roleCanScore.value) return
  const batter = normId(selectedNextBatterId.value)
  if (!batter) return

  await gameStore.replaceBatter(batter)

  // Prefer authoritative IDs from the latest snapshot / state
  const snap: any = (liveSnapshot.value as any) ?? (gameStore as any).state ?? {}
  const sId  = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '')
  const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '')

  if (sId || nsId) {
    if (sId)  selectedStriker.value = sId as string
    if (nsId) selectedNonStriker.value = nsId as string
  } else {
    // Fallback: use last deliveryâ€™s dismissed id to decide end
    const last: any =
      liveSnapshot.value?.last_delivery ??
      (gameStore.currentGame as any)?.deliveries?.slice(-1)?.[0]

    const dismissed = normId(last?.dismissed_player_id || '')
    if (dismissed && normId(selectedStriker.value) === dismissed)       selectedStriker.value = batter as string
    else if (dismissed && normId(selectedNonStriker.value) === dismissed) selectedNonStriker.value = batter as string
    else if (!selectedStriker.value)                                     selectedStriker.value = batter as string
    else if (!selectedNonStriker.value)                                  selectedNonStriker.value = batter as string
  }

  showToast('Next batter set', 'success')
  closeSelectBatter()
}


function openStartOver(): void {
  if (!roleCanScore.value) return
  const first = eligibleNextOverBowlers.value[0]?.id ?? '' as UUID
  selectedNextOverBowlerId.value = first as UUID
  startOverDlgOpen.value = true
}
function closeStartOver(): void { startOverDlgOpen.value = false }

// Store only
async function confirmStartOver(): Promise<void> {
  if (!roleCanScore.value) return
  const id = gameId.value
  const bowler = selectedNextOverBowlerId.value
  if (!id || !bowler) return
  try {
    await gameStore.startNewOver(bowler)
    selectedBowler.value = bowler
    selectedNextOverBowlerId.value = '' as UUID
    showToast('Over started', 'success')
    closeStartOver()
  } catch (err:any) {
    const msg = err?.message || 'Failed to start over'
    showToast(msg, 'error')
    console.error('confirmStartOver error:', err)
  }
}

function openChangeBowler(): void {
  if (!roleCanScore.value) return
  selectedReplacementBowlerId.value = '' as UUID
  changeBowlerDlgOpen.value = true
}
function closeChangeBowler(): void { changeBowlerDlgOpen.value = false }

async function confirmChangeBowler(): Promise<void> {
  const id = gameId.value
  const repl = selectedReplacementBowlerId.value
  if (!id || !repl) return
  try {
    await gameStore.changeBowlerMidOver(id, repl, 'injury')
    if (currentBowlerId.value) selectedBowler.value = currentBowlerId.value as UUID
    showToast('Bowler changed', 'success')
  } catch (e: any) {
    await gameStore.loadGame(id)
    selectedBowler.value = (currentBowlerId.value || '') as UUID
    onError(e?.message || 'Failed to change bowler')
  } finally {
    selectedReplacementBowlerId.value = '' as UUID
    closeChangeBowler()
  }
}
</script>

<template>
  <div class="game-scoring">
    <!-- Top toolbar -->
    <header class="toolbar">
      <div class="left">
        <h2 class="title">Scoring Console</h2>
        <span v-if="gameId" class="meta">Game: {{ gameId }}</span>
      </div>

      <div class="right">
        <button
          class="btn"
          :class="matchAiEnabled ? 'btn-primary' : 'btn-ghost'"
          title="Toggle Match AI Commentary"
          @click="matchAiEnabled = !matchAiEnabled"
        >
          🤖 AI {{ matchAiEnabled ? 'On' : 'Off' }}
        </button>

        <select v-model="theme" class="sel" aria-label="Theme" name="theme">
          <option value="auto">Theme: Auto</option>
          <option value="dark">Theme: Dark</option>
          <option value="light">Theme: Light</option>
        </select>

        <input v-model="title" class="inp" type="text" name="embedTitle" placeholder="Embed title (optional)" aria-label="Embed title" />
        <input v-model="logo" class="inp" type="url" name="logoUrl" placeholder="Logo URL (optional)" aria-label="Logo URL" />
        <button class="btn btn-primary" @click="shareOpen = true">Share</button>
      </div>
    </header>

    <main class="content">
      <!-- Live scoreboard preview â€” widget reads from store; interruptions polling disabled -->
      <ScoreboardWidget
        :game-id="gameId"
        :theme="theme"
        :title="title"
        :logo="logo"
        :api-base="apiBase"
        :sponsors-url="sponsorsUrl"
        :can-control="false"
        interruptions-mode="off"
      />

      <PresenceBar class="mb-3" :game-id="gameId" :status="gameStore.connectionStatus" :pending="pendingCount" />
      <div v-if="showScoringUpsell" class="rbac-banner warn" role="alert">
        <strong>Scoring is a Pro feature.</strong>
        <span>
          Please log in with a Coach Pro or Organization Pro account to enter deliveries.
          <RouterLink to="/login">Sign in</RouterLink>
        </span>
      </div>
      <div v-else-if="showAnalystReadOnly" class="rbac-banner info" role="status">
        <strong>Read-only mode.</strong>
        <span>Analyst Pro accounts can monitor scoring but cannot submit deliveries.</span>
      </div>

      <section
        v-if="Number((gameStore.currentGame as any)?.current_inning) === 2 && (firstInnings || targetSafe != null)"
        class="selectors card alt small-metrics"
      >
        <div class="row compact">
          <div v-if="firstInnings" class="col">
            <strong>Innings 1:</strong>
            {{ firstInnings.runs }}/{{ firstInnings.wickets }} ({{ firstInnings.overs }})
          </div>

          <div v-if="targetSafe != null" class="col">
            <strong>Target:</strong> {{ targetSafe }}
          </div>

          <div v-if="requiredRunRate != null" class="col">
            <strong>Req RPO:</strong> {{ requiredRunRate.toFixed(2) }}
            <small v-if="runsRequired != null && ballsRemaining >= 0" class="hint">
              Â· Need {{ runsRequired }} off {{ ballsRemaining }} balls ({{ oversRemainingDisplay }} overs)
            </small>
          </div>
        </div>
      </section>


      <!-- Player selectors -->
      <section class="selectors card" style="border:1px solid rgba(0,0,0,.08); border-radius:12px; padding:12px; margin-bottom:12px;">
        <h3 style="margin:0 0 8px; font-size:14px;">Players</h3>
        <div class="row">
          <div class="col">
            <label class="lbl">Striker</label>
            <select v-model="selectedStriker" class="sel" aria-label="Select striker">
              <option disabled value="">Choose striker…</option>
              <option
                v-for="p in battingPlayers"
                :key="p.id"
                :value="p.id"
                :disabled="p.id === selectedNonStriker"
              >
                {{ p.name }}{{ roleBadge(p.id) }}
              </option>
            </select>
          </div>

          <div class="col">
            <label class="lbl">Non-striker</label>
            <select v-model="selectedNonStriker" class="sel" aria-label="Select non-striker">
              <option disabled value="">Choose non-striker…</option>
              <option
                v-for="p in battingPlayers"
                :key="p.id"
                :value="p.id"
                :disabled="p.id === selectedStriker"
              >
                {{ p.name }}{{ roleBadge(p.id) }}
              </option>
            </select>
          </div>

          <div class="col">
            <label class="lbl">Bowler</label>
            <select v-model="selectedBowler" class="sel" aria-label="Select bowler">
              <option disabled value="">Choose bowler…</option>
              <option v-for="p in bowlingPlayers" :key="p.id" :value="p.id">
                {{ p.name }}{{ bowlerRoleBadge(p.id) }}
              </option>
            </select>
          </div>
        </div>

        <small v-if="selectedStrikerName && selectedBowlerName" class="hint">
          <RouterLink v-if="isValidUUID(selectedStriker)" :to="{ name: 'PlayerProfile', params: { playerId: selectedStriker } }" class="player-link">{{ selectedStrikerName }}</RouterLink><span v-else>{{ selectedStrikerName }}</span> facing <RouterLink v-if="isValidUUID(selectedBowler)" :to="{ name: 'PlayerProfile', params: { playerId: selectedBowler } }" class="player-link">{{ selectedBowlerName }}</RouterLink><span v-else>{{ selectedBowlerName }}</span>.
        </small>
      </section>

      <!-- Bowling controls -->
      <section class="selectors card alt">
        <div class="row tight">
          <div class="col">
            <button class="btn" :disabled="needsNewInningsLive || !canStartOverNow" @click="openStartOver">
              Start Next Over
            </button>
            <small class="hint">
              {{ !currentBowlerId ? 'No active bowler yet â€” start the over.' : 'Disables previous overâ€™s last bowler.' }}
            </small>
          </div>
          <div class="col">
            <button class="btn" :disabled="!canUseMidOverChange" @click="openChangeBowler">Mid-over Change</button>
            <small class="hint">Allowed once per over (injury).</small>
          </div>
          <div v-if="currentBowler" class="col bowler-now">
            <strong>Current:</strong> <RouterLink v-if="isValidUUID(currentBowler.id)" :to="{ name: 'PlayerProfile', params: { playerId: currentBowler.id } }" class="player-link">{{ currentBowler.name }}</RouterLink><span v-else>{{ currentBowler.name }}</span> ·
            <span>{{ currentBowlerDerived?.wkts ?? 0 }}-{{ currentBowlerDerived?.runs ?? 0 }}
              ({{ currentBowlerDerived?.oversText ?? '0.0' }})
            </span>
            <span> Â· Econ {{ currentBowlerDerived?.econText ?? 'â€”' }}</span>
          </div>
        </div>
      </section>

      <!-- Match controls -->
      <section class="selectors card alt">
        <div class="row tight">
          <div class="col">
            <button class="btn" data-testid="btn-open-weather" @click="openWeather">Weather interruption</button>
            <small class="hint">Pause/resume play; logs delay.</small>
          </div>
          <div class="col">
            <button class="btn" @click="jumpToReduceOvers">Reduce oversâ€¦</button>
            <small class="hint">Adjust match or innings limit.</small>
          </div>
          <div class="col">
            <button class="btn btn-ghost" :disabled="!canForceStartInnings" @click="forceStartInnings">
              Start next innings (fallback)
            </button>
            <small class="hint">Use if the innings gate doesnâ€™t appear.</small>
          </div>
          <!-- NEW: toggle for subs card -->
          <div class="col">
            <label class="lbl" style="display:flex; align-items:center; gap:6px;">
              <input v-model="showSubsCard" type="checkbox" />
              Fielding subs card
            </label>
            <small class="hint">Lists eligible substitute fielders.</small>
          </div>
        </div>
      </section>


      <!-- Gate banners -->
      <div
        v-if="needsNewBatterLive || needsNewOverLive || needsNewInningsLive"
        class="placeholder mb-3"
        role="status"
        aria-live="polite"
        data-testid="gate-banner"
      >
        <div v-if="needsNewInningsLive" data-testid="gate-innings">
          New innings required.
          <button
            v-if="roleCanScore"
            class="btn btn-ghost"
            :title="!roleCanScore ? proTooltip : undefined"
            data-testid="btn-open-start-innings"
            @click="openStartInnings"
          >
            Start next innings
          </button>
          <small v-else class="hint">Waiting for an authorized scorer.</small>
        </div>
        <div v-else-if="needsNewBatterLive" data-testid="gate-new-batter">
          New batter required.
          <button
            v-if="roleCanScore"
            class="btn btn-ghost"
            :title="!roleCanScore ? proTooltip : undefined"
            data-testid="btn-open-select-batter"
            @click="openSelectBatter"
          >
            Select next batter
          </button>
          <small v-else class="hint">Waiting for an authorized scorer.</small>
        </div>
        <div v-else-if="needsNewOverLive" data-testid="gate-new-over">
          New over required.
          <button
            v-if="roleCanScore"
            class="btn btn-ghost"
            :title="!roleCanScore ? proTooltip : undefined"
            data-testid="btn-open-start-over"
            @click="openStartOver"
          >
            Choose bowler
          </button>
          <small v-else class="hint">Waiting for an authorized scorer.</small>
        </div>
      </div>
      <small v-if="(!canScore || !canSubmitSimple) && cantScoreReasons.length" class="hint">
        {{ cantScoreReasons[0] }}
      </small>

      <pre v-if="isDev" class="dev-debug">
      canScore: {{ canScore }}
      striker: {{ selectedStriker }} ({{ selectedStrikerName }})
      nonStriker: {{ selectedNonStriker }}
      bowler: {{ selectedBowler }} ({{ selectedBowlerName }})
      battingPlayers: {{ battingPlayers.length }} | bowlingPlayers: {{ bowlingPlayers.length }}
      currentBowlerId: {{ currentBowlerId }} | needsNewOverLive: {{ needsNewOverLive }} (store: {{ needsNewOver }})
      needsNewInningsLive: {{ needsNewInningsLive }}
      allOut: {{ allOut }} | wicketsFromDeliveries: {{ wicketsFromDeliveries }}
      oversExhausted: {{ oversExhausted }} | legalBallsBowled: {{ legalBallsBowled }} / {{ oversLimit*6 || 'âˆž' }} | current_over_balls: {{ stateAny?.current_over_balls }}
      inningsStartIso: {{ inningsStartIso }}
      ballsThisInnings(legal): {{ legalBallsBowled }}
      </pre>

      <!-- Delivery (single panel) -->
      <section class="selectors card" style="border:1px solid rgba(0,0,0,.08); border-radius:12px; padding:12px; margin-bottom:12px;">
        <h3 style="margin:0 0 8px; font-size:14px;">Delivery</h3>

        <div class="row" style="grid-template-columns:1fr;">
          <!-- Extra type -->
          <div class="col" style="display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn" :class="extra==='none' && 'btn-primary'" @click="extra='none'">Legal</button>
            <button class="btn" :class="extra==='nb' && 'btn-primary'" @click="extra='nb'">No-ball</button>
            <button class="btn" :class="extra==='wd' && 'btn-primary'" @click="extra='wd'">Wide</button>
            <button class="btn" :class="extra==='b' && 'btn-primary'" @click="extra='b'">Bye</button>
            <button class="btn" :class="extra==='lb' && 'btn-primary'" @click="extra='lb'">Leg-bye</button>
          </div>

          <!-- Amount selector -->
          <div v-if="extra==='none' || extra==='nb'" class="col">
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <span>Off the bat:</span>
              <button
                v-for="r in [0,1,2,3,4,5,6]"
                :key="r"
                class="btn"
                :class="offBat===r && 'btn-primary'"
                :data-testid="`delivery-run-${r}`"
                @click="offBat=r"
              >
                {{ r }}
              </button>
            </div>
          </div>

          <div v-else class="col">
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <span v-if="extra==='wd'">Total wides:</span>
              <span v-else>Extras:</span>
              <button
                v-for="r in (extra==='wd' ? [1,2,3,4,5] : [0,1,2,3,4])"
                :key="r"
                class="btn"
                :class="extraRuns===r && 'btn-primary'"
                @click="extraRuns=r"
              >{{ r }}</button>
            </div>
            <small v-if="extra==='wd'" class="hint">
              1 = just wide; 2 = wide + 1 run; 5 = wide to boundary.
            </small>
          </div>


          <!-- Optional wicket -->
          <div class="col" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <label><input v-model="isWicket" type="checkbox" data-testid="toggle-wicket" /> Wicket</label>
            <select v-if="isWicket" v-model="dismissal" class="sel" data-testid="select-dismissal">
              <option disabled value="">Select dismissal</option>
              <option value="bowled">Bowled</option>
              <option value="caught">Caught</option>
              <option value="lbw">LBW</option>
              <option value="run_out">Run-out</option>
              <option value="stumped">Stumped</option>
              <option value="hit_wicket">Hit wicket</option>
            </select>
           <!-- NEW: Fielder (XI + subs) when needed -->
          <select
            v-if="isWicket && needsFielder"
            v-model="selectedFielderId"
            class="sel"
            data-testid="select-fielder"
            aria-label="Select fielder"
          >
            <option disabled value="">Select fielderâ€¦</option>
            <option v-for="p in fielderOptions" :key="p.id" :value="p.id">
              {{ p.name }}{{ bowlerRoleBadge(p.id) }}{{ bowlingXIIds.has(p.id) ? '' : ' (sub)' }}
            </option>
          </select>
          <small
            v-if="isWicket && needsFielder && selectedFielderId && !bowlingXIIds.has(selectedFielderId)"
            class="hint"
          >
            Sub fielder will be credited.
          </small>
          <!-- /NEW -->

          <select v-if="isWicket" v-model="dismissedName" class="sel" aria-label="Select dismissed batter" data-testid="select-dismissed-batter">
            <option disabled value="">Select dismissed batter…</option>
            <option v-for="p in dismissedOptions" :key="p.id" :value="p.name">{{ p.name }}</option>
          </select>
        </div>

        <div v-if="extra==='none' || extra==='nb'" class="col shot-map-column">
          <label class="shot-map-label">Shot map</label>
          <ShotMapCanvas v-model="shotMap" :width="240" :height="200" />
          <small class="hint">Optional: sketch the shot path for analytics.</small>
        </div>

          <!-- Submit -->
          <div class="col" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <button
              class="btn btn-primary"
              :disabled="!canSubmitSimple || !canScore"
              @click="submitSimple"
              data-testid="submit-delivery"
            >
              Submit delivery
            </button>

            <button
class="btn btn-ghost"
                    :disabled="!canDeleteLast || deletingLast"
                    @click="deleteLastDelivery">
              {{ deletingLast ? 'Deletingâ€¦' : 'Delete last delivery' }}
            </button>
            <small v-if="pendingCount > 0" class="hint">
              Wait for queued actions to finish before deleting.
            </small>

            <small v-if="!canScore" class="hint">
              Select striker/non-striker/bowler and clear any â€œNew over / New batterâ€ prompts.
            </small>
          </div>
        </div>
      </section>

      <!-- Score pad + deliveries on the left; 3 cards side-by-side on the right -->
      <section class="mt-3 layout-2col">
        <div class="left">
          <DeliveryTable
            :deliveries="deliveriesThisInnings"
            :player-name-by-id="playerNameById"
            class="mt-3"
          />
        </div>

        <div class="right">
          <div class="scorecards-grid">
            <BattingCard :entries="battingEntries" />

            <BowlingCard :entries="bowlingEntries" />

            <!-- AI Commentary Panel -->
            <div class="card ai-commentary-panel">
              <div class="ai-header">
                <h4>AI Commentary</h4>
                <button
                  v-if="!aiLoading && aiCommentary"
                  class="btn btn-ghost ai-regen-btn"
                  title="Regenerate commentary"
                  @click="generateCommentary"
                >
                  ↻
                </button>
              </div>

              <div v-if="aiLoading" class="ai-skeleton">
                <div class="ai-skeleton-line" />
                <div class="ai-skeleton-line short" />
              </div>

              <div v-else-if="aiError" class="ai-error">
                <p class="ai-error-text">{{ aiError }}</p>
                <button class="btn btn-ghost" @click="generateCommentary">
                  Try Again
                </button>
              </div>

              <p v-else-if="aiCommentary" class="ai-output">
                {{ aiCommentary }}
              </p>

              <p v-else class="ai-placeholder">
                Commentary will appear here as the match progresses.
              </p>
            </div>

            <!-- Match AI Commentary Panel (toggle-driven) -->
            <div v-if="matchAiEnabled" class="card match-ai-commentary-panel">
              <div class="ai-header">
                <h4>🤖 Match AI Commentary</h4>
                <button
                  class="btn btn-ghost ai-regen-btn"
                  title="Refresh commentary"
                  :disabled="matchAiLoading"
                  @click="loadMatchAiCommentary"
                >
                  ↻
                </button>
              </div>

              <div v-if="matchAiLoading" class="ai-skeleton">
                <div class="ai-skeleton-line" />
                <div class="ai-skeleton-line short" />
                <div class="ai-skeleton-line" />
              </div>

              <div v-else-if="matchAiError" class="ai-error">
                <p class="ai-error-text">{{ matchAiError }}</p>
                <button class="btn btn-ghost" @click="loadMatchAiCommentary">
                  Try Again
                </button>
              </div>

              <div v-else-if="matchAiCommentary.length" class="match-ai-list">
                <div
                  v-for="(item, idx) in matchAiCommentary"
                  :key="idx"
                  class="match-ai-item"
                  :class="'tone-' + item.tone"
                >
                  <div class="match-ai-item-header">
                    <span v-if="item.over !== null" class="over-badge">
                      Over {{ item.over }}<template v-if="item.ball_index !== null">.{{ item.ball_index }}</template>
                    </span>
                    <span
                      v-for="tag in item.event_tags"
                      :key="tag"
                      class="event-tag"
                    >{{ tag }}</span>
                  </div>
                  <p class="match-ai-item-text">{{ item.text }}</p>
                </div>
              </div>

              <p v-else class="ai-placeholder">
                No commentary available. Score some deliveries!
              </p>
            </div>

            <!-- NEW: compact fielding subs card -->
            <div v-if="showSubsCard" class="card subs-card">
              <div class="subs-hdr">
                <h4>Fielding subs</h4>
                <span v-if="fieldingSubs?.length" class="count">{{ fieldingSubs.length }}</span>
              </div>

              <ul v-if="fieldingSubs && fieldingSubs.length" class="subs-list">
                <li v-for="p in fieldingSubs" :key="p.id" class="subs-row">
                  <span class="name">{{ p.name }}</span>
                  <span class="chip">SUB</span>
                </li>
              </ul>
              <div v-else class="empty">
                <small class="hint">No subs on the bench.</small>
              </div>
            </div>

            <!-- Extras / DLS / Reduce Overs -->
            <div class="card extras-card">
              <h4>Extras</h4>
              <div class="extras-grid">
                <span>Wides</span><strong>{{ extrasBreakdown.wides }}</strong>
                <span>No-balls</span><strong>{{ extrasBreakdown.no_balls }}</strong>
                <span>Byes</span><strong>{{ extrasBreakdown.byes }}</strong>
                <span>Leg-byes</span><strong>{{ extrasBreakdown.leg_byes }}</strong>
                <span>Penalty</span><strong>{{ extrasBreakdown.penalty }}</strong>

                <span class="sep">Total</span>
                <strong class="sep">{{ extrasBreakdown.total }}</strong>
              </div>

              <!-- DLS panel -->
              <div v-if="canShowDls" class="card dls-card">
                <h4>DLS</h4>
                <div class="dls-grid">
                  <div class="row-inline">
                    <label class="lbl">G50</label>
                    <input
                      v-model.number="G50"
                      class="inp"
                      type="number"
                      min="150"
                      max="300"
                      step="1"
                      style="width:90px;"
                    />
                    <button class="btn" :disabled="loadingDls" @click="refreshDls">
                      {{ loadingDls ? 'Loadingâ€¦' : 'Preview' }}
                    </button>
                  </div>

                  <template v-if="dls">
                    <div class="dls-stats">
                      <span>Team 1</span>
                      <strong>{{ dls.team1_score }} ({{ dls.team1_resources.toFixed(1) }}%)</strong>

                      <span>Team 2 resources</span>
                      <strong>{{ dls.team2_resources.toFixed(1) }}%</strong>

                      <span>Revised target</span>
                      <strong>{{ dls.target }}</strong>
                    </div>

                    <button class="btn btn-primary" :disabled="applyingDls" @click="applyDls">
                      {{ applyingDls ? 'Applyingâ€¦' : 'Apply DLS Target' }}
                    </button>

                    <small v-if="gameStore.dlsApplied" class="hint">DLS target applied.</small>
                  </template>
                  <small v-else class="hint">Preview to compute a DLS target based on current resources.</small>
                </div>
              </div>

              <!-- Reduce Overs -->
              <div ref="reduceOversCardRef" class="card dls-card" style="margin-top:12px;">
                <h4>Reduce Overs</h4>
                <div class="dls-grid">
                  <div class="row-inline" style="flex-wrap:wrap;">
                    <label class="lbl">Scope</label>
                    <label><input v-model="reduceScope" type="radio" value="match"> Match</label>
                    <label><input v-model="reduceScope" type="radio" value="innings"> Specific innings</label>

                    <select v-if="reduceScope==='innings'" v-model.number="reduceInnings" class="sel">
                      <option :value="1">Innings 1</option>
                      <option :value="2">Innings 2</option>
                    </select>
                  </div>

                  <div class="row-inline" style="flex-wrap:wrap;">
                    <label class="lbl">New limit</label>
                    <input v-model.number="oversNew" class="inp" type="number" min="1" step="1" style="width:90px;">
                    <small class="hint">Current limit: {{ oversLimit || 'â€”' }} overs</small>
                  </div>

                  <button class="btn btn-primary" :disabled="!canReduce || reducingOvers" @click="doReduceOvers">
                    {{ reducingOvers ? 'Updatingâ€¦' : 'Apply Overs Limit' }}
                  </button>
                </div>
              </div>

              <!-- Live Par helper -->
              <div class="card dls-card" style="margin-top:12px;">
                <h4>DLS â€” Par Now</h4>
                <div class="dls-grid">
                  <button class="btn" :disabled="computingPar" @click="updateParNow">
                    {{ computingPar ? 'Computingâ€¦' : 'Update Live Par' }}
                  </button>
                  <small v-if="(gameStore.dlsPanel as any)?.par != null" class="hint">
                    Par: {{ (gameStore.dlsPanel as any).par }}
                  </small>
                  <small v-else class="hint">Par will appear here once computed.</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Share & Monetize Modal -->
    <div v-if="shareOpen" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="share-title" @click.self="closeShare">
      <BaseCard padding="lg" class="modal-card modal-card--wide">
        <header class="modal-header">
          <h3 id="share-title" class="modal-title">Share & Monetize</h3>
          <BaseButton variant="ghost" size="sm" aria-label="Close modal" @click="closeShare">âœ•</BaseButton>
        </header>

        <div class="modal-content">
          <div class="form-group">
            <label class="lbl">Embed code (read-only)</label>
            <div class="code-wrap">
              <textarea ref="codeRef" class="code" readonly :value="iframeCode" aria-label="Embed iframe HTML"></textarea>
              <BaseButton variant="secondary" size="sm" class="copy" @click="copyEmbed">{{ copied ? 'Copied!' : 'Copy' }}</BaseButton>
            </div>
          </div>

          <div class="form-row">
            <div>
              <BaseInput :model-value="embedUrl" label="Preview URL" readonly @focus="(e: FocusEvent) => (e.target as HTMLInputElement | null)?.select()" />
            </div>
            <div class="align-end">
              <BaseButton variant="ghost" as="a" :href="embedUrl" target="_blank" rel="noopener">Open preview</BaseButton>
            </div>
          </div>

          <div class="note">
            <strong>Tip (TV/OBS):</strong> Add a <em>Browser Source</em> with the iframeâ€™s
            <code>src</code> URL (or paste this embed into a simple HTML file). Set width to your canvas,
            height â‰ˆ <b>{{ height }}</b> px, and enable transparency if you want rounded corners to blend.
          </div>
        </div>

        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeShare">Close</BaseButton>
          <BaseButton variant="primary" @click="copyEmbed">{{ copied ? 'Copied!' : 'Copy embed' }}</BaseButton>
        </div>
      </BaseCard>
    </div>

    <!-- Start Over Modal -->
    <div v-if="roleCanScore && startOverDlgOpen" class="modal-backdrop" role="dialog" aria-modal="true" data-testid="modal-start-over">
      <BaseCard padding="lg" class="modal-card">
        <h3 class="modal-title">Start next over</h3>
        <p class="modal-body-text">Select a bowler (cannot be the bowler who delivered the last ball of previous over).</p>
        <select v-model="selectedNextOverBowlerId" class="sel" data-testid="select-next-over-bowler">
          <option disabled value="">Choose bowlerâ€¦</option>
          <option v-for="p in eligibleNextOverBowlers" :key="p.id" :value="p.id">{{ p.name }}{{ bowlerRoleBadge(p.id) }}</option>
        </select>
        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeStartOver">Cancel</BaseButton>
          <BaseButton variant="primary" :disabled="!selectedNextOverBowlerId" data-testid="confirm-start-over" @click="confirmStartOver">Start</BaseButton>
        </div>
      </BaseCard>
    </div>

    <!-- Start Next Innings Modal -->
    <div v-if="roleCanScore && startInningsDlgOpen" class="modal-backdrop" role="dialog" aria-modal="true" data-testid="modal-start-innings">
      <BaseCard padding="lg" class="modal-card">
        <h3 class="modal-title">Start next innings</h3>
        <p class="modal-body-text">Select openers and (optional) opening bowler.</p>

        <div class="form-group">
          <label class="lbl">Striker</label>
          <select v-model="nextStrikerId" class="sel" data-testid="select-next-striker">
            <option disabled value="">Choose strikerâ€¦</option>
            <option v-for="p in nextBattingXI" :key="p.id" :value="p.id">{{ p.name }}{{ roleBadge(p.id) }}</option>
          </select>
        </div>

        <div class="form-group">
          <label class="lbl">Non-striker</label>
          <select v-model="nextNonStrikerId" class="sel" data-testid="select-next-nonstriker">
            <option disabled value="">Choose non-strikerâ€¦</option>
            <option v-for="p in nextBattingXI" :key="p.id" :value="p.id" :disabled="p.id === nextStrikerId">{{ p.name }}{{ roleBadge(p.id) }}</option>
          </select>
        </div>

        <div class="form-group">
          <label class="lbl">Opening bowler (optional)</label>
          <select v-model="openingBowlerId" class="sel" data-testid="select-opening-bowler">
            <option value="">— None (choose later) —</option>
            <option v-for="p in nextBowlingXI" :key="p.id" :value="p.id">{{ p.name }}{{ bowlerRoleBadge(p.id) }}</option>
          </select>
        </div>

        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeStartInnings">Cancel</BaseButton>
          <BaseButton
            variant="primary"
            :disabled="!nextStrikerId || !nextNonStrikerId || nextStrikerId===nextNonStrikerId"
            data-testid="confirm-start-innings"
            @click="confirmStartInnings"
          >
            Start innings
          </BaseButton>
        </div>
      </BaseCard>
    </div>

    <!-- Select Next Batter Modal (Gate) -->
    <div v-if="roleCanScore && selectBatterDlgOpen" class="modal-backdrop" role="dialog" aria-modal="true" data-testid="modal-select-batter">
      <BaseCard padding="lg" class="modal-card">
        <h3 class="modal-title">Select next batter</h3>
        <p class="modal-body-text">Pick a batter who is not out.</p>
        <select v-model="selectedNextBatterId" class="sel" data-testid="select-next-batter">
          <option disabled value="">Choose batter…</option>
          <option v-for="p in candidateBatters" :key="p.id" :value="p.id">{{ p.name }}{{ roleBadge(p.id) }}</option>
        </select>
        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeSelectBatter">Cancel</BaseButton>
          <BaseButton variant="primary" :disabled="!selectedNextBatterId" data-testid="confirm-select-batter" @click="confirmSelectBatter">Confirm</BaseButton>
        </div>
      </BaseCard>
    </div>

    <!-- Weather Interruption Modal -->
    <div v-if="weatherDlgOpen" class="modal-backdrop" role="dialog" aria-modal="true">
      <BaseCard padding="lg" class="modal-card">
        <h3 class="modal-title">Weather interruption</h3>
        <p class="modal-body-text">Add an optional note (e.g., "Rain, covers on").</p>
        <div class="form-group">
          <BaseInput v-model="weatherNote" label="Note" placeholder="Note (optional)" data-testid="input-weather-note" />
        </div>
        <div class="modal-actions modal-actions--wrap">
          <BaseButton variant="ghost" data-testid="btn-weather-close" @click="closeWeather">Close</BaseButton>
          <BaseButton variant="secondary" data-testid="btn-weather-resume" @click="resumeAfterWeather">Resume play</BaseButton>
          <BaseButton variant="primary" data-testid="btn-weather-start" @click="startWeatherDelay">Start delay</BaseButton>
          <BaseButton
            v-if="roleCanScore"
            variant="secondary"
            :disabled="needsNewInningsLive || !canStartOverNow"
            :title="!roleCanScore ? proTooltip : undefined"
            data-testid="btn-weather-start-over"
            @click="openStartOver"
          >Start Next Over</BaseButton>
        </div>
      </BaseCard>
    </div>

    <!-- Mid-over Change Modal -->
    <div v-if="changeBowlerDlgOpen" class="modal-backdrop" role="dialog" aria-modal="true">
      <BaseCard padding="lg" class="modal-card">
        <h3 class="modal-title">Mid-over change (injury)</h3>
        <p class="modal-body-text">Pick a replacement to finish this over. You can do this only once per over.</p>
        <select v-model="selectedReplacementBowlerId" class="sel">
          <option disabled value="">Choose replacement…</option>
          <option v-for="p in replacementOptions" :key="p.id" :value="p.id">{{ p.name }}{{ bowlerRoleBadge(p.id) }}</option>
        </select>
        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeChangeBowler">Cancel</BaseButton>
          <BaseButton variant="primary" :disabled="!selectedReplacementBowlerId" @click="confirmChangeBowler">Change</BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<style scoped>
/* =====================================================
   GAME SCORING VIEW - Using Design System Tokens
   ===================================================== */

.shot-map-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 260px;
}

.shot-map-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

/* Layout */
.game-scoring {
  padding: var(--space-3);
  display: grid;
  gap: var(--space-3);
}

.toolbar {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
}

.left {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--font-extrabold);
  letter-spacing: 0.01em;
}

.meta {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.right {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.content {
  padding: var(--space-2) 0;
}

.mb-3 {
  margin-bottom: var(--space-3);
}

.mt-3 {
  margin-top: var(--space-3);
}

.placeholder {
  padding: var(--space-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  background: var(--color-surface-hover);
}

.dev-debug {
  background: var(--color-bg);
  color: var(--color-text);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  white-space: pre-wrap;
  margin: var(--space-2) 0;
}

/* Controls */
.inp, .sel {
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: 0 var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-surface);
  color: var(--color-text);
}

.inp.wide {
  width: 100%;
}

.btn {
  appearance: none;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

.btn:hover:not(:disabled) {
  background: var(--color-surface-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  border: 0;
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-ghost {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  text-decoration: none;
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-surface-hover);
}

/* Bowling controls block */
.card.alt {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
}

.row.tight {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-2);
  align-items: center;
}

.bowler-now {
  font-size: var(--text-sm);
  color: var(--color-text);
}

/* Selectors */
.selectors.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  background: var(--color-surface);
}

.row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
}

.col {
  display: grid;
  gap: var(--space-2);
}

.align-end {
  display: grid;
  align-items: end;
}

.lbl {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-medium);
}

.hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.debug {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Two-column shell with a wider right column */
.layout-2col {
  display: grid;
  grid-template-columns: minmax(620px, 1.65fr) minmax(440px, 1fr);
  gap: var(--space-3);
}

.layout-2col .left,
.layout-2col .right {
  display: block;
}

.layout-2col .right {
  position: sticky;
  top: var(--space-3);
  align-self: start;
}

/* Scorecards grid */
.scorecards-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  align-items: start;
}

.scorecards-grid .extras-card {
  grid-column: 1 / -1;
}

.scorecards-grid :deep(table) {
  font-size: var(--text-sm);
}

.scorecards-grid :deep(th),
.scorecards-grid :deep(td) {
  padding: var(--space-2) var(--space-2);
}

.scorecards-grid :deep(.card),
.scorecards-grid :deep(.pane) {
  padding: var(--space-4);
}

/* Extras & DLS polish */
.extras-card {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.extras-card h4 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.extras-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.extras-grid .sep {
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-1);
  padding-top: var(--space-1);
}

.scorecards-grid > * {
  align-self: start;
}

.scorecards-grid .card,
.scorecards-grid .extras-card {
  height: 100%;
}

/* AI Commentary Panel */
.ai-commentary-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-header h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.ai-regen-btn {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  min-width: auto;
}

.ai-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ai-skeleton-line {
  background: var(--color-border-subtle);
  height: 0.9rem;
  border-radius: var(--radius-sm);
  animation: ai-pulse 1.3s ease-in-out infinite;
}

.ai-skeleton-line.short {
  width: 60%;
}

@keyframes ai-pulse {
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.8;
  }
}

.ai-error {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  background: var(--color-error-soft);
}

.ai-error-text {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-error);
}

.ai-output {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text);
}

.ai-placeholder {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

/* Match AI Commentary Panel */
.match-ai-commentary-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  max-height: 320px;
  overflow-y: auto;
}

.match-ai-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.match-ai-item {
  padding: var(--space-2);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.match-ai-item.tone-hype {
  border-left-color: var(--color-success);
  background: var(--color-success-soft, rgba(34, 197, 94, 0.1));
}

.match-ai-item.tone-critical {
  border-left-color: var(--color-warning);
  background: var(--color-warning-soft, rgba(245, 158, 11, 0.1));
}

.match-ai-item.tone-neutral {
  border-left-color: var(--color-primary);
}

.match-ai-item-header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}

.over-badge {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  background: var(--color-primary);
  color: var(--color-on-primary, #fff);
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
}

.event-tag {
  font-size: var(--text-xs);
  background: var(--color-border-subtle);
  color: var(--color-text-muted);
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
}

.match-ai-item-text {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text);
}

/* Subs card */
.subs-card {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.subs-card h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.subs-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.subs-hdr .count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.subs-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: var(--space-2);
}

.subs-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-sm);
  padding: var(--space-1) 0;
  border-bottom: 1px dashed var(--color-border-subtle);
}

.subs-row:last-child {
  border-bottom: 0;
}

.subs-row .name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  letter-spacing: 0.02em;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}

.subs-card .empty {
  padding: var(--space-2) 0;
}

/* DLS card */
.dls-card {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.dls-card h4 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.dls-grid {
  display: grid;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.row-inline {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.dls-stats {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2);
}

/* Compact metrics row */
.small-metrics .row.compact {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.small-metrics .col {
  align-items: center;
  grid-auto-flow: column;
  grid-auto-columns: max-content;
  gap: var(--space-2);
}

/* Responsive */
@media (max-width: 1200px) {
  .layout-2col {
    grid-template-columns: 1.4fr 1fr;
  }
}

@media (max-width: 1100px) {
  .scorecards-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .layout-2col {
    grid-template-columns: 1fr;
  }
  .layout-2col .right {
    position: static;
  }
}

/* Modal overlay (Share) */
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  place-items: center;
  padding: var(--space-4);
  z-index: var(--z-modal-backdrop);
}

.modal {
  width: min(760px, 96vw);
  background: var(--color-surface);
  color: var(--color-text);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-modal);
  overflow: hidden;
}

.modal-hdr, .modal-ftr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.modal-hdr {
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.modal-ftr {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
}

.modal-hdr h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  letter-spacing: 0.01em;
}

.x {
  background: transparent;
  border: 0;
  color: var(--color-text-muted);
  font-size: var(--h3-size);
  cursor: pointer;
}

.modal-body {
  padding: var(--space-4);
  display: grid;
  gap: var(--space-3);
}

.code-wrap {
  position: relative;
}

.code {
  width: 100%;
  min-height: 120px;
  resize: vertical;
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
}

.copy {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  cursor: pointer;
}

/* Standard Modal Pattern */
.modal-backdrop {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, #000 65%, transparent);
  z-index: var(--z-modal-backdrop);
  padding: var(--space-4);
}

.modal-card {
  width: 100%;
  max-width: 420px;
}

.modal-card--wide {
  max-width: 760px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-2);
}

.modal-content {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.modal-body-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-4);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.modal-actions--wrap {
  flex-wrap: wrap;
}

.form-group {
  margin-bottom: var(--space-3);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-3);
  align-items: end;
}

.note {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  background: var(--color-surface-hover);
  padding: var(--space-3);
  border-radius: var(--radius-md);
}

/* Dialog (native) - can be removed once all modals converted */
dialog::backdrop {
  background: rgba(0, 0, 0, 0.2);
}

dialog .dlg {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 320px;
}

dialog footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

/* RBAC banners */
.rbac-banner {
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
  border: 1px solid var(--color-error);
  background: var(--color-error-soft);
  color: var(--color-error);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.rbac-banner.warn {
  border-color: var(--color-error);
  background: var(--color-error-soft);
  color: var(--color-error);
}

.rbac-banner.info {
  border-color: var(--color-info);
  background: var(--color-info-soft);
  color: var(--color-info);
}

/* Player profile link */
.player-link {
  color: inherit;
  text-decoration: none;
}

.player-link:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
}

/* Dark mode polish */
@media (prefers-color-scheme: dark) {
  .chip {
    border-color: var(--color-border);
    background: var(--color-surface-hover);
    color: var(--color-text-secondary);
  }

  .toolbar {
    border-bottom-color: var(--color-border);
  }

  .placeholder {
    border-color: var(--color-border);
    background: var(--color-surface);
  }

  .inp, .sel {
    background: var(--color-surface);
    color: var(--color-text);
    border-color: var(--color-border);
  }

  .btn-ghost {
    background: var(--color-surface);
    color: var(--color-text);
    border-color: var(--color-border);
  }

  .modal {
    background: var(--color-surface);
    color: var(--color-text);
  }

  .modal-hdr {
    border-bottom-color: var(--color-border);
  }

  .modal-ftr {
    border-top-color: var(--color-border);
  }

  .x {
    color: var(--color-text-muted);
  }

  .code {
    background: var(--color-bg);
    color: var(--color-text);
    border-color: var(--color-border);
  }
}
</style>
