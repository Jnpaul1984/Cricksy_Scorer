<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  createSchoolPlayer,
  deactivateSchoolPlayer,
  listSchoolPlayers,
  updateSchoolPlayer,
} from '@/services/schoolAdminApi';
import type { SchoolRosterPlayer } from '@/types/schoolAdmin';

const { organizationId, canManageRosterMetadata, canManageRosterLifecycle } = useSchoolContext();
const players = ref<SchoolRosterPlayer[]>([]);
const filter = ref<'active' | 'inactive' | 'all'>('active');
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const success = ref('');
const editing = ref<SchoolRosterPlayer | null>(null);
const createForm = reactive({ player_name: '', student_identifier: '', year_group: '' });
const editForm = reactive({ student_identifier: '', year_group: '' });

async function load() {
  loading.value = true;
  error.value = '';
  try {
    players.value = await listSchoolPlayers(organizationId.value, filter.value);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}
async function create() {
  saving.value = true;
  error.value = '';
  success.value = '';
  try {
    await createSchoolPlayer(organizationId.value, {
      player_name: createForm.player_name,
      student_identifier: createForm.student_identifier || null,
      year_group: createForm.year_group || null,
    });
    Object.assign(createForm, { player_name: '', student_identifier: '', year_group: '' });
    success.value = 'Player added to the School master roster.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    saving.value = false;
  }
}
function beginEdit(player: SchoolRosterPlayer) {
  editing.value = player;
  Object.assign(editForm, {
    student_identifier: player.student_identifier || '',
    year_group: player.year_group || '',
  });
}
async function saveMetadata() {
  if (!editing.value) return;
  saving.value = true;
  error.value = '';
  success.value = '';
  try {
    await updateSchoolPlayer(organizationId.value, editing.value.id, {
      student_identifier: editForm.student_identifier || null,
      year_group: editForm.year_group || null,
    });
    editing.value = null;
    success.value = 'School-local player details updated.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    saving.value = false;
  }
}
async function setLifecycle(player: SchoolRosterPlayer, status: 'active' | 'inactive') {
  error.value = '';
  success.value = '';
  try {
    if (status === 'inactive') await deactivateSchoolPlayer(organizationId.value, player.id);
    else await updateSchoolPlayer(organizationId.value, player.id, { status: 'active' });
    success.value =
      status === 'active' ? 'Roster membership reactivated.' : 'Roster membership deactivated.';
    await load();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  }
}

watch(filter, load);
onMounted(load);
</script>

<template>
  <section class="panel" aria-labelledby="players-heading">
    <header>
      <p class="eyebrow">Reusable player identities</p>
      <h2 id="players-heading">School master roster</h2>
      <p>
        Students can be rostered without a Cricksy login. A player can be reused across multiple
        teams.
      </p>
    </header>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-if="success" class="notice success" role="status">{{ success }}</div>
    <form v-if="canManageRosterMetadata" class="editor" @submit.prevent="create">
      <h3>Add player</h3>
      <label
        >Player name <input v-model.trim="createForm.player_name" required maxlength="255"
      /></label>
      <label
        >Student identifier <input v-model.trim="createForm.student_identifier" maxlength="128"
      /></label>
      <label>Year group <input v-model.trim="createForm.year_group" maxlength="64" /></label>
      <button type="submit" :disabled="saving" :aria-busy="saving">Add to roster</button>
    </form>
    <div class="toolbar">
      <label
        >Roster status
        <select v-model="filter">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="all">All retained records</option>
        </select></label
      >
    </div>
    <p v-if="loading" role="status">Loading master roster…</p>
    <div v-else-if="!players.length" class="notice">No players match this status.</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Player</th>
            <th>Student ID</th>
            <th>Year group</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="player in players" :key="player.id">
            <td>{{ player.player_name }}</td>
            <td>{{ player.student_identifier || '—' }}</td>
            <td>{{ player.year_group || '—' }}</td>
            <td>
              <span class="status">{{ player.status }}</span>
            </td>
            <td>
              <div class="button-row">
                <button
                  v-if="canManageRosterMetadata"
                  type="button"
                  class="compact secondary"
                  @click="beginEdit(player)"
                >
                  Edit metadata
                </button>
                <button
                  v-if="canManageRosterLifecycle && player.status === 'active'"
                  type="button"
                  class="compact danger"
                  @click="setLifecycle(player, 'inactive')"
                >
                  Deactivate
                </button>
                <button
                  v-if="canManageRosterLifecycle && player.status === 'inactive'"
                  type="button"
                  class="compact"
                  @click="setLifecycle(player, 'active')"
                >
                  Reactivate
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <dialog :open="Boolean(editing)" aria-labelledby="edit-player-title">
      <form v-if="editing" method="dialog" @submit.prevent="saveMetadata">
        <h3 id="edit-player-title">Edit {{ editing.player_name }}</h3>
        <label
          >Student identifier
          <input v-model.trim="editForm.student_identifier" maxlength="128" /></label
        ><label>Year group <input v-model.trim="editForm.year_group" maxlength="64" /></label>
        <div class="button-row">
          <button type="submit" :disabled="saving">Save</button
          ><button type="button" class="secondary" @click="editing = null">Cancel</button>
        </div>
      </form>
    </dialog>
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
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 0.8rem;
  align-items: end;
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #20283d;
}
.editor h3 {
  grid-column: 1/-1;
}
.editor label,
dialog label,
.toolbar label {
  display: grid;
  gap: 0.3rem;
}
.toolbar {
  display: flex;
  justify-content: flex-end;
  margin: 1rem 0;
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
  min-width: 760px;
}
.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.compact {
  padding: 0.35rem 0.55rem;
  font-size: 0.9rem;
}
.danger {
  background: #8f3535;
  border-color: #b84d4d;
}
.status {
  text-transform: capitalize;
}
dialog {
  max-width: 480px;
  border: 1px solid #657394;
  border-radius: 12px;
  background: #1b2235;
  color: #eef2ff;
}
dialog form {
  display: grid;
  gap: 1rem;
}
@media (max-width: 800px) {
  .editor {
    grid-template-columns: 1fr;
  }
}
</style>
