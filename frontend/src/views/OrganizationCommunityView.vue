<script setup lang="ts">
import { getActivePinia } from 'pinia';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import type { ComponentPublicInstance } from 'vue';
import { RouterLink } from 'vue-router';
import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';

import { organizationTerminology } from '@/composables/useOrganizationTerminology';
import {
  getPublicOrganizationCommunity,
  getPublicOrganizationLeaderboards,
  getPublicOrganizationSponsorPlacement,
  listAllMyPublicFavorites,
  recordPublicSponsorPlacementEvent,
  removeMyPublicFavorite,
  saveMyPublicFavorite,
} from '@/services/schoolAdminApi';
import type { PublicOrganizationSponsorPlacement } from '@/services/schoolAdminApi';
import { useAuthStore } from '@/stores/authStore';
import type { PublicAnonymousLeaderboards, PublicOrganizationCommunity } from '@/types/schoolAdmin';

const props = defineProps<{ publicIdentifier: string }>();
const activePinia = getActivePinia();
const auth = activePinia ? useAuthStore(activePinia) : { user: null };
const community = ref<PublicOrganizationCommunity | null>(null);
const favoriteId = ref<string | null>(null);
const competitionFavoriteIds = ref<Record<string, string>>({});
const favoriteError = ref('');
const sponsor = ref<PublicOrganizationSponsorPlacement | null>(null);
const leaderboards = ref<PublicAnonymousLeaderboards | null>(null);
const loading = ref(true);
const notFound = ref(false);
const logoFailed = ref(false);
let generation = 0;
let favoriteGeneration = 0;
let refreshTimer: ReturnType<typeof setInterval> | undefined;
const sponsorElement = ref<HTMLElement | null>(null);
const reportedCapabilities = new Set<string>();
const reportedDisplayKeys = new Set<string>();
let displayObserver: IntersectionObserver | null = null;
let lastDisplayEntry: IntersectionObserverEntry | null = null;

function eventId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `00000000-0000-4000-8000-${Date.now().toString(16).padStart(12, '0').slice(-12)}`;
}

function reportSponsorEvent(capability: string | undefined) {
  if (!capability || reportedCapabilities.has(capability)) return;
  reportedCapabilities.add(capability);
  // Reporting is anonymous and best-effort; public content never depends on it.
  void Promise.resolve(recordPublicSponsorPlacementEvent(capability, eventId())).catch(() => undefined);
}

function displayKey() {
  const placement = sponsor.value;
  const reportViewKey = placement?.reporting?.report_view_key;
  // Capabilities rotate on every polling response. The server-issued opaque
  // revision key is stable for the actual public placement and changes when
  // that placement is replaced; it never exposes a private placement ID.
  return reportViewKey ? `${props.publicIdentifier}\u001f${reportViewKey}` : null;
}

function reportDisplayIfEligible(entry: IntersectionObserverEntry | null) {
  if (document.visibilityState !== 'visible' || !entry?.isIntersecting || entry.intersectionRatio < 0.5) return;
  const key = displayKey();
  const capability = sponsor.value?.reporting?.display_capability;
  if (!key || !capability || reportedDisplayKeys.has(key)) return;
  reportedDisplayKeys.add(key);
  reportSponsorEvent(capability);
}

function clearDisplayObserver() {
  displayObserver?.disconnect();
  displayObserver = null;
  lastDisplayEntry = null;
  document.removeEventListener('visibilitychange', onDocumentVisibilityChange);
}

function onDocumentVisibilityChange() {
  reportDisplayIfEligible(lastDisplayEntry);
}

function observeSponsorDisplay() {
  clearDisplayObserver();
  if (!sponsorElement.value || !sponsor.value?.reporting?.display_capability || !window.IntersectionObserver) return;
  displayObserver = new window.IntersectionObserver((entries) => {
    lastDisplayEntry = entries[0] ?? null;
    reportDisplayIfEligible(lastDisplayEntry);
  }, { threshold: [0.5] });
  displayObserver.observe(sponsorElement.value);
  document.addEventListener('visibilitychange', onDocumentVisibilityChange);
}

// A function ref runs only once the sponsor has actually been rendered. This
// avoids treating a successful placement fetch as an impression.
function setSponsorElement(element: Element | ComponentPublicInstance | null) {
  sponsorElement.value = element instanceof HTMLElement ? element : null;
  if (sponsorElement.value) observeSponsorDisplay();
  else clearDisplayObserver();
}

const terminology = computed(() =>
  organizationTerminology(community.value?.organization_type || 'school'),
);

function formatDate(value: string | null) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

async function refreshFavorite() {
  const current = ++favoriteGeneration;
  const key = props.publicIdentifier;
  favoriteId.value = null;
  competitionFavoriteIds.value = {};
  if (!auth.user?.id) return;
  try {
    const favorites = await listAllMyPublicFavorites();
    if (current === favoriteGeneration && auth.user?.id && props.publicIdentifier === key) {
      favoriteId.value = favorites.find(item => item.subject_kind === 'organization' && item.public_key === key)?.id || null;
      competitionFavoriteIds.value = Object.fromEntries(
        favorites
          .filter(item => item.subject_kind === 'competition')
          .map(item => [item.public_key, item.id]),
      );
    }
  } catch { /* Private saved-state failures do not affect public content. */ }
}

async function toggleCompetitionFavorite(competitionPublicKey: string) {
  const current = favoriteGeneration;
  const organizationKey = props.publicIdentifier;
  favoriteError.value = '';
  try {
    const existingId = competitionFavoriteIds.value[competitionPublicKey];
    if (existingId) {
      await removeMyPublicFavorite(existingId);
      if (current === favoriteGeneration && props.publicIdentifier === organizationKey) {
        const next = { ...competitionFavoriteIds.value };
        delete next[competitionPublicKey];
        competitionFavoriteIds.value = next;
      }
    } else {
      const favorite = await saveMyPublicFavorite('competition', competitionPublicKey);
      if (current === favoriteGeneration && props.publicIdentifier === organizationKey) {
        competitionFavoriteIds.value = {
          ...competitionFavoriteIds.value,
          [competitionPublicKey]: favorite.id,
        };
      }
    }
  } catch {
    if (current === favoriteGeneration && props.publicIdentifier === organizationKey) {
      favoriteError.value = 'Sign in with an active staff membership to save public pages.';
    }
  }
}

async function toggleFavorite() {
  const key = props.publicIdentifier;
  const current = favoriteGeneration;
  favoriteError.value = '';
  try {
    if (favoriteId.value) {
      await removeMyPublicFavorite(favoriteId.value);
      if (current === favoriteGeneration && props.publicIdentifier === key) favoriteId.value = null;
    } else {
      const favorite = await saveMyPublicFavorite('organization', key);
      if (current === favoriteGeneration && props.publicIdentifier === key) favoriteId.value = favorite.id;
    }
  } catch {
    if (current === favoriteGeneration && props.publicIdentifier === key) favoriteError.value = 'Sign in with an active staff membership to save public pages.';
  }
}

async function load() {
  const currentGeneration = ++generation;
  const currentIdentifier = props.publicIdentifier;
  clearDisplayObserver();
  community.value = null;
  sponsor.value = null;
  leaderboards.value = null;
  notFound.value = false;
  logoFailed.value = false;
  loading.value = true;
  try {
    const response = await getPublicOrganizationCommunity(currentIdentifier);
    if (generation !== currentGeneration || props.publicIdentifier !== currentIdentifier) return;
    if (response.public_identifier !== currentIdentifier) {
      notFound.value = true;
      return;
    }
    community.value = response;
    if (auth.user?.id) void refreshFavorite();
    try {
      const leaderboardResponse = await getPublicOrganizationLeaderboards(currentIdentifier);
      if (generation !== currentGeneration || props.publicIdentifier !== currentIdentifier) return;
      leaderboards.value = leaderboardResponse;
    } catch {
      if (generation !== currentGeneration || props.publicIdentifier !== currentIdentifier) return;
      leaderboards.value = null;
    }
    try {
      const placement = await getPublicOrganizationSponsorPlacement(currentIdentifier);
      if (generation !== currentGeneration || props.publicIdentifier !== currentIdentifier) return;
      sponsor.value = placement;
    } catch {
      if (generation !== currentGeneration || props.publicIdentifier !== currentIdentifier) return;
      // An absent, revoked, or not-yet-approved placement is intentionally invisible.
      sponsor.value = null;
    }
  } catch {
    if (generation === currentGeneration && props.publicIdentifier === currentIdentifier) {
      notFound.value = true;
    }
  } finally {
    if (generation === currentGeneration && props.publicIdentifier === currentIdentifier) {
      loading.value = false;
    }
  }
}

watch(() => props.publicIdentifier, load, { immediate: true });
watch(() => auth.user?.id, () => { ++favoriteGeneration; favoriteId.value = null; competitionFavoriteIds.value = {}; favoriteError.value = ''; if (auth.user?.id && community.value?.public_identifier === props.publicIdentifier) void refreshFavorite(); }, { immediate: true });
// Takedown is checked at most every 30 seconds while this public page is open.
refreshTimer = setInterval(() => { void load(); }, 30_000);
onBeforeUnmount(() => { if (refreshTimer) clearInterval(refreshTimer); clearDisplayObserver(); });
</script>

<template>
  <main class="community-page">
    <p v-if="loading" class="page-state" role="status">Loading community page…</p>
    <section v-else-if="notFound" class="page-state" role="alert">
      <h1>Community page not found</h1>
      <p>This page is unavailable or private.</p>
      <RouterLink to="/landing">Return to Cricksy</RouterLink>
    </section>
    <template v-else-if="community">
      <header class="hero">
        <img
          v-if="community.branding.logo_url && !logoFailed"
          class="organization-logo"
          :src="community.branding.logo_url"
          :alt="community.branding.logo_alt_text"
          @error="logoFailed = true"
        />
        <span v-else class="logo-fallback" aria-hidden="true">
          {{ community.branding.fallback_text }}
        </span>
        <div>
          <p class="eyebrow">{{ terminology.kindLabel }} cricket community</p>
          <h1>{{ community.display_name }}</h1>
          <p>Public {{ terminology.kindLabelLower }} competitions, fixtures, results, and standings.</p>
          <PublicShareLinkButton :path="`/community/${community.public_identifier}`" label="Copy community link" />
          <button type="button" class="favorite-button" @click="toggleFavorite">{{ favoriteId ? 'Saved public page' : 'Save public page' }}</button>
          <p v-if="favoriteError" class="favorite-error" role="status">{{ favoriteError }}</p>
        </div>
      </header>
      <aside v-if="sponsor" :ref="setSponsorElement" class="sponsor-placement" aria-label="Organization sponsor">
        <span>Supported by</span>
        <a v-if="sponsor.sponsor_url" :href="sponsor.sponsor_url" rel="noopener noreferrer" target="_blank" @click="reportSponsorEvent(sponsor.reporting?.click_capability)">{{ sponsor.sponsor_name }}</a>
        <strong v-else>{{ sponsor.sponsor_name }}</strong>
      </aside>

      <section v-if="leaderboards && (leaderboards.runs.length || leaderboards.wickets.length)" class="leaderboards" aria-labelledby="leaderboards-title">
        <h2 id="leaderboards-title">Anonymous leaderboards</h2>
        <p>Final results from this community’s published competitions. Participant names are not shown.</p>
        <div class="leaderboard-grid">
          <section v-if="leaderboards.runs.length" aria-labelledby="runs-leaderboard-title">
            <h3 id="runs-leaderboard-title">Most runs</h3>
            <ol><li v-for="entry in leaderboards.runs" :key="`runs-${entry.participant_label}`"><span>{{ entry.rank }}. {{ entry.participant_label }}</span><strong>{{ entry.value }}</strong></li></ol>
          </section>
          <section v-if="leaderboards.wickets.length" aria-labelledby="wickets-leaderboard-title">
            <h3 id="wickets-leaderboard-title">Most wickets</h3>
            <ol><li v-for="entry in leaderboards.wickets" :key="`wickets-${entry.participant_label}`"><span>{{ entry.rank }}. {{ entry.participant_label }}</span><strong>{{ entry.value }}</strong></li></ol>
          </section>
        </div>
      </section>

      <section v-if="community.competitions.length" aria-labelledby="public-competitions-title">
        <h2 id="public-competitions-title">Public competitions</h2>
        <div class="competition-grid">
          <article v-for="competition in community.competitions" :key="`${competition.name}:${competition.start_date || ''}`" class="competition-card">
            <header>
              <p class="competition-status">{{ competition.status }} · {{ competition.tournament_type }}</p>
              <h3>{{ competition.name }}</h3>
              <RouterLink :to="`/community/${community.public_identifier}/competitions/${competition.public_key}`">Open competition</RouterLink>
              <button
                type="button"
                class="favorite-button competition-favorite-button"
                @click="toggleCompetitionFavorite(competition.public_key)"
              >{{ competitionFavoriteIds[competition.public_key] ? 'Saved competition' : 'Save competition' }}</button>
              <p v-if="competition.start_date || competition.end_date">
                <span v-if="competition.start_date">Starts {{ formatDate(competition.start_date) }}</span>
                <span v-if="competition.end_date"> · Ends {{ formatDate(competition.end_date) }}</span>
              </p>
            </header>

            <section v-if="competition.team_names.length" :aria-label="`${competition.name} teams`">
              <h4>Teams</h4>
              <ul class="team-list">
                <li v-for="teamName in competition.team_names" :key="teamName">{{ teamName }}</li>
              </ul>
            </section>

            <section v-if="competition.fixtures.length" :aria-label="`${competition.name} fixtures and results`">
              <h4>Fixtures and results</h4>
              <ul class="fixture-list">
                <li v-for="(fixture, index) in competition.fixtures" :key="`${fixture.team_a_name}:${fixture.team_b_name}:${fixture.scheduled_date || index}`">
                  <div>
                    <RouterLink :to="fixture.canonical_path"><strong>{{ fixture.team_a_name }} vs {{ fixture.team_b_name }}</strong></RouterLink>
                    <p v-if="fixture.scheduled_date">{{ formatDate(fixture.scheduled_date) }}</p>
                    <p v-if="fixture.venue">{{ fixture.venue }}</p>
                    <p>{{ fixture.result || fixture.game_status || fixture.fixture_status }}</p>
                  </div>
                  <RouterLink v-if="fixture.canonical_scorecard_path" :to="fixture.canonical_scorecard_path">
                    View published scorecard
                  </RouterLink>
                  <PublicShareLinkButton v-if="fixture.canonical_scorecard_path" :path="fixture.canonical_scorecard_path" label="Copy scorecard link" />
                  <RouterLink v-if="fixture.public_result_path" :to="fixture.public_result_path">View published result</RouterLink>
                  <PublicShareLinkButton :path="fixture.canonical_path" label="Copy fixture link" />
                </li>
              </ul>
            </section>

            <section v-if="competition.standings.length" :aria-label="`${competition.name} standings`">
              <h4>Standings</h4>
              <div class="table-scroll">
                <table>
                  <thead>
                    <tr><th scope="col">Team</th><th scope="col">P</th><th scope="col">W</th><th scope="col">L</th><th scope="col">D</th><th scope="col">Pts</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="standing in competition.standings" :key="standing.team_name">
                      <th scope="row">{{ standing.team_name }}</th>
                      <td>{{ standing.matches_played }}</td><td>{{ standing.matches_won }}</td><td>{{ standing.matches_lost }}</td><td>{{ standing.matches_drawn }}</td><td>{{ standing.points }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </article>
        </div>
      </section>
      <section v-else class="empty-state" aria-labelledby="community-empty-title">
        <h2 id="community-empty-title">No public competitions</h2>
        <p>This {{ terminology.kindLabelLower }} has not published competition content.</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.community-page { width: min(100% - 2rem, 72rem); margin: 0 auto; padding: clamp(1rem, 3vw, 2.5rem) 0 3rem; min-width: 0; color: #172b3a; }
.hero { display: flex; align-items: center; gap: clamp(1rem, 4vw, 2rem); padding: clamp(1rem, 4vw, 2rem); border-radius: 1rem; background: linear-gradient(135deg, #e9f7ef, #eef6ff); }
.organization-logo, .logo-fallback { width: clamp(4.5rem, 14vw, 8rem); height: clamp(4.5rem, 14vw, 8rem); flex: 0 0 auto; border-radius: 1rem; background: #fff; object-fit: contain; }
.logo-fallback { display: grid; place-items: center; color: #fff; background: #176b45; font-size: clamp(2rem, 7vw, 4rem); font-weight: 800; }
.eyebrow, .competition-status { color: #3d596b; font-weight: 700; text-transform: capitalize; }
.sponsor-placement { margin: 1rem 0; padding: 0.75rem 1rem; border-left: 4px solid #176b45; background: #f4f8f5; }
.sponsor-placement span { margin-right: 0.5rem; color: #3d596b; }
.leaderboards { margin: 1.5rem 0; padding: 1rem; border: 1px solid #d7e0e8; border-radius: 0.85rem; background: #fbfdff; }
.leaderboards > p { color: #3d596b; }
.leaderboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: 1rem; }
.leaderboard-grid ol { margin: 0; padding-left: 1.5rem; }
.leaderboard-grid li { display: flex; justify-content: space-between; gap: 1rem; padding: 0.35rem 0; border-bottom: 1px solid #e4e9ee; }
.competition-grid { display: grid; gap: 1rem; }
.competition-card { border: 1px solid #d7e0e8; border-radius: 0.85rem; padding: clamp(1rem, 3vw, 1.5rem); min-width: 0; }
.team-list { display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; padding: 0; }
.team-list li { border-radius: 999px; background: #edf3f7; padding: 0.35rem 0.7rem; }
.fixture-list { display: grid; gap: 0.75rem; list-style: none; padding: 0; }
.fixture-list li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.75rem; border-top: 1px solid #e4e9ee; padding-top: 0.75rem; }
.fixture-list p { margin: 0.2rem 0; }
.table-scroll { max-width: 100%; overflow-x: auto; }
table { width: 100%; min-width: 32rem; border-collapse: collapse; }
th, td { border-bottom: 1px solid #e4e9ee; padding: 0.55rem; text-align: left; }
.page-state, .empty-state { text-align: center; padding: 3rem 1rem; }
a:focus-visible { outline: 3px solid #1d70b8; outline-offset: 3px; }
@media (max-width: 36rem) {
  .hero { align-items: flex-start; flex-direction: column; }
  .fixture-list li { display: block; }
}
</style>
