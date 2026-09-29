<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  getOrganizationAvailability,
  listSchoolTeams,
  recordOrganizationPlayerAvailability,
  sendOrganizationAvailabilityReminder,
  updateOrganizationAvailabilityDeadline,
} from '@/services/schoolAdminApi';
import type {
  OrganizationAvailabilityFilter,
  OrganizationAvailabilityReminderResult,
  OrganizationAvailabilityState,
  OrganizationAvailabilitySummary,
  OrganizationAvailabilityTargetType,
  SchoolTeam,
} from '@/types/schoolAdmin';
import { organizationOperationError } from '@/utils/organizationOperations';

const route = useRoute();
const { organizationId, organizationBasePath, terminology, membership, entitlement } =
  useSchoolContext();
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
const reminderResult = ref<OrganizationAvailabilityReminderResult | null>(null);
const reminding = ref(false);
let loadGeneration = 0;
let resettingFilters = false;

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

async function load(includeTeams = false) {
  const generation = ++loadGeneration;
  const currentOrganizationId = organizationId.value;
  const currentTargetType = targetType.value;
  const currentTargetId = targetId.value;
  if (!canView.value) {
    summary.value = null;
    teams.value = [];
    loading.value = false;
    return;
  }
  loading.value = summary.value === null;
  error.value = '';
  try {
    const summaryRequest = getOrganizationAvailability(
      currentOrganizationId,
      currentTargetType,
      currentTargetId,
      {
        state: stateFilter.value || undefined,
        teamId: teamFilter.value || undefined,
        limit: 500,
      },
    );
    const [nextSummary, nextTeams] = await Promise.all([
      summaryRequest,
      includeTeams ? listSchoolTeams(currentOrganizationId) : Promise.resolve(teams.value),
    ]);
    if (
      generation !== loadGeneration ||
      organizationId.value !== currentOrganizationId ||
      targetId.value !== currentTargetId ||
      targetType.value !== currentTargetType
    )
      return;
    summary.value = nextSummary;
    teams.value = nextTeams;
    deadline.value = localDateTime(nextSummary.target.response_deadline);
  } catch (reason) {
    if (generation !== loadGeneration) return;
    error.value = organizationOperationError(reason, 'availability register');
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

async function saveDeadline() {
  saving.value = true;
  error.value = '';
  const currentOrganizationId = organizationId.value;
  const currentTargetType = targetType.value;
  const currentTargetId = targetId.value;
  try {
    await updateOrganizationAvailabilityDeadline(
      currentOrganizationId,
      currentTargetType,
      currentTargetId,
      deadline.value ? new Date(deadline.value).toISOString() : null,
    );
    if (organizationId.value === currentOrganizationId) await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'availability deadline');
    }
  } finally {
    saving.value = false;
  }
}

async function record(rosterMembershipId: string, state: OrganizationAvailabilityState) {
  saving.value = true;
  error.value = '';
  const currentOrganizationId = organizationId.value;
  const currentTargetType = targetType.value;
  const currentTargetId = targetId.value;
  try {
    await recordOrganizationPlayerAvailability(
      currentOrganizationId,
      currentTargetType,
      currentTargetId,
      rosterMembershipId,
      state,
    );
    if (organizationId.value === currentOrganizationId) await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'availability response');
    }
  } finally {
    saving.value = false;
  }
}

async function sendReminder() {
  const generation = loadGeneration;
  const currentOrganizationId = organizationId.value;
  const currentTargetType = targetType.value;
  const currentTargetId = targetId.value;
  reminding.value = true;
  reminderResult.value = null;
  error.value = '';
  try {
    const result = await sendOrganizationAvailabilityReminder(
      currentOrganizationId,
      currentTargetType,
      currentTargetId,
    );
    if (
      generation !== loadGeneration ||
      organizationId.value !== currentOrganizationId ||
      targetType.value !== currentTargetType ||
      targetId.value !== currentTargetId
    )
      return;
    reminderResult.value = result;
  } catch (reason) {
    if (generation === loadGeneration && organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'availability reminder');
    }
  } finally {
    if (generation === loadGeneration) reminding.value = false;
  }
}

watch([stateFilter, teamFilter], () => {
  if (!resettingFilters) void load();
});
watch(
  [organizationId, targetType, targetId, canView],
  async () => {
    ++loadGeneration;
    resettingFilters = true;
    summary.value = null;
    teams.value = [];
    deadline.value = '';
    error.value = '';
    reminderResult.value = null;
    reminding.value = false;
    stateFilter.value = '';
    teamFilter.value = '';
    await nextTick();
    resettingFilters = false;
    await load(true);
  },
  { immediate: true },
);
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
        <div>
          <strong>{{ summary.counts.available }}</strong
          ><span>Available</span>
        </div>
        <div>
          <strong>{{ summary.counts.unavailable }}</strong
          ><span>Unavailable</span>
        </div>
        <div>
          <strong>{{ summary.counts.maybe }}</strong
          ><span>Maybe</span>
        </div>
        <div>
          <strong>{{ summary.counts.no_response }}</strong
          ><span>No response</span>
        </div>
      </section>

      <section class="controls" :aria-busy="loading || saving">
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
        <div v-if="canManage" class="reminder-action">
          <button
            type="button"
            data-test="send-availability-reminder"
            :disabled="reminding"
            @click="sendReminder"
          >
            {{ reminding ? 'Sending…' : 'Send staff reminder' }}
          </button>
          <p>
            Sends one bounded in-app operational reminder. It does not record or change player
            availability.
          </p>
        </div>
        <p v-if="reminderResult" class="dispatch-result" role="status">
          Reminder sent to {{ reminderResult.delivered_count }} staff User{{
            reminderResult.delivered_count === 1 ? '' : 's'
          }}; {{ reminderResult.suppressed_by_preference_count }} suppressed by preference.
          {{ reminderResult.no_response_count }} roster response{{
            reminderResult.no_response_count === 1 ? ' is' : 's are'
          }} still outstanding and not directly reachable in-app.
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
            <small v-if="!player.eligible" class="retained-note">
              Retained response · no longer eligible to update
            </small>
          </div>
          <div v-if="canManage && player.eligible" class="state-actions">
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
.reminder-action,
.dispatch-result {
  flex-basis: 100%;
}
.reminder-action p,
.dispatch-result {
  margin: 0.4rem 0 0;
  color: #cbd5ee;
}
.retained-note {
  display: block;
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
