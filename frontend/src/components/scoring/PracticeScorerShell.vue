<script setup lang="ts">
import { computed, ref } from 'vue';

const props = defineProps<{
  status: string; revision: number; totalRuns: number; totalWickets: number; overs: string; inning: number; target: number | null;
  strikerName: string; nonStrikerName: string; bowlerName: string; canScore: boolean; needsNextOver: boolean; loading: boolean; startLocked: boolean;
  publicationState: 'private' | 'published_live' | 'published_final'; canPublish: boolean; publicHref: string;
}>();
const emit = defineEmits<{
  (event: 'score', runs: number): void; (event: 'extra', extra: 'wd' | 'nb' | 'b' | 'lb', runs: number): void;
  (event: 'wicket', dismissal: { type: string; dismissed: 'striker' | 'non_striker' }): void; (event: 'undo'): void; (event: 'start-over'): void; (event: 'start-innings'): void; (event: 'reload'): void;
  (event: 'publication', state: 'private' | 'published_live'): void;
}>();
const extraRuns = ref(1);
const showWicket = ref(false);
const dismissalType = ref('bowled');
const dismissed = ref<'striker' | 'non_striker'>('striker');
const isPublished = computed(() => props.publicationState !== 'private');
const dismissalTypes = ['bowled', 'caught', 'lbw', 'stumped', 'run_out', 'hit_wicket', 'retired_out'];
</script>

<template>
  <section class="practice-scorer" data-testid="practice-familiar-scorer">
    <header class="scorer-header"><div class="brand-mark">CRICKSY</div><span class="practice-badge">PRACTICE SCORER</span><span class="revision">Revision {{ props.revision }}</span></header>
    <section class="scoreboard" aria-label="Practice score">
      <div><p class="eyebrow">Innings {{ props.inning }} · {{ props.status.replace('_', ' ') }}</p><div class="score"><strong>{{ props.totalRuns }}</strong><span>/</span><strong>{{ props.totalWickets }}</strong></div><p>Overs {{ props.overs }}<span v-if="props.target !== null"> · Target {{ props.target }}</span></p></div>
      <div class="progress"><span :class="{ live: props.status === 'in_progress' }">{{ props.status === 'in_progress' ? 'LIVE' : props.status.replace('_', ' ').toUpperCase() }}</span></div>
    </section>
    <section class="players" aria-label="Authorized current players">
      <article class="player striker"><small>STRIKER</small><strong>{{ props.strikerName }}</strong></article>
      <article class="player non-striker"><small>NON-STRIKER</small><strong>{{ props.nonStrikerName }}</strong></article>
      <article class="player bowler"><small>BOWLER</small><strong>{{ props.bowlerName }}</strong></article>
    </section>
    <template v-if="props.status === 'started'"><button class="primary" :disabled="props.loading || props.startLocked" data-testid="start-first-innings" @click="emit('start-innings')">Start first innings</button><button class="quiet" :disabled="props.loading" data-testid="reload-practice" @click="emit('reload')">Reload private state</button></template>
    <template v-else-if="props.status === 'innings_break'"><button class="primary" :disabled="props.loading" data-testid="start-second-innings" @click="emit('start-innings')">Start next innings</button></template>
    <template v-else-if="props.needsNextOver"><p class="prompt">Choose the next bowler below, then start the over.</p><button class="primary" :disabled="props.loading" data-testid="start-next-over" @click="emit('start-over')">Start next over</button></template>
    <section v-else class="controls" aria-label="Private practice scoring controls">
      <h3>Score this delivery</h3><div class="runs"><button v-for="runs in [0, 1, 2, 3, 4, 5, 6]" :key="runs" :data-testid="`score-${runs}`" :disabled="!props.canScore || props.loading" @click="emit('score', runs)">{{ runs }}</button></div>
      <div class="extra-amount"><label for="practice-extra-runs">Extra runs</label><select id="practice-extra-runs" v-model.number="extraRuns" :disabled="!props.canScore || props.loading" data-testid="extra-runs"><option v-for="runs in [1, 2, 3, 4, 5, 6]" :key="runs" :value="runs">{{ runs }}</option></select></div>
      <div class="extras"><button v-for="extra in ['wd', 'nb', 'b', 'lb'] as const" :key="extra" :data-testid="`extra-${extra}`" :disabled="!props.canScore || props.loading" @click="emit('extra', extra, extra === 'nb' ? extraRuns - 1 : extraRuns)">{{ extra.toUpperCase() }}</button></div>
      <div class="actions"><button class="wicket" data-testid="wicket" :disabled="!props.canScore || props.loading" @click="showWicket = true">Wicket</button><button class="undo" data-testid="undo-ball" :disabled="props.loading" @click="emit('undo')">Undo last ball</button></div>
      <div v-if="showWicket" class="wicket-dialog" role="dialog" aria-label="Record wicket"><h4>Record wicket</h4><label>Dismissal <select v-model="dismissalType"><option v-for="type in dismissalTypes" :key="type" :value="type">{{ type.replace('_', ' ') }}</option></select></label><fieldset><legend>Dismissed batter</legend><label><input v-model="dismissed" type="radio" value="striker"> {{ props.strikerName }}</label><label><input v-model="dismissed" type="radio" value="non_striker"> {{ props.nonStrikerName }}</label></fieldset><div><button class="quiet" type="button" @click="showWicket = false">Cancel</button><button class="wicket" type="button" data-testid="confirm-wicket" :disabled="!props.canScore || props.loading" @click="emit('wicket', { type: dismissalType, dismissed }); showWicket = false">Record wicket</button></div></div>
    </section>
    <section class="publication" aria-label="Practice publication"><p><strong>{{ isPublished ? 'Practice scorecard published' : 'Private by default' }}</strong> — practice results remain excluded from official scorecards and team statistics.</p><a v-if="isPublished" :href="props.publicHref" data-testid="public-practice-link">View published practice scorecard</a><template v-if="props.canPublish"><button v-if="!isPublished" class="publish" :disabled="props.loading" data-testid="publish-practice" @click="emit('publication', 'published_live')">Publish practice scorecard</button><button v-else class="quiet" :disabled="props.loading" data-testid="unpublish-practice" @click="emit('publication', 'private')">Keep private</button></template></section>
    <p class="scope-note">Practice supports complete run, extra, wicket, undo, innings and over scoring. Shot maps, commentary, fielder attribution, delivery correction and analytics require dedicated private contracts.</p>
  </section>
</template>

<style scoped>
.practice-scorer{max-width:66rem;margin:1rem auto;padding:1.25rem;background:#f4f7fb;color:#24364b;border-radius:16px}.scorer-header{display:flex;gap:.8rem;align-items:center;margin-bottom:1rem}.brand-mark{font-weight:900;letter-spacing:.12em;color:#0b5ed7}.practice-badge{background:#4f46e5;color:#fff;border-radius:999px;padding:.25rem .55rem;font-size:.72rem;font-weight:800}.revision{margin-left:auto;color:#64748b;font-size:.8rem}.scoreboard{background:linear-gradient(135deg,#1e293b,#334155);color:#fff;border-radius:12px;padding:1.4rem;display:flex;justify-content:space-between}.eyebrow{margin:0;color:#cbd5e1;text-transform:uppercase;font-size:.75rem}.score{font-size:3.2rem;line-height:1.1}.score strong:first-child{color:#4ade80}.score strong:last-child{color:#fb7185}.progress span{padding:.45rem .7rem;border-radius:999px;background:#64748b;font-size:.8rem;font-weight:800}.progress .live{background:#16a34a}.players{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin:1rem 0}.player{padding:1rem;background:#fff;border-left:4px solid #94a3b8;border-radius:8px;box-shadow:0 2px 8px #0f172a14}.player small{display:block;color:#64748b;margin-bottom:.3rem}.striker{border-color:#22c55e}.non-striker{border-color:#3b82f6}.bowler{border-color:#ef4444}.controls{background:#fff;padding:1rem;border-radius:10px}.controls h3{margin:0 0 .75rem}.runs,.extras,.actions{display:grid;gap:.5rem;margin:.6rem 0}.runs{grid-template-columns:repeat(7,1fr)}.extras{grid-template-columns:repeat(4,1fr)}button{border:0;border-radius:8px;padding:.75rem;background:#0ea5a4;color:#fff;font-weight:800;cursor:pointer}.runs button:nth-child(5),.runs button:nth-child(7){background:#e85d04}.extras button{background:#2563eb}.actions{grid-template-columns:1fr 1fr}.wicket{background:#dc2626}.undo,.quiet{background:#475569}.primary{background:#16a34a;margin-right:.5rem}.prompt,.scope-note{color:#64748b;font-size:.88rem}.scope-note{margin:1rem 0 0}button:disabled{opacity:.5;cursor:not-allowed}@media(max-width:640px){.players{grid-template-columns:1fr}.runs{grid-template-columns:repeat(4,1fr)}.score{font-size:2.4rem}}
.extra-amount{display:flex;align-items:center;gap:.5rem}.extra-amount select{padding:.35rem}.wicket-dialog{margin-top:.75rem;padding:1rem;border:1px solid #fecaca;border-radius:8px;background:#fff7f7}.wicket-dialog label,.wicket-dialog fieldset{display:block;margin:.5rem 0}.wicket-dialog select{margin-left:.5rem}.publication{margin-top:1rem;padding:.8rem;border-radius:8px;background:#e8f1ff;color:#1e3a5f}.publication p{margin:.1rem 0 .6rem}.publish{background:#16a34a}
</style>
