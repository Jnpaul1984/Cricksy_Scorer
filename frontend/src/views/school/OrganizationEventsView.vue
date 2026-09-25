<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  cancelOrganizationEvent,
  createOrganizationEvent,
  getOrganizationCalendar,
  listOrganizationEvents,
  listSchoolPlayers,
  listSchoolTeams,
  updateOrganizationEvent,
} from '@/services/schoolAdminApi';
import type {
  OrganizationCalendarItem,
  OrganizationEvent,
  OrganizationEventInput,
  OrganizationEventParticipantScope,
  OrganizationEventType,
  SchoolRosterPlayer,
  SchoolTeam,
} from '@/types/schoolAdmin';

const { organizationId, terminology, canViewEvents, canManageEvents } = useSchoolContext();
const events = ref<OrganizationEvent[]>([]);
const calendarItems = ref<OrganizationCalendarItem[]>([]);
const teams = ref<SchoolTeam[]>([]);
const players = ref<SchoolRosterPlayer[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const editingId = ref<string | null>(null);

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
  if (!canViewEvents.value) return;
  loading.value = true;
  error.value = '';
  try {
    const [eventResult, calendar, teamRows, playerRows] = await Promise.all([
      listOrganizationEvents(organizationId.value, { includeCancelled: true, limit: 100 }),
      getOrganizationCalendar(organizationId.value, { includeCancelled: true, limit: 100 }),
      listSchoolTeams(organizationId.value),
      listSchoolPlayers(organizationId.value),
    ]);
    events.value = eventResult.items;
    calendarItems.value = calendar.items;
    teams.value = teamRows;
    players.value = playerRows;
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  error.value = '';
  try {
    const payload = eventPayload();
    if (editingId.value) {
      await updateOrganizationEvent(organizationId.value, editingId.value, payload);
    } else {
      await createOrganizationEvent(organizationId.value, payload);
    }
    resetForm();
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
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
  try {
    await cancelOrganizationEvent(organizationId.value, event.id);
    if (editingId.value === event.id) resetForm();
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}

function eventFor(item: OrganizationCalendarItem): OrganizationEvent | undefined {
  return item.source_type === 'organization_event'
    ? events.value.find((event) => event.id === item.source_id)
    : undefined;
}

onMounted(load);
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

    <form v-if="canManageEvents" class="event-form" data-test="event-form" @submit.prevent="save">
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
          <p>Status: {{ item.status }}</p>
        </div>
        <div v-if="canManageEvents && eventFor(item)?.status === 'scheduled'" class="actions">
          <button type="button" class="secondary" @click="beginEdit(eventFor(item)!)">Edit</button>
          <button type="button" class="danger" @click="cancel(eventFor(item)!)">Cancel</button>
        </div>
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
.actions {
  display: flex;
  gap: 0.6rem;
}
.secondary {
  background: #33415f;
}
.danger {
  background: #9f3a4a;
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
