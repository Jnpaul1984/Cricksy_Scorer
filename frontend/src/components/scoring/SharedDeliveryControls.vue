<script setup lang="ts">
import { computed } from 'vue';

type Extra = 'none' | 'wd' | 'nb' | 'b' | 'lb';

const props = defineProps<{
  canScore: boolean;
  loading?: boolean;
  extra: Extra;
  runs: number;
  wicket: boolean;
  dismissal: string;
  dismissed: 'striker' | 'non_striker';
  strikerName: string;
  nonStrikerName: string;
  canSubmit: boolean;
  undoDisabled?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:extra', value: Extra): void;
  (event: 'update:runs', value: number): void;
  (event: 'update:wicket', value: boolean): void;
  (event: 'update:dismissal', value: string): void;
  (event: 'update:dismissed', value: 'striker' | 'non_striker'): void;
  (event: 'submit'): void;
  (event: 'undo'): void;
}>();

const requiresRunOut = computed(() => props.wicket && (props.extra === 'wd' || props.extra === 'nb'));
const nonStrikerAllowed = computed(() => props.dismissal === 'run_out');

function updateExtra(value: Extra) {
  emit('update:extra', value);
  if (props.wicket && (value === 'wd' || value === 'nb')) emit('update:dismissal', 'run_out');
}

function updateWicket(value: boolean) {
  emit('update:wicket', value);
  if (value && (props.extra === 'wd' || props.extra === 'nb')) emit('update:dismissal', 'run_out');
}

function updateDismissal(value: string) {
  emit('update:dismissal', value);
  if (value !== 'run_out' && props.dismissed === 'non_striker') emit('update:dismissed', 'striker');
}
</script>

<template>
  <div class="scoring-grid-inputs scorer-controls" :class="{ 'scorer-controls--disabled': !canScore }" :aria-disabled="!canScore" data-testid="scorer-controls">
    <div class="input-row extras-row"><button v-for="kind in ['none', 'wd', 'nb', 'b', 'lb'] as Extra[]" :key="kind" type="button" class="btn-input" :data-testid="`delivery-extra-${kind === 'none' ? 'legal' : kind}`" :class="[{ active: extra === kind }, `btn-extra-${kind}`]" :disabled="!canScore || loading" @click="updateExtra(kind)">{{ kind === 'none' ? 'LEGAL' : kind.toUpperCase() }}</button></div>
    <div class="input-matrix"><button v-for="value in [0, 1, 2, 3, 4, 6, 5]" :key="value" type="button" class="btn-score" :data-testid="`delivery-run-${value}`" :class="[`btn-score-${value}`, { active: runs === value }]" :disabled="!canScore || loading" @click="emit('update:runs', value)">{{ value }}</button></div>
    <div class="input-row action-row"><label class="wicket-toggle" :class="{ checked: wicket, disabled: !canScore }"><input data-testid="delivery-wicket" type="checkbox" :checked="wicket" :disabled="!canScore || loading" @change="updateWicket(($event.target as HTMLInputElement).checked)"> WICKET</label><button data-testid="submit-delivery" type="button" class="btn-submit" :disabled="!canSubmit || loading" @click="emit('submit')">{{ loading ? '...' : 'SUBMIT' }}</button></div>
    <div v-if="wicket" class="wicket-details"><select :value="dismissal" @change="updateDismissal(($event.target as HTMLSelectElement).value)"><option v-for="option in ['bowled', 'caught', 'lbw', 'run_out', 'stumped', 'hit_wicket', 'retired_out']" :key="option" :value="option" :disabled="requiresRunOut && option !== 'run_out'">{{ option.replace('_', ' ') }}</option></select><select data-testid="dismissed-batter" :value="dismissed" @change="emit('update:dismissed', ($event.target as HTMLSelectElement).value as 'striker' | 'non_striker')"><option value="striker">{{ strikerName }} (striker)</option><option value="non_striker" :disabled="!nonStrikerAllowed">{{ nonStrikerName }} (non-striker)</option></select><slot name="wicket-details-extra" /></div>
    <div class="undo-row"><button data-testid="undo-ball" type="button" class="btn-undo" :disabled="undoDisabled || loading" @click="emit('undo')">UNDO LAST</button></div>
  </div>
</template>

<style scoped>
.scoring-grid-inputs{display:flex;flex-direction:column;gap:8px;height:100%}.input-row{display:flex;gap:6px}.extras-row{height:36px}.btn-input,.btn-score{flex:1;padding:0;border:1px solid var(--color-border-strong,#94a3b8);background:var(--color-surface-raised,#fff);color:var(--color-text,#172554);border-radius:6px;font-weight:700;cursor:pointer}.btn-input.active,.btn-score.active{background:var(--scorer-selected-bg,#0e7490);color:var(--scorer-selected-text,#fff);border-color:var(--scorer-selected-bg,#0e7490)}.input-matrix{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:1fr 1fr .6fr;gap:6px;flex:1}.btn-score{font-size:32px}.btn-score:nth-child(7){grid-column:1/-1;font-size:18px}.btn-score-4{color:var(--scorer-boundary-four-text,#166534)}.btn-score-6{color:var(--scorer-boundary-six-text,#1e40af)}.action-row{height:38px}.wicket-toggle,.btn-submit{flex:1;display:flex;align-items:center;justify-content:center;border-radius:6px;font-weight:800;cursor:pointer}.wicket-toggle{border:2px solid #dc2626;color:#b91c1c;background:#fee2e2}.wicket-toggle.checked{background:#dc2626;color:#fff}.btn-submit{flex:2;border:0;background:#15803d;color:#fff}.wicket-details{display:flex;align-items:center;gap:8px;background:#fee2e2;padding:8px;border-radius:6px}.wicket-details select{min-width:0}.dismissal-batters{font-size:12px;color:#475569}.undo-row{text-align:center}.btn-undo{border:0;background:none;color:var(--color-text-secondary,#475569);text-decoration:underline;cursor:pointer}.btn-input:disabled,.btn-score:disabled,.btn-submit:disabled,.wicket-toggle.disabled{cursor:not-allowed;opacity:.65}
</style>
