<script setup lang="ts">
import { ref, toRefs } from 'vue'

import CommentaryInput from './CommentaryInput.vue'
import DismissalForm from './DismissalForm.vue'
import ScoreControls from './ScoreControls.vue'
import UndoLastBall from './UndoLastBall.vue'
import WicketModal from './WicketModal.vue'

import { useAuthStore } from '@/stores/authStore'
import { useGameStore } from '@/stores/gameStore'
import type { Player } from '@/types'

const props = defineProps<{
  gameId: string
  canScore: boolean
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  battingPlayers: Player[]
}>()
const { gameId, canScore, strikerId, nonStrikerId, bowlerId, battingPlayers } = toRefs(props)

const authStore = useAuthStore()
const gameStore = useGameStore()

if (import.meta.env.DEV) {
  console.log('[ScoringPanel debug]', {
    role: authStore.role,
    isSuperuser: authStore.isSuperuser,
    authCanScore: authStore.canScore,
    gameCanScore: gameStore.canScore,
    striker: gameStore.currentStriker?.id ?? null,
    nonStriker: gameStore.currentNonStriker?.id ?? null,
    bowler: gameStore.state?.current_bowler_id ?? null,
  })
}

const emit = defineEmits<{
  (e:'scored'): void
  (e:'error', message: string): void
}>()

const note = ref('')

function onScored() { emit('scored') }
function onError(m: string) { emit('error', m) }
</script>

<template>
  <div class="scoring-panel">
    <h3>⚡ Score This Delivery</h3>

    <CommentaryInput v-model="note" class="mb" />

    <div class="grid">
      <ScoreControls
        v-if="canScore"
        :game-id="gameId"
        :striker-id="strikerId"
        :non-striker-id="nonStrikerId"
        :bowler-id="bowlerId"
        :can-score="canScore"
        :commentary="note"
        @scored="onScored"
        @error="onError"
      >
        <template #wicket-modal="{ visible, close }">
            <WicketModal
              :game-id="gameId"
              :visible="visible"
              :striker-id="strikerId"
              :non-striker-id="nonStrikerId"
              :bowler-id="bowlerId"
              @close="close"
              @scored="onScored"
              @error="onError"
            />
        </template>
      </ScoreControls>

      <DismissalForm
        :game-id="gameId"
        :striker-id="strikerId"
        :non-striker-id="nonStrikerId"
        :bowler-id="bowlerId"
        :can-score="canScore"
        :batting-players="battingPlayers"
        @scored="onScored"
        @error="onError"
      />
    </div>

    <UndoLastBall v-if="canScore" :game-id="gameId" :disabled="true" class="mt" />

    <div v-if="import.meta.env.DEV" class="debug-panel">
      <p>Debug status</p>
      <ul>
        <li>Role: {{ authStore.role }}</li>
        <li>Is superuser: {{ authStore.isSuperuser }}</li>
        <li>Auth can score: {{ authStore.canScore }}</li>
        <li>Game can score: {{ gameStore.canScore }}</li>
        <li>Striker: {{ gameStore.currentStriker?.id ?? 'n/a' }}</li>
        <li>Non-striker: {{ gameStore.currentNonStriker?.id ?? 'n/a' }}</li>
        <li>Bowler: {{ gameStore.state?.current_bowler_id ?? 'n/a' }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.scoring-panel{background:rgba(255,255,255,.1);backdrop-filter:blur(10px);border-radius:20px;padding:2rem;border:1px solid rgba(255,255,255,.2)}
h3{color:#fff;margin-bottom:1rem;text-align:center}
.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:1.25rem}
.mb{margin-bottom:1rem}
.mt{margin-top:1rem}
@media (max-width: 900px){.grid{grid-template-columns:1fr}}
</style>
