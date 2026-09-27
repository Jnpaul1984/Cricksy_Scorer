<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  getOrganizationAttendance,
  listSchoolTeams,
  recordOrganizationPlayerAttendance,
} from '@/services/schoolAdminApi';
import type {
  OrganizationAttendanceFilter,
  OrganizationAttendanceRegister,
  OrganizationAttendanceState,
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
const eventId = computed(() => String(route.params.eventId || ''));
const canAccess = computed(
  () =>
    (entitlement.value?.capabilities || []).includes('organization_attendance') &&
    ['owner', 'admin', 'coach'].includes(membership.value?.role || ''),
);
const register = ref<OrganizationAttendanceRegister | null>(null);
const teams = ref<SchoolTeam[]>([]);
const stateFilter = ref<OrganizationAttendanceFilter | ''>('');
const teamFilter = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');

const states: Array<{ value: OrganizationAttendanceState; label: string }> = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'excused', label: 'Excused' },
];

function stateLabel(state: OrganizationAttendanceState | null): string {
  if (!state) return 'Unmarked';
  return states.find((item) => item.value === state)?.label || state;
}

async function load() {
  if (!canAccess.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    register.value = await getOrganizationAttendance(organizationId.value, eventId.value, {
      state: stateFilter.value || undefined,
      teamId: teamFilter.value || undefined,
      limit: 500,
    });
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

async function record(rosterMembershipId: string, state: OrganizationAttendanceState) {
  saving.value = true;
  error.value = '';
  try {
    await recordOrganizationPlayerAttendance(
      organizationId.value,
      eventId.value,
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
  if (canAccess.value) {
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
  <section class="attendance-view">
    <RouterLink :to="`${organizationBasePath}/${organizationId}/events`">← Calendar</RouterLink>
    <header>
      <p class="eyebrow">Private {{ terminology.kindLabel }} attendance</p>
      <h2>{{ register?.event_title || 'Event attendance' }}</h2>
      <p>Staff-recorded attendance is kept against the roster player and this event.</p>
    </header>

    <p v-if="!canAccess" class="notice">
      Attendance is available only to organization Owners, Admins and Coaches.
    </p>
    <p v-else-if="loading" role="status">Loading attendance…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template v-if="canAccess && register && !loading">
      <p v-if="register.event_status === 'cancelled'" class="notice">
        This event is cancelled. Existing attendance remains visible, but cannot be changed.
      </p>
      <section class="summary" aria-label="Attendance summary">
        <div><strong>{{ register.counts.present }}</strong><span>Present</span></div>
        <div><strong>{{ register.counts.absent }}</strong><span>Absent</span></div>
        <div><strong>{{ register.counts.excused }}</strong><span>Excused</span></div>
        <div><strong>{{ register.counts.unmarked }}</strong><span>Unmarked</span></div>
      </section>
      <p class="metric">
        Attendance:
        <strong>
          {{
            register.counts.attendance_percentage === null
              ? 'Not available'
              : `${register.counts.attendance_percentage}%`
          }}
        </strong>
      </p>

      <section class="controls">
        <label>
          Filter by state
          <select v-model="stateFilter" data-test="attendance-filter">
            <option value="">All states</option>
            <option value="present">Present</option>
            <option value="absent">Absent</option>
            <option value="excused">Excused</option>
            <option value="unmarked">Unmarked</option>
          </select>
        </label>
        <label>
          Team
          <select v-model="teamFilter" data-test="attendance-team-filter">
            <option value="">All eligible players</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">
              {{ team.name }}
            </option>
          </select>
        </label>
      </section>

      <section class="player-list" aria-label="Event attendance register">
        <article
          v-for="player in register.players"
          :key="player.roster_membership_id"
          class="player-row"
        >
          <div>
            <h3>{{ player.player_name }}</h3>
            <p :data-state="player.state || 'unmarked'">{{ stateLabel(player.state) }}</p>
            <small v-if="player.recorded_at">
              Staff-recorded {{ new Date(player.recorded_at).toLocaleString() }}
            </small>
            <small v-if="!player.eligible">Retained history · no longer eligible to update</small>
          </div>
          <div
            v-if="player.eligible && register.event_status !== 'cancelled'"
            class="state-actions"
          >
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
        <p v-if="register.players.length === 0" class="notice">
          No eligible players match this filter.
        </p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.attendance-view {
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
.error,
.metric {
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
  gap: 0.8rem;
}
.controls label {
  display: grid;
  gap: 0.35rem;
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
  margin: 0 0 0.25rem;
}
.player-row small {
  display: block;
  color: #b8c2dc;
}
.state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.state-actions .selected {
  border-color: #70d7b0;
  color: #70d7b0;
}
.error {
  color: #ff9e9e;
}
@media (max-width: 720px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .player-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
