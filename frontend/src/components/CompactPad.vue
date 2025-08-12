<script setup lang="ts">
import { useGameStore } from '@/stores/gameStore'
const props = defineProps<{
  gameId: string
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  canScore: boolean
}>()
const game = useGameStore()

async function doRun(n: number) {
  if (!props.canScore) return
  await game.submitDelivery(props.gameId, {
    striker_id: props.strikerId,
    non_striker_id: props.nonStrikerId,
    bowler_id: props.bowlerId,
    runs_scored: n,
    is_wicket: false
  } as any)
}
async function extra(code: 'wd'|'nb') {
  if (!props.canScore) return
  await game.submitDelivery(props.gameId, {
    striker_id: props.strikerId,
    non_striker_id: props.nonStrikerId,
    bowler_id: props.bowlerId,
    runs_scored: 1,
    extra: code,
    is_wicket: false
  } as any)
}
async function wicket() {
  if (!props.canScore) return
  await game.submitDelivery(props.gameId, {
    striker_id: props.strikerId,
    non_striker_id: props.nonStrikerId,
    bowler_id: props.bowlerId,
    runs_scored: 0,
    is_wicket: true,
    dismissal_type: 'bowled'
  } as any)
}
</script>

<template>
  <div class="pad">
    <div class="row runs">
      <button v-for="n in [0,1,2,3,4,5,6]" :key="n" :disabled="!canScore" @click="doRun(n)">
        {{ n }}
      </button>
    </div>
    <div class="row">
      <button class="wd" :disabled="!canScore" @click="extra('wd')">Wd</button>
      <button class="nb" :disabled="!canScore" @click="extra('nb')">Nb</button>
      <button class="wkt" :disabled="!canScore" @click="wicket">Wkt</button>
    </div>
  </div>
</template>

<style scoped>
.pad{position:sticky;bottom:0;background:rgba(0,0,0,.25);backdrop-filter:blur(10px);padding:.75rem;border-radius:16px;margin:.5rem;border:1px solid rgba(255,255,255,.2)}
.row{display:flex;gap:.5rem;justify-content:center;margin:.25rem 0}
.runs button{flex:1}
button{padding:.7rem 1rem;border:none;border-radius:10px;color:#fff;background:rgba(255,255,255,.12)}
button:disabled{opacity:.5}
.wd{background:linear-gradient(135deg,#17a2b8,#138496)}
.nb{background:linear-gradient(135deg,#6f42c1,#5a32a3)}
.wkt{background:linear-gradient(135deg,#dc3545,#c82333)}
</style>
