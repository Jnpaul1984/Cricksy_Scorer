<script setup lang="ts">
/* eslint-disable */
/*
 * QA CHECKLIST (beta/fix-extras-recentballs-correction-theme):
 * ✅ Recent Balls: Extras (WD/NB) should persist in last 6 even after next legal ball
 * ✅ Extras Tab: Totals should match backend snapshot (prefer liveSnapshot.extras_totals)
 * ✅ Field Map: Tap marker dot should NOT appear on zone clicks
 * ✅ Dark Theme: Scoring UI should use CSS variables, no hardcoded white/light colors
 * ✅ Zone Selection: recordZone() should still work for shot tracking
 * ✅ Ball Number: Clamped to 0-5 range to prevent invalid over states
 * ✅ Sorting: Timestamp comparison uses Date.parse() for ISO date strings
 */
/* --- Vue & Router --- */

/* --- Stores --- */
import { storeToRefs } from 'pinia'
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'

/* --- UI Components --- */
import { BaseButton, BaseCard, BaseInput } from '@/components'
import BattingCard from '@/components/BattingCard.vue'
import BowlingCard from '@/components/BowlingCard.vue'
import DeliveryTable from '@/components/DeliveryTable.vue'
import DeliveryCorrectionModal from '@/components/DeliveryCorrectionModal.vue'
import PresenceBar from '@/components/PresenceBar.vue'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import ShotMapCanvas from '@/components/scoring/ShotMapCanvas.vue'
import WinProbabilityWidget from '@/components/WinProbabilityWidget.vue'
import WinProbabilityChart from '@/components/WinProbabilityChart.vue'
import InningsGradeWidget from '@/components/InningsGradeWidget.vue'
import PressureMapWidget from '@/components/PressureMapWidget.vue'
import PhaseTimelineWidget from '@/components/PhaseTimelineWidget.vue'
import { useRoleBadge } from '@/composables/useRoleBadge'
import { useInningsGrade } from '@/composables/useInningsGrade'
import { usePressureAnalytics } from '@/composables/usePressureAnalytics'
import { usePhaseAnalytics } from '@/composables/usePhaseAnalytics'
import { apiService, type DeliveryCorrectionRequest } from '@/services/api'
import { generateAICommentary, type AICommentaryRequest, fetchMatchAiCommentary, type MatchCommentaryItem } from '@/services/api'
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
const recordedZone = ref<number | null>(null)

const recordZone = (zone: number) => {
  recordedZone.value = zone
}

if (import.meta.env?.DEV) {
  console.info('GameScoringView setup refs', { isWicket, extra })
}

// ================== AI Commentary state ==================
const aiCommentary = ref<string | null>(null)
const aiLoading = ref(false)
const aiError = ref<string | null>(null)

// ================== Match AI Commentary state (toggle & panel) ==================
const matchAiEnabled = ref(false)
const matchAiCommentary = ref<MatchCommentaryItem[]>([])
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

// [REMOVED tapMarker and handleMapClick - field tap feedback not needed]


const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const authStore = useAuthStore()
const { grade: currentInningsGrade, fetchCurrentGrade: fetchCurrentInningsGrade } = useInningsGrade()
const { pressureData, fetchPressureMap, loading: pressureLoading } = usePressureAnalytics()
const { phaseData, predictions, fetchPhaseMap, fetchPredictions, loading: phaseLoading } = usePhaseAnalytics()

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

// Header score display: prefer liveSnapshot, fall back to store score (helps tests and early UI)
const headerRuns = computed(() => {
  const snap: any = liveSnapshot.value as any
  const storeScore: any = (gameStore as any)?.score
  return snap?.total_runs ?? snap?.batting_team_score ?? storeScore?.runs ?? 0
})
const headerWickets = computed(() => {
  const snap: any = liveSnapshot.value as any
  const storeScore: any = (gameStore as any)?.score
  return snap?.total_wickets ?? snap?.batting_team_wickets ?? storeScore?.wickets ?? 0
})
const headerOvers = computed(() => {
  const snap: any = liveSnapshot.value as any
  const storeScore: any = (gameStore as any)?.score
  // Format overs as "X.Y" from overs_completed and balls_this_over
  const overs = snap?.overs_completed ?? 0
  const balls = snap?.balls_this_over ?? 0
  const oversDisplay = `${overs}.${balls}`
  return snap?.batting_team_overs ?? oversDisplay ?? storeScore?.overs ?? '0.0'
})
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

// Watch for gameId changes and fetch innings grade, pressure map, & phase data
watch(gameId, async (id) => {
  if (id) {
    try {
      // Get current inning number from game state (default to 1)
      const currentInning = currentGame.value?.current_inning || 1
      await fetchCurrentInningsGrade(id)  // Function only accepts gameId
      await fetchPressureMap(id, currentInning)
      await fetchPhaseMap(id, currentInning)
      await fetchPredictions(id)

      // Manually fetch win probability prediction to populate initial state
      // (predictions are normally only emitted via Socket.IO after deliveries)
      try {
        const predictionResponse = await fetch(`http://localhost:8000/games/${id}/snapshot`)
        const snapshotData = await predictionResponse.json()

        // Update liveSnapshot so CRR and other stats display correctly
        gameStore.liveSnapshot = snapshotData

        if (snapshotData.prediction) {
          gameStore.currentPrediction = snapshotData.prediction
        }
      } catch {
        // Silently ignore - predictions will come via Socket.IO after next delivery
      }
    } catch (err) {
      // Silently handle - analytics features may not be fully implemented yet
    }
  }
}, { immediate: true })

// --- UI State for UX Improvements ---
const isSubmitting = ref(false)
// [REMOVED tapMarker] Field tap feedback not needed - zone selection still works via recordZone()

// --- Delivery Correction State ---
const showCorrectionModal = ref(false)
const correctionDelivery = ref<any>(null)

function openCorrectionModal(delivery: any) {
  correctionDelivery.value = delivery
  showCorrectionModal.value = true
}

function closeCorrectionModal() {
  showCorrectionModal.value = false
  correctionDelivery.value = null
}

async function submitCorrection({ deliveryId, correction }: { deliveryId: number; correction: DeliveryCorrectionRequest }) {
  if (!gameId.value) return

  try {
    const snapshot = await apiService.correctDelivery(gameId.value, deliveryId, correction)
    // Update store with corrected snapshot
    if (snapshot) {
      gameStore.liveSnapshot = snapshot as any
    }
    closeCorrectionModal()
  } catch (err: any) {
    console.error('Failed to correct delivery:', err)
    alert(err?.message || 'Failed to correct delivery')
  }
}

function getBallClass(b: DeliveryRowForTable) {
  if (b.is_wicket) return 'is-wicket'
  if (b.runs_scored === 6) return 'is-6'
  if (b.runs_scored === 4) return 'is-4'
  if (b.extra) return 'is-extra'
  if (b.runs_scored === 0) return 'is-dot'
  return 'is-run'
}

function getBallLabel(b: DeliveryRowForTable) {
  if (b.is_wicket) return 'W'
  if (b.extra === 'wd') return 'WD'
  if (b.extra === 'nb') return 'NB'
  if (b.extra === 'b') return 'B'
  if (b.extra === 'lb') return 'LB'
  return b.runs_scored
}

const canSubmitSimple = computed(() => {
  if (!canScore.value) return false
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
  if (isSubmitting.value) return
  if (!canScore.value) return
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) {
    openStartOver(); onError('Start the next over first'); return
  }
  if (needsNewBatterLive.value) { openSelectBatter(); onError('Select the next batter first'); return }

  isSubmitting.value = true
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
  } finally {
    setTimeout(() => { isSubmitting.value = false }, 400)
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

const lastDelivery = computed<any | null>(() => {
  // FIX B7: Use backend last_delivery from liveSnapshot (primary source)
  // Backend provides correct over/ball numbers, no local calculation needed
  return gameStore.liveSnapshot?.last_delivery ?? null
})

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
  // FIX B4: Use backend-calculated balls_remaining from snapshot
  // NO local calculation - backend handles extras/illegal balls correctly
  return gameStore.liveSnapshot?.balls_remaining ?? 0
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

// Last 6 balls for the center strip
const last6Balls = computed(() => {
  // deliveriesThisInnings is sorted by over/ball ascending (oldest -> newest)
  // We want the last 6, but displayed left-to-right as oldest-of-the-6 -> newest
  const all = deliveriesThisInnings.value || []
  return all.slice(-6)
})

const recentBallSlots = computed(() => {
  const filled = last6Balls.value
  const emptyCount = 6 - filled.length
  const empty = new Array(Math.max(0, emptyCount)).fill(null)
  return [...filled, ...empty]
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



// ================== Deliveries (CHRONOLOGICAL - NO DEDUP) ==================
// ✅ FIX: Treat deliveries as event stream - extras are separate events
// ✅ Order by backend delivery ID (if present), else timestamp, else array order
// ✅ Do NOT deduplicate by over:ball - wide at 3.0 and legal at 3.1 are DIFFERENT

function parseOverBall(overLike: unknown, ballLike: unknown) {
  // ✅ HARDENED: Clamp ball to 0-5 for all formats to prevent invalid ball numbers
  if (typeof ballLike === 'number') {
    return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: Math.max(0, Math.min(5, ballLike)) }
  }
  if (typeof overLike === 'string') {
    const [o, b] = overLike.split('.')
    return { over: Number(o) || 0, ball: Math.max(0, Math.min(5, Number(b) || 0)) }
  }
  if (typeof overLike === 'number') {
    const over = Math.floor(overLike)
    const ball = Math.max(0, Math.min(5, Math.round((overLike - over) * 10)))
    return { over, ball }
  }
  return { over: 0, ball: 0 }
}


const rawDeliveries = computed<any[]>(() => {
  const g = gameStore.currentGame as any
  return Array.isArray(g?.deliveries) ? g.deliveries : []
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



const deliveriesThisInnings = computed<DeliveryRowForTable[]>(() => {
  // ✅ NO deduplication - keep ALL delivery events in chronological order
  // Sort by: 1) delivery.id (backend PK), 2) at_utc timestamp, 3) over/ball
  const raw = deliveriesThisInningsRaw.value
  const mapped = raw.map((d: any, index: number) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      _delivery_id: d.id ?? d.delivery_id ?? null,
      _timestamp: d.at_utc ?? d.created_at ?? null,
      _index: index,
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
  })

  // Sort by delivery ID > timestamp > over/ball > insertion order
  mapped.sort((a: any, b: any) => {
    if (a._delivery_id != null && b._delivery_id != null) {
      return a._delivery_id - b._delivery_id
    }
    if (a._timestamp && b._timestamp) {
      // ✅ HARDENED: Use Date.parse for valid ISO timestamps, fallback to string compare
      const aTime = Date.parse(a._timestamp)
      const bTime = Date.parse(b._timestamp)
      if (!isNaN(aTime) && !isNaN(bTime)) {
        return aTime - bTime
      }
      return a._timestamp < b._timestamp ? -1 : a._timestamp > b._timestamp ? 1 : 0
    }
    const overDiff = a.over_number - b.over_number
    if (overDiff !== 0) return overDiff
    const ballDiff = a.ball_number - b.ball_number
    if (ballDiff !== 0) return ballDiff
    return a._index - b._index
  })

  return mapped as DeliveryRowForTable[]
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


// For next over: exclude the bowler from the last delivery (cannot bowl consecutive overs)
const eligibleNextOverBowlers = computed<Player[]>(() => {
  const lastBowler = lastBallBowlerId.value
  // Only filter if we have a valid lastBallBowlerId
  return lastBowler
    ? bowlingPlayers.value.filter(p => p.id !== lastBowler)
    : bowlingPlayers.value
})

// For correction at START of over: allow ALL available bowlers (no restrictions at over start)
const eligibleCorrectionBowlers = computed<Player[]>(() => bowlingPlayers.value)

const replacementOptions = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== currentBowlerId.value))
const canUseMidOverChange = computed(() => currentOverBalls.value < 6 && !midOverChangeUsed.value)
const overInProgress = computed<boolean>(() => Number((stateAny.value?.balls_this_over ?? 0)) > 0)

// NEW: Derive legal balls in current over to allow correction even if wides were bowled
const legalBallsInCurrentOver = computed(() => {
  // Use deliveries as the source of truth to avoid store sync delays
  const currentOverIndex = Math.floor(Number(stateAny.value?.overs_completed ?? 0))
  const arr = deliveriesThisInnings.value
  const ballsInThisOver = arr.filter(d =>
    d.over_number === currentOverIndex &&
    (d.extra !== 'wd' && d.extra !== 'nb')
  )
  return ballsInThisOver.length
})

const canCorrectBowler = computed(() => {
  // Allow correction at ANY point during the over (not just at start)
  // As long as there's a bowler selected and the over isn't finished (< 6 legal balls)
  const balls = legalBallsInCurrentOver.value
  const overNotFinished = balls < 6

  if (import.meta.env.DEV) {
    console.log('[canCorrectBowler] balls:', balls, 'overNotFinished:', overNotFinished, 'currentBowlerId:', currentBowlerId.value)
  }

  // Available during the over when a bowler has been selected
  return overNotFinished && !!currentBowlerId.value
})

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
const isBowlerCorrection = ref(false)
const selectedNextOverBowlerId = ref<UUID>('' as UUID)
const selectedReplacementBowlerId = ref<UUID>('' as UUID)
const selectBatterDlgOpen = ref(false)
const selectedNextBatterId = ref<UUID>('' as UUID)
const activeTab = ref<'recent' | 'batting' | 'bowling' | 'ai' | 'analytics' | 'extras'>('recent')
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

function openCorrectionBowler(): void {
  if (!roleCanScore.value) return
  if (!canCorrectBowler.value) {
    showToast('Cannot correct bowler after legal balls bowled', 'error')
    return
  }
  isBowlerCorrection.value = true
  // Auto-select first available bowler for correction
  const firstBowler = eligibleCorrectionBowlers.value[0]?.id ?? ('' as UUID)
  selectedReplacementBowlerId.value = firstBowler
  changeBowlerDlgOpen.value = true
  if (import.meta.env.DEV) {
    console.log('[openCorrectionBowler] Eligible bowlers:', eligibleCorrectionBowlers.value.length, 'Selected:', firstBowler)
  }
}

function openChangeBowler(): void {
  if (!roleCanScore.value) return
  isBowlerCorrection.value = false
  selectedReplacementBowlerId.value = '' as UUID
  changeBowlerDlgOpen.value = true
}
function closeChangeBowler(): void { changeBowlerDlgOpen.value = false }

async function confirmChangeBowler(): Promise<void> {
  const id = gameId.value
  const repl = selectedReplacementBowlerId.value
  if (!id || !repl) return

  if (isBowlerCorrection.value) {
    try {
      await gameStore.startNewOver(repl)
      selectedBowler.value = repl
      showToast('Bowler corrected', 'success')
    } catch (e: any) {
      onError(e?.message || 'Failed to correct bowler')
    } finally {
      selectedReplacementBowlerId.value = '' as UUID
      closeChangeBowler()
    }
    return
  }

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
  <div class="broadcast-layout">
    <!-- Top toolbar -->
    <header class="broadcast-header">
      <div class="header-left">
        <div class="brand">CRICKSY</div>
        <div v-if="gameId" class="game-meta">#{{ gameId.slice(0,6) }}</div>
      </div>

      <!-- Dense Match State -->
      <div class="header-center dense-stats">
        <div class="stat-group main-score">
          <span class="team-name">{{ battingTeamName || 'Team' }}</span>
          <span class="score-display">
            <span data-testid="scoreboard-runs">{{ headerRuns }}</span>/{{ headerWickets }}
          </span>
          <span class="overs-display">
            (<span data-testid="scoreboard-overs">{{ headerOvers }}</span>)
          </span>
        </div>

        <div class="stat-divider"></div>

        <div class="stat-group rates">
          <span class="rate-item">CRR: <strong>{{ ((liveSnapshot as any)?.current_run_rate ?? (liveSnapshot as any)?.crr ?? 0).toFixed(2) }}</strong></span>
          <span v-if="targetSafe" class="rate-item">Target: <strong>{{ targetSafe }}</strong></span>
          <span v-if="targetSafe" class="rate-item">RRR: <strong>{{ (requiredRunRate ?? 0).toFixed(2) }}</strong></span>
          <span v-if="targetSafe" class="rate-item need-txt">Need <strong>{{ runsRequired }}</strong></span>
        </div>
      </div>

      <div class="header-right">
        <button class="btn-icon" @click="matchAiEnabled = !matchAiEnabled" :class="{active: matchAiEnabled}" title="AI Commentary">
          🤖
        </button>
        <button class="btn-ghost-sm" @click="shareOpen = true">
          Share
        </button>
      </div>
    </header>

    <!-- PLAYER BAR (Split Panels) -->
    <section class="player-bar">
      <!-- Striker Panel -->
      <div class="player-box striker-box">
        <div class="pb-label">STRIKER</div>
        <select v-model="selectedStriker" class="pb-select-full">
          <option disabled value="">Select...</option>
          <option v-for="p in battingPlayers" :key="p.id" :value="p.id" :disabled="p.id === selectedNonStriker">
            {{ p.name }} {{ roleBadge(p.id) }}
          </option>
        </select>
      </div>

      <!-- Non-Striker Panel -->
      <div class="player-box non-striker-box">
        <div class="pb-label">NON-STRIKER</div>
        <select v-model="selectedNonStriker" class="pb-select-full">
          <option disabled value="">Select...</option>
          <option v-for="p in battingPlayers" :key="p.id" :value="p.id" :disabled="p.id === selectedStriker">
            {{ p.name }} {{ roleBadge(p.id) }}
          </option>
        </select>
      </div>

      <!-- Bowler Panel -->
      <div class="player-box bowler-box">
        <div class="pb-label">
          <span>BOWLER</span>
          <div class="bowler-actions" v-if="roleCanScore">
            <button class="btn-action-xs" @click="openStartOver" :disabled="!canStartOverNow" title="Start new over / Change bowler">
              New Over
            </button>
            <button class="btn-action-xs" @click="openChangeBowler" :disabled="!canUseMidOverChange" title="Mid-over replacement (injury/suspension)">
              Replace
            </button>
            <button class="btn-action-xs"
              @click="openCorrectionBowler"
              :disabled="!canCorrectBowler"
              :title="!canCorrectBowler ? 'Correction only available at the start of an over' : 'Correct wrong bowler selection'">
              Correction
            </button>
          </div>
        </div>
        <select v-model="selectedBowler" class="pb-select-full">
          <option disabled value="">Select...</option>
          <option v-for="p in bowlingPlayers" :key="p.id" :value="p.id">
            {{ p.name }} {{ bowlerRoleBadge(p.id) }}
          </option>
        </select>
      </div>
    </section>

    <main class="broadcast-main">


      <!-- LEFT: SCORING INPUTS -->
      <div class="panel scoring-panel">
        <!-- Gate Banners -->
        <div v-if="needsNewBatterLive || needsNewOverLive || needsNewInningsLive" class="gate-overlay">
           <div v-if="needsNewInningsLive">
             <h3>Innings Break</h3>
             <button v-if="roleCanScore" class="btn-gate" @click="openStartInnings">Start Next Innings</button>
           </div>
           <div v-else-if="needsNewBatterLive">
             <h3>Wicket Fall</h3>
             <button v-if="roleCanScore" class="btn-gate" @click="openSelectBatter">Select New Batter</button>
           </div>
           <div v-else-if="needsNewOverLive">
             <h3>End of Over</h3>
             <button v-if="roleCanScore" class="btn-gate" @click="openStartOver">Start Next Over</button>
           </div>
        </div>

        <div class="scoring-grid-inputs" :class="{disabled: !canScore}">
          <!-- Extras Row -->
          <div class="input-row extras-row">
            <button class="btn-input btn-extra-legal" :class="{active: extra==='none'}" @click="extra='none'">LEGAL</button>
            <button class="btn-input btn-extra-wd" :class="{active: extra==='wd'}" @click="extra='wd'">WD</button>
            <button class="btn-input btn-extra-nb" :class="{active: extra==='nb'}" @click="extra='nb'">NB</button>
            <button class="btn-input btn-extra-b" :class="{active: extra==='b'}" @click="extra='b'">B</button>
            <button class="btn-input btn-extra-lb" :class="{active: extra==='lb'}" @click="extra='lb'">LB</button>
          </div>

          <!-- Runs Matrix -->
          <div class="input-matrix">
            <button v-for="r in [0,1,2,3,4,6,5]" :key="r"
              :data-testid="`delivery-run-${r}`"
              class="btn-score"
              :class="[
                `btn-score-${r}`,
                { active: (extra==='none'||extra==='nb' ? offBat : extraRuns) === r }
              ]"
              @click="extra==='none'||extra==='nb' ? offBat=r : extraRuns=r">
              {{ r }}
            </button>
          </div>

          <!-- Wicket & Submit -->
          <div class="input-row action-row">
            <label class="wicket-toggle" :class="{checked: isWicket}">
              <input type="checkbox" v-model="isWicket"> WICKET
            </label>
            <button
              data-testid="submit-delivery"
              class="btn-submit"
              :disabled="!canSubmitSimple || isSubmitting"
              @click="submitSimple"
            >
              {{ isSubmitting ? '...' : 'SUBMIT' }}
            </button>
          </div>

          <!-- Wicket Details (Conditional) - Teleported to avoid clipping -->
          <Teleport to="body">
            <div v-if="isWicket" class="wicket-details-floating">
               <div class="wd-label">WICKET DETAILS</div>
               <div class="wd-row">
                 <select v-model="dismissal" class="sel-sm"><option value="bowled">Bowled</option><option value="caught">Caught</option><option value="lbw">LBW</option><option value="run_out">Run Out</option><option value="stumped">Stumped</option></select>
                 <select v-if="needsFielder" v-model="selectedFielderId" class="sel-sm"><option v-for="p in fielderOptions" :key="p.id" :value="p.id">{{p.name}}</option></select>
               </div>
            </div>
          </Teleport>

          <!-- Undo -->
          <div class="undo-row">
             <button class="btn-undo" :disabled="!canDeleteLast" @click="deleteLastDelivery">UNDO LAST</button>
          </div>
        </div>
      </div>

      <!-- RIGHT: SHOT MAP -->
      <div class="panel map-panel">
        <!-- Recent Balls Strip (Compact) -->
        <div class="recent-strip">
          <div class="recent-label">
             LAST 6
             <span class="active-ball-text" v-if="overInProgress">
               (Over {{ oversDisplay }})
             </span>
          </div>
          <div class="recent-balls">
            <div 
              v-for="(b, i) in recentBallSlots" 
              :key="i" 
              class="ball-badge" 
              :class="b ? getBallClass(b) : 'empty'"
              @click="b ? openCorrectionModal(b) : null"
              :title="b ? 'Click to correct this delivery' : ''"
              :style="b ? 'cursor: pointer;' : ''"
            >
              {{ b ? getBallLabel(b) : '•' }}
            </div>
          </div>
        </div>

        <div class="map-container">
           <!-- Placeholder for Shot Map - In real app this would be canvas/SVG -->
           <div class="wagon-wheel-placeholder">
              <div class="field-oval">
                 <div class="pitch-rect"></div>
                 <!-- Simple 8-zone click overlay -->
                 <div class="zone-overlay">
                    <div class="zone z1" @click.stop="recordZone(1)"></div>
                    <div class="zone z2" @click.stop="recordZone(2)"></div>
                    <div class="zone z3" @click.stop="recordZone(3)"></div>
                    <div class="zone z4" @click.stop="recordZone(4)"></div>
                    <div class="zone z5" @click.stop="recordZone(5)"></div>
                    <div class="zone z6" @click.stop="recordZone(6)"></div>
                    <div class="zone z7" @click.stop="recordZone(7)"></div>
                    <div class="zone z8" @click.stop="recordZone(8)"></div>
                 </div>
              </div>
              <div class="map-label">TAP ZONE TO RECORD SHOT</div>
           </div>
        </div>
      </div>


    </main>

    <!-- FOOTER TABS -->
    <footer class="broadcast-footer">
      <div class="tabs-nav">
        <button :class="{active: activeTab==='recent'}" @click="activeTab='recent'">RECENT</button>
        <button :class="{active: activeTab==='batting'}" @click="activeTab='batting'">BATTING</button>
        <button :class="{active: activeTab==='bowling'}" @click="activeTab='bowling'">BOWLING</button>
        <button :class="{active: activeTab==='ai'}" @click="activeTab='ai'">AI COMM</button>
        <button :class="{active: activeTab==='analytics'}" @click="activeTab='analytics'">ANALYTICS</button>
        <button :class="{active: activeTab==='extras'}" @click="activeTab='extras'">EXTRAS</button>
      </div>

      <div class="tab-content">
        <!-- RECENT: Delivery Table -->
        <div v-show="activeTab==='recent'" class="tab-pane">
           <DeliveryTable :deliveries="deliveriesThisInnings" :player-name-by-id="playerNameById" />
        </div>

        <!-- BATTING CARD -->
        <div v-show="activeTab==='batting'" class="tab-pane">
           <BattingCard :entries="battingEntries" />
        </div>

        <!-- BOWLING CARD -->
        <div v-show="activeTab==='bowling'" class="tab-pane">
           <BowlingCard :entries="bowlingEntries" />
        </div>

        <!-- AI COMMENTARY -->
        <div v-show="activeTab==='ai'" class="tab-pane">
            <div class="ai-header">
                <h4>AI Commentary</h4>
                <button v-if="!aiLoading && aiCommentary" class="btn-icon" @click="generateCommentary">↻</button>
            </div>
            <div v-if="aiLoading">Loading...</div>
            <p v-else-if="aiCommentary">{{ aiCommentary }}</p>
            <p v-else>No commentary yet.</p>
        </div>

        <!-- ANALYTICS: Win Probability, Innings Grade, Pressure Map & Phase Timeline -->
        <div v-show="activeTab==='analytics'" class="tab-pane analytics-container">
            <div class="analytics-widgets">
                <div class="analytics-widget-section">
                    <PhaseTimelineWidget
                      :phase-data="phaseData"
                      :predictions="predictions"
                      :loading="phaseLoading"
                      :on-refresh="() => fetchPhaseMap(gameId)"
                    />
                </div>

                <div class="analytics-widget-section">
                    <PressureMapWidget
                      :pressure-data="pressureData"
                      :loading="pressureLoading"
                    />
                </div>

                <div class="analytics-widget-section">
                    <h3>Innings Grade</h3>
                    <InningsGradeWidget
                      :grade-data="currentInningsGrade"
                      :batting-team="battingTeamName"
                      :bowling-team="(currentGame?.bowling_team_name ?? '')"
                      theme="dark"
                    />
                </div>

                <div class="analytics-widget-section">
                    <WinProbabilityChart :show-chart="true" />
                </div>
            </div>
        </div>

        <!-- EXTRAS & DLS -->
        <div v-show="activeTab==='extras'" class="tab-pane">
            <div class="extras-grid">
                <span>Wides: {{ extrasBreakdown.wides }}</span>
                <span>No-balls: {{ extrasBreakdown.no_balls }}</span>
                <span>Byes: {{ extrasBreakdown.byes }}</span>
                <span>Leg-byes: {{ extrasBreakdown.leg_byes }}</span>
                <span>Total: {{ extrasBreakdown.total }}</span>
            </div>
            <div v-if="canShowDls" class="dls-mini">
               <h4>DLS Target</h4>
               <div v-if="dls">Target: {{ dls.target }} ({{ dls.team2_resources.toFixed(1) }}%)</div>
               <button class="btn-sm" @click="refreshDls">Update</button>
            </div>
        </div>
      </div>
    </footer>

    <!-- Share & Monetize Modal -->
    <div v-if="shareOpen" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="share-title" @click.self="closeShare" @keydown.esc="closeShare" tabindex="0">
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
        <h3 class="modal-title">{{ isBowlerCorrection ? 'Correct Bowler' : 'Mid-over change (injury)' }}</h3>
        <p class="modal-body-text">{{ isBowlerCorrection ? 'Select the correct bowler for this over.' : 'Pick a replacement to finish this over. You can do this only once per over.' }}</p>
        <select v-model="selectedReplacementBowlerId" class="sel">
          <option disabled value="">{{ isBowlerCorrection ? 'Choose correct bowler…' : 'Choose replacement…' }}</option>
          <option v-for="p in (isBowlerCorrection ? eligibleCorrectionBowlers : replacementOptions)" :key="p.id" :value="p.id">{{ p.name }}{{ bowlerRoleBadge(p.id) }}</option>
        </select>
        <div class="modal-actions">
          <BaseButton variant="ghost" @click="closeChangeBowler">Cancel</BaseButton>
          <BaseButton variant="primary" :disabled="!selectedReplacementBowlerId" @click="confirmChangeBowler">{{ isBowlerCorrection ? 'Correct' : 'Change' }}</BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>

  <!-- Delivery Correction Modal -->
  <DeliveryCorrectionModal
    :show="showCorrectionModal"
    :delivery="correctionDelivery"
    :bowlerName="correctionDelivery ? playerNameById(correctionDelivery.bowler_id) : undefined"
    :batterName="correctionDelivery ? playerNameById(correctionDelivery.striker_id) : undefined"
    @close="closeCorrectionModal"
    @submit="submitCorrection"
  />
</template>

<style scoped>
/* =====================================================
   BROADCAST LAYOUT (ONE SCREEN, NO SCROLL)
   ===================================================== */
.broadcast-layout {
  display: grid;
  grid-template-rows: 48px auto 1fr 160px; /* Header, PlayerBar, Main, Footer - reduced footer to 160px */
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #f0f2f5;
  font-family: 'Inter', sans-serif;
}

/* HEADER */
.broadcast-header {
  background: #1a237e;
  color: white;
  padding: 0 16px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  z-index: 10;
  position: sticky;
  top: 0;
}
.header-left { display: flex; align-items: baseline; gap: 8px; min-width: 120px; }
.header-left .brand { font-weight: 900; letter-spacing: 1px; font-size: 18px; }
.header-left .game-meta { font-size: 12px; opacity: 0.8; font-family: monospace; }

.header-center { flex: 1; display: flex; justify-content: center; }

/* Dense Stats Layout */
.dense-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  font-family: 'Inter', sans-serif;
  white-space: nowrap;
}

.stat-group { display: flex; align-items: baseline; gap: 6px; }
.main-score { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
.team-name { font-weight: 400; opacity: 0.9; margin-right: 4px; font-size: 16px; }
.score-display { color: #fff; }
.overs-display { font-size: 14px; opacity: 0.8; font-weight: 400; }

.stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.2); }

.rates { font-size: 13px; gap: 12px; opacity: 0.9; }
.rate-item strong { font-weight: 700; color: #fff; }
.need-txt { color: #ffeb3b; font-weight: 600; }

.header-right { display: flex; gap: 8px; min-width: 120px; justify-content: flex-end; }
.btn-icon { background: rgba(255,255,255,0.1); border: none; color: white; width: 32px; height: 32px; border-radius: 4px; cursor: pointer; }
.btn-icon:hover { background: rgba(255,255,255,0.2); }
.btn-icon.active { background: #4caf50; }

.btn-share {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0 12px;
  height: 32px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s;
}
.btn-share:hover { background: #43a047; }

/* PLAYER BAR (Split Panels) */
.player-bar {
  background: #283593;
  padding: 8px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr; /* 3 Equal Columns */
  gap: 12px;
  align-items: stretch;
}

.player-box {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 6px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pb-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 700;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bowler-actions {
  display: flex;
  gap: 6px;
}

.btn-action-xs {
  background: rgba(255,255,255,0.15);
  border: none;
  color: #fff;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
  transition: background 0.2s;
}
.btn-action-xs:hover { background: rgba(255,255,255,0.3); }
.btn-action-xs:disabled { opacity: 0.3; cursor: not-allowed; }

.pb-select-full {
  background: transparent;
  border: none;
  color: white;
  font-size: 14px;
  font-weight: 600;
  width: 100%;
  cursor: pointer;
  outline: none;
  padding: 0;
  margin: 0;
}
.pb-select-full option {
  background: #333;
  color: white;
}

/* MAIN CONTENT GRID */
.broadcast-main {
  display: grid;
  grid-template-columns: 320px 1fr; /* Fixed Scoring Panel, Flexible Shot Map */
  gap: 1px;
  background: #ddd; /* Grid line color */
  overflow: hidden;
  min-height: 0;
}

/* PANELS */
.panel { background: white; position: relative; overflow: hidden; }

/* SCORING PANEL (Left) */
.scoring-panel {
  display: flex;
  flex-direction: column;
  padding: 8px;
  background: #fff;
}
.gate-overlay {
  position: absolute; inset: 0; background: rgba(255,255,255,0.95); z-index: 20;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center;
}
.btn-gate { background: #1a237e; color: white; padding: 12px 24px; border-radius: 8px; font-weight: bold; border: none; cursor: pointer; margin-top: 12px; }

.scoring-grid-inputs { display: flex; flex-direction: column; gap: 8px; height: 100%; }
.scoring-grid-inputs.disabled { opacity: 0.3; pointer-events: none; }

.input-row { display: flex; gap: 6px; }
.extras-row { height: 36px; }
.btn-input {
  flex: 1;
  padding: 0;
  border: 1px solid #ddd;
  background: #f8f9fa;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.1s;
}
.btn-input:hover { background: #eee; }
.btn-input.active { background: #1a237e; color: white; border-color: #1a237e; }

.input-matrix {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: 1fr 1fr 0.6fr; /* 3rd row smaller for '5' */
  gap: 6px;
  flex: 1;
}
.btn-score {
  font-size: 32px;
  font-weight: 800;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.1s;
  font-family: 'Inter', sans-serif;
  color: #333;
}
.btn-score:hover { background: #f5f5f5; transform: translateY(-1px); }
.btn-score:active { transform: translateY(0); }
.btn-score.active { background: #1a237e; color: white; border-color: #1a237e; }

/* Boundaries */
.btn-score.val-4 { color: #2e7d32; background: #f1f8e9; border-color: #c5e1a5; }
.btn-score.val-4.active { background: #2e7d32; color: white; border-color: #2e7d32; }
.btn-score.val-6 { color: #1565c0; background: #e3f2fd; border-color: #90caf9; }
.btn-score.val-6.active { background: #1565c0; color: white; border-color: #1565c0; }

/* Make '5' span full width */
.btn-score:nth-child(7) {
  grid-column: 1 / -1;
  font-size: 18px;
  color: #666;
}

.action-row { display: flex; gap: 6px; align-items: stretch; height: 38px; position: relative; z-index: 10; }
.wicket-toggle {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 2px solid #d32f2f;
  color: #d32f2f;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.1s;
  position: relative;
  z-index: 10;
}
.wicket-toggle:hover { background: #ffebee; }
.wicket-toggle.checked { background: #d32f2f; color: white; }

.btn-submit {
  flex: 2;
  background: #2e7d32;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  transition: all 0.1s;
  position: relative;
  z-index: 10;
  padding: 0;
}
.btn-submit:hover { background: #1b5e20; transform: translateY(-1px); }
.btn-submit:active { transform: translateY(0); }
.btn-submit:disabled { background: #ccc; cursor: not-allowed; box-shadow: none; transform: none; }

.wicket-details { background: #ffebee; padding: 8px; border-radius: 6px; display: flex; gap: 8px; }
.sel-sm { flex: 1; padding: 6px; border-radius: 4px; border: 1px solid #ef9a9a; }

.undo-row { margin-top: auto; text-align: center; padding-top: 2px; padding-bottom: 2px; }
.btn-undo { background: none; border: none; color: #999; text-decoration: underline; cursor: pointer; font-size: 10px; }
.btn-undo:hover { color: #d32f2f; }

.btn-ghost-sm {
  background: transparent;
  border: 1px solid #ddd;
  color: #666;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-ghost-sm:hover {
  background: #f5f5f5;
  color: #333;
  border-color: #ccc;
}

/* MAP PANEL (Right) */
.map-panel {
  background: #e8f5e9;
  display: flex;
  flex-direction: column; /* Stack strip and map */
  overflow: hidden;
}

.recent-strip {
  height: 40px;
  background: #fff;
  border-bottom: 1px solid #ddd;
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 12px;
  flex-shrink: 0;
}

.recent-label {
  font-size: 11px;
  font-weight: 700;
  color: #666;
  letter-spacing: 0.5px;
}

.recent-balls {
  display: flex;
  gap: 6px;
}

.ball-badge {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eee;
  color: #333;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
}
.ball-badge.wicket { background: #d32f2f; color: white; border-color: #b71c1c; }
.ball-badge.boundary { background: #4caf50; color: white; border-color: #388e3c; }
.ball-badge.empty { background: transparent; border: 1px dashed #ccc; color: #ccc; }

.map-container {
  flex: 1;
  position: relative;
  width: 100%;
  overflow: hidden;
}
.wagon-wheel-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; position: relative; }
.field-oval { width: 80%; height: 80%; border: 2px solid #4caf50; border-radius: 50%; position: relative; background: rgba(76, 175, 80, 0.1); }
.pitch-rect { width: 40px; height: 120px; background: #d7ccc8; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.zone-overlay { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; }
.zone { position: absolute; width: 50%; height: 50%; cursor: pointer; }
.zone:hover { background: rgba(0,0,0,0.05); }
.z1 { top: 0; right: 0; border-left: 1px dashed #ccc; border-bottom: 1px dashed #ccc; }
.z2 { top: 0; left: 0; border-right: 1px dashed #ccc; border-bottom: 1px dashed #ccc; }
.z3 { bottom: 0; left: 0; border-right: 1px dashed #ccc; border-top: 1px dashed #ccc; }
.z4 { bottom: 0; right: 0; border-left: 1px dashed #ccc; border-top: 1px dashed #ccc; }
/* (Simplified zones for demo) */
.map-label { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); font-weight: bold; color: #2e7d32; opacity: 0.6; pointer-events: none; }

/* FOOTER TABS */
.broadcast-footer {
  background: var(--color-bg-secondary, #1e1e1e);
  border-top: 1px solid var(--color-border, #333);
  display: flex;
  flex-direction: column;
  height: 160px; /* Reduced from 240px to show action buttons */
}
.tabs-nav { display: flex; background: var(--color-bg-accent, #2a2a2a); border-bottom: 1px solid var(--color-border, #333); }
.tabs-nav button { flex: 1; padding: 8px 6px; border: none; background: none; font-weight: 600; color: var(--color-text-secondary, #aaa); cursor: pointer; border-bottom: 3px solid transparent; font-size: 12px; }
.tabs-nav button.active { color: var(--color-primary, #667eea); border-bottom-color: var(--color-primary, #667eea); background: var(--color-bg-secondary, #1e1e1e); }

.tab-content { flex: 1; overflow-y: auto; padding: 0; position: relative; }
.tab-pane { height: 100%; padding: 12px; }

/* Utility overrides for components inside tabs */
:deep(.card) { border: none; box-shadow: none; padding: 0; margin: 0; }
:deep(table) { width: 100%; font-size: 13px; }
:deep(th) { background: #f5f5f5; position: sticky; top: 0; }

/* Extras Grid */
.extras-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; text-align: center; font-weight: bold; padding: 16px; background: var(--color-bg-accent, #2a2a2a); border-radius: 8px; color: var(--color-text, #e0e0e0); }
.dls-mini { margin-top: 16px; padding: 12px; background: var(--color-bg-accent, #2a2a2a); border-radius: 8px; display: flex; align-items: center; justify-content: space-between; color: var(--color-text, #e0e0e0); }

/* Modal overrides */
.modal-backdrop {
  z-index: 1000;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 20px;
}

.modal-card {
  position: relative;
  width: 100%;
  max-width: 500px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--color-bg-secondary, #1e1e1e);
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border, #333);
}

.modal-card--wide {
  max-width: 600px;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 12px 0;
  color: var(--color-text, #e0e0e0);
}

.modal-body-text {
  font-size: 14px;
  color: var(--color-text-secondary, #aaa);
  margin: 0 0 16px 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}

.lbl {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text, #e0e0e0);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sel {
  padding: 10px 12px;
  border: 1px solid var(--color-border, #444);
  border-radius: 6px;
  font-size: 14px;
  background: var(--color-bg, #121212);
  color: var(--color-text, #e0e0e0);
  cursor: pointer;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23e0e0e0' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 32px;
  position: relative;
  z-index: 2;
}

.sel:hover {
  border-color: var(--color-border-hover, #555);
}

.sel:focus {
  outline: none;
  border-color: var(--color-primary, #667eea);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.sel option {
  background: var(--color-bg, #121212);
  color: var(--color-text, #e0e0e0);
  padding: 8px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  flex-shrink: 0;
  padding-top: 12px;
  border-top: 1px solid var(--color-border, #333);
}

.modal-form-content {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 0;
}

/* =====================================================
   UX REFINEMENTS (COLORS & ANIMATIONS)
   ===================================================== */

/* 1. Run Button Colors */
.btn-score-0, .btn-score-1, .btn-score-2, .btn-score-3, .btn-score-5 { color: #333; background: #fff; }
.btn-score-4 { color: #1b5e20; background: #e8f5e9; border-color: #a5d6a7; }
.btn-score-6 { color: #0d47a1; background: #e3f2fd; border-color: #90caf9; }

.btn-score.active { background: #333; color: white; border-color: #333; }
.btn-score-4.active { background: #2e7d32; color: white; border-color: #2e7d32; }
.btn-score-6.active { background: #1565c0; color: white; border-color: #1565c0; }

/* Extras Colors */
.btn-extra-wd { color: #e65100; }
.btn-extra-nb { color: #e65100; }
.btn-extra-b  { color: #f57f17; }
.btn-extra-lb { color: #f57f17; }

.btn-extra-wd.active, .btn-extra-nb.active { background: #ff9800; color: white; border-color: #ff9800; }
.btn-extra-b.active, .btn-extra-lb.active  { background: #fbc02d; color: white; border-color: #fbc02d; }

/* 2. [REMOVED] Shot Map Tap Marker - not needed for UX */

/* 3. Last 6 Balls Strip */
.active-ball-text {
  margin-left: 8px;
  font-weight: 400;
  color: #1a237e;
  font-size: 11px;
}

.ball-badge.is-dot { background: #f5f5f5; color: #999; border-color: #ddd; }
.ball-badge.is-run { background: #fff; color: #333; border-color: #ccc; font-weight: 600; }
.ball-badge.is-4   { background: #2e7d32; color: white; border-color: #1b5e20; }
.ball-badge.is-6   { background: #1565c0; color: white; border-color: #0d47a1; }
.ball-badge.is-wicket { background: #d32f2f; color: white; border-color: #b71c1c; }
.ball-badge.is-extra  { background: #ff9800; color: white; border-color: #e65100; font-size: 10px; }

/* 4. Submit Micro-lock */
.btn-submit:disabled {
  opacity: 0.7;
  cursor: wait;
}

/* 5. Floating Wicket Details (Teleported) */
.wicket-details-floating {
  position: fixed;
  bottom: 260px; /* Above footer (240px) + gap */
  left: 16px;
  width: 288px; /* 320px col - 32px margins approx */
  z-index: 9999;
  background: #ffebee;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  border: 2px solid #d32f2f;
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: slide-up 0.2s ease-out;
}

.wd-label {
  font-size: 10px;
  font-weight: 800;
  color: #d32f2f;
  letter-spacing: 1px;
}

.wd-row {
  display: flex;
  gap: 8px;
}

@keyframes slide-up {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Analytics Container */
.analytics-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.analytics-widgets {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  padding: 1rem 0;
}

.analytics-widget-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.analytics-widget-section h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--pico-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

@media (max-width: 768px) {
  .analytics-widgets {
    grid-template-columns: 1fr;
  }
}
</style>
