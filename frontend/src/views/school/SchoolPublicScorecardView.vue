<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import cricksyLogo from '@/assets/logo.png';
import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';
import { getErrorMessage } from '@/services/api';
import { getPublicCompetitionScorecard, getPublicSchoolScorecard } from '@/services/schoolAdminApi';
import type { PublicOpaqueSchoolScorecard, PublicSchoolScorecard } from '@/types/schoolAdmin';

const props = defineProps<{ gameId?: string; publicIdentifier?: string; competitionPublicKey?: string; scorecardPublicIdentifier?: string }>();
const scorecard = ref<(PublicSchoolScorecard | PublicOpaqueSchoolScorecard) | null>(null);
const loading = ref(true);
const error = ref('');
const freshness = ref<'current' | 'refreshing' | 'stale'>('current');
const lastUpdated = ref<Date | null>(null);
const refreshing = ref(false);
const refreshInterval = 120_000;
let refreshTimer: ReturnType<typeof window.setInterval> | undefined;
let inFlight = false;
let requestVersion = 0;
const canonicalSharePath = computed(() => (
  props.publicIdentifier && props.competitionPublicKey && props.scorecardPublicIdentifier
    ? `/community/${props.publicIdentifier}/competitions/${props.competitionPublicKey}/scorecards/${props.scorecardPublicIdentifier}`
    : null
));

const routeKey = () => [props.gameId, props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier].join('\u001f');

function stopPolling() {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer);
  refreshTimer = undefined;
}

function lastUpdatedLabel() {
  return lastUpdated.value ? lastUpdated.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
}

async function load({ background = false } = {}) {
  if (inFlight) return;
  const requestedRoute = routeKey();
  const version = ++requestVersion;
  inFlight = true;
  refreshing.value = true;
  if (!background || !scorecard.value) loading.value = true;
  else freshness.value = 'refreshing';
  error.value = '';
  try {
    const nextScorecard = props.scorecardPublicIdentifier && props.publicIdentifier && props.competitionPublicKey
      ? await getPublicCompetitionScorecard(props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier)
      : await getPublicSchoolScorecard(props.gameId || '');
    if (version !== requestVersion || requestedRoute !== routeKey()) return;
    scorecard.value = nextScorecard;
    lastUpdated.value = new Date();
    freshness.value = 'current';
  } catch (reason) {
    if (version !== requestVersion || requestedRoute !== routeKey()) return;
    const status = (reason as { status?: number })?.status;
    if (status === 404) {
      scorecard.value = null;
      lastUpdated.value = null;
      freshness.value = 'current';
      error.value = 'This scorecard is not published or is no longer available.';
      stopPolling();
    } else if (scorecard.value) {
      freshness.value = 'stale';
      error.value = 'Live updates are temporarily unavailable. Showing the last verified score; retrying automatically.';
    } else {
      error.value = getErrorMessage(reason);
    }
  } finally {
    if (version === requestVersion) {
      loading.value = false;
      inFlight = false;
      refreshing.value = false;
    }
  }
}

function startPolling() {
  stopPolling();
  if (document.visibilityState === 'hidden') return;
  refreshTimer = window.setInterval(() => void load({ background: true }), refreshInterval);
}

function onVisibilityChange() {
  if (document.visibilityState === 'hidden') stopPolling();
  else {
    void load({ background: true });
    startPolling();
  }
}

onMounted(() => {
  void load();
  startPolling();
  document.addEventListener('visibilitychange', onVisibilityChange);
});
watch(() => routeKey(), () => {
  requestVersion += 1;
  inFlight = false;
  scorecard.value = null;
  lastUpdated.value = null;
  freshness.value = 'current';
  void load();
  startPolling();
});
onBeforeUnmount(() => {
  requestVersion += 1;
  stopPolling();
  document.removeEventListener('visibilitychange', onVisibilityChange);
});
</script>

<template>
  <main class="public-scorecard">
    <p v-if="loading" role="status">Loading published scorecard…</p>
    <section v-else-if="error && !scorecard" class="notice error" role="alert">
      <h1>Scorecard unavailable</h1>
      <p>{{ error }}</p>
    </section>
    <template v-else-if="scorecard">
      <header>
        <p class="eyebrow">Published scorecard</p>
        <h1>{{ scorecard.team_a.name }} vs {{ scorecard.team_b.name }}</h1>
        <p>{{ scorecard.status }} · {{ scorecard.publication_state.replace('_', ' ') }}</p>
      </header>
      <section class="score-summary">
        <strong>{{ scorecard.batting_team_name || 'Current innings' }}</strong>
        <span>{{ scorecard.total_runs }}/{{ scorecard.total_wickets }}</span>
        <span>{{ scorecard.overs_completed }}.{{ scorecard.balls_this_over }} overs</span>
      </section>
      <p class="freshness" :class="freshness" role="status">
        <template v-if="freshness === 'refreshing'">Refreshing live score…</template>
        <template v-else-if="freshness === 'stale'">Last verified update {{ lastUpdatedLabel() }}. Retrying automatically.</template>
        <template v-else>Last updated {{ lastUpdatedLabel() }}. This page checks for changes every 2 minutes while open.</template>
      </p>
      <button type="button" class="refresh-now" :disabled="refreshing" @click="load({ background: true })">
        {{ refreshing ? 'Refreshing…' : 'Refresh now' }}
      </button>
      <p v-if="scorecard.result" class="result">{{ scorecard.result }}</p>
      <PublicShareLinkButton v-if="canonicalSharePath" :path="canonicalSharePath" label="Copy scorecard link" />
      <div class="tables">
        <section>
          <h2>Batting</h2>
          <table>
            <thead>
              <tr>
                <th>Player</th>
                <th>R</th>
                <th>B</th>
                <th>4s</th>
                <th>6s</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scorecard.batting_scorecard" :key="row.player_name">
                <td>
                  {{ row.player_name }}<small v-if="row.how_out"> {{ row.how_out }}</small>
                </td>
                <td>{{ row.runs ?? '—' }}</td>
                <td>{{ row.balls_faced ?? '—' }}</td>
                <td>{{ row.fours ?? '—' }}</td>
                <td>{{ row.sixes ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
        <section>
          <h2>Bowling</h2>
          <table>
            <thead>
              <tr>
                <th>Player</th>
                <th>O</th>
                <th>R</th>
                <th>W</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scorecard.bowling_scorecard" :key="row.player_name">
                <td>{{ row.player_name }}</td>
                <td>{{ row.overs_bowled ?? '—' }}</td>
                <td>{{ row.runs_conceded ?? '—' }}</td>
                <td>{{ row.wickets_taken ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <p class="privacy-note">
        This public view contains only published cricket information.
        <template v-if="scorecard.organization_type === 'club'">
          Club membership and private player metadata are not displayed.
        </template>
        <template v-else> School membership and student metadata are not displayed. </template>
      </p>
      <aside class="support-slot" aria-label="Supported by Cricksy">
        <span>Supported by</span>
        <img :src="cricksyLogo" alt="Cricksy" />
        <strong>Cricksy</strong>
      </aside>
    </template>
  </main>
</template>

<style scoped>
.public-scorecard {
  max-width: 980px;
  margin: 2rem auto;
  padding: 1rem;
  color: #eef2ff;
}
.freshness { margin: 0.8rem 0; color: #526174; font-size: 0.9rem; }
.freshness.stale { color: #8a5500; }
.refresh-now { margin: 0 0 1rem; }
.support-slot { display: flex; align-items: center; gap: 0.55rem; margin-top: 1.5rem; padding: 0.75rem 1rem; border-top: 1px solid #d5dde7; color: #526174; font-size: 0.9rem; }
.support-slot img { width: 26px; height: 26px; object-fit: contain; }
.support-slot strong { color: #172033; }
@media (max-width: 520px) { .support-slot { align-items: flex-start; flex-wrap: wrap; } }
header,
.score-summary,
.tables section,
.notice {
  padding: 1.2rem;
  border: 1px solid #3b4768;
  border-radius: 12px;
  background: #171e30;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.score-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1rem;
  margin: 1rem 0;
  font-size: 1.2rem;
}
.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}
table {
  width: 100%;
}
small {
  display: block;
  color: #aebbd7;
}
.result,
.privacy-note {
  padding: 0.8rem;
  border-left: 4px solid #70d7b0;
  background: #20283d;
}
.error {
  border-color: #d56b6b;
}
</style>
