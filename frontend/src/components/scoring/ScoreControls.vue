<script setup lang="ts">
import { ref } from 'vue'

import { useGameStore } from '@/stores/gameStore'

const props = defineProps<{
  gameId: string
  canScore: boolean
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  commentary?: string
}>()

const emit = defineEmits<{
  (e: 'scored'): void
  (e: 'error', message: string): void
}>()

const gameStore = useGameStore()

const submitting = ref(false)
const showWicketModal = ref(false)

async function doScoreRuns(runs: number) {
  if (!props.canScore || submitting.value) return
  submitting.value = true
  try {
    await gameStore.scoreRuns(props.gameId, runs, null)
    emit('scored')
  } catch (e: any) {
    emit('error', e?.message || 'Failed to score')
  } finally {
    submitting.value = false
  }
}

async function doScoreExtra(code: 'wd'|'nb'|'b'|'lb', runs = 1) {
  if (!props.canScore || submitting.value) return
  submitting.value = true
  try {
    await gameStore.scoreExtra(props.gameId, code, runs, null)
    emit('scored')
  } catch (e: any) {
    emit('error', e?.message || 'Failed to score extra')
  } finally {
    submitting.value = false
  }
}

function openWicket() { showWicketModal.value = true }
function closeWicket() { showWicketModal.value = false }
</script>

<template>
  <div class="score-controls">
    <div class="runs">
      <h4>Runs</h4>
      <div class="runs-grid">
        <button v-for="r in [0,1,2,3,4,5,6]" :key="r" :disabled="!props.canScore || submitting" @click="doScoreRuns(r)">{{ r }}</button>
      </div>
    </div>

    <div class="extras">
      <h4>Extras</h4>
      <div class="extras-grid">
        <button :disabled="!props.canScore || submitting" @click="doScoreExtra('wd', 1)">Wd</button>
        <button :disabled="!props.canScore || submitting" @click="doScoreExtra('nb', 0)">Nb</button>
        <button :disabled="!props.canScore || submitting" @click="doScoreExtra('b', 1)">B</button>
        <button :disabled="!props.canScore || submitting" @click="doScoreExtra('lb', 1)">Lb</button>
      </div>
    </div>

    <div class="wicket-row">
      <button class="wicket-btn" :disabled="!props.canScore || submitting" @click="openWicket">Wicket</button>
    </div>

    <slot name="wicket-modal" :visible="showWicketModal" :close="closeWicket" />
  </div>
</template>

<style scoped>
.score-controls{display:flex;flex-direction:column;gap:12px}
.runs-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
.extras-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
button{padding:8px;border-radius:8px;border:none;background:#0ea5a4;color:white;font-weight:700}
.wicket-btn{background:#dc3545}
</style>
