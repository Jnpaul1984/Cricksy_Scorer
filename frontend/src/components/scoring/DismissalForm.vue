<script setup lang="ts">
import { ref, computed } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import type { ScoreDeliveryRequest, Player } from '@/types'

const props = defineProps<{
  gameId: string
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  canScore: boolean
  battingPlayers: Player[]
}>()

const emit = defineEmits<{
  (e: 'scored', payload: ScoreDeliveryRequest): void
  (e: 'error', message: string): void
}>()

const gameStore = useGameStore()

const dismissalType = ref<string>('bowled')
const dismissed = ref<'striker'|'non_striker'>('striker')
const fielderId = ref<string>('')
const note = ref<string>('')

const dismissedPlayerId = computed(() =>
  dismissed.value === 'striker' ? props.strikerId : props.nonStrikerId
)

const DISMISSALS = [
  { value:'bowled', label:'Bowled' },
  { value:'caught', label:'Caught' },
  { value:'lbw', label:'LBW' },
  { value:'stumped', label:'Stumped' },
  { value:'run_out', label:'Run Out' },
  { value:'hit_wicket', label:'Hit Wicket' },
  { value:'obstructing_the_field', label:'Obstructing the Field' },
  { value:'hit_ball_twice', label:'Hit the Ball Twice' },
  { value:'timed_out', label:'Timed Out' },
  { value:'retired_out', label:'Retired - Out' },
  { value:'handled_ball', label:'Handled the Ball (legacy)' },
]

async function submit() {
  if (!props.canScore) return
  try {
    const payload: ScoreDeliveryRequest = {
      striker_id: props.strikerId,
      non_striker_id: props.nonStrikerId,
      bowler_id: props.bowlerId,
      runs_scored: 0,
      is_wicket: true,
      dismissal_type: dismissalType.value,
      dismissed_player_id: dismissedPlayerId.value || props.strikerId,
      commentary: note.value.trim(),
      // fielder_id: fielderId.value || undefined // enable when API supports it
    } as unknown as ScoreDeliveryRequest

    await gameStore.submitDelivery(props.gameId, payload)
    emit('scored', payload)
  } catch (e: any) {
    console.error(e)
    emit('error', e?.message || 'Failed to record dismissal')
  }
}
</script>

<template>
  <div class="dismissal-form">
    <h4>Wicket</h4>

    <div class="row">
      <label>Type</label>
      <select v-model="dismissalType">
        <option v-for="d in DISMISSALS" :key="d.value" :value="d.value">{{ d.label }}</option>
      </select>
    </div>

    <div class="row">
      <label>Dismissed</label>
      <div class="toggle">
        <label><input type="radio" value="striker" v-model="dismissed"> Striker</label>
        <label><input type="radio" value="non_striker" v-model="dismissed"> Non-Striker</label>
      </div>
    </div>

    <div class="row">
      <label>Fielder (optional)</label>
      <select v-model="fielderId">
        <option value="">— none —</option>
        <option v-for="p in battingPlayers" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
    </div>

    <div class="row">
      <label>Commentary</label>
      <textarea v-model="note" rows="2" placeholder="e.g., Bowled through the gate."></textarea>
    </div>

    <button class="submit" @click="submit" :disabled="!canScore">Record Wicket</button>
  </div>
</template>

<style scoped>
.dismissal-form h4{color:rgba(255,255,255,.9);margin-bottom:1rem;text-align:center}
.row{display:flex;align-items:center;gap:.75rem;margin:.5rem 0}
.row label{min-width:120px;color:#fff;opacity:.9}
select,textarea{flex:1;padding:.6rem;border-radius:8px;background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.3)}
.toggle{display:flex;gap:1rem;color:#fff;opacity:.9}
.submit{width:100%;padding:.9rem;border:none;border-radius:10px;color:#fff;font-weight:600;cursor:pointer;background:linear-gradient(135deg,#dc3545 0%,#c82333 100%);transition:.2s}
.submit:disabled{opacity:.5;cursor:not-allowed}
.submit:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 4px 15px rgba(220,53,69,.3)}
</style>
