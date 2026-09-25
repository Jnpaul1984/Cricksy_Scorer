<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  getOrganizationAvailability,
  listSchoolTeams,
  recordOrganizationPlayerAvailability,
  updateOrganizationAvailabilityDeadline,
} from '@/services/schoolAdminApi';
import type {
  OrganizationAvailabilityFilter,
  OrganizationAvailabilityState,
  OrganizationAvailabilitySummary,
  OrganizationAvailabilityTargetType,
  SchoolTeam,
} from '@/types/schoolAdmin';

const route = useRoute();
const {
  organizationId,
  organizationBasePath,
  terminology,
  membership,
  entitlement,
} = useSchoolContext();
const targetType = computed(
  () => String(route.params.targetType || 'event') as OrganizationAvailabilityTargetType,
);
const targetId = computed(() => String(route.params.targetId || ''));
const canView = computed(() =>
  (entitlement.value?.capabilities || []).includes('organization_availability'),
);
const canManage = computed(
  () => canView.value && ['owner', 'admin', 'coach'].includes(membership.value?.role || ''),
);
const summary = ref<OrganizationAvailabilitySummary | null>(null);
const teams = ref<SchoolTeam[]>([]);
const stateFilter = ref<OrganizationAvailabilityFilter | ''>('');
const teamFilter = ref('');
const deadline = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');

const states: Array<{ value: OrganizationAvailabilityState; label: string }> = [
  { value: 'available', label: 'Available' },
  { value: 'unavailable', label: 'Unavailable' },
  { value: 'maybe', label: 'Maybe' },
];

function localDateTime(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function stateLabel(state: OrganizationAvailabilityState | null): string {
  if (!state) return 'No response';
  return states.find((item) => item.value === state)?.label || state;
}

async function load() {
  if (!canView.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    summary.value = await getOrganizationAvailability(
      organizationId.value,
      targetType.value,
      targetId.value,
      {
        state: stateFilter.value || undefined,
        teamId: teamFilter.value || undefined,
        limit: 500,
      },
    );
    deadline.value = localDateTime(summary.value.target.response_deadline);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

async function saveDeadline() {
  saving.value = true;
  error.value = '';
  try {
    await updateOrganizationAvailabilityDeadline(
      organizationId.value,
      targetType.value,
      targetId.value,
      deadline.value ? new Date(deadline.value).toISOString() : null,
    );
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    saving.value = false;
  }
}

async function record(rosterMembershipId: string, state: OrganizationAvailabilityState) {
  saving.value = true;
  error.value = '';
  try {
    await recordOrganizationPlayerAvailability(
      organizationId.value,
      targetType.value,
      targetId.value,
      rosterMembershipId,
      state,
    );
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    saving.value = false;
  }
}

watch([stateFilter, teamFilter], load);
onMounted(async () => {
  if (canView.value) {
    try {
      teams.value = await listSchoolTeams(organizationId.value);
    } catch (reason) {
      error.value = getErrorMessage(reason);
    }
  }
  await load();
});
</script>

<template>
  <section class="availability-view">
    <RouterLink :to="`${organizationBasePath}/${organizationId}/events`">← Calendar</RouterLink>
    <header>
      <p class="eyebrow">Shared {{ terminology.kindLabel }} availability</p>
      <h2>{{ summary?.target.title || 'Player availability' }}</h2>
      <p>
        Availability is an advisory planning signal. It does not select a playing XI or block
        scoring.
      </p>
    </header>

    <p v-if="!canView" class="notice">Availability is not enabled for this organization.</p>
    <p v-else-if="loading" role="status">Loading availability…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template v-if="canView && summary && !loading">
      <section class="summary" aria-label="Availability summary">
        <div><strong>{{ summary.counts.available }}</strong><span>Available</span></div>
        <div><strong>{{ summary.counts.unavailable }}</strong><span>Unavailable</span></div>
        <div><strong>{{ summary.counts.maybe }}</strong><span>Maybe</span></div>
        <div><strong>{{ summary.counts.no_response }}</strong><span>No response</span></div>
      </section>

      <section class="controls">
        <label>
          Filter by state
          <select v-model="stateFilter" data-test="availability-filter">
            <option value="">All states</option>
            <option value="available">Available</option>
            <option value="unavailable">Unavailable</option>
            <option value="maybe">Maybe</option>
            <option value="no_response">No response</option>
          </select>
        </label>
        <label>
          Team overview
          <select v-model="teamFilter" data-test="availability-team-filter">
            <option value="">All eligible players</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">
              {{ team.name }}
            </option>
          </select>
        </label>
        <form v-if="canManage" class="deadline" @submit.prevent="saveDeadline">
          <label>
            Response deadline (optional)
            <input v-model="deadline" type="datetime-local" data-test="availability-deadline" />
          </label>
          <button type="submit" :disabled="saving">Save deadline</button>
        </form>
        <p v-else>
          Deadline:
          {{
            summary.target.response_deadline
              ? new Date(summary.target.response_deadline).toLocaleString()
              : 'Not set'
          }}
        </p>
        <p v-if="summary.target.deadline_passed" class="late-note">
          The response deadline has passed. Authorized staff may still record a documented late
          correction.
        </p>
      </section>

      <section class="player-list" aria-label="Eligible player availability">
        <article
          v-for="player in summary.players"
          :key="player.roster_membership_id"
          class="player-row"
        >
          <div>
            <h3>{{ player.player_name }}</h3>
            <p :data-state="player.state || 'no_response'">{{ stateLabel(player.state) }}</p>
            <small v-if="player.recorded_at">
              Staff-recorded {{ new Date(player.recorded_at).toLocaleString() }}
              <span v-if="player.recorded_after_deadline"> · after deadline</span>
            </small>
          </div>
          <div v-if="canManage" class="state-actions">
            <button
              v-for="option in states"
              :key="option.value"
              type="button"
              :class="{ selected: player.state === option.value }"
              :disabled="saving"
              :data-test="`set-${option.value}-${player.roster_membership_id}`"
              @click="record(player.roster_membership_id, option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </article>
        <p v-if="summary.players.length === 0" class="notice">
          No eligible players match this filter.
        </p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.availability-view {
  padding: 1.25rem 0;
}
.eyebrow {
  margin: 1rem 0 0.25rem;
  color: #70d7b0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}
.summary div,
.controls,
.player-row,
.notice,
.error {
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #182036;
}
.summary div {
  display: grid;
  gap: 0.25rem;
  text-align: center;
}
.summary strong {
  font-size: 1.5rem;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.8rem;
}
.controls label,
.deadline {
  display: grid;
  gap: 0.35rem;
}
.deadline {
  grid-template-columns: minmax(220px, 1fr) auto;
  align-items: end;
}
.late-note {
  flex-basis: 100%;
  color: #ffd580;
}
.player-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}
.player-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.player-row h3,
.player-row p {
  margin: 0.2rem 0;
}
.state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.state-actions button.selected {
  color: #10231d;
  background: #70d7b0;
}
.error {
  border-color: #d56b6b;
}
@media (max-width: 700px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .player-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .deadline {
    grid-template-columns: 1fr;
  }
}
</style>
