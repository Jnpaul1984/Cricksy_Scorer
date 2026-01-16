<!-- frontend/src/components/LiveMatchCardCoach.vue -->
<template>
  <div class="coach-match-card">
    <!-- Layer 1: Match Snapshot Header -->
    <div class="layer-snapshot">
      <div class="snapshot-row">
        <div class="teams-section">
          <span class="team-name">{{ battingTeam }}</span>
          <span class="vs-badge">vs</span>
          <span class="team-name">{{ bowlingTeam }}</span>
        </div>
        <div v-if="isLive" class="live-badge">● LIVE</div>
      </div>

      <div class="snapshot-stats">
        <div class="stat-pill">
          <span class="label">Score</span>
          <span class="value">{{ totalRuns }}/{{ totalWickets }}</span>
        </div>
        <div class="stat-pill">
          <span class="label">Overs</span>
          <span class="value">{{ oversDisplay }}</span>
        </div>
        <div class="stat-pill">
          <span class="label">CRR</span>
          <span class="value">{{ currentRunRate }}</span>
        </div>
        <div v-if="target" class="stat-pill target-pill">
          <span class="label">Target</span>
          <span class="value">{{ target }}</span>
        </div>
      </div>
    </div>

    <!-- Layer 2: Current Matchups -->
    <div class="layer-matchups">
      <div class="matchup-box striker">
        <div class="matchup-role">STRIKER</div>
        <div class="matchup-name">{{ strikerName }}</div>
        <div class="matchup-stats">
          <span class="stat">{{ strikerRuns }}({{ strikerBalls }})</span>
          <span class="stat sr">SR {{ strikerSR }}</span>
        </div>
      </div>

      <div class="matchup-box non-striker">
        <div class="matchup-role">NON-STRIKER</div>
        <div class="matchup-name">{{ nonStrikerName }}</div>
        <div class="matchup-stats">
          <span class="stat">{{ nonStrikerRuns }}({{ nonStrikerBalls }})</span>
          <span class="stat sr">SR {{ nonStrikerSR }}</span>
        </div>
      </div>

      <div class="matchup-box bowler">
        <div class="matchup-role">BOWLER</div>
        <div class="matchup-name">{{ bowlerName }}</div>
        <div class="matchup-stats">
          <span class="stat">{{ bowlerOvers }}-{{ bowlerRuns }}-{{ bowlerWkts }}</span>
          <span class="stat econ">Econ {{ bowlerEcon }}</span>
        </div>
      </div>
    </div>

    <!-- Layer 3: Momentum & Signals -->
    <div class="layer-momentum">
      <div class="momentum-row">
        <div class="momentum-section">
          <span class="section-label">Last 6</span>
          <div class="balls-strip">
            <div
              v-for="(ball, idx) in lastSixBalls"
              :key="idx"
              :class="['ball-pill', ballClass(ball)]"
            >
              {{ ball || '-' }}
            </div>
          </div>
        </div>

        <div class="momentum-section">
          <span class="section-label">Wkts In Hand</span>
          <span class="wkts-value">{{ wicketsInHand }}</span>
        </div>

        <div v-if="parRunRate" class="momentum-section">
          <span class="section-label">Par vs CRR</span>
          <span :class="['par-badge', parComparison]">{{ parVsCRR }}</span>
        </div>

        <div class="momentum-section">
          <span class="section-label">Bowler Status</span>
          <span :class="['status-badge', bowlerStatus]">{{ bowlerStatusLabel }}</span>
        </div>
      </div>
    </div>

    <!-- Layer 4: Coach Actions -->
    <div class="layer-actions">
      <BaseButton
        variant="ghost"
        size="sm"
        title="Add a tactical note about this moment"
        @click="openNoteDialog"
      >
        + Tactical Note
      </BaseButton>
      <BaseButton
        variant="ghost"
        size="sm"
        title="Flag a player for analysis"
        @click="flagPlayer"
      >
        🚩 Flag Player
      </BaseButton>
      <BaseButton
        variant="ghost"
        size="sm"
        title="Open detailed analyst view"
        @click="openAnalyst"
      >
        📊 Analyst View
      </BaseButton>
    </div>

    <!-- Note Dialog (Simple) -->
    <div v-if="noteDialogOpen" class="note-dialog-backdrop" @click.self="noteDialogOpen = false">
      <div class="note-dialog">
        <h4>Add Tactical Note</h4>
        <textarea
          v-model="noteText"
          placeholder="Jot down observations, tactics, or player notes..."
          class="note-textarea"
          rows="4"
        />
        <div class="dialog-actions">
          <BaseButton variant="ghost" size="sm" @click="noteDialogOpen = false">
            Cancel
          </BaseButton>
          <BaseButton variant="primary" size="sm" @click="saveNote">
            Save Note
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { BaseButton } from '@/components'
import { useGameStore } from '@/stores/gameStore'
import { fmtSR, fmtEconomy } from '@/utils/cricket'

/* ============================================================================
   Props
   ============================================================================ */
const props = withDefaults(
  defineProps<{
    gameId: string
    canAction?: boolean
  }>(),
  {
    canAction: true,
  }
)

/* ============================================================================
   Store & Router
   ============================================================================ */
const router = useRouter()
const gameStore = useGameStore()

const {
  currentGame,
  state,
  battingRowsXI,
  bowlingRowsXI,
  liveSnapshot,
  currentPrediction,
} = storeToRefs(gameStore)

/* ============================================================================
   Dialog State
   ============================================================================ */
const noteDialogOpen = ref(false)
const noteText = ref('')

/* ============================================================================
   Computed: Match Snapshot (Layer 1)
   ============================================================================ */
const isLive = computed(() => {
  const status = String(currentGame.value?.status || '').toUpperCase()
  return status === 'IN_PROGRESS' || status === 'LIVE'
})

const battingTeam = computed(() => currentGame.value?.batting_team_name || 'BAT')
const bowlingTeam = computed(() => currentGame.value?.bowling_team_name || 'BOWL')

const totalRuns = computed(() => currentGame.value?.total_runs ?? 0)
const totalWickets = computed(() => currentGame.value?.total_wickets ?? 0)

const oversDisplay = computed(() => {
  const oc = currentGame.value?.overs_completed ?? 0
  const bto = currentGame.value?.balls_this_over ?? 0
  return `${oc}.${bto}`
})

const currentRunRate = computed(() => {
  const runs = totalRuns.value
  const overs = Number(oversDisplay.value) || 0
  if (overs === 0) return '—'
  const crr = (runs / overs).toFixed(2)
  return crr
})

const target = computed(() => currentGame.value?.target ?? null)

/* ============================================================================
   Computed: Current Matchups (Layer 2)
   ============================================================================ */
const strikerBatting = computed(() => {
  const id = currentGame.value?.current_striker_id
  if (!id || !currentGame.value?.batting_scorecard) return null
  return (currentGame.value.batting_scorecard as any)[id]
})

const strikerName = computed(() => strikerBatting.value?.player_name || 'Striker')
const strikerRuns = computed(() => strikerBatting.value?.runs ?? 0)
const strikerBalls = computed(() => strikerBatting.value?.balls_faced ?? 0)
const strikerSR = computed(() => {
  const balls = strikerBalls.value
  if (balls === 0) return '—'
  const sr = ((strikerRuns.value / balls) * 100).toFixed(1)
  return sr
})

const nonStrikerBatting = computed(() => {
  const id = currentGame.value?.current_non_striker_id
  if (!id || !currentGame.value?.batting_scorecard) return null
  return (currentGame.value.batting_scorecard as any)[id]
})

const nonStrikerName = computed(() => nonStrikerBatting.value?.player_name || 'Non-Striker')
const nonStrikerRuns = computed(() => nonStrikerBatting.value?.runs ?? 0)
const nonStrikerBalls = computed(() => nonStrikerBatting.value?.balls_faced ?? 0)
const nonStrikerSR = computed(() => {
  const balls = nonStrikerBalls.value
  if (balls === 0) return '—'
  const sr = ((nonStrikerRuns.value / balls) * 100).toFixed(1)
  return sr
})

const bowlerBowling = computed(() => {
  const id = (state.value as any)?.current_bowler_id
  if (!id || !currentGame.value?.bowling_scorecard) return null
  return (currentGame.value.bowling_scorecard as any)[id]
})

const bowlerName = computed(() => bowlerBowling.value?.player_name || 'Bowler')
const bowlerOvers = computed(() => {
  const val = bowlerBowling.value?.overs_bowled ?? 0
  const whole = Math.floor(val)
  const frac = Math.round((val - whole) * 10)
  return whole
})
const bowlerRuns = computed(() => bowlerBowling.value?.runs_conceded ?? 0)
const bowlerWkts = computed(() => bowlerBowling.value?.wickets_taken ?? 0)
const bowlerEcon = computed(() => {
  // FIX B6: Use backend-calculated economy from bowling_scorecard
  // NO local calculation - backend handles overs→balls conversion correctly
  const bowlerId = (state.value as any)?.current_bowler_id
  const bowler = gameStore.liveSnapshot?.bowling_scorecard?.[bowlerId]
  return bowler?.economy?.toFixed(2) ?? '—'
})

/* ============================================================================
   Computed: Momentum & Signals (Layer 3)
   ============================================================================ */
const lastSixBalls = computed(() => {
  // FIX A3: Use actual deliveries from liveSnapshot
  const deliveries = gameStore.liveSnapshot?.deliveries ?? []
  const lastSix = deliveries.slice(-6)
  
  return lastSix.map((d: any) => {
    if (d.is_wicket) return 'W'
    if (d.runs_off_bat === 4) return '4'
    if (d.runs_off_bat === 6) return '6'
    if (!d.extra_type && d.runs_scored === 0) return '0'
    return String(d.runs_scored)
  })
})

const ballClass = (ball: string | null) => {
  if (!ball) return 'empty'
  if (ball === 'W') return 'wicket'
  if (ball === '4') return 'four'
  if (ball === '6') return 'six'
  if (ball === '0') return 'dot'
  return 'run'
}

const wicketsInHand = computed(() => {
  const max = 10
  const out = totalWickets.value
  return max - out
})

const parRunRate = computed(() => {
  // FIX B5: Use liveSnapshot for real-time DLS par value
  const dls = gameStore.liveSnapshot?.dls
  if (!dls || !dls.par) return null
  return dls.par
})

const parVsCRR = computed(() => {
  // FIX B5: Calculate par vs CRR using snapshot values only
  const snapshot = gameStore.liveSnapshot
  if (!snapshot?.dls?.par || !snapshot?.current_run_rate) return null
  
  const diff = snapshot.current_run_rate - snapshot.dls.par
  return diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)
})

const parComparison = computed(() => {
  if (!parVsCRR.value) return ''
  const diff = Number(parVsCRR.value)
  if (diff >= 0.5) return 'ahead'
  if (diff <= -0.5) return 'behind'
  return 'neutral'
})

const bowlerStatus = computed(() => {
  const econ = Number(bowlerEcon.value) || 0
  // Simple heuristic: econ > 8 = under pressure, < 5 = good
  if (econ > 8) return 'under-pressure'
  if (econ < 5) return 'good'
  return 'neutral'
})

const bowlerStatusLabel = computed(() => {
  switch (bowlerStatus.value) {
    case 'good':
      return '✓ Good'
    case 'under-pressure':
      return '⚠ Pressure'
    default:
      return '○ Neutral'
  }
})

/* ============================================================================
   Actions
   ============================================================================ */
function openNoteDialog() {
  noteText.value = ''
  noteDialogOpen.value = true
}

function saveNote() {
  console.log('[Coach] Note saved:', noteText.value)
  // TODO: Persist to backend or local storage
  noteDialogOpen.value = false
  noteText.value = ''
}

function flagPlayer() {
  console.log('[Coach] TODO: Flag player for analysis')
  // TODO: Implement flag player workflow
}

function openAnalyst() {
  router.push({ name: 'AnalystWorkspace', params: { gameId: props.gameId } })
}

/* ============================================================================
   Lifecycle
   ============================================================================ */
onMounted(async () => {
  try {
    if (!currentGame.value || (currentGame.value as any).id !== props.gameId) {
      await gameStore.loadGame(props.gameId)
    }
  } catch (err) {
    console.error('[LiveMatchCardCoach] Failed to load game:', err)
  }
})
</script>

<style scoped>
.coach-match-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  max-height: 50vh;
  overflow: hidden;
}

/* ========================================================================
   Layer 1: Match Snapshot Header
   ======================================================================== */
.layer-snapshot {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.snapshot-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.teams-section {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.team-name {
  color: #1a237e;
  font-weight: 700;
}

.vs-badge {
  color: #999;
  font-size: 12px;
  text-transform: uppercase;
}

.live-badge {
  background: #ff4444;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.snapshot-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f5f5f5;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  min-width: 70px;
}

.stat-pill .label {
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-pill .value {
  font-weight: 700;
  color: #1a237e;
  font-size: 14px;
}

.target-pill {
  background: #e3f2fd;
  border: 1px solid #90caf9;
}

/* ========================================================================
   Layer 2: Current Matchups
   ======================================================================== */
.layer-matchups {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  flex-shrink: 0;
}

.matchup-box {
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.matchup-box.striker {
  border-left: 3px solid #2e7d32;
}

.matchup-box.non-striker {
  border-left: 3px solid #1565c0;
}

.matchup-box.bowler {
  border-left: 3px solid #d32f2f;
}

.matchup-role {
  font-size: 10px;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.matchup-name {
  font-weight: 700;
  color: #1a237e;
  font-size: 13px;
}

.matchup-stats {
  display: flex;
  gap: 6px;
  font-size: 11px;
  color: #666;
}

.matchup-stats .stat {
  font-weight: 600;
  color: #333;
}

.matchup-stats .sr,
.matchup-stats .econ {
  color: #999;
  font-weight: 400;
}

/* ========================================================================
   Layer 3: Momentum & Signals
   ======================================================================== */
.layer-momentum {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
  padding: 8px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
}

.momentum-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.momentum-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.section-label {
  font-size: 10px;
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.balls-strip {
  display: flex;
  gap: 4px;
}

.ball-pill {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 11px;
  border: 1px solid #ddd;
  background: white;
  color: #333;
}

.ball-pill.empty {
  background: #f5f5f5;
  color: #ccc;
  border-style: dashed;
}

.ball-pill.dot {
  background: #f5f5f5;
  color: #999;
}

.ball-pill.run {
  background: #fff;
  color: #333;
}

.ball-pill.four {
  background: #e8f5e9;
  color: #2e7d32;
  border-color: #a5d6a7;
}

.ball-pill.six {
  background: #e3f2fd;
  color: #1565c0;
  border-color: #90caf9;
}

.ball-pill.wicket {
  background: #ffebee;
  color: #d32f2f;
  border-color: #ef9a9a;
}

.wkts-value {
  font-weight: 700;
  font-size: 16px;
  color: #1a237e;
}

.par-badge,
.status-badge {
  font-weight: 600;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  text-align: center;
  min-width: 70px;
}

.par-badge.ahead {
  background: #e8f5e9;
  color: #2e7d32;
}

.par-badge.behind {
  background: #ffebee;
  color: #d32f2f;
}

.par-badge.neutral {
  background: #f5f5f5;
  color: #666;
}

.status-badge.good {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.under-pressure {
  background: #fff3e0;
  color: #e65100;
}

.status-badge.neutral {
  background: #f5f5f5;
  color: #666;
}

/* ========================================================================
   Layer 4: Coach Actions
   ======================================================================== */
.layer-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  border-top: 1px solid #e0e0e0;
  padding-top: 8px;
}

.layer-actions :deep(.ds-btn) {
  flex: 1;
  font-size: 12px;
}

/* ========================================================================
   Note Dialog
   ======================================================================== */
.note-dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.note-dialog {
  background: white;
  border-radius: 8px;
  padding: 16px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.note-dialog h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 700;
  color: #1a237e;
}

.note-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  resize: vertical;
  margin-bottom: 12px;
}

.note-textarea:focus {
  outline: none;
  border-color: #1a237e;
  box-shadow: 0 0 0 3px rgba(26, 35, 126, 0.1);
}

.dialog-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.dialog-actions :deep(.ds-btn) {
  font-size: 12px;
}
</style>
