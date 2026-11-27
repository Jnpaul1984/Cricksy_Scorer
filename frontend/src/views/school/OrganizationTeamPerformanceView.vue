<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  getOrganizationTeamPerformance,
  getOrganizationTeamRecentForm,
  listOrganizationTeamPerformanceTeams,
} from '@/services/schoolAdminApi';
import type {
  OrganizationTeamPerformance,
  OrganizationTeamRecentForm,
  OrganizationTeamPerformanceTeamOption,
} from '@/types/schoolAdmin';

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
const teams = ref<OrganizationTeamPerformanceTeamOption[]>([]);
const selectedTeamId = ref('');
const oversLimit = ref(20);
const data = ref<OrganizationTeamPerformance | null>(null);
const asOfDate = ref('');
const recentForm = ref<OrganizationTeamRecentForm | null>(null);
const recentFormState = ref<
  | 'idle'
  | 'loading'
  | 'ready'
  | 'not_ready'
  | 'data_unavailable'
  | 'unavailable_access'
  | 'scope_too_large'
  | 'request_failure'
>('idle');
const recentFormError = ref('');
const state = ref<ViewState>('loading');
const error = ref('');
const teamsOrganizationId = ref('');
let teamGeneration = 0;
let requestGeneration = 0;
let formGeneration = 0;

function clearData() {
  data.value = null;
  error.value = '';
}

function formatOvers(balls: number): string {
  return `${Math.floor(balls / 6)}.${balls % 6}`;
}

function failureStatus(
  reason: unknown,
): 'unavailable_access' | 'scope_too_large' | 'request_failure' {
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
      const result = await listOrganizationTeamPerformanceTeams(requestedOrganizationId);
      if (
        teamsRequestGeneration !== teamGeneration ||
        requestedOrganizationId !== organizationId.value ||
        !canManageTeams.value
      ) {
        return;
      }
      teams.value = result;
      teamsOrganizationId.value = requestedOrganizationId;
      selectedTeamId.value =
        result.find((team) => team.status === 'active')?.id ?? result[0]?.id ?? '';
      if (!result.length) state.value = 'no_team';
    } catch (reason) {
      if (
        teamsRequestGeneration !== teamGeneration ||
        requestedOrganizationId !== organizationId.value ||
        !canManageTeams.value
      ) {
        return;
      }
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
        requestedTeamId !== selectedTeamId.value ||
        requestedOvers !== oversLimit.value ||
        !canManageTeams.value
      ) {
        return;
      }
      state.value = failureStatus(reason);
      if (state.value === 'request_failure') error.value = getErrorMessage(reason);
    }
  },
  { immediate: true },
);

watch(
  [organizationId, canManageTeams, selectedTeamId, asOfDate],
  async ([requestedOrganizationId, allowed, requestedTeamId, requestedDate]) => {
    const generation = ++formGeneration;
    recentForm.value = null;
    recentFormError.value = '';
    if (!allowed || !requestedOrganizationId) {
      recentFormState.value = 'unavailable_access';
      return;
    }
    if (
      !requestedTeamId ||
      !requestedDate ||
      teamsOrganizationId.value !== requestedOrganizationId
    ) {
      recentFormState.value = 'idle';
      return;
    }
    recentFormState.value = 'loading';
    try {
      const result = await getOrganizationTeamRecentForm(
        requestedOrganizationId,
        requestedTeamId,
        requestedDate,
      );
      if (
        generation !== formGeneration ||
        requestedOrganizationId !== organizationId.value ||
        requestedTeamId !== selectedTeamId.value ||
        requestedDate !== asOfDate.value ||
        !canManageTeams.value
      )
        return;
      recentForm.value = result;
      recentFormState.value =
        result.readiness.state === 'data_unavailable' &&
        result.readiness.exclusion_counts.scope_too_large
          ? 'scope_too_large'
          : result.readiness.state;
    } catch (reason) {
      if (
        generation !== formGeneration ||
        requestedOrganizationId !== organizationId.value ||
        requestedTeamId !== selectedTeamId.value ||
        requestedDate !== asOfDate.value ||
        !canManageTeams.value
      )
        return;
      recentFormState.value = failureStatus(reason);
      if (recentFormState.value === 'request_failure')
        recentFormError.value = getErrorMessage(reason);
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  teamGeneration += 1;
  requestGeneration += 1;
  formGeneration += 1;
  clearData();
  recentForm.value = null;
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
        <section
          v-if="data.coverage.usable_batting_innings > 0"
          class="metric-card"
          aria-labelledby="batting-heading"
        >
          <h3 id="batting-heading">Team batting</h3>
          <dl>
            <dt>Team runs</dt>
            <dd>{{ data.batting.team_runs }}</dd>
            <dt>Bat runs</dt>
            <dd>{{ data.batting.bat_runs }}</dd>
            <dt>Wickets lost</dt>
            <dd>{{ data.batting.wickets_lost }}</dd>
            <dt>Legal balls (overs)</dt>
            <dd>{{ data.batting.legal_balls }} ({{ formatOvers(data.batting.legal_balls) }})</dd>
            <dt>Run rate</dt>
            <dd>{{ data.batting.run_rate ?? '—' }}</dd>
            <dt>Legal dots</dt>
            <dd>{{ data.batting.legal_dots }}</dd>
            <dt>Wides / no-ball penalties</dt>
            <dd>{{ data.batting.wides }} / {{ data.batting.no_ball_penalties }}</dd>
            <dt>Byes / leg-byes</dt>
            <dd>{{ data.batting.byes }} / {{ data.batting.leg_byes }}</dd>
            <dt>Recorded fours / sixes</dt>
            <dd>{{ data.batting.fours }} / {{ data.batting.sixes }}</dd>
            <dt>Team runs per wicket</dt>
            <dd>{{ data.batting.runs_per_wicket ?? '—' }}</dd>
          </dl>
        </section>
        <section
          v-if="data.coverage.usable_bowling_innings > 0"
          class="metric-card"
          aria-labelledby="bowling-heading"
        >
          <h3 id="bowling-heading">Team bowling</h3>
          <dl>
            <dt>Opposition team runs conceded</dt>
            <dd>{{ data.bowling.opposition_team_runs }}</dd>
            <dt>Bowler-charged runs</dt>
            <dd>{{ data.bowling.bowler_charged_runs }}</dd>
            <dt>Legal balls (overs)</dt>
            <dd>{{ data.bowling.legal_balls }} ({{ formatOvers(data.bowling.legal_balls) }})</dd>
            <dt>Team concession rate</dt>
            <dd>{{ data.bowling.team_concession_rate ?? '—' }}</dd>
            <dt>Bowling economy</dt>
            <dd>{{ data.bowling.bowling_economy ?? '—' }}</dd>
            <dt>Team wickets</dt>
            <dd>{{ data.bowling.team_wickets }}</dd>
            <dt>Bowler-credited wickets</dt>
            <dd>{{ data.bowling.bowler_credited_wickets }}</dd>
            <dt>Legal dots</dt>
            <dd>{{ data.bowling.legal_dots }}</dd>
            <dt>Wides / no-ball penalties</dt>
            <dd>{{ data.bowling.wides }} / {{ data.bowling.no_ball_penalties }}</dd>
            <dt>Byes / leg-byes</dt>
            <dd>{{ data.bowling.byes }} / {{ data.bowling.leg_byes }}</dd>
          </dl>
        </section>
      </div>

      <section class="coverage" aria-labelledby="coverage-heading">
        <h3 id="coverage-heading">Recorded-data coverage</h3>
        <dl>
          <dt>Eligible / included games</dt>
          <dd>{{ data.coverage.eligible_games }} / {{ data.coverage.included_games }}</dd>
          <dt>Usable batting innings</dt>
          <dd>{{ data.coverage.usable_batting_innings }}</dd>
          <dt>Usable bowling innings</dt>
          <dd>{{ data.coverage.usable_bowling_innings }}</dd>
          <dt>Used / observed delivery rows</dt>
          <dd>
            {{ data.coverage.used_delivery_rows }} / {{ data.coverage.observed_delivery_rows }}
          </dd>
          <dt>Excluded games / innings</dt>
          <dd>{{ data.coverage.excluded_games }} / {{ data.coverage.excluded_innings }}</dd>
          <dt>Ordinary cohort exclusions</dt>
          <dd>{{ data.coverage.cohort_excluded_games }}</dd>
          <dt>No-ledger games</dt>
          <dd>{{ data.coverage.no_ledger_games }}</dd>
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
        <ul
          v-if="Object.keys(data.coverage.warning_counts).length"
          class="warnings"
          aria-label="Recorded-data validation warnings"
        >
          <li v-for="(count, code) in data.coverage.warning_counts" :key="code">
            {{ code.replace(/_/g, ' ') }}: {{ count }}
          </li>
        </ul>
        <p v-if="data.coverage.cohort_excluded_games" class="notice">
          Games outside the selected format or cohort are counted separately.
        </p>
        <p v-if="Object.keys(data.coverage.warning_counts).length" class="notice">
          Recorded-data validation warnings are listed above; data availability is reported
          separately.
        </p>
        <p
          v-if="data.coverage.eligible_games > 0 && data.coverage.usable_batting_innings === 0"
          class="notice"
          role="status"
        >
          No usable batting data.
        </p>
        <p
          v-if="data.coverage.eligible_games > 0 && data.coverage.usable_bowling_innings === 0"
          class="notice"
          role="status"
        >
          No usable bowling data.
        </p>
      </section>
    </template>

    <section
      v-if="canManageTeams && teamsOrganizationId === organizationId"
      class="coverage"
      aria-labelledby="recent-form-heading"
    >
      <h3 id="recent-form-heading">Recent 25-over Team form</h3>
      <p>
        Choose an exclusive venue-local as-of date. Only five prior, verified original 25-over
        matches can form a trend.
      </p>
      <label
        >As-of date <input v-model="asOfDate" type="date" aria-label="Recent form as-of date"
      /></label>
      <p v-if="recentFormState === 'idle'" role="status">
        Choose an as-of date to check five-match readiness.
      </p>
      <p v-else-if="recentFormState === 'loading'" role="status">Loading recent form…</p>
      <p v-else-if="recentFormState === 'unavailable_access'" role="alert">
        Recent form is unavailable for your current access.
      </p>
      <p v-else-if="recentFormState === 'scope_too_large'" role="alert">
        Recent form scope exceeds the safe workload limit; no trend is shown.
      </p>
      <p v-else-if="recentFormState === 'request_failure'" role="alert">{{ recentFormError }}</p>
      <template v-if="recentForm">
        <p>
          Usable prior matches: {{ recentForm.readiness.usable_prior_match_count }} /
          {{ recentForm.readiness.required_history }}. Sample size: {{ recentForm.sample_size }}.
          Historical completeness: unknown.
        </p>
        <p v-if="recentFormState === 'not_ready'" role="status">
          Insufficient history: {{ recentForm.readiness.remaining_match_count }} more usable prior
          matches needed.
        </p>
        <p v-else-if="recentFormState === 'data_unavailable'" role="status">
          Chronology or evidence is unavailable; no five-match trend can be shown.
        </p>
        <ul class="warnings" aria-label="Recent form coverage">
          <li
            v-for="(count, code) in recentForm.readiness.exclusion_counts"
            v-show="count > 0"
            :key="code"
          >
            {{ code.replace(/_/g, ' ') }}: {{ count }}
          </li>
        </ul>
        <template v-if="recentFormState === 'ready' && recentForm.batting && recentForm.bowling">
          <p>
            Five matches, oldest to newest. Rates use summed runs and legal balls. Based on recorded
            delivery data; historical completeness has not been verified.
          </p>
          <div class="trend-scroll">
            <table aria-label="Recent Team form trend">
              <thead>
                <tr>
                  <th>Match</th>
                  <th>Played date</th>
                  <th>Recorded rows</th>
                  <th>Batting runs</th>
                  <th>Wickets lost</th>
                  <th>Batting balls</th>
                  <th>Run rate</th>
                  <th>Batting dot %</th>
                  <th>Recorded 4s / 6s</th>
                  <th>Runs conceded</th>
                  <th>Team wickets</th>
                  <th>Bowling balls</th>
                  <th>Economy</th>
                  <th>Bowling dot %</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="match in recentForm.matches" :key="match.ordinal">
                  <th>{{ match.ordinal }}</th>
                  <td>{{ match.played_date }}</td>
                  <td>{{ match.recorded_delivery_rows }}</td>
                  <td>{{ match.batting.team_runs }}</td>
                  <td>{{ match.batting.wickets_lost }}</td>
                  <td>{{ match.batting.legal_balls }}</td>
                  <td>{{ match.batting.run_rate ?? '—' }}</td>
                  <td>{{ match.batting.legal_dot_percentage ?? '—' }}</td>
                  <td>{{ match.batting.fours }} / {{ match.batting.sixes }}</td>
                  <td>{{ match.bowling.opposition_team_runs }}</td>
                  <td>{{ match.bowling.team_wickets }}</td>
                  <td>{{ match.bowling.legal_balls }}</td>
                  <td>{{ match.bowling.bowling_economy ?? '—' }}</td>
                  <td>{{ match.bowling.legal_dot_percentage ?? '—' }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <th colspan="2">Five-match aggregate</th>
                  <td>{{ recentForm.recorded_delivery_rows }}</td>
                  <td>{{ recentForm.batting.team_runs }}</td>
                  <td>{{ recentForm.batting.wickets_lost }}</td>
                  <td>{{ recentForm.batting.legal_balls }}</td>
                  <td>{{ recentForm.batting.run_rate ?? '—' }}</td>
                  <td>{{ recentForm.batting.legal_dot_percentage ?? '—' }}</td>
                  <td>{{ recentForm.batting.fours }} / {{ recentForm.batting.sixes }}</td>
                  <td>{{ recentForm.bowling.opposition_team_runs }}</td>
                  <td>{{ recentForm.bowling.team_wickets }}</td>
                  <td>{{ recentForm.bowling.legal_balls }}</td>
                  <td>{{ recentForm.bowling.bowling_economy ?? '—' }}</td>
                  <td>{{ recentForm.bowling.legal_dot_percentage ?? '—' }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </template>
      </template>
    </section>

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
.trend-scroll {
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  min-width: 70rem;
}
th,
td {
  padding: 0.5rem;
  border: 1px solid #53617c;
  text-align: right;
}
</style>
