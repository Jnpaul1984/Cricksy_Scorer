<script setup lang="ts">
import { ref } from 'vue'

import { useGameStore } from '@/stores/gameStore'
import type { ScoreDeliveryRequest } from '@/types'

const props = defineProps<{
  gameId: string
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  canScore: boolean
  commentary?: string
}>()

const emit = defineEmits<{
  (e: 'scored', payload: ScoreDeliveryRequest): void
  (e: 'error', message: string): void
}>()

const gameStore = useGameStore()
const byeRuns = ref<number>(1)
const legByeRuns = ref<number>(1)

/**
 * Record an extra delivery
 * extra: 'wd' (wide), 'nb' (no-ball), 'b' (bye), 'lb' (leg-bye)
 */
async function score(extra: 'wd' | 'nb' | 'b' | 'lb', runs: number = 1) {
  if (!props.canScore) return
  try {
    const payload: ScoreDeliveryRequest = {
      striker_id: props.strikerId,
      non_striker_id: props.nonStrikerId,
      bowler_id: props.bowlerId,
      runs_scored: runs,
      extra,
      is_wicket: false,
      commentary: props.commentary ?? ''
    }

    await gameStore.submitDelivery(props.gameId, payload)
    emit('scored', payload)
  } catch (e: any) {
    console.error(e)
    emit('error', e?.message || 'Failed to score extra')
  }
}
</script>

<template>
  <div class="extras-section">
    <h4>Extras</h4>

    <div class="extras-buttons">
      <button class="extra-button wide" :disabled="!canScore" @click="score('wd', 1)">Wide (Wd)</button>
      <button class="extra-button no-ball" :disabled="!canScore" @click="score('nb', 1)">No Ball (Nb)</button>
    </div>

    <div class="extras-row">
      <label for="sel-byes">Byes (B):</label>
      <select
        id="sel-byes"
        v-model.number="byeRuns"
        :disabled="!canScore"
        title="Byes"
        aria-describedby="sel-byes-hint"
      >
        <option v-for="n in [1,2,3,4]" :key="'b-'+n" :value="n">{{ n }}</option>
      </select>
      <small id="sel-byes-hint" class="sr-only">Choose number of byes</small>
      <button class="extra-button bye" :disabled="!canScore" @click="score('b', byeRuns)">Add</button>
    </div>

    <div class="extras-row">
      <label for="sel-leg-byes">Leg Byes (LB):</label>
      <select
        id="sel-leg-byes"
        v-model.number="legByeRuns"
        :disabled="!canScore"
        title="Leg byes"
        aria-describedby="sel-leg-byes-hint"
      >
        <option v-for="n in [1,2,3,4]" :key="'lb-'+n" :value="n">{{ n }}</option>
      </select>
      <small id="sel-leg-byes-hint" class="sr-only">Choose number of leg byes</small>
      <button class="extra-button leg-bye" :disabled="!canScore" @click="score('lb', legByeRuns)">Add</button>
    </div>
  </div>
</template>

<style scoped>
.extras-section h4{color:rgba(255,255,255,.9);margin-bottom:1rem;text-align:center;font-size:1rem}
.extras-buttons{display:flex;flex-direction:column;gap:.5rem;margin-bottom:1rem}
.extra-button{padding:.75rem;border:none;border-radius:8px;font-weight:500;cursor:pointer;transition:.2s;color:#fff}
.extra-button:disabled{opacity:.5;cursor:not-allowed}
.wide{background:linear-gradient(135deg,#17a2b8 0%,#138496 100%)}
.no-ball{background:linear-gradient(135deg,#6f42c1 0%,#5a32a3 100%)}
.bye{background:linear-gradient(135deg,#007bff 0%,#0056b3 100%)}
.leg-bye{background:linear-gradient(135deg,#28a745 0%,#1e7e34 100%)}
.extras-row{display:flex;align-items:center;gap:.5rem;margin:.5rem 0}
.extras-row label{color:#fff;opacity:.8;min-width:110px}
.extras-row select{padding:.5rem;border-radius:8px;background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.3)}
/* screen-reader only helper (keeps audit happy without visual noise) */
.sr-only {
  position: absolute !important;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 1px, 1px);
  white-space: nowrap; border: 0;
}
</style>
