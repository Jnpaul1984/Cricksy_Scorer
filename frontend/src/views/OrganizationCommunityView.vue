<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { organizationTerminology } from '@/composables/useOrganizationTerminology';
import { getPublicOrganizationCommunity } from '@/services/schoolAdminApi';
import type { PublicOrganizationCommunity } from '@/types/schoolAdmin';

const props = defineProps<{ publicIdentifier: string }>();
const community = ref<PublicOrganizationCommunity | null>(null);
const loading = ref(true);
const notFound = ref(false);
const logoFailed = ref(false);
let generation = 0;

const terminology = computed(() =>
  organizationTerminology(community.value?.organization_type || 'school'),
);

function formatDate(value: string | null) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

async function load() {
  const currentGeneration = ++generation;
  const currentIdentifier = props.publicIdentifier;
  community.value = null;
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
        </div>
      </header>

      <section v-if="community.competitions.length" aria-labelledby="public-competitions-title">
        <h2 id="public-competitions-title">Public competitions</h2>
        <div class="competition-grid">
          <article v-for="competition in community.competitions" :key="`${competition.name}:${competition.start_date || ''}`" class="competition-card">
            <header>
              <p class="competition-status">{{ competition.status }} · {{ competition.tournament_type }}</p>
              <h3>{{ competition.name }}</h3>
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
                    <strong>{{ fixture.team_a_name }} vs {{ fixture.team_b_name }}</strong>
                    <p v-if="fixture.scheduled_date">{{ formatDate(fixture.scheduled_date) }}</p>
                    <p v-if="fixture.venue">{{ fixture.venue }}</p>
                    <p>{{ fixture.result || fixture.game_status || fixture.fixture_status }}</p>
                  </div>
                  <RouterLink v-if="fixture.public_scorecard_path" :to="fixture.public_scorecard_path">
                    View published scorecard
                  </RouterLink>
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
