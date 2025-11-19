<script setup lang="ts">
import { ref, watch } from 'vue'

import { useGameStore } from '@/stores/gameStore'

const props = defineProps<{
  gameId: string
  visible: boolean
  strikerId: string
  nonStrikerId: string
  bowlerId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'scored'): void
  (e: 'error', message: string): void
}>()

const gameStore = useGameStore()

const dismissal = ref('bowled')
const dismissed = ref<'striker'|'non_striker'>('striker')
const note = ref('')
const submitting = ref(false)

watch(() => props.visible, (v) => { if (!v) { dismissal.value = 'bowled'; dismissed.value = 'striker'; note.value = '' } })

async function submit() {
  if (submitting.value) return
  submitting.value = true
  try {
    const dismissedPlayer = dismissed.value === 'striker' ? props.strikerId : props.nonStrikerId
    await gameStore.scoreWicket(props.gameId, String(dismissal.value), dismissedPlayer)
    emit('scored')
    emit('close')
  } catch (e: any) {
    emit('error', e?.message || 'Failed to record wicket')
  } finally { submitting.value = false }
}

function close() { emit('close') }
</script>

<template>
  <div v-if="props.visible" class="modal-backdrop" role="dialog" aria-modal="true">
    <div class="modal">
      <h3>Record Wicket</h3>
      <div class="row">
        <label>Type</label>
        <select v-model="dismissal">
          <option value="bowled">Bowled</option>
          <option value="caught">Caught</option>
          <option value="lbw">LBW</option>
          <option value="stumped">Stumped</option>
          <option value="run_out">Run out</option>
        </select>
      </div>
      <div class="row">
        <label>Who</label>
        <select v-model="dismissed">
          <option value="striker">Striker</option>
          <option value="non_striker">Non-striker</option>
        </select>
      </div>
      <div class="row">
        <label>Note</label>
        <input v-model="note" placeholder="Optional note" />
      </div>

      <div class="actions">
        <button @click="close">Cancel</button>
        <button :disabled="submitting" @click="submit">Record</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center}
.modal{background:white;padding:16px;border-radius:8px;min-width:320px}
.row{display:flex;gap:8px;align-items:center;margin:8px 0}
.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
button{padding:8px 12px;border-radius:6px;border:none}
</style>
