<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import { createSchoolMatch, listSchoolTeams, listTeamRoster } from '@/services/schoolAdminApi';
import type {
  SchoolMatchCreate,
  SchoolTeam,
  SchoolTeamRosterPlayer,
} from '@/types/schoolAdmin';

type Side = 'a' | 'b';

const router = useRouter();
const { organizationId, canCreateSchoolMatch } = useSchoolContext();
const teams = ref<SchoolTeam[]>([]);
const teamAId = ref('');
const teamBId = ref('');
const rosterA = ref<SchoolTeamRosterPlayer[]>([]);
const rosterB = ref<SchoolTeamRosterPlayer[]>([]);
const selectedA = ref<string[]>([]);
const selectedB = ref<string[]>([]);
const captainA = ref('');
const captainB = ref('');
const wicketkeeperA = ref('');
const wicketkeeperB = ref('');
const loadingTeams = ref(false);
const loadingA = ref(false);
const loadingB = ref(false);
const creating = ref(false);
const error = ref('');

const matchType = ref<'limited' | 'multi_day' | 'custom'>('limited');
const oversLimit = ref<number | null>(20);
const daysLimit = ref<number | null>(null);
const oversPerDay = ref<number | null>(null);
const dlsEnabled = ref(false);
const tossWinnerSide = ref<'team_a' | 'team_b'>('team_a');
const decision = ref<'bat' | 'bowl'>('bat');

const teamA = computed(() => teams.value.find((team) => team.id === teamAId.value));
const teamB = computed(() => teams.value.find((team) => team.id === teamBId.value));

function resetSide(side: Side) {
  if (side === 'a') {
    rosterA.value = [];
    selectedA.value = [];
    captainA.value = '';
    wicketkeeperA.value = '';
  } else {
    rosterB.value = [];
    selectedB.value = [];
    captainB.value = '';
    wicketkeeperB.value = '';
  }
}

function resetSchoolState() {
  teams.value = [];
  teamAId.value = '';
  teamBId.value = '';
  resetSide('a');
  resetSide('b');
  error.value = '';
}

async function loadTeams() {
  const requestedOrganization = organizationId.value;
  resetSchoolState();
  if (!canCreateSchoolMatch.value) return;
  loadingTeams.value = true;
  try {
    const result = await listSchoolTeams(requestedOrganization);
    if (organizationId.value === requestedOrganization && canCreateSchoolMatch.value) {
      teams.value = result;
    }
  } catch (reason) {
    if (organizationId.value === requestedOrganization && canCreateSchoolMatch.value) {
      error.value = getErrorMessage(reason);
    }
  } finally {
    if (organizationId.value === requestedOrganization) loadingTeams.value = false;
  }
}

async function loadRoster(side: Side, teamId: string) {
  resetSide(side);
  if (!teamId || !canCreateSchoolMatch.value) return;
  const requestedOrganization = organizationId.value;
  if (side === 'a') loadingA.value = true;
  else loadingB.value = true;
  try {
    const result = await listTeamRoster(requestedOrganization, teamId);
    const stillCurrent =
      organizationId.value === requestedOrganization &&
      canCreateSchoolMatch.value &&
      (side === 'a' ? teamAId.value === teamId : teamBId.value === teamId);
    if (!stillCurrent) return;
    if (side === 'a') rosterA.value = result;
    else rosterB.value = result;
  } catch (reason) {
    const stillCurrent =
      organizationId.value === requestedOrganization &&
      canCreateSchoolMatch.value &&
      (side === 'a' ? teamAId.value === teamId : teamBId.value === teamId);
    if (stillCurrent) error.value = getErrorMessage(reason);
  } finally {
    if (side === 'a' && teamAId.value === teamId) loadingA.value = false;
    if (side === 'b' && teamBId.value === teamId) loadingB.value = false;
  }
}

function togglePlayer(side: Side, player: SchoolTeamRosterPlayer) {
  if (!player.operationally_available) return;
  const selected = side === 'a' ? selectedA : selectedB;
  const current = selected.value;
  if (current.includes(player.id)) {
    selected.value = current.filter((id) => id !== player.id);
    if (side === 'a') {
      if (captainA.value === player.id) captainA.value = '';
      if (wicketkeeperA.value === player.id) wicketkeeperA.value = '';
    } else {
      if (captainB.value === player.id) captainB.value = '';
      if (wicketkeeperB.value === player.id) wicketkeeperB.value = '';
    }
    return;
  }
  if (current.length < 11) selected.value = [...current, player.id];
}

function selectedPlayers(side: Side) {
  const selected = side === 'a' ? selectedA.value : selectedB.value;
  const roster = side === 'a' ? rosterA.value : rosterB.value;
  return selected
    .map((membershipId) => roster.find((player) => player.id === membershipId))
    .filter((player): player is SchoolTeamRosterPlayer => Boolean(player));
}

function validationMessage(): string {
  if (!teamAId.value || !teamBId.value) return 'Choose two saved School Teams.';
  if (teamAId.value === teamBId.value) return 'Choose two different saved School Teams.';
  if (selectedA.value.length !== 11 || selectedB.value.length !== 11)
    return 'Explicitly select exactly 11 eligible players for each playing XI.';
  if (!captainA.value || !captainB.value || !wicketkeeperA.value || !wicketkeeperB.value)
    return 'Choose a captain and wicketkeeper from each playing XI.';
  const profileIdsA = selectedPlayers('a').map((player) => player.player_profile_id);
  const profileIdsB = selectedPlayers('b').map((player) => player.player_profile_id);
  if (new Set(profileIdsA).size !== 11 || new Set(profileIdsB).size !== 11)
    return 'A playing XI cannot contain the same canonical player twice.';
  if (profileIdsA.some((id) => profileIdsB.includes(id)))
    return 'The same canonical player cannot represent both sides in one match.';
  if (matchType.value === 'limited' && !oversLimit.value)
    return 'Set the overs limit for this limited-overs match.';
  if (matchType.value === 'multi_day' && (!daysLimit.value || !oversPerDay.value))
    return 'Set days and overs per day for this multi-day match.';
  return '';
}

const canSubmit = computed(
  () => canCreateSchoolMatch.value && !loadingA.value && !loadingB.value && !validationMessage(),
);

async function createMatch() {
  const validation = validationMessage();
  if (validation || creating.value || !canCreateSchoolMatch.value) {
    error.value = validation || 'Your School membership cannot create matches.';
    return;
  }
  const payload: SchoolMatchCreate = {
    team_a: {
      team_id: teamAId.value,
      playing_xi_membership_ids: [...selectedA.value],
      captain_membership_id: captainA.value,
      wicketkeeper_membership_id: wicketkeeperA.value,
    },
    team_b: {
      team_id: teamBId.value,
      playing_xi_membership_ids: [...selectedB.value],
      captain_membership_id: captainB.value,
      wicketkeeper_membership_id: wicketkeeperB.value,
    },
    match_type: matchType.value,
    overs_limit: matchType.value === 'limited' ? oversLimit.value : null,
    days_limit: matchType.value === 'multi_day' ? daysLimit.value : null,
    overs_per_day: matchType.value === 'multi_day' ? oversPerDay.value : null,
    dls_enabled: dlsEnabled.value,
    toss_winner_side: tossWinnerSide.value,
    decision: decision.value,
  };
  creating.value = true;
  error.value = '';
  try {
    const result = await createSchoolMatch(organizationId.value, payload);
    await router.push({ name: 'GameScoringView', params: { gameId: result.game_id } });
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    creating.value = false;
  }
}

watch(
  [organizationId, canCreateSchoolMatch],
  ([, allowed]) => {
    if (allowed) void loadTeams();
    else resetSchoolState();
  },
  { immediate: true },
);
watch(teamAId, (teamId) => loadRoster('a', teamId));
watch(teamBId, (teamId) => loadRoster('b', teamId));
</script>

<template>
  <section class="panel" aria-labelledby="school-match-heading">
    <header>
      <p class="eyebrow">Phase 7I · Match setup</p>
      <h2 id="school-match-heading">Create a match from saved School Teams</h2>
      <p class="boundary">
        A Team roster is not a playing XI. Select exactly eleven eligible players for this match;
        no roster is selected automatically.
      </p>
      <RouterLink to="/setup">Use generic/manual match setup instead</RouterLink>
    </header>

    <p v-if="!canCreateSchoolMatch" class="notice" role="alert">
      Your active School role or entitlement does not permit match setup.
    </p>
    <p v-else-if="loadingTeams" role="status">Loading saved Teams…</p>
    <p v-else-if="teams.length < 2" class="notice" role="status">
      Create at least two active saved Teams before starting a School match.
    </p>

    <form v-else class="setup-form" @submit.prevent="createMatch">
      <div class="teams-grid">
        <fieldset>
          <legend>Team A and playing XI</legend>
          <label for="school-team-a">Saved Team</label>
          <select id="school-team-a" v-model="teamAId" data-testid="school-team-a">
            <option value="">Choose Team A…</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
          </select>
          <p v-if="loadingA" role="status">Loading Team A roster…</p>
          <ul v-else-if="teamA" class="roster" aria-label="Team A roster">
            <li v-for="player in rosterA" :key="player.id">
              <label>
                <input
                  type="checkbox"
                  :checked="selectedA.includes(player.id)"
                  :disabled="
                    !player.operationally_available ||
                    (selectedA.length >= 11 && !selectedA.includes(player.id))
                  "
                  @change="togglePlayer('a', player)"
                />
                <span>{{ player.player_name }}</span>
                <small>
                  {{
                    player.operationally_available
                      ? 'Eligible'
                      : `Unavailable (${player.status}/${player.school_player_status})`
                  }}
                </small>
              </label>
            </li>
          </ul>
          <p v-if="teamA">Selected {{ selectedA.length }}/11</p>
          <label for="captain-a">Captain</label>
          <select id="captain-a" v-model="captainA" :disabled="selectedA.length !== 11">
            <option value="">Choose from XI…</option>
            <option v-for="player in selectedPlayers('a')" :key="player.id" :value="player.id">
              {{ player.player_name }}
            </option>
          </select>
          <label for="keeper-a">Wicketkeeper</label>
          <select id="keeper-a" v-model="wicketkeeperA" :disabled="selectedA.length !== 11">
            <option value="">Choose from XI…</option>
            <option v-for="player in selectedPlayers('a')" :key="player.id" :value="player.id">
              {{ player.player_name }}
            </option>
          </select>
        </fieldset>

        <fieldset>
          <legend>Team B and playing XI</legend>
          <label for="school-team-b">Saved Team</label>
          <select id="school-team-b" v-model="teamBId" data-testid="school-team-b">
            <option value="">Choose Team B…</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
          </select>
          <p v-if="loadingB" role="status">Loading Team B roster…</p>
          <ul v-else-if="teamB" class="roster" aria-label="Team B roster">
            <li v-for="player in rosterB" :key="player.id">
              <label>
                <input
                  type="checkbox"
                  :checked="selectedB.includes(player.id)"
                  :disabled="
                    !player.operationally_available ||
                    (selectedB.length >= 11 && !selectedB.includes(player.id))
                  "
                  @change="togglePlayer('b', player)"
                />
                <span>{{ player.player_name }}</span>
                <small>
                  {{
                    player.operationally_available
                      ? 'Eligible'
                      : `Unavailable (${player.status}/${player.school_player_status})`
                  }}
                </small>
              </label>
            </li>
          </ul>
          <p v-if="teamB">Selected {{ selectedB.length }}/11</p>
          <label for="captain-b">Captain</label>
          <select id="captain-b" v-model="captainB" :disabled="selectedB.length !== 11">
            <option value="">Choose from XI…</option>
            <option v-for="player in selectedPlayers('b')" :key="player.id" :value="player.id">
              {{ player.player_name }}
            </option>
          </select>
          <label for="keeper-b">Wicketkeeper</label>
          <select id="keeper-b" v-model="wicketkeeperB" :disabled="selectedB.length !== 11">
            <option value="">Choose from XI…</option>
            <option v-for="player in selectedPlayers('b')" :key="player.id" :value="player.id">
              {{ player.player_name }}
            </option>
          </select>
        </fieldset>
      </div>

      <fieldset class="match-details">
        <legend>Existing match details</legend>
        <label for="match-type">Match type</label>
        <select id="match-type" v-model="matchType">
          <option value="limited">Limited overs</option>
          <option value="multi_day">Multi-day</option>
          <option value="custom">Custom</option>
        </select>
        <label v-if="matchType === 'limited'" for="overs-limit">Overs per innings</label>
        <input
          v-if="matchType === 'limited'"
          id="overs-limit"
          v-model.number="oversLimit"
          type="number"
          min="1"
          max="120"
        />
        <template v-if="matchType === 'multi_day'">
          <label for="days-limit">Days</label>
          <input id="days-limit" v-model.number="daysLimit" type="number" min="1" max="7" />
          <label for="overs-per-day">Overs per day</label>
          <input
            id="overs-per-day"
            v-model.number="oversPerDay"
            type="number"
            min="1"
            max="120"
          />
        </template>
        <label><input v-model="dlsEnabled" type="checkbox" /> Enable DLS</label>
        <label for="toss-winner">Toss winner</label>
        <select id="toss-winner" v-model="tossWinnerSide">
          <option value="team_a">{{ teamA?.name || 'Team A' }}</option>
          <option value="team_b">{{ teamB?.name || 'Team B' }}</option>
        </select>
        <fieldset class="decision">
          <legend>Toss decision</legend>
          <label><input v-model="decision" type="radio" value="bat" /> Bat</label>
          <label><input v-model="decision" type="radio" value="bowl" /> Bowl</label>
        </fieldset>
      </fieldset>

      <p v-if="validationMessage()" class="validation" role="status">
        {{ validationMessage() }}
      </p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button type="submit" :disabled="!canSubmit || creating" data-testid="create-school-match">
        {{ creating ? 'Creating match…' : 'Create match and open scoring' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.panel {
  padding: 1.4rem;
  border: 1px solid #3b4768;
  border-top: 0;
  background: #171e30;
  color: #eef2ff;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.boundary,
.notice,
.validation,
.error {
  padding: 0.8rem;
  border-left: 4px solid #70d7b0;
  background: #20283d;
}
.notice,
.validation {
  border-color: #f2bb5f;
}
.error {
  border-color: #e57b7b;
}
.setup-form {
  display: grid;
  gap: 1rem;
  margin-top: 1rem;
}
.teams-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
fieldset {
  display: grid;
  gap: 0.6rem;
  min-width: 0;
  padding: 1rem;
  border: 1px solid #445171;
  border-radius: 10px;
}
legend {
  padding: 0 0.4rem;
  font-weight: 700;
}
select,
input[type='number'] {
  padding: 0.65rem;
  border: 1px solid #607095;
  border-radius: 7px;
  background: #111827;
  color: inherit;
}
.roster {
  display: grid;
  gap: 0.35rem;
  max-height: 24rem;
  margin: 0;
  padding: 0;
  overflow: auto;
  list-style: none;
}
.roster label {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.55rem;
  border-radius: 6px;
  background: #222c43;
}
.roster small {
  color: #aebbd7;
}
.match-details {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.decision {
  display: flex;
  align-items: center;
}
button {
  justify-self: end;
  padding: 0.8rem 1rem;
  border: 0;
  border-radius: 8px;
  background: #70d7b0;
  color: #0d1b18;
  font-weight: 700;
  cursor: pointer;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
@media (max-width: 900px) {
  .teams-grid,
  .match-details {
    grid-template-columns: 1fr;
  }
}
</style>
