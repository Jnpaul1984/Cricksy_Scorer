<script setup lang="ts">
import { ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  listSchoolFixtures,
  listSchoolResults,
  updateSchoolMatchPublication,
} from '@/services/schoolAdminApi';
import type {
  SchoolFixtureSummary,
  SchoolMatchResult,
  SchoolPublicationState,
} from '@/types/schoolAdmin';

const { organizationId, terminology, canViewFixturesResults, canPublishScorecards } =
  useSchoolContext();
const fixtures = ref<SchoolFixtureSummary[]>([]);
const results = ref<SchoolMatchResult[]>([]);
const loading = ref(true);
const error = ref('');
const success = ref('');

async function load() {
  fixtures.value = [];
  results.value = [];
  loading.value = true;
  error.value = '';
  try {
    [fixtures.value, results.value] = await Promise.all([
      listSchoolFixtures(organizationId.value),
      listSchoolResults(organizationId.value),
    ]);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

async function publish(match: SchoolMatchResult, state: SchoolPublicationState) {
  const verb =
    state === 'private' ? 'make this scorecard private' : `publish as ${state.replace('_', ' ')}`;
  if (!window.confirm(`Confirm: ${verb}?`)) return;
  error.value = '';
  success.value = '';
  try {
    await updateSchoolMatchPublication(organizationId.value, match.game_id, state);
    success.value = `Scorecard is now ${state.replace('_', ' ')}.`;
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}

watch(organizationId, load, { immediate: true });
</script>

<template>
  <section class="panel" aria-labelledby="fixtures-results-heading">
    <header>
      <p class="eyebrow">{{ terminology.kindLabel }} match experience</p>
      <h2 id="fixtures-results-heading">Fixtures and results</h2>
      <p>Competition fixtures stay separate from matches until an authorized user links them.</p>
    </header>
    <p v-if="!canViewFixturesResults" class="notice error" role="alert">
      Fixtures and results are not enabled for this organization.
    </p>
    <p v-else-if="loading" role="status">Loading fixtures and results…</p>
    <p v-else-if="error" class="notice error" role="alert">{{ error }}</p>
    <template v-else>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <h3>Fixtures</h3>
      <p v-if="!fixtures.length" class="notice">No competition fixtures yet.</p>
      <div v-else class="cards">
        <article v-for="fixture in fixtures" :key="fixture.fixture_id">
          <strong>{{ fixture.team_a_name }} vs {{ fixture.team_b_name }}</strong>
          <p>{{ fixture.competition_name }} · {{ fixture.fixture_status }}</p>
          <p>
            {{
              fixture.scheduled_date
                ? new Date(fixture.scheduled_date).toLocaleString()
                : 'Date not set'
            }}
            · {{ fixture.venue || 'Venue not set' }}
          </p>
          <p v-if="fixture.game_id">
            Linked match: {{ fixture.game_id }} · {{ fixture.game_status || 'not started' }}
          </p>
          <p v-if="fixture.result">Official result: {{ fixture.result }}</p>
          <RouterLink
            v-if="fixture.game_id && fixture.public_scorecard_available"
            :to="`/school-scorecards/${fixture.game_id}`"
            >Public scorecard</RouterLink
          >
        </article>
      </div>

      <h3>{{ terminology.kindLabel }} matches</h3>
      <p v-if="!results.length" class="notice">
        No attributable {{ terminology.kindLabel }} matches yet.
      </p>
      <div v-else class="table-wrap">
        <table data-test="school-results">
          <thead>
            <tr>
              <th>Match</th>
              <th>Status</th>
              <th>Score</th>
              <th>Official result</th>
              <th>Publication</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="match in results" :key="match.game_id">
              <td>{{ match.team_a_name }} vs {{ match.team_b_name }}</td>
              <td>{{ match.status }}</td>
              <td>
                {{ match.team_a_runs }}/{{ match.team_a_wickets }} · {{ match.team_b_runs }}/{{
                  match.team_b_wickets
                }}
              </td>
              <td>{{ match.result || 'Pending' }}</td>
              <td>{{ match.publication_state.replace('_', ' ') }}</td>
              <td>
                <div class="actions">
                  <RouterLink :to="`/view/${match.game_id}`">Internal score</RouterLink>
                  <RouterLink
                    v-if="match.public_scorecard_available"
                    :to="`/school-scorecards/${match.game_id}`"
                    >Public scorecard</RouterLink
                  >
                  <template v-if="canPublishScorecards">
                    <button type="button" class="compact" @click="publish(match, 'published_live')">
                      Publish live
                    </button>
                    <button
                      v-if="match.status === 'completed'"
                      type="button"
                      class="compact"
                      @click="publish(match, 'published_final')"
                    >
                      Publish final
                    </button>
                    <button
                      v-if="match.publication_state !== 'private'"
                      type="button"
                      class="compact secondary"
                      @click="publish(match, 'private')"
                    >
                      Make private
                    </button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.panel {
  padding: 1.4rem;
  border: 1px solid #3b4768;
  border-top: 0;
  background: #171e30;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.notice {
  margin: 0.8rem 0;
  padding: 0.8rem;
  border: 1px solid #53617c;
  border-radius: 8px;
}
.error {
  border-color: #d56b6b;
}
.success {
  border-color: #58b893;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.8rem;
  margin-bottom: 1.4rem;
}
.cards article {
  padding: 1rem;
  border: 1px solid #39445f;
  border-radius: 10px;
  background: #20283d;
}
.table-wrap {
  overflow-x: auto;
}
table {
  min-width: 950px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}
.compact {
  padding: 0.35rem 0.55rem;
  font-size: 0.85rem;
}
a {
  color: #9fd9ff;
}
</style>
