<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  archiveSchoolTeam,
  createSchoolTeam,
  listSchoolTeams,
  updateSchoolTeam,
} from '@/services/schoolAdminApi';
import type { SchoolTeam } from '@/types/schoolAdmin';

const { organizationId, organizationBasePath, canManageTeams } = useSchoolContext();
const teams = ref<SchoolTeam[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const success = ref('');
const editingId = ref<string | null>(null);
const form = reactive({ name: '', home_ground: '', season: '', coach_name: '' });

function clearMessages() {
  error.value = '';
  success.value = '';
}
function resetForm() {
  editingId.value = null;
  Object.assign(form, { name: '', home_ground: '', season: '', coach_name: '' });
}
function edit(team: SchoolTeam) {
  editingId.value = team.id;
  Object.assign(form, {
    name: team.name,
    home_ground: team.home_ground || '',
    season: team.season || '',
    coach_name: team.coach_name || '',
  });
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    teams.value = await listSchoolTeams(organizationId.value);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}
async function save() {
  clearMessages();
  saving.value = true;
  const payload = {
    name: form.name,
    home_ground: form.home_ground || null,
    season: form.season || null,
    coach_name: form.coach_name || null,
  };
  try {
    if (editingId.value) {
      await updateSchoolTeam(organizationId.value, editingId.value, payload);
      success.value = 'Team updated.';
    } else {
      await createSchoolTeam(organizationId.value, payload);
      success.value = 'Team created.';
    }
    resetForm();
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    saving.value = false;
  }
}
async function archive(team: SchoolTeam) {
  if (!window.confirm(`Archive ${team.name}? Its historical metadata will be retained.`)) return;
  clearMessages();
  try {
    await archiveSchoolTeam(organizationId.value, team.id);
    success.value = 'Team archived.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}

onMounted(load);
</script>

<template>
  <section class="panel" aria-labelledby="teams-heading">
    <header class="section-heading">
      <div>
        <p class="eyebrow">Persistent teams</p>
        <h2 id="teams-heading">Teams</h2>
      </div>
    </header>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-if="success" class="notice success" role="status">{{ success }}</div>
    <form v-if="canManageTeams" class="editor" @submit.prevent="save">
      <h3>{{ editingId ? 'Edit team' : 'Create team' }}</h3>
      <label>Team name <input v-model.trim="form.name" required maxlength="255" /></label>
      <label>Home ground <input v-model.trim="form.home_ground" maxlength="255" /></label>
      <label>Season <input v-model.trim="form.season" maxlength="50" /></label>
      <label>Coach name <input v-model.trim="form.coach_name" maxlength="255" /></label>
      <div class="button-row">
        <button type="submit" :aria-busy="saving" :disabled="saving">
          {{ editingId ? 'Save changes' : 'Create team' }}</button
        ><button v-if="editingId" type="button" class="secondary" @click="resetForm">Cancel</button>
      </div>
    </form>
    <p v-if="loading" role="status">Loading teams…</p>
    <div v-else-if="!teams.length" class="notice">No active teams yet.</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Team</th>
            <th>Season</th>
            <th>Home ground</th>
            <th>Coach</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="team in teams" :key="team.id">
            <td>
              <RouterLink :to="`${organizationBasePath}/${organizationId}/teams/${team.id}`">{{
                team.name
              }}</RouterLink>
            </td>
            <td>{{ team.season || '—' }}</td>
            <td>{{ team.home_ground || '—' }}</td>
            <td>{{ team.coach_name || '—' }}</td>
            <td>
              <span class="status">{{ team.status }}</span>
            </td>
            <td>
              <div class="button-row">
                <RouterLink :to="`${organizationBasePath}/${organizationId}/teams/${team.id}`"
                  >Roster</RouterLink
                ><button
                  v-if="canManageTeams"
                  type="button"
                  class="compact secondary"
                  @click="edit(team)"
                >
                  Edit</button
                ><button
                  v-if="canManageTeams"
                  type="button"
                  class="compact danger"
                  @click="archive(team)"
                >
                  Archive
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
.editor {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  margin: 1rem 0 1.5rem;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #20283d;
}
.editor h3,
.button-row {
  grid-column: 1 / -1;
}
label {
  display: grid;
  gap: 0.3rem;
}
input {
  width: 100%;
}
.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.compact {
  padding: 0.35rem 0.55rem;
  font-size: 0.9rem;
}
.danger {
  background: #8f3535;
  border-color: #b84d4d;
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
  min-width: 850px;
}
.status {
  text-transform: capitalize;
}
a {
  color: #9fd9ff;
}
@media (max-width: 720px) {
  .editor {
    grid-template-columns: 1fr;
  }
}
</style>
