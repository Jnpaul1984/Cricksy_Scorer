<script setup lang="ts">
import { ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import { listSchoolPlayerStatistics, listSchoolTeamStatistics } from '@/services/schoolAdminApi';
import type { SchoolPlayerStatistics, SchoolTeamStatistics } from '@/types/schoolAdmin';

const { organizationId, terminology, canViewStatistics } = useSchoolContext();
const players = ref<SchoolPlayerStatistics[]>([]);
const teams = ref<SchoolTeamStatistics[]>([]);
const loading = ref(true);
const error = ref('');

async function load() {
  players.value = [];
  teams.value = [];
  loading.value = true;
  error.value = '';
  try {
    [players.value, teams.value] = await Promise.all([
      listSchoolPlayerStatistics(organizationId.value),
      listSchoolTeamStatistics(organizationId.value),
    ]);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

watch(organizationId, load, { immediate: true });
</script>

<template>
  <section class="panel" aria-labelledby="statistics-heading">
    <header>
      <p class="eyebrow">{{ terminology.freePlanLabel }} statistics</p>
      <h2 id="statistics-heading">Player and team statistics</h2>
      <p>
        Calculated from completed {{ terminology.kindLabel }} match scoring records and canonical
        player identities.
      </p>
    </header>
    <p v-if="!canViewStatistics" class="notice error" role="alert">
      {{ terminology.kindLabel }} statistics are not enabled for this organization.
    </p>
    <p v-else-if="loading" role="status">Loading statistics…</p>
    <p v-else-if="error" class="notice error" role="alert">{{ error }}</p>
    <template v-else>
      <h3>Players</h3>
      <p v-if="!players.length" class="notice">
        No attributable {{ terminology.kindLabel }} match statistics yet.
      </p>
      <div v-else class="table-wrap">
        <table data-test="player-statistics">
          <thead>
            <tr>
              <th>Player</th>
              <th>Matches</th>
              <th>Runs</th>
              <th>High</th>
              <th>Average</th>
              <th>Strike rate</th>
              <th>Overs</th>
              <th>Wickets</th>
              <th>Bowling average</th>
              <th>Economy</th>
              <th>Best</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="player in players" :key="player.player_profile_id">
              <td>
                {{ player.player_name }}
                <span v-if="player.roster_status === 'inactive'" class="badge">inactive</span>
              </td>
              <td>{{ player.matches }}</td>
              <td>{{ player.runs }}</td>
              <td>{{ player.highest_score }}</td>
              <td>{{ player.batting_average ?? '—' }}</td>
              <td>{{ player.strike_rate }}</td>
              <td>{{ player.overs }}</td>
              <td>{{ player.wickets }}</td>
              <td>{{ player.bowling_average ?? '—' }}</td>
              <td>{{ player.economy ?? '—' }}</td>
              <td>{{ player.best_bowling ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3>Teams</h3>
      <p v-if="!teams.length" class="notice">
        No persistent {{ terminology.kindLabel }} teams are available.
      </p>
      <div v-else class="table-wrap">
        <table data-test="team-statistics">
          <thead>
            <tr>
              <th>Team</th>
              <th>Played</th>
              <th>Won</th>
              <th>Lost</th>
              <th>Tied</th>
              <th>Drawn</th>
              <th>No result</th>
              <th>Runs for</th>
              <th>Runs against</th>
              <th>Wickets taken</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="team in teams" :key="team.team_id">
              <td>
                {{ team.team_name }}
                <span v-if="team.team_status === 'archived'" class="badge">archived</span>
              </td>
              <td>{{ team.matches }}</td>
              <td>{{ team.wins }}</td>
              <td>{{ team.losses }}</td>
              <td>{{ team.ties }}</td>
              <td>{{ team.draws }}</td>
              <td>{{ team.no_results }}</td>
              <td>{{ team.runs_scored }}</td>
              <td>{{ team.runs_conceded }}</td>
              <td>{{ team.wickets_taken }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="boundary-note">
        Fielding statistics are not shown because the current scoring ledger does not reliably
        retain fielder identity. Advanced analytics are outside {{ terminology.freePlanLabel }}.
      </p>
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
.notice,
.boundary-note {
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
.table-wrap {
  overflow-x: auto;
  margin-bottom: 1.4rem;
}
table {
  min-width: 920px;
}
.badge {
  margin-left: 0.35rem;
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
  background: #4a3950;
  font-size: 0.78rem;
  text-transform: uppercase;
}
</style>
