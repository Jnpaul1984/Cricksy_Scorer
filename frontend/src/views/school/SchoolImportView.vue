<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import { applyPlayerImport, previewPlayerImport } from '@/services/schoolAdminApi';
import type {
  ImportResolutionAction,
  PlayerImportPreview,
  PlayerImportPreviewRow,
  PlayerImportResult,
} from '@/types/schoolAdmin';

interface ResolutionDraft {
  action: ImportResolutionAction | '';
  membershipId: string;
  teamId: string;
}

const {
  organizationId,
  organizationBasePath,
  terminology,
  canImport,
  canManageRosterLifecycle,
} = useSchoolContext();
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const mapping = reactive({
  player_name: '',
  student_identifier: '',
  year_group: '',
  team_name: '',
});
const preview = ref<PlayerImportPreview | null>(null);
const result = ref<PlayerImportResult | null>(null);
const resolutions = reactive<Record<number, ResolutionDraft>>({});
const previewing = ref(false);
const applying = ref(false);
const error = ref('');
const conflict = ref('');

const mappingPayload = computed(() =>
  Object.fromEntries(
    Object.entries(mapping)
      .filter(([, source]) => source.trim())
      .map(([target, source]) => [source.trim(), target]),
  ),
);
const requiredRows = computed(
  () => preview.value?.rows.filter((row) => row.resolution_required) || [],
);

function candidateFor(row: PlayerImportPreviewRow, id: string) {
  return row.candidate_memberships.find(
    (candidate) => candidate.school_player_membership_id === id,
  );
}
function resolutionComplete(row: PlayerImportPreviewRow): boolean {
  if (!row.resolution_required) return true;
  const draft = resolutions[row.source_row_number];
  if (!draft?.action) return false;
  if (['use_existing', 'reactivate_existing'].includes(draft.action) && !draft.membershipId)
    return false;
  if (draft.action === 'reactivate_existing') {
    if (
      !canManageRosterLifecycle.value ||
      candidateFor(row, draft.membershipId)?.status !== 'inactive'
    )
      return false;
  }
  if (draft.action === 'use_existing' && candidateFor(row, draft.membershipId)?.status !== 'active')
    return false;
  if (row.values.team_name && !(draft.teamId || row.resolved_team_id)) return false;
  return true;
}
const incompleteCount = computed(
  () => requiredRows.value.filter((row) => !resolutionComplete(row)).length,
);

function resetImport() {
  preview.value = null;
  result.value = null;
  error.value = '';
  conflict.value = '';
  file.value = null;
  Object.keys(resolutions).forEach((key) => delete resolutions[Number(key)]);
  Object.assign(mapping, {
    player_name: '',
    student_identifier: '',
    year_group: '',
    team_name: '',
  });
  if (fileInput.value) fileInput.value.value = '';
}
function onFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0] || null;
  error.value = '';
  if (!selected) {
    file.value = null;
    return;
  }
  const extension = selected.name.toLowerCase().split('.').pop();
  if (!['csv', 'xlsx'].includes(extension || '')) {
    error.value = 'Choose a .csv or .xlsx file. Legacy .xls is not supported.';
    file.value = null;
    return;
  }
  if (selected.size > 2 * 1024 * 1024) {
    error.value = 'The file exceeds the 2 MiB upload limit.';
    file.value = null;
    return;
  }
  file.value = selected;
}
async function createPreview() {
  if (!file.value || !canImport.value) return;
  previewing.value = true;
  error.value = '';
  conflict.value = '';
  result.value = null;
  try {
    preview.value = await previewPlayerImport(
      organizationId.value,
      file.value,
      mappingPayload.value,
    );
    Object.keys(resolutions).forEach((key) => delete resolutions[Number(key)]);
    for (const row of preview.value.rows) {
      resolutions[row.source_row_number] = {
        action: '',
        membershipId: '',
        teamId: row.resolved_team_id || '',
      };
    }
  } catch (reason) {
    error.value = friendlyError(reason);
  } finally {
    previewing.value = false;
  }
}
function friendlyError(reason: unknown) {
  const status = (reason as { status?: number })?.status;
  if (status === 403)
    return `Your ${terminology.value.kindLabel} role cannot perform this import action.`;
  if (status === 404)
    return `This ${terminology.value.kindLabel} or import preview is unavailable.`;
  if (status === 422) return `The import could not be validated: ${getErrorMessage(reason)}`;
  return getErrorMessage(reason);
}
function buildResolutions() {
  if (!preview.value) return [];
  return preview.value.rows.flatMap((row) => {
    const draft = resolutions[row.source_row_number];
    if (!draft?.action) return [];
    const item: {
      source_row_number: number;
      action: ImportResolutionAction;
      school_player_membership_id?: string;
      team_id?: string;
    } = {
      source_row_number: row.source_row_number,
      action: draft.action,
    };
    if (['use_existing', 'reactivate_existing'].includes(draft.action) && draft.membershipId)
      item.school_player_membership_id = draft.membershipId;
    if (row.values.team_name && draft.action !== 'skip' && (draft.teamId || row.resolved_team_id))
      item.team_id = draft.teamId || row.resolved_team_id || undefined;
    return [item];
  });
}
async function applyImport() {
  if (!preview.value || incompleteCount.value) return;
  applying.value = true;
  error.value = '';
  conflict.value = '';
  try {
    result.value = await applyPlayerImport(
      organizationId.value,
      preview.value.import_id,
      buildResolutions(),
    );
  } catch (reason) {
    const status = (reason as { status?: number })?.status;
    if (status === 410) {
      error.value = 'This preview expired. Upload the file again to create a new preview.';
      preview.value = null;
    } else if (status === 409)
      conflict.value = 'This preview was already applied or is being applied. It was not retried.';
    else error.value = friendlyError(reason);
  } finally {
    applying.value = false;
  }
}
function availableActions(
  row: PlayerImportPreviewRow,
): Array<{ value: ImportResolutionAction; label: string }> {
  const actions: Array<{ value: ImportResolutionAction; label: string }> = [
    { value: 'create_new', label: 'Create a separate player' },
    { value: 'skip', label: 'Skip this row' },
  ];
  if (row.candidate_memberships.some((candidate) => candidate.status === 'active')) {
    actions.splice(1, 0, { value: 'use_existing', label: 'Use active existing player' });
  }
  if (
    canManageRosterLifecycle.value &&
    row.candidate_memberships.some((candidate) => candidate.status === 'inactive')
  ) {
    actions.splice(-1, 0, { value: 'reactivate_existing', label: 'Reactivate inactive player' });
  }
  return actions;
}
watch(organizationId, resetImport);
</script>

<template>
  <section class="panel" aria-labelledby="import-heading">
    <header>
      <p class="eyebrow">Bulk player import</p>
      <h2 id="import-heading">Upload → Map → Preview → Resolve → Apply → Results</h2>
      <p>
        CSV and XLSX only. Maximum 2 MiB, 1,000 data rows, and 32 columns. Legacy XLS and macros are
        not supported.
      </p>
    </header>
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-if="conflict" class="notice warning" role="alert">{{ conflict }}</div>
    <div v-if="!canImport" class="notice warning" role="status">
      Your {{ terminology.kindLabel }} role is read-only. Player imports are available to owners,
      admins, and coaches.
    </div>
    <section v-else-if="!result" class="upload-card" aria-labelledby="upload-heading">
      <h3 id="upload-heading">1. Upload and map</h3>
      <label
        >Roster file
        <input
          ref="fileInput"
          type="file"
          accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          @change="onFile"
      /></label>
      <fieldset>
        <legend>Optional column mapping</legend>
        <p>Enter the exact source header for any non-standard column.</p>
        <div class="mapping-grid">
          <label
            >Player name header
            <input v-model="mapping.player_name" placeholder="Student Name" /></label
          ><label
            >Student ID header
            <input v-model="mapping.student_identifier" placeholder="ID Number" /></label
          ><label>Year group header <input v-model="mapping.year_group" placeholder="Form" /></label
          ><label
            >Team header <input v-model="mapping.team_name" placeholder="Cricket Team"
          /></label>
        </div>
      </fieldset>
      <button
        data-test="preview-import"
        type="button"
        :disabled="!file || previewing || !canImport"
        :aria-busy="previewing"
        @click="createPreview"
      >
        Create preview
      </button>
    </section>

    <section v-if="preview && !result" aria-labelledby="preview-heading">
      <div class="preview-banner" role="status">
        <strong>Preview does not add or change players.</strong
        ><span
          >Review {{ preview.row_count }} rows from {{ preview.original_filename }}. Expires
          {{ new Date(preview.expires_at).toLocaleString() }}.</span
        >
      </div>
      <h3 id="preview-heading">2. Preview and resolve</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              <th>Player values</th>
              <th>Classification</th>
              <th>Validation</th>
              <th>Candidates and resolution</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in preview.rows" :key="row.source_row_number">
              <td>{{ row.source_row_number }}</td>
              <td>
                <strong>{{ row.values.player_name || 'Missing name' }}</strong
                ><br />ID: {{ row.values.student_identifier || '—' }}<br />Year:
                {{ row.values.year_group || '—' }}<br />Team: {{ row.values.team_name || '—' }}
              </td>
              <td>
                {{ row.classification.replace(/_/g, ' ') }}
                <p v-if="row.ambiguity_reason" class="warning-text">{{ row.ambiguity_reason }}</p>
              </td>
              <td>
                <ul v-if="row.validation_errors.length" class="error-list">
                  <li v-for="message in row.validation_errors" :key="message">{{ message }}</li>
                </ul>
                <ul v-if="row.warnings.length">
                  <li v-for="message in row.warnings" :key="message">{{ message }}</li>
                </ul>
                <span v-if="!row.validation_errors.length && !row.warnings.length">No issues</span>
              </td>
              <td>
                <template v-if="row.resolution_required"
                  ><label :for="`action-${row.source_row_number}`">Required decision</label
                  ><select
                    :id="`action-${row.source_row_number}`"
                    v-model="resolutions[row.source_row_number].action"
                    :data-test="`action-${row.source_row_number}`"
                  >
                    <option value="">Choose…</option>
                    <option
                      v-for="action in availableActions(row)"
                      :key="action.value"
                      :value="action.value"
                    >
                      {{ action.label }}
                    </option>
                  </select>
                  <label
                    v-if="
                      ['use_existing', 'reactivate_existing'].includes(
                        resolutions[row.source_row_number].action,
                      )
                    "
                    :for="`player-${row.source_row_number}`"
                    >Exact preview candidate</label
                  ><select
                    v-if="
                      ['use_existing', 'reactivate_existing'].includes(
                        resolutions[row.source_row_number].action,
                      )
                    "
                    :id="`player-${row.source_row_number}`"
                    v-model="resolutions[row.source_row_number].membershipId"
                  >
                    <option value="">Choose candidate…</option>
                    <option
                      v-for="candidate in row.candidate_memberships.filter((candidate) =>
                        resolutions[row.source_row_number].action === 'reactivate_existing'
                          ? candidate.status === 'inactive'
                          : candidate.status === 'active',
                      )"
                      :key="candidate.school_player_membership_id"
                      :value="candidate.school_player_membership_id"
                    >
                      {{ candidate.player_name }} — {{ candidate.status }}
                    </option>
                  </select>
                  <label
                    v-if="
                      row.values.team_name && resolutions[row.source_row_number].action !== 'skip'
                    "
                    :for="`team-${row.source_row_number}`"
                    >Exact Team</label
                  ><select
                    v-if="
                      row.values.team_name && resolutions[row.source_row_number].action !== 'skip'
                    "
                    :id="`team-${row.source_row_number}`"
                    v-model="resolutions[row.source_row_number].teamId"
                  >
                    <option value="">Choose Team…</option>
                    <option
                      v-for="candidate in row.team_candidates"
                      :key="candidate.team_id"
                      :value="candidate.team_id"
                    >
                      {{ candidate.team_name }} — {{ candidate.team_id }}
                    </option>
                  </select> </template
                ><span v-else>Backend-ready; no decision required.</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="apply-bar">
        <p v-if="incompleteCount" role="status">
          {{ incompleteCount }} required resolution{{
            incompleteCount === 1 ? '' : 's'
          }}
          incomplete.
        </p>
        <button
          data-test="apply-import"
          type="button"
          :disabled="Boolean(incompleteCount) || applying"
          :aria-busy="applying"
          @click="applyImport"
        >
          Apply reviewed import
        </button>
      </div>
    </section>

    <section v-if="result" aria-labelledby="result-heading">
      <h3 id="result-heading">Import results</h3>
      <dl class="summary-grid">
        <div v-for="(count, key) in result.summary" :key="key">
          <dt>{{ String(key).replace(/_/g, ' ') }}</dt>
          <dd>{{ count }}</dd>
        </div>
      </dl>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              <th>Outcome</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in result.rows" :key="row.source_row_number">
              <td>{{ row.source_row_number }}</td>
              <td>{{ row.outcome.replace(/_/g, ' ') }}</td>
              <td>{{ row.detail }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav class="result-links">
        <RouterLink :to="`${organizationBasePath}/${organizationId}/players`"
          >Go to Players</RouterLink
        ><RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">Go to Teams</RouterLink
        ><button type="button" class="secondary" @click="resetImport">Start another import</button>
      </nav>
    </section>
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
.upload-card {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #20283d;
}
.upload-card > label,
fieldset label,
td label {
  display: grid;
  gap: 0.3rem;
}
.mapping-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}
.preview-banner {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1rem 0;
  padding: 1rem;
  border: 2px solid #70d7b0;
  border-radius: 10px;
  background: #17352f;
}
.table-wrap {
  overflow-x: auto;
}
table {
  min-width: 1050px;
}
td select {
  width: 100%;
  margin: 0.25rem 0 0.6rem;
}
.warning-text,
.warning {
  color: #ffd990;
}
.error-list,
.error {
  color: #ffb1b1;
}
.notice {
  margin: 0.8rem 0;
  padding: 0.8rem;
  border: 1px solid currentColor;
  border-radius: 8px;
}
.apply-bar,
.result-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 0.8rem;
  margin-top: 1rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.7rem;
}
.summary-grid div {
  padding: 0.8rem;
  border: 1px solid #3b4768;
  border-radius: 8px;
  background: #20283d;
}
.summary-grid dt {
  text-transform: capitalize;
  color: #afbdd8;
}
.summary-grid dd {
  margin: 0.2rem 0 0;
  font-size: 1.5rem;
  font-weight: 700;
}
.result-links a {
  padding: 0.65rem 0.85rem;
  border-radius: 7px;
  color: #0d1b18;
  background: #70d7b0;
  font-weight: 700;
  text-decoration: none;
}
@media (max-width: 720px) {
  .mapping-grid {
    grid-template-columns: 1fr;
  }
  .apply-bar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
