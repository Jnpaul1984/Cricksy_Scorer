<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  createOrganizationSelectionPlan,
  getOrganizationSelectionCandidates,
  getOrganizationSelectionPlan,
  listSchoolFixtures,
  listSchoolTeams,
  updateOrganizationSelectionPlan,
} from '@/services/schoolAdminApi';
import type {
  OrganizationSelectionAvailabilityState,
  OrganizationSelectionCandidate,
  OrganizationSelectionPlan,
  SchoolFixtureSummary,
  SchoolTeam,
} from '@/types/schoolAdmin';
import { organizationOperationError } from '@/utils/organizationOperations';

type AvailabilityFilter = OrganizationSelectionAvailabilityState | 'no_response' | 'all';

const route = useRoute();
const { organizationId, terminology, membership } = useSchoolContext();
const fixtureId = computed(() => String(route.params.fixtureId || ''));
const teamId = computed(() => String(route.params.teamId || ''));
const canEdit = computed(() =>
  ['owner', 'admin', 'coach'].includes(membership.value?.role || ''),
);

const team = ref<SchoolTeam | null>(null);
const fixture = ref<SchoolFixtureSummary | null>(null);
const plan = ref<OrganizationSelectionPlan | null>(null);
const candidates = ref<OrganizationSelectionCandidate[]>([]);
const xiIds = ref<string[]>([]);
const reserveIds = ref<string[]>([]);
const captainId = ref<string | null>(null);
const wicketkeeperId = ref<string | null>(null);
const availabilityFilter = ref<AvailabilityFilter>('all');
const loading = ref(true);
const creating = ref(false);
const saving = ref(false);
const missing = ref(false);
const error = ref('');
const conflict = ref('');
const success = ref('');
let loadGeneration = 0;

const candidateById = computed(
  () => new Map(candidates.value.map((candidate) => [candidate.roster_membership_id, candidate])),
);
const filteredCandidates = computed(() => {
  if (availabilityFilter.value === 'all') return candidates.value;
  if (availabilityFilter.value === 'no_response') {
    return candidates.value.filter((candidate) => candidate.availability_state === null);
  }
  return candidates.value.filter(
    (candidate) => candidate.availability_state === availabilityFilter.value,
  );
});
const opponentName = computed(() => {
  if (!fixture.value) return '';
  return fixture.value.team_a_id === teamId.value
    ? fixture.value.team_b_name
    : fixture.value.team_a_name;
});

function availabilityLabel(state: OrganizationSelectionAvailabilityState | null): string {
  if (state === null) return 'No response';
  return state[0].toUpperCase() + state.slice(1);
}

function playerName(rosterMembershipId: string): string {
  return candidateById.value.get(rosterMembershipId)?.player_name || 'Retained roster player';
}

function syncDraft(serverPlan: OrganizationSelectionPlan) {
  plan.value = serverPlan;
  xiIds.value = [...serverPlan.xi_roster_membership_ids];
  reserveIds.value = [...serverPlan.reserve_roster_membership_ids];
  captainId.value = serverPlan.captain_roster_membership_id;
  wicketkeeperId.value = serverPlan.wicketkeeper_roster_membership_id;
}

function clearWorkspace() {
  team.value = null;
  fixture.value = null;
  plan.value = null;
  candidates.value = [];
  xiIds.value = [];
  reserveIds.value = [];
  captainId.value = null;
  wicketkeeperId.value = null;
  availabilityFilter.value = 'all';
  missing.value = false;
  error.value = '';
  conflict.value = '';
  success.value = '';
}

async function load() {
  const generation = ++loadGeneration;
  const currentOrganizationId = organizationId.value;
  const currentTeamId = teamId.value;
  const currentFixtureId = fixtureId.value;
  clearWorkspace();
  loading.value = true;
  try {
    const [teams, fixtures] = await Promise.all([
      listSchoolTeams(currentOrganizationId),
      listSchoolFixtures(currentOrganizationId),
    ]);
    if (
      generation !== loadGeneration ||
      organizationId.value !== currentOrganizationId ||
      teamId.value !== currentTeamId ||
      fixtureId.value !== currentFixtureId
    ) {
      return;
    }
    team.value = teams.find((item) => item.id === currentTeamId) || null;
    fixture.value = fixtures.find((item) => item.fixture_id === currentFixtureId) || null;
    if (
      !team.value ||
      !fixture.value ||
      ![fixture.value.team_a_id, fixture.value.team_b_id].includes(currentTeamId)
    ) {
      throw Object.assign(new Error('Selection context not found'), { status: 404 });
    }

    try {
      const existing = await getOrganizationSelectionPlan(
        currentOrganizationId,
        currentTeamId,
        currentFixtureId,
      );
      if (generation !== loadGeneration) return;
      syncDraft(existing);
      const response = await getOrganizationSelectionCandidates(currentOrganizationId, existing.id);
      if (generation !== loadGeneration) return;
      candidates.value = response.candidates;
    } catch (reason) {
      if (generation !== loadGeneration) return;
      if ((reason as { status?: number })?.status === 404) {
        missing.value = true;
        return;
      }
      throw reason;
    }
  } catch (reason) {
    if (generation !== loadGeneration) return;
    error.value = organizationOperationError(reason, 'selection plan');
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

async function createDraft() {
  if (!canEdit.value || creating.value) return;
  const generation = loadGeneration;
  creating.value = true;
  error.value = '';
  try {
    const created = await createOrganizationSelectionPlan(
      organizationId.value,
      teamId.value,
      fixtureId.value,
    );
    if (generation !== loadGeneration) return;
    syncDraft(created);
    const response = await getOrganizationSelectionCandidates(organizationId.value, created.id);
    if (generation !== loadGeneration) return;
    candidates.value = response.candidates;
    missing.value = false;
    success.value = 'Draft selection created.';
  } catch (reason) {
    if (generation === loadGeneration) {
      error.value = organizationOperationError(reason, 'selection plan');
    }
  } finally {
    if (generation === loadGeneration) creating.value = false;
  }
}

function addToXi(id: string) {
  if (!canEdit.value || xiIds.value.includes(id) || xiIds.value.length >= 11) return;
  reserveIds.value = reserveIds.value.filter((current) => current !== id);
  xiIds.value = [...xiIds.value, id];
}

function addToReserves(id: string) {
  if (!canEdit.value || reserveIds.value.includes(id)) return;
  xiIds.value = xiIds.value.filter((current) => current !== id);
  if (captainId.value === id) captainId.value = null;
  if (wicketkeeperId.value === id) wicketkeeperId.value = null;
  reserveIds.value = [...reserveIds.value, id];
}

function removeFromXi(id: string) {
  if (!canEdit.value) return;
  xiIds.value = xiIds.value.filter((current) => current !== id);
  if (captainId.value === id) captainId.value = null;
  if (wicketkeeperId.value === id) wicketkeeperId.value = null;
}

function removeFromReserves(id: string) {
  if (!canEdit.value) return;
  reserveIds.value = reserveIds.value.filter((current) => current !== id);
}

async function reloadAfterConflict() {
  const generation = ++loadGeneration;
  const currentOrganizationId = organizationId.value;
  const latest = await getOrganizationSelectionPlan(
    currentOrganizationId,
    teamId.value,
    fixtureId.value,
  );
  const response = await getOrganizationSelectionCandidates(currentOrganizationId, latest.id);
  if (generation !== loadGeneration || organizationId.value !== currentOrganizationId) return;
  syncDraft(latest);
  candidates.value = response.candidates;
  conflict.value = 'This draft changed elsewhere. The latest server version was loaded; review it before saving again.';
}

async function saveDraft() {
  if (!canEdit.value || !plan.value || saving.value) return;
  saving.value = true;
  error.value = '';
  conflict.value = '';
  success.value = '';
  const generation = loadGeneration;
  try {
    const updated = await updateOrganizationSelectionPlan(organizationId.value, plan.value.id, {
      expected_revision: plan.value.revision,
      xi_roster_membership_ids: xiIds.value,
      reserve_roster_membership_ids: reserveIds.value,
      captain_roster_membership_id: captainId.value,
      wicketkeeper_roster_membership_id: wicketkeeperId.value,
    });
    if (generation !== loadGeneration) return;
    syncDraft(updated);
    success.value = `Draft saved at revision ${updated.revision}.`;
  } catch (reason) {
    if (generation !== loadGeneration) return;
    if ((reason as { status?: number })?.status === 409) {
      try {
        await reloadAfterConflict();
      } catch (reloadReason) {
        error.value = organizationOperationError(reloadReason, 'selection plan');
      }
    } else {
      error.value = organizationOperationError(reason, 'selection plan');
    }
  } finally {
    saving.value = false;
  }
}

watch([organizationId, teamId, fixtureId], load, { immediate: true });
</script>

<template>
  <section class="selection-workspace" aria-labelledby="selection-heading">
    <header>
      <p class="eyebrow">{{ terminology.kindLabel }} match preparation</p>
      <h2 id="selection-heading">Draft selection</h2>
      <p>Selection is planning. The Playing XI in match setup remains match truth.</p>
    </header>

    <p v-if="loading" role="status">Loading draft selection…</p>
    <p v-else-if="error" class="notice error" role="alert">{{ error }}</p>
    <template v-else>
      <section v-if="team && fixture" class="context-card" aria-label="Selection context">
        <strong>{{ team.name }} vs {{ opponentName }}</strong>
        <span>{{ fixture.competition_name }}</span>
        <span>{{ fixture.scheduled_date ? new Date(fixture.scheduled_date).toLocaleString() : 'Date not set' }}</span>
      </section>

      <div v-if="missing" class="notice" data-test="missing-selection-plan">
        <p>No draft selection has been created for this Team and Fixture.</p>
        <button
          v-if="canEdit"
          type="button"
          data-test="create-selection-plan"
          :disabled="creating"
          @click="createDraft"
        >
          {{ creating ? 'Creating…' : 'Create draft selection' }}
        </button>
        <p v-else>This is a read-only workspace. Ask an Owner, Admin or Coach to create the draft.</p>
      </div>

      <template v-else-if="plan">
        <p class="revision">Revision {{ plan.revision }} · {{ canEdit ? 'Editable draft' : 'Read-only draft' }}</p>
        <p v-if="conflict" class="notice warning" role="alert">{{ conflict }}</p>
        <p v-if="success" class="notice success" role="status">{{ success }}</p>

        <label class="filter-label">
          Availability filter
          <select v-model="availabilityFilter" data-test="selection-availability-filter">
            <option value="all">All candidates</option>
            <option value="available">Available</option>
            <option value="unavailable">Unavailable</option>
            <option value="maybe">Maybe</option>
            <option value="no_response">No response</option>
          </select>
        </label>

        <div class="workspace-grid">
          <section class="candidate-panel" aria-labelledby="candidate-heading">
            <h3 id="candidate-heading">Candidates</h3>
            <p>Availability is advisory and never changes this draft automatically.</p>
            <ul class="player-list">
              <li v-for="candidate in filteredCandidates" :key="candidate.roster_membership_id">
                <div>
                  <strong>{{ candidate.player_name }}</strong>
                  <span
                    class="availability"
                    :data-state="candidate.availability_state || 'no_response'"
                    >{{ availabilityLabel(candidate.availability_state) }}</span
                  >
                </div>
                <div v-if="canEdit" class="actions">
                  <button
                    type="button"
                    :data-test="`add-xi-${candidate.roster_membership_id}`"
                    :disabled="xiIds.includes(candidate.roster_membership_id) || xiIds.length >= 11"
                    @click="addToXi(candidate.roster_membership_id)"
                  >
                    Add to XI
                  </button>
                  <button
                    type="button"
                    class="secondary"
                    :data-test="`add-reserve-${candidate.roster_membership_id}`"
                    :disabled="reserveIds.includes(candidate.roster_membership_id)"
                    @click="addToReserves(candidate.roster_membership_id)"
                  >
                    Add reserve
                  </button>
                </div>
              </li>
            </ul>
          </section>

          <section class="draft-panel" aria-labelledby="xi-heading">
            <h3 id="xi-heading">Planned XI · {{ xiIds.length }}/11</h3>
            <p v-if="!xiIds.length">No players selected yet.</p>
            <ul v-else class="player-list">
              <li v-for="id in xiIds" :key="id">
                <strong>{{ playerName(id) }}</strong>
                <div v-if="canEdit" class="actions">
                  <button type="button" class="secondary" @click="addToReserves(id)">Move to reserves</button>
                  <button type="button" class="danger" @click="removeFromXi(id)">Remove</button>
                </div>
              </li>
            </ul>

            <div class="role-grid">
              <label>
                Captain
                <select v-model="captainId" :disabled="!canEdit" data-test="selection-captain">
                  <option :value="null">Not set</option>
                  <option v-for="id in xiIds" :key="id" :value="id">{{ playerName(id) }}</option>
                </select>
              </label>
              <label>
                Wicketkeeper
                <select v-model="wicketkeeperId" :disabled="!canEdit" data-test="selection-wicketkeeper">
                  <option :value="null">Not set</option>
                  <option v-for="id in xiIds" :key="id" :value="id">{{ playerName(id) }}</option>
                </select>
              </label>
            </div>

            <h3>Reserves</h3>
            <p v-if="!reserveIds.length">No reserves selected.</p>
            <ul v-else class="player-list">
              <li v-for="id in reserveIds" :key="id">
                <strong>{{ playerName(id) }}</strong>
                <div v-if="canEdit" class="actions">
                  <button type="button" :disabled="xiIds.length >= 11" @click="addToXi(id)">Move to XI</button>
                  <button type="button" class="danger" @click="removeFromReserves(id)">Remove</button>
                </div>
              </li>
            </ul>

            <button
              v-if="canEdit"
              type="button"
              class="save"
              data-test="save-selection-plan"
              :disabled="saving"
              @click="saveDraft"
            >
              {{ saving ? 'Saving…' : 'Save draft' }}
            </button>
          </section>
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.selection-workspace { padding: 1.4rem; border: 1px solid #3b4768; border-top: 0; background: #171e30; }
.eyebrow { color: #70d7b0; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
.context-card { display: flex; flex-wrap: wrap; gap: 0.5rem 1.2rem; padding: 1rem; border: 1px solid #465475; border-radius: 10px; background: #20283d; }
.revision { font-weight: 700; }
.notice { margin: 0.9rem 0; padding: 0.9rem; border: 1px solid #53617c; border-radius: 8px; }
.error { border-color: #d56b6b; }
.warning { border-color: #e2b75b; }
.success { border-color: #58b893; }
.filter-label { display: inline-grid; gap: 0.35rem; margin: 1rem 0; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; }
.candidate-panel, .draft-panel { padding: 1rem; border: 1px solid #39445f; border-radius: 10px; background: #20283d; }
.player-list { display: grid; gap: 0.55rem; padding: 0; list-style: none; }
.player-list li { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; padding: 0.7rem; border: 1px solid #46516d; border-radius: 8px; }
.availability { display: block; margin-top: 0.2rem; color: #cbd5ee; }
.availability[data-state='available'] { color: #70d7b0; }
.availability[data-state='unavailable'] { color: #ff9b9b; }
.availability[data-state='maybe'] { color: #f3ca72; }
.actions { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.role-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin: 1rem 0; }
.role-grid label { display: grid; gap: 0.35rem; }
button, select { min-height: 2.5rem; }
button { padding: 0.45rem 0.7rem; border: 0; border-radius: 6px; background: #70d7b0; color: #10201b; font-weight: 700; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: 0.5; }
button.secondary { background: #9fb4dc; }
button.danger { background: #e58b8b; }
.save { width: 100%; margin-top: 1rem; }
@media (max-width: 760px) {
  .workspace-grid, .role-grid { grid-template-columns: 1fr; }
  .player-list li { align-items: stretch; flex-direction: column; }
  .actions button { flex: 1 1 9rem; }
}
</style>
