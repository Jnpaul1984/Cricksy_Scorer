<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  createOrganizationAnnouncement,
  createOrganizationAnnouncementRevision,
  listOrganizationAnnouncements,
  listSchoolTeams,
  publishOrganizationAnnouncement,
  updateOrganizationAnnouncement,
} from '@/services/schoolAdminApi';
import type {
  OrganizationAnnouncementAudience,
  OrganizationAnnouncementDraft,
  OrganizationAnnouncementFeedItem,
  SchoolTeam,
} from '@/types/schoolAdmin';
import { organizationOperationError } from '@/utils/organizationOperations';

const {
  organizationId,
  terminology,
  canViewAnnouncements,
  canManageAnnouncements,
} = useSchoolContext();
const items = ref<OrganizationAnnouncementFeedItem[]>([]);
const teams = ref<SchoolTeam[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const notice = ref('');
const editingId = ref<string | null>(null);
const editingRevision = ref<number | null>(null);
let loadGeneration = 0;

const form = reactive({
  title: '',
  body: '',
  audienceType: 'organization' as OrganizationAnnouncementAudience,
  teamId: '',
});

const audienceLabel = computed(() => {
  if (form.audienceType === 'organization') return `Whole ${terminology.value.kindLabelLower}`;
  if (form.audienceType === 'staff') return 'Staff only';
  return teams.value.find((team) => team.id === form.teamId)?.name || 'Select a Team';
});

function resetForm() {
  editingId.value = null;
  editingRevision.value = null;
  Object.assign(form, { title: '', body: '', audienceType: 'organization', teamId: '' });
}

function beginEdit(item: OrganizationAnnouncementFeedItem | OrganizationAnnouncementDraft) {
  editingId.value = 'announcement_id' in item ? item.announcement_id : item.id;
  editingRevision.value = item.revision;
  Object.assign(form, {
    title: item.title,
    body: item.body,
    audienceType: item.audience_type,
    teamId: item.team_id || '',
  });
}

async function load() {
  const generation = ++loadGeneration;
  const currentOrganizationId = organizationId.value;
  items.value = [];
  teams.value = [];
  error.value = '';
  if (!canViewAnnouncements.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  try {
    const [feed, teamRows] = await Promise.all([
      listOrganizationAnnouncements(currentOrganizationId, { limit: 100 }),
      listSchoolTeams(currentOrganizationId),
    ]);
    if (generation !== loadGeneration || organizationId.value !== currentOrganizationId) return;
    items.value = feed.items;
    teams.value = teamRows;
  } catch (reason) {
    if (generation !== loadGeneration) return;
    error.value = organizationOperationError(reason, 'announcement feed');
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

async function saveDraft() {
  const currentOrganizationId = organizationId.value;
  saving.value = true;
  error.value = '';
  notice.value = '';
  try {
    const payload = {
      title: form.title,
      body: form.body,
      audience_type: form.audienceType,
      team_id: form.audienceType === 'team' ? form.teamId || null : null,
    };
    if (editingId.value && editingRevision.value !== null) {
      await updateOrganizationAnnouncement(currentOrganizationId, editingId.value, {
        ...payload,
        expected_revision: editingRevision.value,
      });
      notice.value = 'Draft updated. No notifications were sent.';
    } else {
      await createOrganizationAnnouncement(currentOrganizationId, payload);
      notice.value = 'Draft created. No notifications were sent.';
    }
    if (organizationId.value !== currentOrganizationId) return;
    resetForm();
    await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'announcement');
    }
  } finally {
    saving.value = false;
  }
}

async function publish(item: OrganizationAnnouncementFeedItem) {
  if (!window.confirm(`Publish “${item.title}” to ${audienceName(item)}?`)) return;
  const currentOrganizationId = organizationId.value;
  saving.value = true;
  error.value = '';
  notice.value = '';
  try {
    const publication = await publishOrganizationAnnouncement(
      currentOrganizationId,
      item.announcement_id,
      item.revision,
    );
    if (organizationId.value !== currentOrganizationId) return;
    notice.value = `Published version ${publication.publication_version}: ${publication.delivered_count} delivered, ${publication.suppressed_by_preference_count} suppressed.`;
    resetForm();
    await load();
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'announcement');
    }
  } finally {
    saving.value = false;
  }
}

async function startRevision(item: OrganizationAnnouncementFeedItem) {
  const currentOrganizationId = organizationId.value;
  saving.value = true;
  error.value = '';
  notice.value = '';
  try {
    const draft = await createOrganizationAnnouncementRevision(
      currentOrganizationId,
      item.announcement_id,
      item.revision,
    );
    if (organizationId.value !== currentOrganizationId) return;
    await load();
    beginEdit(draft);
    notice.value = `Draft revision ${draft.revision} created. Published versions remain unchanged.`;
  } catch (reason) {
    if (organizationId.value === currentOrganizationId) {
      error.value = organizationOperationError(reason, 'announcement revision');
    }
  } finally {
    saving.value = false;
  }
}

function audienceName(item: OrganizationAnnouncementFeedItem): string {
  if (item.audience_type === 'organization') return `whole ${terminology.value.kindLabelLower}`;
  if (item.audience_type === 'staff') return 'staff';
  return teams.value.find((team) => team.id === item.team_id)?.name || 'assigned Team staff';
}

function canStartRevision(item: OrganizationAnnouncementFeedItem): boolean {
  if (item.status !== 'published') return false;
  const currentDraftExists = items.value.some(
    (candidate) =>
      candidate.announcement_id === item.announcement_id && candidate.status === 'draft',
  );
  const latestVersion = Math.max(
    ...items.value
      .filter((candidate) => candidate.announcement_id === item.announcement_id)
      .map((candidate) => candidate.publication_version || 0),
  );
  return !currentDraftExists && item.publication_version === latestVersion;
}

watch(
  [organizationId, canViewAnnouncements],
  () => {
    ++loadGeneration;
    resetForm();
    notice.value = '';
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <section class="announcements-view">
    <header>
      <p class="eyebrow">Shared {{ terminology.kindLabel }} communication</p>
      <h2>Announcements</h2>
      <p>
        Publish structured organization, Team or staff updates. This feed does not support private
        messages, replies or reactions.
      </p>
    </header>

    <p v-if="!canViewAnnouncements" class="notice">Announcements are not enabled.</p>
    <p v-else-if="loading" role="status">Loading announcements…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>

    <form
      v-if="canManageAnnouncements"
      class="announcement-form"
      data-test="announcement-form"
      :aria-busy="saving"
      @submit.prevent="saveDraft"
    >
      <h3>{{ editingId ? 'Edit draft' : 'Create draft' }}</h3>
      <label>
        Title
        <input v-model="form.title" data-test="announcement-title" required maxlength="255" />
      </label>
      <label>
        Audience
        <select v-model="form.audienceType" data-test="announcement-audience">
          <option value="organization">Whole {{ terminology.kindLabelLower }}</option>
          <option value="team">Team</option>
          <option value="staff">Staff only</option>
        </select>
      </label>
      <label v-if="form.audienceType === 'team'">
        Team
        <select v-model="form.teamId" data-test="announcement-team" required>
          <option value="" disabled>Select a Team</option>
          <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
      </label>
      <label class="wide">
        Body
        <textarea
          v-model="form.body"
          data-test="announcement-body"
          required
          maxlength="6000"
          rows="6"
        />
      </label>
      <aside v-if="form.title || form.body" class="preview wide" aria-label="Announcement preview">
        <p class="eyebrow">Preview · {{ audienceLabel }}</p>
        <h4>{{ form.title || 'Untitled announcement' }}</h4>
        <p class="body">{{ form.body }}</p>
      </aside>
      <div class="actions wide">
        <button type="submit" data-test="save-announcement" :disabled="saving">
          {{ saving ? 'Saving…' : editingId ? 'Save draft' : 'Create draft' }}
        </button>
        <button v-if="editingId" type="button" class="secondary" @click="resetForm">
          Cancel editing
        </button>
      </div>
    </form>

    <section v-if="canViewAnnouncements && !loading" class="feed" aria-label="Announcement feed">
      <h3>Feed</h3>
      <p v-if="items.length === 0" class="notice">No announcements yet.</p>
      <article
        v-for="item in items"
        :key="`${item.announcement_id}:${item.status}:${item.publication_version || item.revision}`"
        class="announcement-card"
        :data-test="`announcement-${item.status}-${item.announcement_id}`"
      >
        <div>
          <p class="eyebrow">{{ item.status }} · {{ audienceName(item) }}</p>
          <h4>{{ item.title }}</h4>
          <p class="body">{{ item.body }}</p>
          <p v-if="item.published_at" class="metadata">
            Version {{ item.publication_version }} ·
            <time :datetime="item.published_at">{{ new Date(item.published_at).toLocaleString() }}</time>
          </p>
          <dl v-if="item.status === 'published'" class="delivery-summary">
            <div><dt>Eligible</dt><dd>{{ item.eligible_recipient_count }}</dd></div>
            <div><dt>Delivered</dt><dd>{{ item.delivered_count }}</dd></div>
            <div><dt>Suppressed</dt><dd>{{ item.suppressed_by_preference_count }}</dd></div>
            <div><dt>Unresolved</dt><dd>{{ item.unresolved_recipient_count }}</dd></div>
          </dl>
        </div>
        <div v-if="canManageAnnouncements" class="actions">
          <template v-if="item.status === 'draft'">
            <button type="button" class="secondary" :disabled="saving" @click="beginEdit(item)">
              Edit
            </button>
            <button
              type="button"
              data-test="publish-announcement"
              :disabled="saving"
              @click="publish(item)"
            >
              Publish
            </button>
          </template>
          <button
            v-else-if="canStartRevision(item)"
            type="button"
            class="secondary"
            :disabled="saving"
            @click="startRevision(item)"
          >
            New revision
          </button>
        </div>
      </article>
    </section>
  </section>
</template>

<style scoped>
.announcements-view { padding: 1.25rem 0; }
.eyebrow {
  margin: 0 0 0.25rem;
  color: #70d7b0;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.announcement-form,
.announcement-card,
.notice,
.error,
.preview {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #182036;
}
.announcement-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.announcement-form > * { min-width: 0; }
.announcement-form input,
.announcement-form select,
.announcement-form textarea { box-sizing: border-box; width: 100%; max-width: 100%; }
.announcement-form h3,
.wide { grid-column: 1 / -1; }
label { display: grid; gap: 0.35rem; }
.preview { background: #121a2c; }
.preview h4,
.announcement-card h4 { margin: 0.3rem 0; }
.body { white-space: pre-wrap; overflow-wrap: anywhere; }
.announcement-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.announcement-card > div:first-child { min-width: 0; flex: 1; }
.metadata { color: #b8c2dc; }
.delivery-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}
.delivery-summary div { padding: 0.55rem; border-radius: 7px; background: #11182a; }
.delivery-summary dt { color: #b8c2dc; font-size: 0.78rem; }
.delivery-summary dd { margin: 0.2rem 0 0; font-weight: 700; }
.actions { display: flex; flex-wrap: wrap; gap: 0.6rem; }
.secondary { background: #33415f; }
.error { border-color: #d56b6b; }
@media (max-width: 700px) {
  .announcement-form { grid-template-columns: 1fr; }
  .announcement-form h3,
  .wide { grid-column: auto; }
  .announcement-card { flex-direction: column; }
  .delivery-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
