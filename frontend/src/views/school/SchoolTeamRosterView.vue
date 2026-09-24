<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  addTeamRosterPlayer,
  deactivateTeamRosterPlayer,
  getSchoolTeam,
  listSchoolPlayers,
  listTeamRoster,
  setTeamRosterPlayerStatus,
} from '@/services/schoolAdminApi';
import type { SchoolRosterPlayer, SchoolTeam, SchoolTeamRosterPlayer } from '@/types/schoolAdmin';

const route = useRoute();
const { organizationId, organizationBasePath, terminology, canManageTeamRoster } =
  useSchoolContext();
const teamId = computed(() => String(route.params.teamId || ''));
const team = ref<SchoolTeam | null>(null);
const roster = ref<SchoolTeamRosterPlayer[]>([]);
const activeSchoolPlayers = ref<SchoolRosterPlayer[]>([]);
const selectedMembershipId = ref('');
const loading = ref(true);
const error = ref('');
const success = ref('');
const availablePlayers = computed(() =>
  activeSchoolPlayers.value.filter(
    (player) =>
      !roster.value.some(
        (item) => item.school_player_membership_id === player.id && item.status === 'active',
      ),
  ),
);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [loadedTeam, loadedRoster, players] = await Promise.all([
      getSchoolTeam(organizationId.value, teamId.value),
      listTeamRoster(organizationId.value, teamId.value),
      listSchoolPlayers(organizationId.value, 'active'),
    ]);
    team.value = loadedTeam;
    roster.value = loadedRoster;
    activeSchoolPlayers.value = players;
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}
async function assign() {
  const membershipId = selectedMembershipId.value;
  if (!membershipId) return;
  error.value = '';
  success.value = '';
  try {
    const retained = roster.value.find(
      (item) => item.school_player_membership_id === membershipId && item.status === 'inactive',
    );
    if (retained)
      await setTeamRosterPlayerStatus(organizationId.value, teamId.value, retained.id, 'active');
    else await addTeamRosterPlayer(organizationId.value, teamId.value, membershipId);
    selectedMembershipId.value = '';
    success.value = retained ? 'Team membership reactivated.' : 'Player assigned to team.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}
async function setStatus(item: SchoolTeamRosterPlayer, status: 'active' | 'inactive') {
  error.value = '';
  success.value = '';
  try {
    if (status === 'inactive')
      await deactivateTeamRosterPlayer(organizationId.value, teamId.value, item.id);
    else await setTeamRosterPlayerStatus(organizationId.value, teamId.value, item.id, 'active');
    success.value =
      status === 'active' ? 'Team membership reactivated.' : 'Team membership deactivated.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}
onMounted(load);
</script>

<template>
  <section class="panel" aria-labelledby="team-roster-heading">
    <RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">← Teams</RouterLink>
    <header>
      <p class="eyebrow">Team roster</p>
      <h2 id="team-roster-heading">{{ team?.name || 'Team' }}</h2>
      <p>
        Assignments use the exact retained roster membership ID. The
        {{ terminology.kindLabel }} master roster remains canonical.
      </p>
    </header>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-if="success" class="notice success" role="status">{{ success }}</div>
    <form
      v-if="canManageTeamRoster && team?.status === 'active'"
      class="assign"
      @submit.prevent="assign"
    >
      <label
        >Add active {{ terminology.kindLabel }} player
        <select v-model="selectedMembershipId" required>
          <option value="">Select a player</option>
          <option v-for="player in availablePlayers" :key="player.id" :value="player.id">
            {{ player.player_name
            }}{{ player.student_identifier ? ` — ${player.student_identifier}` : '' }}
          </option>
        </select></label
      ><button type="submit">Assign player</button>
    </form>
    <p v-if="loading" role="status">Loading Team roster…</p>
    <div v-else-if="!roster.length" class="notice">
      This Team has no retained roster memberships.
    </div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Player</th>
            <th>Team status</th>
            <th>{{ terminology.kindLabel }} status</th>
            <th>Available</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in roster" :key="item.id">
            <td>{{ item.player_name }}</td>
            <td>{{ item.status }}</td>
            <td>{{ item.school_player_status }}</td>
            <td>{{ item.operationally_available ? 'Available' : 'Unavailable' }}</td>
            <td>
              <div class="button-row">
                <button
                  v-if="canManageTeamRoster && item.status === 'active'"
                  type="button"
                  class="compact danger"
                  @click="setStatus(item, 'inactive')"
                >
                  Deactivate</button
                ><button
                  v-if="
                    canManageTeamRoster &&
                    item.status === 'inactive' &&
                    item.school_player_status === 'active' &&
                    team?.status === 'active'
                  "
                  type="button"
                  class="compact"
                  @click="setStatus(item, 'active')"
                >
                  Reactivate
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
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
.assign {
  display: flex;
  align-items: end;
  gap: 0.8rem;
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #20283d;
}
.assign label {
  display: grid;
  flex: 1;
  gap: 0.3rem;
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
.table-wrap {
  overflow-x: auto;
}
table {
  min-width: 720px;
}
.button-row {
  display: flex;
  gap: 0.4rem;
}
.compact {
  padding: 0.35rem 0.55rem;
  font-size: 0.9rem;
}
.danger {
  background: #8f3535;
  border-color: #b84d4d;
}
a {
  color: #9fd9ff;
}
@media (max-width: 650px) {
  .assign {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
