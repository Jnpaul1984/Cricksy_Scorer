<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  addSchoolCompetitionTeam,
  createSchoolCompetition,
  createSchoolFixture,
  deleteSchoolCompetition,
  deleteSchoolFixture,
  getSchoolStandings,
  linkSchoolFixtureGame,
  listSchoolCompetitionFixtures,
  listSchoolCompetitions,
  listSchoolCompetitionTeams,
  listSchoolTeams,
  removeSchoolCompetitionTeam,
  updateSchoolCompetition,
  updateSchoolFixture,
} from '@/services/schoolAdminApi';
import type {
  SchoolCompetition,
  SchoolCompetitionTeam,
  SchoolFixture,
  SchoolStandings,
  SchoolTeam,
} from '@/types/schoolAdmin';

const {
  organizationId,
  canViewCompetitions,
  canManageCompetitions,
  canDeleteCompetitions,
  canLinkFixtures,
} = useSchoolContext();
const competitions = ref<SchoolCompetition[]>([]);
const entrants = ref<SchoolCompetitionTeam[]>([]);
const fixtures = ref<SchoolFixture[]>([]);
const standings = ref<SchoolStandings | null>(null);
const schoolTeams = ref<SchoolTeam[]>([]);
const selectedId = ref('');
const loading = ref(true);
const error = ref('');
const success = ref('');
const competitionForm = reactive({
  name: '',
  tournament_type: 'league' as SchoolCompetition['tournament_type'],
});
const entrantTeamId = ref('');
const competitionName = ref('');
const competitionStatus = ref<SchoolCompetition['status']>('upcoming');
const fixtureForm = reactive({ team_a_id: '', team_b_id: '', venue: '', scheduled_date: '' });
const linkGameIds = reactive<Record<string, string>>({});
const fixtureStatuses = reactive<Record<string, SchoolFixture['status']>>({});
const selected = computed(() => competitions.value.find((row) => row.id === selectedId.value));

async function loadCompetitionDetails() {
  if (!selectedId.value) {
    entrants.value = [];
    fixtures.value = [];
    standings.value = null;
    return;
  }
  [entrants.value, fixtures.value, standings.value] = await Promise.all([
    listSchoolCompetitionTeams(organizationId.value, selectedId.value),
    listSchoolCompetitionFixtures(organizationId.value, selectedId.value),
    getSchoolStandings(organizationId.value, selectedId.value),
  ]);
  const competition = competitions.value.find((row) => row.id === selectedId.value);
  competitionName.value = competition?.name || '';
  competitionStatus.value = competition?.status || 'upcoming';
  for (const fixture of fixtures.value) fixtureStatuses[fixture.id] = fixture.status;
}

async function load() {
  competitions.value = [];
  entrants.value = [];
  fixtures.value = [];
  standings.value = null;
  schoolTeams.value = [];
  selectedId.value = '';
  loading.value = true;
  error.value = '';
  try {
    [competitions.value, schoolTeams.value] = await Promise.all([
      listSchoolCompetitions(organizationId.value),
      listSchoolTeams(organizationId.value),
    ]);
    if (!competitions.value.some((row) => row.id === selectedId.value)) {
      selectedId.value = competitions.value[0]?.id || '';
    }
    await loadCompetitionDetails();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

async function run(action: () => Promise<unknown>, message: string) {
  error.value = '';
  success.value = '';
  try {
    await action();
    success.value = message;
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}

async function createCompetition() {
  await run(
    () =>
      createSchoolCompetition(organizationId.value, {
        name: competitionForm.name,
        tournament_type: competitionForm.tournament_type,
        status: 'upcoming',
      }),
    'Competition created.',
  );
  competitionForm.name = '';
}

async function removeCompetition() {
  if (!selected.value || !window.confirm(`Delete ${selected.value.name}?`)) return;
  const id = selected.value.id;
  selectedId.value = '';
  await run(() => deleteSchoolCompetition(organizationId.value, id), 'Competition deleted.');
}

async function saveCompetition() {
  await run(
    () =>
      updateSchoolCompetition(organizationId.value, selectedId.value, {
        name: competitionName.value,
        status: competitionStatus.value,
      }),
    'Competition updated.',
  );
}

async function addEntrant() {
  if (!selectedId.value || !entrantTeamId.value) return;
  await run(
    () => addSchoolCompetitionTeam(organizationId.value, selectedId.value, entrantTeamId.value),
    'Team added to competition.',
  );
  entrantTeamId.value = '';
}

async function removeEntrant(entrant: SchoolCompetitionTeam) {
  if (!window.confirm(`Remove ${entrant.team_name} from this competition?`)) return;
  await run(
    () => removeSchoolCompetitionTeam(organizationId.value, selectedId.value, entrant.id),
    'Team removed from competition.',
  );
}

async function createFixtureRow() {
  await run(
    () =>
      createSchoolFixture(organizationId.value, selectedId.value, {
        team_a_id: fixtureForm.team_a_id,
        team_b_id: fixtureForm.team_b_id,
        venue: fixtureForm.venue || null,
        scheduled_date: fixtureForm.scheduled_date
          ? new Date(fixtureForm.scheduled_date).toISOString()
          : null,
      }),
    'Fixture created. It remains unlinked until a match is explicitly selected.',
  );
  Object.assign(fixtureForm, { team_a_id: '', team_b_id: '', venue: '', scheduled_date: '' });
}

async function removeFixture(fixture: SchoolFixture) {
  if (!window.confirm(`Delete fixture ${fixture.team_a_name} vs ${fixture.team_b_name}?`)) return;
  await run(
    () => deleteSchoolFixture(organizationId.value, selectedId.value, fixture.id),
    'Fixture deleted.',
  );
}

async function saveFixture(fixture: SchoolFixture) {
  await run(
    () =>
      updateSchoolFixture(organizationId.value, selectedId.value, fixture.id, {
        status: fixtureStatuses[fixture.id],
      }),
    'Fixture status updated.',
  );
}

async function linkFixture(fixture: SchoolFixture) {
  const gameId = linkGameIds[fixture.id]?.trim();
  if (!gameId || !window.confirm(`Link this fixture to match ${gameId}?`)) return;
  await run(
    () => linkSchoolFixtureGame(organizationId.value, selectedId.value, fixture.id, gameId),
    'Fixture linked to the selected School match.',
  );
}

watch(organizationId, load, { immediate: true });
</script>

<template>
  <section class="panel" aria-labelledby="competitions-heading">
    <header>
      <p class="eyebrow">School competitions</p>
      <h2 id="competitions-heading">Competitions, fixtures, and standings</h2>
      <p>
        Fixtures are planning records. Match linkage is explicit and never creates a match
        automatically.
      </p>
    </header>
    <p v-if="!canViewCompetitions" class="notice error" role="alert">
      Competitions are not enabled for this organization.
    </p>
    <p v-else-if="loading" role="status">Loading competitions…</p>
    <template v-else>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <form v-if="canManageCompetitions" class="editor" @submit.prevent="createCompetition">
        <h3>Create competition</h3>
        <label>Name <input v-model.trim="competitionForm.name" required maxlength="255" /></label>
        <label
          >Format
          <select v-model="competitionForm.tournament_type">
            <option value="league">League</option>
            <option value="round-robin">Round robin</option>
            <option value="knockout">Knockout</option>
          </select>
        </label>
        <button type="submit">Create competition</button>
      </form>

      <p v-if="!competitions.length" class="notice">No School competitions yet.</p>
      <template v-else>
        <div class="selector-row">
          <label
            >Competition
            <select v-model="selectedId" @change="loadCompetitionDetails">
              <option
                v-for="competition in competitions"
                :key="competition.id"
                :value="competition.id"
              >
                {{ competition.name }} · {{ competition.status }}
              </option>
            </select>
          </label>
          <button
            v-if="canDeleteCompetitions"
            type="button"
            class="danger"
            @click="removeCompetition"
          >
            Delete competition
          </button>
        </div>

        <section v-if="selected" class="subpanel">
          <h3>{{ selected.name }}</h3>
          <p>{{ selected.tournament_type }} · {{ selected.status }}</p>
          <form v-if="canManageCompetitions" class="inline-form" @submit.prevent="saveCompetition">
            <input
              v-model.trim="competitionName"
              required
              maxlength="255"
              aria-label="Competition name"
            />
            <select v-model="competitionStatus" aria-label="Competition status">
              <option value="upcoming">Upcoming</option>
              <option value="ongoing">Ongoing</option>
              <option value="completed">Completed</option>
            </select>
            <button type="submit">Save competition</button>
          </form>
          <h4>Teams</h4>
          <form v-if="canManageCompetitions" class="inline-form" @submit.prevent="addEntrant">
            <select v-model="entrantTeamId" required aria-label="Team to add">
              <option value="" disabled>Select an active School team</option>
              <option
                v-for="team in schoolTeams.filter((row) => row.status === 'active')"
                :key="team.id"
                :value="team.id"
              >
                {{ team.name }}
              </option>
            </select>
            <button type="submit">Add team</button>
          </form>
          <ul v-if="entrants.length" class="entrant-list">
            <li v-for="entrant in entrants" :key="entrant.id">
              {{ entrant.team_name }}
              <button
                v-if="canDeleteCompetitions"
                type="button"
                class="compact danger"
                @click="removeEntrant(entrant)"
              >
                Remove
              </button>
            </li>
          </ul>
          <p v-else>No teams entered.</p>

          <h4>Fixtures</h4>
          <form
            v-if="canManageCompetitions"
            class="fixture-form"
            @submit.prevent="createFixtureRow"
          >
            <select v-model="fixtureForm.team_a_id" required aria-label="Fixture team A">
              <option value="" disabled>Team A</option>
              <option v-for="entry in entrants" :key="entry.id" :value="entry.team_id">
                {{ entry.team_name }}
              </option>
            </select>
            <select v-model="fixtureForm.team_b_id" required aria-label="Fixture team B">
              <option value="" disabled>Team B</option>
              <option v-for="entry in entrants" :key="entry.id" :value="entry.team_id">
                {{ entry.team_name }}
              </option>
            </select>
            <input v-model.trim="fixtureForm.venue" placeholder="Venue" maxlength="255" />
            <input
              v-model="fixtureForm.scheduled_date"
              type="datetime-local"
              aria-label="Scheduled date"
            />
            <button type="submit">Create fixture</button>
          </form>
          <div v-if="fixtures.length" class="cards">
            <article v-for="fixture in fixtures" :key="fixture.id">
              <strong>{{ fixture.team_a_name }} vs {{ fixture.team_b_name }}</strong>
              <p>{{ fixture.status }} · {{ fixture.venue || 'Venue not set' }}</p>
              <p>
                {{ fixture.game_id ? `Linked match: ${fixture.game_id}` : 'Not linked to a match' }}
              </p>
              <form
                v-if="canManageCompetitions"
                class="inline-form"
                @submit.prevent="saveFixture(fixture)"
              >
                <select
                  v-model="fixtureStatuses[fixture.id]"
                  :aria-label="`Status for ${fixture.team_a_name} vs ${fixture.team_b_name}`"
                >
                  <option value="scheduled">Scheduled</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <button type="submit">Save fixture</button>
              </form>
              <form
                v-if="canLinkFixtures && !fixture.game_id"
                class="inline-form"
                @submit.prevent="linkFixture(fixture)"
              >
                <input
                  v-model.trim="linkGameIds[fixture.id]"
                  required
                  placeholder="Existing School match ID"
                  aria-label="School match ID"
                />
                <button type="submit">Link match</button>
              </form>
              <button
                v-if="canDeleteCompetitions"
                type="button"
                class="compact danger"
                @click="removeFixture(fixture)"
              >
                Delete fixture
              </button>
            </article>
          </div>
          <p v-else>No fixtures scheduled.</p>

          <h4>Standings</h4>
          <div v-if="standings?.entries.length" class="table-wrap">
            <table data-test="school-standings">
              <thead>
                <tr>
                  <th>Team</th>
                  <th>P</th>
                  <th>W</th>
                  <th>L</th>
                  <th>D</th>
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in standings.entries" :key="entry.team_id">
                  <td>{{ entry.team_name }}</td>
                  <td>{{ entry.matches_played }}</td>
                  <td>{{ entry.matches_won }}</td>
                  <td>{{ entry.matches_lost }}</td>
                  <td>{{ entry.matches_drawn }}</td>
                  <td>{{ entry.points }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else>No standings data yet.</p>
          <p v-if="standings?.unresolved_completed_games" class="notice">
            {{ standings.unresolved_completed_games }} completed linked match(es) have no official
            result yet.
          </p>
        </section>
      </template>
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
.editor,
.subpanel {
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #20283d;
}
.editor,
.fixture-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 0.7rem;
  align-items: end;
}
.editor h3 {
  grid-column: 1 / -1;
}
label {
  display: grid;
  gap: 0.3rem;
}
.selector-row,
.inline-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: end;
}
.selector-row {
  justify-content: space-between;
  margin: 1rem 0;
}
.entrant-list {
  padding: 0;
  list-style: none;
}
.entrant-list li {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid #39445f;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.8rem;
  margin: 0.8rem 0 1.4rem;
}
.cards article {
  padding: 1rem;
  border: 1px solid #39445f;
  border-radius: 8px;
}
.compact {
  padding: 0.3rem 0.5rem;
  font-size: 0.85rem;
}
.danger {
  background: #8f3535;
  border-color: #b84d4d;
}
.table-wrap {
  overflow-x: auto;
}
</style>
