<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  cancelOrganizationEvent,
  createOrganizationEvent,
  deleteOrganizationEvent,
  getOrganizationCalendar,
  listOrganizationEvents,
  listSchoolPlayers,
  listSchoolTeams,
  notifyOrganizationEvent,
  updateOrganizationEvent,
} from '@/services/schoolAdminApi';
import type {
  OrganizationCalendarItem,
  OrganizationEvent,
  OrganizationEventInput,
  OrganizationEventNotificationResult,
  OrganizationEventParticipantScope,
  OrganizationEventType,
  SchoolRosterPlayer,
  SchoolTeam,
} from '@/types/schoolAdmin';
import { organizationOperationError } from '@/utils/organizationOperations';

const {
  organizationId,
  organizationBasePath,
  terminology,
  entitlement,
  canViewEvents,
  canManageEvents,
} = useSchoolContext();
const events = ref<OrganizationEvent[]>([]);
const calendarItems = ref<OrganizationCalendarItem[]>([]);
const teams = ref<SchoolTeam[]>([]);
const players = ref<SchoolRosterPlayer[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const notice = ref('');
const notificationResult = ref<{
  eventId: string;
  result: OrganizationEventNotificationResult;
} | null>(null);
const notifyingEventId = ref<string | null>(null);
const editingId = ref<string | null>(null);
let loadGeneration = 0;

const form = reactive({
  eventType: 'training' as OrganizationEventType,
  title: '',
  description: '',
  startAt: '',
  endAt: '',
  location: '',
  participantScope: 'organization' as OrganizationEventParticipantScope,
  teamIds: [] as string[],
  rosterMembershipIds: [] as string[],
});

const formTitle = computed(() => (editingId.value ? 'Edit event' : 'Create event'));
const canViewAvailability = computed(() =>
  (entitlement.value?.capabilities || []).includes('organization_availability'),
);
const canViewAttendance = computed(
  () =>
    canManageEvents.value &&
    (entitlement.value?.capabilities || []).includes('organization_attendance'),
);

function localDateTime(value: string): string {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    eventType: 'training',
    title: '',
    description: '',
    startAt: '',
    endAt: '',
    location: '',
    participantScope: 'organization',
    teamIds: [],
    rosterMembershipIds: [],
  });
}

function eventPayload(): OrganizationEventInput {
  return {
    event_type: form.eventType,
    title: form.title,
    description: form.description || null,
    start_at: new Date(form.startAt).toISOString(),
    end_at: form.endAt ? new Date(form.endAt).toISOString() : null,
    location: form.location,
    participant_scope: form.participantScope,
    team_ids: form.participantScope === 'teams' ? [...form.teamIds] : [],
    roster_membership_ids:
      form.participantScope === 'selected_players' ? [...form.rosterMembershipIds] : [],
  };
}

async function load() {
  const generation = ++loadGeneration;
  const currentOrganizationId = organizationId.value;
  events.value = [];
  calendarItems.value = [];
  teams.value = [];
  players.value = [];
  if (!canViewEvents.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const [eventResult, calendar, teamRows, playerRows] = await Promise.all([
      listOrganizationEvents(currentOrganizationId, { includeCancelled: true, limit: 100 }),
      getOrganizationCalendar(currentOrganizationId, { includeCancelled: true, limit: 100 }),
      listSchoolTeams(currentOrganizationId),
      listSchoolPlayers(currentOrganizationId),
    ]);
    if (generation !== loadGeneration || organizationId.value !== currentOrganizationId) return;
    events.value = eventResult.items;
    calendarItems.value = calendar.items;
    teams.value = teamRows;
    players.value = playerRows;
  } catch (reason) {
    if (generation !== loadGeneration) return;
    error.value = organizationOperationError(reason, 'calendar');
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

async function save() {
  saving.value = true;
  error.value = '';
  notice.value = '';
  const currentOrganizationId = organizationId.value;
  try {
    const payload = eventPayload();
    if (editingId.value) {
      await updateOrganizationEvent(currentOrganizationId, editingId.value, payload);
    } else {
      await createOrganizationEvent(currentOrganizationId, payload);
    }
    if (organizationId.value !== currentOrganizationId) return;
    notice.value = editingId.value ? 'Event updated.' : 'Event created.';
    resetForm();
    await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'event');
    }
  } finally {
    saving.value = false;
  }
}

function beginEdit(event: OrganizationEvent) {
  editingId.value = event.id;
  Object.assign(form, {
    eventType: event.event_type,
    title: event.title,
    description: event.description || '',
    startAt: localDateTime(event.start_at),
    endAt: event.end_at ? localDateTime(event.end_at) : '',
    location: event.location,
    participantScope: event.participant_scope,
    teamIds: [...event.team_ids],
    rosterMembershipIds: [...event.roster_membership_ids],
  });
}

async function cancel(event: OrganizationEvent) {
  if (!window.confirm(`Cancel ${event.title}? The event will remain in calendar history.`)) return;
  error.value = '';
  notice.value = '';
  saving.value = true;
  const currentOrganizationId = organizationId.value;
  try {
    await cancelOrganizationEvent(currentOrganizationId, event.id);
    if (organizationId.value !== currentOrganizationId) return;
    notice.value = 'Event cancelled. Its operational history remains retained.';
    if (editingId.value === event.id) resetForm();
    await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'event');
    }
  } finally {
    saving.value = false;
  }
}

async function remove(event: OrganizationEvent) {
  if (!window.confirm(`Delete ${event.title}? Events with retained history cannot be deleted.`))
    return;
  error.value = '';
  notice.value = '';
  saving.value = true;
  const currentOrganizationId = organizationId.value;
  try {
    await deleteOrganizationEvent(currentOrganizationId, event.id);
    if (organizationId.value !== currentOrganizationId) return;
    if (editingId.value === event.id) resetForm();
    notice.value = 'Event deleted.';
    await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'event');
    }
  } finally {
    saving.value = false;
  }
}

async function notify(event: OrganizationEvent, notificationType: 'update' | 'cancellation') {
  const generation = loadGeneration;
  const currentOrganizationId = organizationId.value;
  notifyingEventId.value = event.id;
  notificationResult.value = null;
  error.value = '';
  try {
    const result = await notifyOrganizationEvent(
      currentOrganizationId,
      event.id,
      notificationType,
    );
    if (generation !== loadGeneration || organizationId.value !== currentOrganizationId) return;
    notificationResult.value = { eventId: event.id, result };
  } catch (reason) {
    if (generation === loadGeneration && organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'event notification');
    }
  } finally {
    if (generation === loadGeneration) notifyingEventId.value = null;
  }
}

function audience(item: OrganizationCalendarItem): string {
  if (item.source_type === 'fixture') {
    const names = item.team_ids.map((id) => teams.value.find((team) => team.id === id)?.name || id);
    return names.length ? names.join(' vs ') : 'Fixture teams';
  }
  const event = eventFor(item);
  if (!event || event.participant_scope === 'organization') {
    return `Whole ${terminology.value.kindLabelLower}`;
  }
  if (event.participant_scope === 'teams') {
    return event.team_ids
      .map((id) => teams.value.find((team) => team.id === id)?.name || 'Unknown team')
      .join(', ');
  }
  return event.roster_membership_ids
    .map((id) => players.value.find((player) => player.id === id)?.player_name || 'Retained player')
    .join(', ');
}

function eventFor(item: OrganizationCalendarItem): OrganizationEvent | undefined {
  return item.source_type === 'organization_event'
    ? events.value.find((event) => event.id === item.source_id)
    : undefined;
}

watch(
  [organizationId, canViewEvents],
  () => {
    ++loadGeneration;
    resetForm();
    notice.value = '';
    notificationResult.value = null;
    notifyingEventId.value = null;
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <section class="events-view">
    <header>
      <p class="eyebrow">Shared {{ terminology.kindLabel }} calendar</p>
      <h2>Events and fixtures</h2>
      <p>
        Schedule training and other organization events. Existing cricket fixtures are shown as
        read-only calendar entries and remain authoritative in Competitions.
      </p>
    </header>

    <p v-if="!canViewEvents" class="notice">Events are not enabled for this organization.</p>
    <p v-else-if="loading" role="status">Loading calendar…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>

    <form
      v-if="canManageEvents"
      class="event-form"
      data-test="event-form"
      :aria-busy="saving"
      @submit.prevent="save"
    >
      <h3>{{ formTitle }}</h3>
      <label>
        Type
        <select v-model="form.eventType" data-test="event-type">
          <option value="training">Training</option>
          <option value="other">Other</option>
        </select>
      </label>
      <label>
        Title
        <input v-model="form.title" data-test="event-title" required maxlength="255" />
      </label>
      <label>
        Location
        <input v-model="form.location" data-test="event-location" required maxlength="255" />
      </label>
      <label>
        Starts
        <input v-model="form.startAt" data-test="event-start" required type="datetime-local" />
      </label>
      <label>
        Ends (optional)
        <input v-model="form.endAt" type="datetime-local" />
      </label>
      <label class="wide">
        Description (optional)
        <textarea v-model="form.description" maxlength="4000" rows="3" />
      </label>
      <label>
        Participants
        <select v-model="form.participantScope" data-test="participant-scope">
          <option value="organization">Whole {{ terminology.kindLabelLower }}</option>
          <option value="teams">Selected teams</option>
          <option value="selected_players">Selected roster players</option>
        </select>
      </label>
      <fieldset v-if="form.participantScope === 'teams'" class="wide">
        <legend>Teams</legend>
        <label v-for="team in teams" :key="team.id" class="choice">
          <input v-model="form.teamIds" type="checkbox" :value="team.id" />
          {{ team.name }}
        </label>
      </fieldset>
      <fieldset v-if="form.participantScope === 'selected_players'" class="wide">
        <legend>Roster players</legend>
        <label v-for="player in players" :key="player.id" class="choice">
          <input v-model="form.rosterMembershipIds" type="checkbox" :value="player.id" />
          {{ player.player_name }}
        </label>
      </fieldset>
      <div class="actions wide">
        <button type="submit" data-test="save-event" :disabled="saving">
          {{ saving ? 'Saving…' : editingId ? 'Save event' : 'Create event' }}
        </button>
        <button v-if="editingId" type="button" class="secondary" @click="resetForm">
          Cancel editing
        </button>
      </div>
    </form>

    <section v-if="canViewEvents && !loading" class="calendar-list" aria-label="Calendar entries">
      <h3>Calendar</h3>
      <p v-if="calendarItems.length === 0" class="notice">No calendar entries yet.</p>
      <article
        v-for="item in calendarItems"
        :key="`${item.source_type}:${item.source_id}`"
        class="calendar-card"
        :class="{ cancelled: item.status === 'cancelled' }"
      >
        <div>
          <p class="eyebrow">
            {{ item.source_type === 'fixture' ? 'Cricket fixture' : item.event_type }}
          </p>
          <h4>{{ item.title }}</h4>
          <p>
            <time :datetime="item.start_at">{{ new Date(item.start_at).toLocaleString() }}</time>
            <span v-if="item.location"> · {{ item.location }}</span>
          </p>
          <dl class="event-details">
            <div>
              <dt>Participants</dt>
              <dd>{{ item.participant_scope || 'Fixture teams' }}</dd>
            </div>
            <div>
              <dt>Audience</dt>
              <dd>{{ audience(item) }}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{{ item.status }}</dd>
            </div>
          </dl>
        </div>
        <div class="actions">
          <RouterLink
            v-if="canViewAvailability"
            class="availability-link"
            :to="`${organizationBasePath}/${organizationId}/availability/${
              item.source_type === 'organization_event' ? 'event' : 'fixture'
            }/${item.source_id}`"
          >
            Availability
          </RouterLink>
          <RouterLink
            v-if="canViewAttendance && item.source_type === 'organization_event'"
            class="attendance-link"
            :to="`${organizationBasePath}/${organizationId}/attendance/${item.source_id}`"
          >
            Attendance
          </RouterLink>
          <template v-if="canManageEvents && eventFor(item)?.status === 'scheduled'">
            <button
              type="button"
              class="secondary"
              :disabled="saving"
              @click="beginEdit(eventFor(item)!)"
            >
              Edit
            </button>
            <button
              type="button"
              class="danger"
              :disabled="saving"
              @click="cancel(eventFor(item)!)"
            >
              Cancel
            </button>
            <button
              type="button"
              class="secondary"
              :disabled="notifyingEventId !== null"
              :data-test="`notify-event-update-${item.source_id}`"
              @click="notify(eventFor(item)!, 'update')"
            >
              {{ notifyingEventId === item.source_id ? 'Sending…' : 'Notify update' }}
            </button>
          </template>
          <button
            v-if="canManageEvents && eventFor(item)?.status === 'cancelled'"
            type="button"
            class="secondary"
            :disabled="notifyingEventId !== null"
            :data-test="`notify-event-cancellation-${item.source_id}`"
            @click="notify(eventFor(item)!, 'cancellation')"
          >
            {{ notifyingEventId === item.source_id ? 'Sending…' : 'Notify cancellation' }}
          </button>
          <button
            v-if="canManageEvents && eventFor(item)"
            type="button"
            class="danger secondary"
            :disabled="saving"
            :data-test="`delete-event-${item.source_id}`"
            @click="remove(eventFor(item)!)"
          >
            Delete
          </button>
        </div>
        <p
          v-if="notificationResult?.eventId === item.source_id"
          class="dispatch-result"
          role="status"
          :data-test="`event-notification-result-${item.source_id}`"
        >
          Sent to {{ notificationResult.result.delivered_count }} safe in-app User{{
            notificationResult.result.delivered_count === 1 ? '' : 's'
          }}.
          {{ notificationResult.result.suppressed_by_preference_count }} suppressed by preference.
          {{ notificationResult.result.unresolved_roster_recipient_count }} roster participant{{
            notificationResult.result.unresolved_roster_recipient_count === 1 ? '' : 's'
          }} {{
            notificationResult.result.unresolved_roster_recipient_count === 1 ? 'is' : 'are'
          }} not directly reachable in-app.
        </p>
      </article>
    </section>
  </section>
</template>

<style scoped>
.events-view {
  padding: 1.25rem 0;
}
.eyebrow {
  margin: 0 0 0.25rem;
  color: #70d7b0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.event-form,
.calendar-card,
.notice,
.error {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #182036;
}
.event-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
  min-width: 0;
}
.event-form > * {
  min-width: 0;
}
.event-form input,
.event-form select,
.event-form textarea {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.event-form h3,
.wide {
  grid-column: 1 / -1;
}
label {
  display: grid;
  gap: 0.35rem;
}
.choice {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.calendar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.calendar-card.cancelled {
  opacity: 0.68;
}
.calendar-card h4,
.calendar-card p {
  margin: 0.25rem 0;
}
.event-details {
  display: grid;
  gap: 0.3rem;
  margin: 0.65rem 0 0;
}
.event-details div {
  display: grid;
  grid-template-columns: 7rem minmax(0, 1fr);
  gap: 0.5rem;
}
.event-details dt {
  color: #b8c2dc;
  font-weight: 700;
}
.event-details dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.secondary {
  background: #33415f;
}
.availability-link {
  align-content: center;
  padding: 0.55rem 0.8rem;
  border-radius: 7px;
  color: #10231d;
  background: #70d7b0;
  font-weight: 700;
  text-decoration: none;
}
.danger {
  background: #9f3a4a;
}
.dispatch-result {
  flex-basis: 100%;
  margin: 0.5rem 0 0;
  color: #cbd5ee;
}
.error {
  border-color: #d56b6b;
}
@media (max-width: 700px) {
  .event-form {
    grid-template-columns: 1fr;
  }
  .event-form h3,
  .wide {
    grid-column: auto;
  }
  .calendar-card {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
