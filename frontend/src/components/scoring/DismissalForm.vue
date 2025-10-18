<script setup lang="ts">
import { ref, computed } from 'vue'

import { useGameStore } from '@/stores/gameStore'
import type { ScoreDeliveryRequest, Player } from '@/types'

type DismissalType =
  | 'bowled'
  | 'caught'
  | 'lbw'
  | 'stumped'
  | 'run_out'
  | 'hit_wicket'
  | 'obstructing_the_field'
  | 'hit_ball_twice'
  | 'timed_out'
  | 'retired_out'
  | 'handled_ball'

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

const dismissalType = ref<DismissalType>('bowled')
const dismissed = ref<'striker' | 'non_striker'>('striker')
const fielderId = ref<string>('')
const note = ref<string>('')

const dismissedPlayerId = computed(() =>
  dismissed.value === 'striker' ? props.strikerId : props.nonStrikerId
)

const DISMISSALS: { value: DismissalType; label: string }[] = [
  { value: 'bowled', label: 'Bowled' },
  { value: 'caught', label: 'Caught' },
  { value: 'lbw', label: 'LBW' },
  { value: 'stumped', label: 'Stumped' },
  { value: 'run_out', label: 'Run Out' },
  { value: 'hit_wicket', label: 'Hit Wicket' },
  { value: 'obstructing_the_field', label: 'Obstructing the Field' },
  { value: 'hit_ball_twice', label: 'Hit the Ball Twice' },
  { value: 'timed_out', label: 'Timed Out' },
  { value: 'retired_out', label: 'Retired - Out' },
  { value: 'handled_ball', label: 'Handled the Ball (legacy)' },
]

// Enable button only when we have IDs to submit and scoring is allowed
const canSubmit = computed(
  () => props.canScore && !!props.strikerId && !!props.nonStrikerId && !!props.bowlerId
)

async function submit() {
  if (!canSubmit.value) return
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
    }

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
      <label for="sel-dismissal-type">Type</label>
      <select
        id="sel-dismissal-type"
        v-model="dismissalType"
        :disabled="!canScore"
        title="Dismissal type"
        aria-describedby="sel-dismissal-type-hint"
      >
        <option v-for="d in DISMISSALS" :key="d.value" :value="d.value">{{ d.label }}</option>
      </select>
      <small id="sel-dismissal-type-hint" class="sr-only">Choose the dismissal type</small>
    </div>

    <div class="row">
      <span class="lbl">Dismissed</span>
      <div class="toggle" role="radiogroup" aria-labelledby="dismissed-group-label">
        <span id="dismissed-group-label" class="sr-only">Who is dismissed</span>

        <label for="rad-striker">
          <input
            id="rad-striker"
            v-model="dismissed"
            type="radio"
            value="striker"
            :disabled="!canScore"
          />
          Striker
        </label>

        <label for="rad-nonstriker">
          <input
            id="rad-nonstriker"
            v-model="dismissed"
            type="radio"
            value="non_striker"
            :disabled="!canScore"
          />
          Non‑Striker
        </label>
      </div>
    </div>

    <div class="row">
      <label for="sel-fielder">Fielder (optional)</label>
      <select
        id="sel-fielder"
        v-model="fielderId"
        :disabled="!canScore"
        title="Fielder"
        aria-describedby="sel-fielder-hint"
      >
        <option value="">— none —</option>
        <option v-for="p in battingPlayers" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <small id="sel-fielder-hint" class="sr-only">Select a fielder if applicable</small>
    </div>

    <div class="row">
      <label for="txt-note">Commentary</label>
      <textarea
        id="txt-note"
        v-model="note"
        rows="2"
        placeholder="e.g., Bowled through the gate."
        :disabled="!canScore"
      ></textarea>
    </div>

    <button class="submit" :disabled="!canSubmit" @click="submit">Record Wicket</button>
  </div>
</template>

<style scoped>
.dismissal-form h4{color:rgba(255,255,255,.9);margin-bottom:1rem;text-align:center}
.row{display:flex;align-items:center;gap:.75rem;margin:.5rem 0}
.row label{min-width:120px;color:#fff;opacity:.9}
.lbl{min-width:120px;color:#fff;opacity:.9}
select,textarea{flex:1;padding:.6rem;border-radius:8px;background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.3)}
.toggle{display:flex;gap:1rem;color:#fff;opacity:.9}
.submit{width:100%;padding:.9rem;border:none;border-radius:10px;color:#fff;font-weight:600;cursor:pointer;background:linear-gradient(135deg,#dc3545 0%,#c82333 100%);transition:.2s}
.submit:disabled{opacity:.5;cursor:not-allowed}
.submit:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 4px 15px rgba(220,53,69,.3)}
/* screen-reader only helper */
.sr-only{
  position:absolute !important;
  width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip:rect(0,0,1px,1px);
  white-space:nowrap;border:0;
}
</style>
