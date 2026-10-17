<script setup lang="ts">
import { computed, ref } from 'vue';
import BroadcastScorerFrame from './BroadcastScorerFrame.vue';
import SharedFieldMap from './SharedFieldMap.vue';

type Extra = 'none' | 'wd' | 'nb' | 'b' | 'lb';
const props = defineProps<{
  status: string; totalRuns: number; totalWickets: number; overs: string; inning: number; target: number | null;
  strikerName: string; nonStrikerName: string; bowlerName: string; canScore: boolean; needsNextOver: boolean; loading: boolean;
  publicationState: 'private' | 'published_live' | 'published_final'; canPublish: boolean; publicHref: string; fieldZone: number | null;
}>();
const emit = defineEmits<{
  (event: 'delivery', value: { runs: number; extra: Exclude<Extra, 'none'> | null; isWicket: boolean; dismissal: string; dismissed: 'striker' | 'non_striker'; fieldZone: number | null }): void;
  (event: 'undo'): void; (event: 'start-over'): void; (event: 'start-innings'): void; (event: 'reload'): void;
  (event: 'update:fieldZone', value: number | null): void; (event: 'publication', state: 'private' | 'published_live'): void;
}>();
const extra = ref<Extra>('none');
const runs = ref(0); const wicket = ref(false); const dismissal = ref('bowled'); const dismissed = ref<'striker' | 'non_striker'>('striker');
const isPublished = computed(() => props.publicationState !== 'private');
const canSubmit = computed(() => props.canScore && !props.loading && (extra.value !== 'wd' || runs.value >= 1));
function submit() {
  if (!canSubmit.value) return;
  emit('delivery', { runs: runs.value, extra: extra.value === 'none' ? null : extra.value, isWicket: wicket.value, dismissal: dismissal.value, dismissed: dismissed.value, fieldZone: (extra.value === 'none' || extra.value === 'nb') ? props.fieldZone : null });
}
</script>

<template>
  <BroadcastScorerFrame>
    <header class="broadcast-header">
      <div class="header-left"><div class="brand">CRICKSY</div><div class="game-meta">PRACTICE</div></div>
      <div class="header-center dense-stats"><div class="stat-group main-score"><span class="team-name">Practice innings {{ props.inning }}</span><span class="score-display">{{ props.totalRuns }}/{{ props.totalWickets }}</span><span class="overs-display">({{ props.overs }})</span></div><div class="stat-divider" /><div class="stat-group rates"><span class="rate-item">PRIVATE PRACTICE</span><span v-if="props.target !== null" class="rate-item">Target: <strong>{{ props.target }}</strong></span></div></div>
      <div class="header-right"><span class="practice-tag">PRIVATE</span></div>
    </header>
    <section class="player-bar">
      <div class="player-box striker-box"><div class="pb-label">STRIKER</div><div class="pb-select-full">{{ props.strikerName }}</div></div>
      <div class="player-box non-striker-box"><div class="pb-label">NON-STRIKER</div><div class="pb-select-full">{{ props.nonStrikerName }}</div></div>
      <div class="player-box bowler-box"><div class="pb-label">BOWLER</div><div class="pb-select-full">{{ props.bowlerName }}</div></div>
    </section>
    <main class="broadcast-main">
      <div class="panel scoring-panel">
        <div v-if="props.status !== 'in_progress' || props.needsNextOver" class="gate-overlay"><div class="gate-card"><span class="gate-eyebrow">Practice action</span><h3>{{ props.status === 'started' ? 'Ready to Start' : props.needsNextOver ? 'End of Over' : 'Innings Break' }}</h3><button class="btn-gate" type="button" :disabled="props.loading" @click="props.needsNextOver ? emit('start-over') : emit('start-innings')">{{ props.needsNextOver ? 'Start Next Over' : 'Start Innings' }}</button></div></div>
        <div class="scoring-grid-inputs scorer-controls" :class="{ 'scorer-controls--disabled': !props.canScore }" data-testid="practice-shared-scorer">
          <div class="input-row extras-row"><button v-for="kind in ['none', 'wd', 'nb', 'b', 'lb'] as Extra[]" :key="kind" type="button" class="btn-input" :data-testid="`delivery-extra-${kind === 'none' ? 'legal' : kind}`" :class="[{ active: extra === kind }, `btn-extra-${kind}`]" :disabled="!props.canScore || props.loading" @click="extra = kind">{{ kind === 'none' ? 'LEGAL' : kind.toUpperCase() }}</button></div>
          <div class="input-matrix"><button v-for="run in [0, 1, 2, 3, 4, 6, 5]" :key="run" type="button" class="btn-score" :data-testid="`delivery-run-${run}`" :class="[`btn-score-${run}`, { active: runs === run }]" :disabled="!props.canScore || props.loading" @click="runs = run">{{ run }}</button></div>
          <div class="input-row action-row"><label class="wicket-toggle" :class="{ checked: wicket, disabled: !props.canScore }"><input data-testid="delivery-wicket" type="checkbox" v-model="wicket" :disabled="!props.canScore || props.loading"> WICKET</label><button data-testid="submit-delivery" type="button" class="btn-submit" :disabled="!canSubmit" @click="submit">SUBMIT</button></div>
          <div v-if="wicket" class="wicket-details"><select v-model="dismissal"><option v-for="option in ['bowled', 'caught', 'lbw', 'run_out', 'stumped']" :key="option" :value="option">{{ option.replace('_', ' ') }}</option></select><select v-model="dismissed"><option value="striker">{{ props.strikerName }}</option><option value="non_striker">{{ props.nonStrikerName }}</option></select></div>
          <div class="undo-row"><button data-testid="undo-ball" type="button" class="btn-undo" :disabled="props.loading" @click="emit('undo')">UNDO LAST</button></div>
        </div>
      </div>
      <div class="panel map-panel"><div class="recent-strip"><div class="recent-label">LAST 6 <span class="active-ball-text">(Over {{ props.overs }})</span></div><div class="recent-balls"><span v-for="slot in 6" :key="slot" class="ball-badge empty">–</span></div></div><SharedFieldMap :model-value="props.fieldZone" :disabled="!props.canScore || props.loading" @update:model-value="emit('update:fieldZone', $event)" /></div>
    </main>
    <footer class="broadcast-footer"><div class="tabs-nav"><button class="active">RECENT</button><button> BATTING</button><button>BOWLING</button><button>EVENT LOG</button></div><div class="tab-content"><div class="tab-pane"><p>Practice deliveries are private to this organization. Field zones stay in the private practice ledger.</p></div><div class="practice-publication"><strong>{{ isPublished ? 'Practice scorecard published' : 'Private by default' }}</strong><a v-if="isPublished" :href="props.publicHref" data-testid="public-practice-link">View published practice scorecard</a><button v-if="props.canPublish && !isPublished" data-testid="publish-practice" type="button" @click="emit('publication', 'published_live')">Publish practice scorecard</button><button v-else-if="props.canPublish" data-testid="unpublish-practice" type="button" @click="emit('publication', 'private')">Keep private</button><button type="button" @click="emit('reload')">Reload private state</button></div></div></footer>
  </BroadcastScorerFrame>
</template>

<style scoped>
.broadcast-header{height:64px;background:#192735;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 18px}.header-left,.header-center,.header-right,.dense-stats,.stat-group,.player-bar,.recent-balls{display:flex;align-items:center}.brand{font-weight:900;letter-spacing:.12em}.game-meta,.practice-tag{font-size:11px;margin-left:10px;color:#d8e6f0}.header-center{gap:14px}.main-score{gap:7px}.team-name,.rate-item{font-size:12px;color:#d8e6f0}.score-display{font-size:24px;font-weight:800}.overs-display{font-size:13px}.stat-divider{height:28px;border-left:1px solid #50606e}.practice-tag{border:1px solid #93c5fd;border-radius:999px;padding:4px 8px}.player-bar{background:#223342;gap:8px;padding:8px 12px}.player-box{flex:1;min-width:0}.pb-label{font-size:10px;font-weight:800;letter-spacing:.08em;color:#b9c9d5}.pb-select-full{background:#fff;color:#172534;border-radius:6px;padding:8px 10px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.broadcast-main{display:grid;grid-template-columns:320px minmax(0,1fr);flex:1;min-height:380px}.panel{min-height:0}.scoring-panel{position:relative;padding:12px;background:var(--color-surface-raised,#fff)}.map-panel{background:var(--color-surface-raised,#fff);display:flex;flex-direction:column;border-left:1px solid var(--color-border,#ccd)}.scoring-grid-inputs{display:flex;flex-direction:column;gap:8px;height:100%}.input-row{display:flex;gap:6px}.extras-row{height:36px}.btn-input,.btn-score{flex:1;border:1px solid #aab7c4;background:#fff;color:#152535;border-radius:6px;font-weight:700;cursor:pointer}.btn-input.active,.btn-score.active{background:#2563eb;color:#fff;border-color:#2563eb}.input-matrix{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:1fr 1fr .6fr;gap:6px;flex:1}.btn-score{font-size:32px}.btn-score:nth-child(7){grid-column:1/-1;font-size:18px}.btn-score-4{color:#166534}.btn-score-6{color:#1d4ed8}.action-row{height:38px}.wicket-toggle,.btn-submit{flex:1;display:flex;align-items:center;justify-content:center;border-radius:6px;font-weight:800;cursor:pointer}.wicket-toggle{border:2px solid #dc2626;color:#b91c1c;background:#fee2e2}.wicket-toggle.checked{background:#dc2626;color:#fff}.btn-submit{flex:2;border:0;background:#15803d;color:#fff}.wicket-details{display:flex;gap:8px;background:#fee2e2;padding:8px;border-radius:6px}.wicket-details select{min-width:0;flex:1}.undo-row{text-align:center}.btn-undo{border:0;background:none;color:#475569;text-decoration:underline;cursor:pointer}.recent-strip{height:40px;padding:0 12px;gap:12px;border-bottom:1px solid #ccd}.recent-label{font-size:11px;font-weight:800;color:#334155}.active-ball-text{font-weight:400}.ball-badge{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;border:1px dashed #9aa;color:#64748b;font-size:12px}.broadcast-footer{background:#192735;color:#fff;border-top:1px solid #41515f;min-height:132px}.tabs-nav{display:flex;border-bottom:1px solid #41515f}.tabs-nav button{flex:1;border:0;background:transparent;color:#d8e6f0;padding:8px;cursor:pointer}.tabs-nav button.active{background:#223342;color:#fff;border-bottom:3px solid #60a5fa}.tab-content{padding:10px 12px;font-size:13px}.tab-pane p{margin:0;color:#d8e6f0}.practice-publication{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}.practice-publication a,.practice-publication button{font:inherit}.practice-publication button{border:1px solid #93c5fd;border-radius:5px;background:#fff;color:#17324d;padding:4px 7px}.gate-overlay{position:absolute;inset:12px;z-index:2;display:grid;place-items:center;background:#ffffffdc}.gate-card{max-width:280px;text-align:center;padding:18px;background:#fff;border:1px solid #b5c2ce;border-radius:10px;box-shadow:0 5px 20px #0002}.gate-eyebrow{font-size:10px;text-transform:uppercase;font-weight:800;color:#1d4ed8}.btn-gate{border:0;border-radius:6px;background:#2563eb;color:#fff;padding:10px 16px;font-weight:800}.scorer-controls--disabled{opacity:.7}.btn-input:disabled,.btn-score:disabled,.btn-submit:disabled,.wicket-toggle.disabled{cursor:not-allowed;opacity:.65}@media(max-width:768px){.broadcast-header{height:auto;min-height:64px;padding:9px;gap:8px}.header-center{flex-wrap:wrap}.rates{display:none}.player-bar{gap:5px;padding:7px}.pb-select-full{font-size:12px;padding:7px}.broadcast-main{grid-template-columns:1fr;grid-template-rows:330px 340px}.map-panel{border-left:0;border-top:1px solid #ccd}.broadcast-footer{min-height:150px}}
</style>
