<script setup lang="ts">
import { BaseButton } from '@/components'
import { useGameStore } from '@/stores/gameStore'

const props = defineProps<{
  gameId: string
  strikerId: string
  nonStrikerId: string
  bowlerId: string
  canScore: boolean
}>()
const game = useGameStore()
const proTooltip = 'Requires Coach Pro or Organization Pro'

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
      <BaseButton
        v-for="n in [0,1,2,3,4,5,6]"
        :key="n"
        variant="primary"
        size="sm"
        :disabled="!canScore"
        :title="!canScore ? proTooltip : undefined"
        @click="doRun(n)"
      >
        {{ n }}
      </BaseButton>
    </div>
    <div class="row">
      <BaseButton
        variant="secondary"
        size="sm"
        class="extra-wd"
        :disabled="!canScore"
        :title="!canScore ? proTooltip : undefined"
        @click="extra('wd')"
      >
        Wd
      </BaseButton>
      <BaseButton
        variant="secondary"
        size="sm"
        class="extra-nb"
        :disabled="!canScore"
        :title="!canScore ? proTooltip : undefined"
        @click="extra('nb')"
      >
        Nb
      </BaseButton>
      <BaseButton
        variant="danger"
        size="sm"
        :disabled="!canScore"
        :title="!canScore ? proTooltip : undefined"
        @click="wicket"
      >
        Wkt
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.pad {
  position: sticky;
  bottom: 0;
  background: var(--color-surface);
  backdrop-filter: blur(10px);
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  margin: var(--space-2);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
}

.row {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  margin: var(--space-1) 0;
}

.runs :deep(.ds-btn) {
  flex: 1;
}

/* Extra button accent colors */
.extra-wd {
  --color-secondary: var(--color-info);
  --color-secondary-hover: var(--color-info-hover, #138496);
}

.extra-nb {
  --color-secondary: #6f42c1;
  --color-secondary-hover: #5a32a3;
}
</style>
