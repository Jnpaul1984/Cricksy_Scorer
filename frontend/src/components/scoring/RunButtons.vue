<script setup lang="ts">
import { ref, computed } from 'vue'

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
const proTooltip = 'Requires Coach Pro or Organization Pro'

/** Local UI state */
const submitting = ref(false)
const isDisabled = computed(() => submitting.value || !props.canScore)

/** Main action */
async function score(runs: number) {
  console.log('[RunButtons] CLICK', { runs })

  if (!props.canScore) {
    console.warn('[RunButtons] blocked: canScore=false', {
      strikerId: props.strikerId,
      nonStrikerId: props.nonStrikerId,
      bowlerId: props.bowlerId,
    })
    return
  }
  if (submitting.value) {
    console.warn('[RunButtons] blocked: already submitting')
    return
  }

  submitting.value = true
  try {
    const payload: ScoreDeliveryRequest = {
      striker_id: props.strikerId,
      non_striker_id: props.nonStrikerId,
      bowler_id: props.bowlerId,
      runs_scored: runs,
      is_wicket: false,
      commentary: props.commentary ?? ''
    }

    console.log('[RunButtons] SUBMIT', payload)
    const res = await gameStore.submitDelivery(props.gameId, payload)
    console.log('[RunButtons] OK', res)

    // No manual swap here — rotation handled by server + snapshot/store merge
    emit('scored', payload)
  } catch (e: any) {
    console.error('[RunButtons] FAIL', e)
    emit('error', e?.message || 'Failed to score runs')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="runs-section" role="group" aria-label="Runs Scored">
    <h4>Runs Scored</h4>

    <div class="runs-buttons">
      <button
        v-for="runs in [0,1,2,3,4,5,6]"
        :key="runs"
        type="button"
        :disabled="isDisabled"
        :aria-disabled="isDisabled ? 'true' : 'false'"
        :title="!canScore ? proTooltip : isDisabled ? 'Select striker, non-striker (different) and bowler first' : `Record ${runs} run${runs===1?'':'s'}`"
        :class="['run-button', `runs-${runs}`]"
        @click="score(runs)"
      >
        {{ runs }}
      </button>
    </div>

    <p v-if="submitting" class="submitting">Saving…</p>
  </div>
</template>

<style scoped>
.runs-section h4{color:rgba(255,255,255,.9);margin-bottom:1rem;text-align:center;font-size:1rem}
.runs-buttons{display:grid;grid-template-columns:repeat(7,1fr);gap:.5rem}
.run-button{padding:1rem;border:none;border-radius:8px;font-weight:bold;font-size:1.2rem;cursor:pointer;transition:.2s;color:#fff}
.run-button:disabled{opacity:.5;cursor:not-allowed}
.runs-0{background:linear-gradient(135deg,#6c757d 0%,#5a6268 100%)}
.runs-1{background:linear-gradient(135deg,#007bff 0%,#0056b3 100%)}
.runs-2{background:linear-gradient(135deg,#28a745 0%,#1e7e34 100%)}
.runs-3{background:linear-gradient(135deg,#ffc107 0%,#e0a800 100%);color:#000}
.runs-4{background:linear-gradient(135deg,#fd7e14 0%,#e55a00 100%)}
.runs-5{background:linear-gradient(135deg,#e83e8c 0%,#c2185b 100%)}
.runs-6{background:linear-gradient(135deg,#dc3545 0%,#c82333 100%)}
.run-button:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.2)}
.submitting{margin-top:.5rem;text-align:center;font-size:.9rem;opacity:.8}
</style>
