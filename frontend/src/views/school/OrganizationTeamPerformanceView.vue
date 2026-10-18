<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  getOrganizationTeamPerformance,
  listSchoolTeams,
} from '@/services/schoolAdminApi';
import type { OrganizationTeamPerformance, SchoolTeam } from '@/types/schoolAdmin';

type ViewState =
  | 'unavailable_access'
  | 'loading'
  | 'no_team'
  | 'no_eligible_games'
  | 'no_usable_ledger'
  | 'usable_with_exclusions'
  | 'usable_recorded_data'
  | 'request_failure'
  | 'scope_too_large';

const { organizationId, organizationBasePath, terminology, canManageTeams } = useSchoolContext();
const teams = ref<SchoolTeam[]>([]);
const selectedTeamId = ref('');
const oversLimit = ref(20);
const data = ref<OrganizationTeamPerformance | null>(null);
const state = ref<ViewState>('loading');
const error = ref('');
const teamsOrganizationId = ref('');
let teamGeneration = 0;
let requestGeneration = 0;

function clearData() {
  data.value = null;
  error.value = '';
}

function formatOvers(balls: number): string {
  return `${Math.floor(balls / 6)}.${balls % 6}`;
}

function failureStatus(reason: unknown): ViewState {
  const httpStatus = (reason as { status?: number } | null)?.status;
  if (httpStatus === 403 || httpStatus === 404) return 'unavailable_access';
  if (httpStatus === 413) return 'scope_too_large';
  return 'request_failure';
}

watch(
  [organizationId, canManageTeams],
  async ([requestedOrganizationId, allowed]) => {
    const teamsRequestGeneration = ++teamGeneration;
    requestGeneration += 1;
    teams.value = [];
    selectedTeamId.value = '';
    teamsOrganizationId.value = '';
    clearData();
    if (!allowed || !requestedOrganizationId) {
      state.value = 'unavailable_access';
      return;
    }
    state.value = 'loading';
    try {
      const result = await listSchoolTeams(requestedOrganizationId);
      if (
        teamsRequestGeneration !== teamGeneration ||
        requestedOrganizationId !== organizationId.value ||
        !canManageTeams.value
      ) {
        return;
      }
      teams.value = result;
      teamsOrganizationId.value = requestedOrganizationId;
      selectedTeamId.value = result.find((team) => team.status === 'active')?.id ?? result[0]?.id ?? '';
      if (!result.length) state.value = 'no_team';
    } catch (reason) {
      if (teamsRequestGeneration !== teamGeneration) return;
      state.value = failureStatus(reason);
      if (state.value === 'request_failure') error.value = getErrorMessage(reason);
    }
  },
  { immediate: true },
);

watch(
  [organizationId, canManageTeams, selectedTeamId, oversLimit],
  async ([requestedOrganizationId, allowed, requestedTeamId, requestedOvers]) => {
    const analyticsRequestGeneration = ++requestGeneration;
    clearData();
    if (!allowed || !requestedOrganizationId) {
      state.value = 'unavailable_access';
      return;
    }
    if (teamsOrganizationId.value !== requestedOrganizationId) {
      state.value = 'loading';
      return;
    }
    if (!requestedTeamId) {
      state.value = 'no_team';
      return;
    }
    if (!Number.isInteger(requestedOvers) || requestedOvers < 1 || requestedOvers > 120) {
      state.value = 'request_failure';
      error.value = 'Choose an overs limit from 1 to 120.';
      return;
    }
    state.value = 'loading';
    try {
      const result = await getOrganizationTeamPerformance(
        requestedOrganizationId,
        requestedTeamId,
        requestedOvers,
      );
      if (
        analyticsRequestGeneration !== requestGeneration ||
        requestedOrganizationId !== organizationId.value ||
        requestedTeamId !== selectedTeamId.value ||
        requestedOvers !== oversLimit.value ||
        !canManageTeams.value
      ) {
        return;
      }
      data.value = result;
      state.value = result.coverage.status;
    } catch (reason) {
      if (
        analyticsRequestGeneration !== requestGeneration ||
        requestedOrganizationId !== organizationId.value ||
        requestedTeamId !== selectedTeamId.value
      ) {
        return;
      }
      state.value = failureStatus(reason);
      if (state.value === 'request_failure') error.value = getErrorMessage(reason);
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  teamGeneration += 1;
  requestGeneration += 1;
  clearData();
  teams.value = [];
});
</script>

<template>
  <section class="panel" aria-labelledby="team-performance-heading">
    <header>
      <p class="eyebrow">{{ terminology.kindLabel }} staff pilot</p>
      <h2 id="team-performance-heading">Team Performance</h2>
      <p>Read-only batting and bowling aggregates from recorded limited-overs deliveries.</p>
    </header>

    <p class="boundary-note">
      Based on recorded delivery data. Historical completeness has not been verified.
    </p>

    <p v-if="state === 'unavailable_access'" class="notice error" role="alert">
      Team Performance is unavailable for this organization or your current access.
    </p>
    <p v-else-if="state === 'loading'" role="status">Loading Team Performance…</p>
    <p v-else-if="state === 'request_failure'" class="notice error" role="alert">{{ error }}</p>
    <p v-else-if="state === 'scope_too_large'" class="notice error" role="alert">
      This complete recorded-history scope is too large to analyze in one request. No games were
      omitted; contact your organization operator for guidance.
    </p>
    <p v-else-if="state === 'no_team'" class="notice">
      No persistent Teams are available in this organization.
    </p>

    <template v-if="canManageTeams && teamsOrganizationId === organizationId">
      <div class="scope-controls">
        <label>
          Team
          <select v-model="selectedTeamId" aria-label="Team">
            <option v-for="team in teams" :key="team.id" :value="team.id">
              {{ team.name }}{{ team.status === 'archived' ? ' (archived)' : '' }}
            </option>
          </select>
        </label>
        <label>
          Overs limit
          <input
            v-model.number="oversLimit"
            aria-label="Overs limit"
            type="number"
            min="1"
            max="120"
            step="1"
          />
        </label>
      </div>
    </template>

    <p v-if="state === 'no_eligible_games'" class="notice" role="status">
      No eligible official completed limited-overs games match this Team and overs limit.
    </p>
    <p v-else-if="state === 'no_usable_ledger'" class="notice" role="status">
      Eligible games exist, but no usable batting or bowling delivery ledger is available.
    </p>
    <template v-if="data">
      <div
        v-if="state === 'usable_with_exclusions' || state === 'usable_recorded_data'"
        class="cards"
      >
        <section class="metric-card" aria-labelledby="batting-heading">
          <h3 id="batting-heading">Team batting</h3>
          <dl>
            <dt>Team runs</dt><dd>{{ data.batting.team_runs }}</dd>
            <dt>Bat runs</dt><dd>{{ data.batting.bat_runs }}</dd>
            <dt>Wickets lost</dt><dd>{{ data.batting.wickets_lost }}</dd>
            <dt>Legal balls (overs)</dt>
            <dd>{{ data.batting.legal_balls }} ({{ formatOvers(data.batting.legal_balls) }})</dd>
            <dt>Run rate</dt><dd>{{ data.batting.run_rate ?? '—' }}</dd>
            <dt>Legal dots</dt><dd>{{ data.batting.legal_dots }}</dd>
            <dt>Wides / no-ball penalties</dt>
            <dd>{{ data.batting.wides }} / {{ data.batting.no_ball_penalties }}</dd>
            <dt>Byes / leg-byes</dt><dd>{{ data.batting.byes }} / {{ data.batting.leg_byes }}</dd>
            <dt>Recorded fours / sixes</dt><dd>{{ data.batting.fours }} / {{ data.batting.sixes }}</dd>
            <dt>Team runs per wicket</dt><dd>{{ data.batting.runs_per_wicket ?? '—' }}</dd>
          </dl>
        </section>
        <section class="metric-card" aria-labelledby="bowling-heading">
          <h3 id="bowling-heading">Team bowling</h3>
          <dl>
            <dt>Opposition team runs conceded</dt><dd>{{ data.bowling.opposition_team_runs }}</dd>
            <dt>Bowler-charged runs</dt><dd>{{ data.bowling.bowler_charged_runs }}</dd>
            <dt>Legal balls (overs)</dt>
            <dd>{{ data.bowling.legal_balls }} ({{ formatOvers(data.bowling.legal_balls) }})</dd>
            <dt>Team concession rate</dt><dd>{{ data.bowling.team_concession_rate ?? '—' }}</dd>
            <dt>Bowling economy</dt><dd>{{ data.bowling.bowling_economy ?? '—' }}</dd>
            <dt>Team wickets</dt><dd>{{ data.bowling.team_wickets }}</dd>
            <dt>Bowler-credited wickets</dt><dd>{{ data.bowling.bowler_credited_wickets }}</dd>
            <dt>Legal dots</dt><dd>{{ data.bowling.legal_dots }}</dd>
            <dt>Wides / no-ball penalties</dt>
            <dd>{{ data.bowling.wides }} / {{ data.bowling.no_ball_penalties }}</dd>
            <dt>Byes / leg-byes</dt><dd>{{ data.bowling.byes }} / {{ data.bowling.leg_byes }}</dd>
          </dl>
        </section>
      </div>

      <section class="coverage" aria-labelledby="coverage-heading">
        <h3 id="coverage-heading">Recorded-data coverage</h3>
        <dl>
          <dt>Eligible / included games</dt>
          <dd>{{ data.coverage.eligible_games }} / {{ data.coverage.included_games }}</dd>
          <dt>Usable batting innings</dt><dd>{{ data.coverage.usable_batting_innings }}</dd>
          <dt>Usable bowling innings</dt><dd>{{ data.coverage.usable_bowling_innings }}</dd>
          <dt>Used / observed delivery rows</dt>
          <dd>{{ data.coverage.used_delivery_rows }} / {{ data.coverage.observed_delivery_rows }}</dd>
          <dt>Excluded games / innings</dt>
          <dd>{{ data.coverage.excluded_games }} / {{ data.coverage.excluded_innings }}</dd>
          <dt>Ordinary cohort exclusions</dt><dd>{{ data.coverage.cohort_excluded_games }}</dd>
          <dt>No-ledger games</dt><dd>{{ data.coverage.no_ledger_games }}</dd>
          <dt>Invalid/missing-data games / innings</dt>
          <dd>{{ data.coverage.invalid_data_games }} / {{ data.coverage.invalid_data_innings }}</dd>
        </dl>
        <ul
          v-if="Object.keys(data.coverage.cohort_exclusion_counts).length"
          class="warnings"
          aria-label="Ordinary cohort exclusions"
        >
          <li v-for="(count, code) in data.coverage.cohort_exclusion_counts" :key="code">
            {{ code.replace(/_/g, ' ') }}: {{ count }}
          </li>
        </ul>
        <ul v-if="Object.keys(data.coverage.warning_counts).length" class="warnings">
          <li v-for="(count, code) in data.coverage.warning_counts" :key="code">
            {{ code.replace(/_/g, ' ') }}: {{ count }}
          </li>
        </ul>
        <p v-if="state === 'usable_with_exclusions'" class="notice">
          Usable recorded data is shown with exclusions and validation warnings.
        </p>
      </section>
    </template>

    <RouterLink
      v-if="canManageTeams"
      class="back-link"
      :to="`${organizationBasePath}/${organizationId}/statistics`"
    >
      Back to Free statistics
    </RouterLink>
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
.notice,
.boundary-note,
.coverage,
.metric-card {
  margin: 0.8rem 0;
  padding: 0.8rem;
  border: 1px solid #53617c;
  border-radius: 8px;
}
.error {
  border-color: #d56b6b;
}
.boundary-note {
  border-left: 4px solid #f2bb5f;
  background: #292536;
}
.scope-controls,
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 1rem;
}
label {
  display: grid;
  gap: 0.4rem;
  font-weight: 700;
}
select,
input {
  min-height: 2.5rem;
  padding: 0.4rem;
}
dl {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) auto;
  gap: 0.45rem 1rem;
}
dd {
  margin: 0;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.warnings {
  padding-left: 1.25rem;
}
.back-link {
  display: inline-block;
  margin-top: 1rem;
}
</style>
