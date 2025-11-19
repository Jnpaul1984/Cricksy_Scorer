<script setup lang="ts">
import { computed, ref } from 'vue'

import { useGameStore } from '@/stores/gameStore'

const props = defineProps<{
  canScore: boolean
  gameId: string
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
const canScore = computed(() => props.canScore && !submitting.value)

async function doScoreRuns(runs: number) {
  if (!canScore.value) return
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
  if (!canScore.value) return
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
        <button v-for="r in [0,1,2,3,4,5,6]" :key="r" :disabled="!canScore" @click="doScoreRuns(r)">{{ r }}</button>
      </div>
    </div>

    <div class="extras">
      <h4>Extras</h4>
      <div class="extras-grid">
        <button :disabled="!canScore" @click="doScoreExtra('wd', 1)">Wd</button>
        <button :disabled="!canScore" @click="doScoreExtra('nb', 0)">Nb</button>
        <button :disabled="!canScore" @click="doScoreExtra('b', 1)">B</button>
        <button :disabled="!canScore" @click="doScoreExtra('lb', 1)">Lb</button>
      </div>
    </div>

    <div class="wicket-row">
      <button class="wicket-btn" :disabled="!canScore" @click="openWicket">Wicket</button>
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
