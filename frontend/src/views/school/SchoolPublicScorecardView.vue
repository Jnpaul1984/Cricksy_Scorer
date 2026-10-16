<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import cricksyLogo from '@/assets/optimized/logo-w480.webp';
import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';
import { getErrorMessage } from '@/services/api';
import { getPublicCompetitionScorecard, getPublicPracticeScorecard, getPublicSchoolScorecard } from '@/services/schoolAdminApi';
import type { PublicOpaqueSchoolScorecard, PublicSchoolScorecard } from '@/types/schoolAdmin';
import { youtubeVideoUrls } from '@/utils/youtubeVideo';

const props = defineProps<{ gameId?: string; publicIdentifier?: string; competitionPublicKey?: string; scorecardPublicIdentifier?: string; overlay?: boolean; practice?: boolean }>();
const scorecard = ref<(PublicSchoolScorecard | PublicOpaqueSchoolScorecard) | null>(null);
const loading = ref(true);
const error = ref('');
const freshness = ref<'current' | 'refreshing' | 'stale'>('current');
const lastUpdated = ref<Date | null>(null);
const refreshing = ref(false);
const refreshInterval = 120_000;
const overlayRefreshInterval = 12_000;
const finalOverlayRefreshInterval = 300_000;
const maxOverlayRefreshInterval = 60_000;
const offline = ref(false);
const activeVideoId = ref<string | null>(null);
let refreshTimer: ReturnType<typeof window.setInterval> | undefined;
let overlayRefreshTimer: ReturnType<typeof window.setTimeout> | undefined;
let inFlight = false;
let requestVersion = 0;
let transientFailures = 0;
let revoked = false;
let mounted = false;
const canonicalSharePath = computed(() => (
  props.publicIdentifier && props.competitionPublicKey && props.scorecardPublicIdentifier
    ? `/community/${props.publicIdentifier}/competitions/${props.competitionPublicKey}/scorecards/${props.scorecardPublicIdentifier}`
    : null
));
const overlaySharePath = computed(() => canonicalSharePath.value ? `${canonicalSharePath.value}/overlay` : null);
const youtubeVideoId = computed(() => {
  const current = scorecard.value;
  return current && 'youtube_video_id' in current && typeof current.youtube_video_id === 'string'
    ? current.youtube_video_id
    : null;
});
const youtubeUrls = computed(() => (
  !props.overlay && youtubeVideoId.value ? youtubeVideoUrls(youtubeVideoId.value) : null
));
const youtubePlayerActive = computed(() => (
  youtubeUrls.value !== null && activeVideoId.value === youtubeVideoId.value
));

const routeKey = () => [props.overlay, props.practice, props.gameId, props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier].join('\u001f');

function stopPolling() {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer);
  refreshTimer = undefined;
  if (overlayRefreshTimer !== undefined) window.clearTimeout(overlayRefreshTimer);
  overlayRefreshTimer = undefined;
}

function scheduleOverlayRefresh(delay: number) {
  if (overlayRefreshTimer !== undefined) window.clearTimeout(overlayRefreshTimer);
  overlayRefreshTimer = undefined;
  if (!props.overlay || !mounted || revoked || offline.value
    || document.visibilityState === 'hidden') return;
  overlayRefreshTimer = window.setTimeout(() => {
    overlayRefreshTimer = undefined;
    void load({ background: true });
  }, delay);
}

function lastUpdatedLabel() {
  return lastUpdated.value ? lastUpdated.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
}

async function load({ background = false } = {}) {
  if (inFlight) return;
  if (props.overlay && revoked) return;
  const requestedRoute = routeKey();
  const version = ++requestVersion;
  if (props.overlay) {
    if (overlayRefreshTimer !== undefined) window.clearTimeout(overlayRefreshTimer);
    overlayRefreshTimer = undefined;
    if (![props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier]
      .every(value => typeof value === 'string' && value.trim().length > 0)) {
      scorecard.value = null;
      loading.value = false;
      refreshing.value = false;
      error.value = 'This public scorecard link is incomplete or invalid.';
      revoked = true;
      stopPolling();
      return;
    }
  }
  inFlight = true;
  refreshing.value = true;
  if (!background || !scorecard.value) loading.value = true;
  else freshness.value = 'refreshing';
  error.value = '';
  try {
    const nextScorecard = props.overlay
      ? await getPublicCompetitionScorecard(props.publicIdentifier!, props.competitionPublicKey!, props.scorecardPublicIdentifier!)
      : props.scorecardPublicIdentifier && props.publicIdentifier && props.competitionPublicKey
      ? await getPublicCompetitionScorecard(props.publicIdentifier, props.competitionPublicKey, props.scorecardPublicIdentifier)
      : props.practice ? await getPublicPracticeScorecard(props.gameId || '') : await getPublicSchoolScorecard(props.gameId || '');
    if (version !== requestVersion || requestedRoute !== routeKey()) return;
    if (youtubeVideoIdFor(nextScorecard) !== youtubeVideoId.value) activeVideoId.value = null;
    scorecard.value = nextScorecard;
    lastUpdated.value = new Date();
    freshness.value = 'current';
    if (props.overlay) {
      transientFailures = 0;
      offline.value = false;
    }
  } catch (reason) {
    if (version !== requestVersion || requestedRoute !== routeKey()) return;
    const status = (reason as { status?: number })?.status;
    if (status === 404) {
      scorecard.value = null;
      activeVideoId.value = null;
      lastUpdated.value = null;
      freshness.value = 'current';
      error.value = 'This scorecard is not published or is no longer available.';
      if (props.overlay) revoked = true;
      stopPolling();
    } else if (scorecard.value) {
      freshness.value = 'stale';
      if (props.overlay) {
        transientFailures += 1;
        offline.value = typeof navigator !== 'undefined' && navigator.onLine === false;
        error.value = offline.value
          ? 'The browser is offline. Showing the last verified score until the connection returns.'
          : 'Live updates are temporarily unavailable. Showing the last verified score; retrying automatically.';
      } else {
        error.value = 'Live updates are temporarily unavailable. Showing the last verified score; retrying automatically.';
      }
    } else if (props.overlay) {
      transientFailures += 1;
      offline.value = typeof navigator !== 'undefined' && navigator.onLine === false;
      error.value = offline.value
        ? 'The browser is offline. The score will load when a connection returns.'
        : 'The published score is temporarily unavailable. Retrying automatically.';
    } else {
      error.value = getErrorMessage(reason);
    }
  } finally {
    if (props.overlay) {
      inFlight = false;
      if (version === requestVersion) {
        loading.value = false;
        refreshing.value = false;
      }
      if (mounted && !revoked) {
        if (requestedRoute !== routeKey()) {
          void load();
        } else {
          const delay = scorecard.value?.publication_state === 'published_final'
            ? finalOverlayRefreshInterval
            : transientFailures
              ? Math.min(overlayRefreshInterval * (2 ** transientFailures), maxOverlayRefreshInterval)
              : overlayRefreshInterval;
          scheduleOverlayRefresh(delay);
        }
      }
    } else if (version === requestVersion) {
      loading.value = false;
      inFlight = false;
      refreshing.value = false;
    }
  }
}

function startPolling() {
  if (props.overlay) {
    scheduleOverlayRefresh(overlayRefreshInterval);
    return;
  }
  stopPolling();
  if (document.visibilityState === 'hidden') return;
  refreshTimer = window.setInterval(() => void load({ background: true }), refreshInterval);
}

function youtubeVideoIdFor(value: PublicSchoolScorecard | PublicOpaqueSchoolScorecard): string | null {
  return 'youtube_video_id' in value && typeof value.youtube_video_id === 'string'
    ? value.youtube_video_id
    : null;
}

function activateYoutubePlayer() {
  if (youtubeUrls.value && youtubeVideoId.value) activeVideoId.value = youtubeVideoId.value;
}

function onVisibilityChange() {
  if (document.visibilityState === 'hidden') stopPolling();
  else if (props.overlay) {
    if (!revoked) void load({ background: true });
  } else {
    void load({ background: true });
    startPolling();
  }
}

function onOffline() {
  if (!props.overlay || revoked) return;
  offline.value = true;
  if (scorecard.value) freshness.value = 'stale';
  error.value = 'The browser is offline. Showing the last verified score until the connection returns.';
  stopPolling();
}

function onOnline() {
  if (!props.overlay) return;
  offline.value = false;
  if (!revoked) void load({ background: true });
}

onMounted(() => {
  mounted = true;
  offline.value = typeof navigator !== 'undefined' && navigator.onLine === false;
  void load();
  startPolling();
  document.addEventListener('visibilitychange', onVisibilityChange);
  if (props.overlay) {
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
  }
});
watch(() => routeKey(), () => {
  requestVersion += 1;
  if (!props.overlay) inFlight = false;
  stopPolling();
  transientFailures = 0;
  revoked = false;
  offline.value = typeof navigator !== 'undefined' && navigator.onLine === false;
  scorecard.value = null;
  activeVideoId.value = null;
  lastUpdated.value = null;
  freshness.value = 'current';
  void load();
  startPolling();
});
onBeforeUnmount(() => {
  mounted = false;
  requestVersion += 1;
  stopPolling();
  document.removeEventListener('visibilitychange', onVisibilityChange);
  window.removeEventListener('offline', onOffline);
  window.removeEventListener('online', onOnline);
});
</script>

<template>
  <main class="public-scorecard" :class="{ 'public-scorecard--overlay': overlay }">
    <p v-if="loading" role="status">{{ overlay ? 'Loading published live score…' : practice ? 'Loading published practice scorecard…' : 'Loading published scorecard…' }}</p>
    <section v-else-if="error && !scorecard" class="notice error" role="alert">
      <h1>{{ overlay ? 'Scoreboard unavailable' : practice ? 'Practice scorecard unavailable' : 'Scorecard unavailable' }}</h1>
      <p>{{ error }}</p>
    </section>
    <template v-else-if="scorecard && overlay">
      <section class="obs-scoreboard" aria-label="OBS team scoreboard">
        <header class="obs-heading">
          <p class="eyebrow">{{ scorecard.publication_state === 'published_final' ? 'Final score' : 'Live score' }} · {{ scorecard.organization_type }}</p>
          <span>Innings {{ scorecard.current_inning }} · {{ scorecard.status.replace('_', ' ') }}</span>
        </header>
        <div class="obs-teams">
          <div>
            <span>Team A</span>
            <strong>{{ scorecard.team_a.name }}</strong>
            <small v-if="scorecard.batting_team_name === scorecard.team_a.name">Batting</small>
          </div>
          <section class="obs-innings" aria-label="Current innings score">
            <span>{{ scorecard.batting_team_name ? 'Batting' : 'Current innings' }}</span>
            <strong>{{ scorecard.total_runs }}/{{ scorecard.total_wickets }}</strong>
            <span>Overs {{ scorecard.overs_completed }}.{{ scorecard.balls_this_over }}</span>
          </section>
          <div>
            <span>Team B</span>
            <strong>{{ scorecard.team_b.name }}</strong>
            <small v-if="scorecard.batting_team_name === scorecard.team_b.name">Batting</small>
          </div>
        </div>
        <p v-if="scorecard.result" class="obs-result">{{ scorecard.result }}</p>
        <div class="obs-status">
          <p class="freshness" :class="{ stale: freshness === 'stale' || offline }" role="status">
            <template v-if="offline">Offline<template v-if="lastUpdated"> · last verified {{ lastUpdatedLabel() }}</template></template>
            <template v-else-if="freshness === 'stale'">Stale · last verified {{ lastUpdatedLabel() }}</template>
            <template v-else-if="freshness === 'refreshing'">Refreshing score…</template>
            <template v-else-if="scorecard.publication_state === 'published_final'">Final result · rechecked every 5 minutes · last verified {{ lastUpdatedLabel() }}</template>
            <template v-else>Last verified {{ lastUpdatedLabel() }} · checks every 12 seconds while visible</template>
          </p>
          <button type="button" class="refresh-now" :disabled="refreshing || revoked" @click="load({ background: true })">
            {{ refreshing ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>
      </section>
    </template>
    <template v-else-if="scorecard">
      <header>
        <p class="eyebrow">{{ practice ? 'Published practice scorecard' : 'Published scorecard' }}</p>
        <h1>{{ scorecard.team_a.name }} vs {{ scorecard.team_b.name }}</h1>
        <p>{{ scorecard.status }} · {{ scorecard.publication_state.replace('_', ' ') }}</p>
      </header>
      <section class="score-summary">
        <strong>{{ scorecard.batting_team_name || 'Current innings' }}</strong>
        <span>{{ scorecard.total_runs }}/{{ scorecard.total_wickets }}</span>
        <span>{{ scorecard.overs_completed }}.{{ scorecard.balls_this_over }} overs</span>
      </section>
      <section v-if="youtubeUrls" class="youtube-player" aria-labelledby="youtube-video-heading">
        <h2 id="youtube-video-heading">Associated YouTube video</h2>
        <p v-if="!youtubePlayerActive" id="youtube-player-help">
          Choose to load the video. The player is not contacted until you activate it.
        </p>
        <button
          v-if="!youtubePlayerActive"
          type="button"
          aria-describedby="youtube-player-help"
          @click="activateYoutubePlayer"
        >
          Load YouTube video
        </button>
        <div v-else class="youtube-frame">
          <iframe
            :src="youtubeUrls.embedUrl"
            title="Associated YouTube video"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="encrypted-media; picture-in-picture; fullscreen"
            allowfullscreen
          />
        </div>
        <a :href="youtubeUrls.watchUrl" target="_blank" rel="noopener noreferrer">
          Watch on YouTube
        </a>
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
      <PublicShareLinkButton v-if="overlaySharePath" :path="overlaySharePath" label="Copy OBS overlay link" />
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
.public-scorecard--overlay {
  max-width: none;
  margin: 0;
  padding: 0;
  color: #f8fafc;
  background: transparent;
}
.obs-scoreboard {
  width: 100%;
  max-width: 960px;
  min-height: 0;
  margin: 0 auto;
  padding: clamp(0.4rem, 1.4vw, 0.8rem);
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.94);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
  font-variant-numeric: tabular-nums;
}
.obs-scoreboard header {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
.obs-heading,
.obs-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.obs-heading .eyebrow { margin: 0; font-size: 0.72rem; }
.obs-heading > span,
.obs-teams > div > span { color: #cbd5e1; font-size: 0.78rem; text-transform: uppercase; }
.obs-heading > span { text-align: right; }
.obs-teams {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.45rem;
  margin: 0.3rem 0;
}
.obs-teams > div { min-width: 0; display: grid; gap: 0.1rem; }
.obs-teams > div:last-child { text-align: right; }
.obs-teams strong { overflow-wrap: anywhere; font-size: clamp(0.9rem, 2.4vw, 1.25rem); line-height: 1.15; }
.obs-teams small { color: #70d7b0; font-weight: 700; }
.obs-innings {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.05rem;
  margin: 0;
  padding: 0.15rem 0.35rem;
  border-radius: 8px;
  background: rgba(51, 65, 85, 0.72);
}
.obs-innings span { color: #cbd5e1; font-size: 0.68rem; line-height: 1.1; }
.obs-innings strong { font-size: clamp(1.3rem, 4vw, 2rem); line-height: 1.05; }
.obs-result { margin: 0.2rem 0 0; font-size: 0.82rem; line-height: 1.2; }
.obs-result { color: #86efac; font-weight: 700; }
.obs-status { margin-top: 0.2rem; }
.freshness { margin: 0.8rem 0; color: #aebbd7; font-size: 0.9rem; }
.freshness.stale { color: #ffd08a; }
.obs-status p.freshness { margin: 0; font-size: 0.67rem; line-height: 1.15; }
.obs-status .refresh-now { margin: 0; padding: 0.2rem 0.55rem; font-size: 0.75rem; }
.public-scorecard--overlay .notice {
  padding: 0.75rem;
  color: #f8fafc;
}
.public-scorecard--overlay .notice h1,
.public-scorecard--overlay .notice p {
  color: #f8fafc;
}
.public-scorecard--overlay .notice h1 {
  margin: 0 0 0.35rem;
  font-size: 1.25rem;
}
.public-scorecard--overlay .notice p { margin: 0; }
@media (max-width: 520px) {
  .obs-scoreboard { padding: 0.4rem; }
  .obs-teams { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 0.25rem; }
  .obs-teams > div > span { font-size: 0.65rem; }
}
.refresh-now { margin: 0 0 1rem; }
.support-slot { display: flex; align-items: center; gap: 0.55rem; margin-top: 1.5rem; padding: 0.75rem 1rem; border-top: 1px solid #d5dde7; color: #aebbd7; font-size: 0.9rem; }
.support-slot img { width: 26px; height: 26px; object-fit: contain; }
.support-slot strong { color: #eef2ff; }
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
.youtube-player {
  display: grid;
  justify-items: start;
  gap: 0.6rem;
  margin: 1rem 0;
}
.youtube-player h2,
.youtube-player p {
  margin: 0;
}
.youtube-frame {
  width: 100%;
  aspect-ratio: 16 / 9;
}
.youtube-frame iframe {
  width: 100%;
  height: 100%;
  border: 0;
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
