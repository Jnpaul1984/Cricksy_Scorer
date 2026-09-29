<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';

import { useOrganizationNotificationShell } from '@/composables/useOrganizationNotificationShell';
import { useSchoolContext } from '@/composables/useSchoolContext';
import {
  listOrganizationNotificationPreferences,
  listOrganizationNotifications,
  markOrganizationNotificationRead,
  updateOrganizationNotificationPreference,
} from '@/services/schoolAdminApi';
import type {
  OrganizationNotification,
  OrganizationNotificationCategory,
  OrganizationNotificationPreference,
} from '@/types/schoolAdmin';
import { organizationOperationError } from '@/utils/organizationOperations';

const PAGE_SIZE = 20;
const categories: Array<{ value: OrganizationNotificationCategory; label: string }> = [
  { value: 'organization_announcement', label: 'Organization announcements' },
  { value: 'team_announcement', label: 'Team announcements' },
  { value: 'event', label: 'Events and training' },
  { value: 'selection', label: 'Selection' },
  { value: 'availability_reminder', label: 'Availability reminders' },
];

const { organizationId, organizationType, terminology, membership, entitlement } =
  useSchoolContext();
const shell = useOrganizationNotificationShell();
const canView = computed(
  () =>
    membership.value?.status === 'active' &&
    (entitlement.value?.capabilities || []).includes('organization_notifications'),
);
const items = ref<OrganizationNotification[]>([]);
const preferences = ref<OrganizationNotificationPreference[]>([]);
const total = ref(0);
const unreadOnly = ref(false);
const category = ref<OrganizationNotificationCategory | ''>('');
const loading = ref(true);
const loadingMore = ref(false);
const preferencesLoading = ref(true);
const error = ref('');
const preferenceError = ref('');
const notice = ref('');
const markingIds = ref<Set<string>>(new Set());
const updatingCategories = ref<Set<OrganizationNotificationCategory>>(new Set());
let contextGeneration = 0;
let inboxRequestGeneration = 0;
let preferenceRequestGeneration = 0;
let resettingFilters = false;

const hasMore = computed(() => items.value.length < total.value);

function categoryLabel(value: OrganizationNotificationCategory): string {
  return categories.find((item) => item.value === value)?.label || value;
}

function sourceLabel(item: OrganizationNotification): string {
  if (item.source_type === 'organization_announcement') return 'Organization announcement';
  if (item.source_type === 'team_announcement') return 'Team announcement';
  if (item.source_type === 'organization_event') return 'Event or training';
  if (item.source_type === 'selection_publication') return 'Published selection';
  return 'Availability';
}

function statusOf(reason: unknown): number | undefined {
  return (reason as { status?: number })?.status;
}

function isAccessFailure(reason: unknown): boolean {
  return [403, 404].includes(statusOf(reason) || 0);
}

function clearProtectedState() {
  ++inboxRequestGeneration;
  ++preferenceRequestGeneration;
  items.value = [];
  preferences.value = [];
  total.value = 0;
  markingIds.value = new Set();
  updatingCategories.value = new Set();
  shell?.clearPrivateState();
}

function resetWorkspace() {
  clearProtectedState();
  error.value = '';
  preferenceError.value = '';
  notice.value = '';
  resettingFilters = true;
  unreadOnly.value = false;
  category.value = '';
  void nextTick(() => {
    resettingFilters = false;
  });
}

async function loadInbox(reset = true) {
  if (!canView.value) {
    clearProtectedState();
    loading.value = false;
    loadingMore.value = false;
    return;
  }
  const context = contextGeneration;
  const request = ++inboxRequestGeneration;
  const currentOrganizationId = organizationId.value;
  const currentOrganizationType = organizationType.value;
  const offset = reset ? 0 : items.value.length;
  if (reset) {
    items.value = [];
    total.value = 0;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  error.value = '';
  try {
    const response = await listOrganizationNotifications(currentOrganizationId, {
      category: category.value || undefined,
      unreadOnly: unreadOnly.value,
      limit: PAGE_SIZE,
      offset,
    });
    if (
      context !== contextGeneration ||
      request !== inboxRequestGeneration ||
      organizationId.value !== currentOrganizationId ||
      organizationType.value !== currentOrganizationType
    )
      return;
    items.value = reset ? response.items : [...items.value, ...response.items];
    total.value = response.total;
  } catch (reason) {
    if (context !== contextGeneration || request !== inboxRequestGeneration) return;
    if (isAccessFailure(reason)) clearProtectedState();
    error.value = organizationOperationError(reason, 'notification inbox');
  } finally {
    if (context === contextGeneration && request === inboxRequestGeneration) {
      loading.value = false;
      loadingMore.value = false;
    }
  }
}

async function loadPreferences() {
  if (!canView.value) {
    preferences.value = [];
    preferencesLoading.value = false;
    return;
  }
  const context = contextGeneration;
  const request = ++preferenceRequestGeneration;
  const currentOrganizationId = organizationId.value;
  const currentOrganizationType = organizationType.value;
  preferencesLoading.value = true;
  preferenceError.value = '';
  try {
    const response = await listOrganizationNotificationPreferences(currentOrganizationId);
    if (
      context !== contextGeneration ||
      request !== preferenceRequestGeneration ||
      organizationId.value !== currentOrganizationId ||
      organizationType.value !== currentOrganizationType
    )
      return;
    preferences.value = response.items;
  } catch (reason) {
    if (context !== contextGeneration || request !== preferenceRequestGeneration) return;
    if (isAccessFailure(reason)) clearProtectedState();
    preferenceError.value = organizationOperationError(reason, 'notification preferences');
  } finally {
    if (context === contextGeneration && request === preferenceRequestGeneration) {
      preferencesLoading.value = false;
    }
  }
}

async function refresh() {
  const context = contextGeneration;
  await Promise.all([loadInbox(true), loadPreferences(), shell?.refreshUnreadCount()]);
  if (context === contextGeneration) notice.value = 'Notification inbox refreshed.';
}

async function markRead(item: OrganizationNotification) {
  if (item.read_at || markingIds.value.has(item.id)) return;
  const context = contextGeneration;
  const currentOrganizationId = organizationId.value;
  const currentOrganizationType = organizationType.value;
  markingIds.value = new Set(markingIds.value).add(item.id);
  error.value = '';
  notice.value = '';
  try {
    const updated = await markOrganizationNotificationRead(currentOrganizationId, item.id);
    if (
      context !== contextGeneration ||
      organizationId.value !== currentOrganizationId ||
      organizationType.value !== currentOrganizationType
    )
      return;
    if (unreadOnly.value) {
      items.value = items.value.filter((candidate) => candidate.id !== item.id);
      total.value = Math.max(0, total.value - 1);
    } else {
      items.value = items.value.map((candidate) =>
        candidate.id === item.id ? updated : candidate,
      );
    }
    notice.value = 'Notification marked read.';
    await shell?.refreshUnreadCount();
  } catch (reason) {
    if (context !== contextGeneration) return;
    if (isAccessFailure(reason)) clearProtectedState();
    error.value = organizationOperationError(reason, 'notification');
  } finally {
    if (context === contextGeneration) {
      const next = new Set(markingIds.value);
      next.delete(item.id);
      markingIds.value = next;
    }
  }
}

function preferenceEnabled(value: OrganizationNotificationCategory): boolean {
  return preferences.value.find((item) => item.category === value)?.enabled ?? true;
}

async function changePreference(value: OrganizationNotificationCategory, enabled: boolean) {
  if (updatingCategories.value.has(value)) return;
  const context = contextGeneration;
  const currentOrganizationId = organizationId.value;
  const currentOrganizationType = organizationType.value;
  updatingCategories.value = new Set(updatingCategories.value).add(value);
  preferenceError.value = '';
  notice.value = '';
  try {
    const updated = await updateOrganizationNotificationPreference(
      currentOrganizationId,
      value,
      enabled,
    );
    if (
      context !== contextGeneration ||
      organizationId.value !== currentOrganizationId ||
      organizationType.value !== currentOrganizationType
    )
      return;
    preferences.value = [...preferences.value.filter((item) => item.category !== value), updated];
    notice.value = `${categoryLabel(value)} preference updated for future deliveries.`;
  } catch (reason) {
    if (context !== contextGeneration) return;
    if (isAccessFailure(reason)) clearProtectedState();
    preferenceError.value = organizationOperationError(reason, 'notification preference');
  } finally {
    if (context === contextGeneration) {
      const next = new Set(updatingCategories.value);
      next.delete(value);
      updatingCategories.value = next;
    }
  }
}

async function onPreferenceChange(value: OrganizationNotificationCategory, event: Event) {
  const input = event.target as HTMLInputElement;
  await changePreference(value, input.checked);
  input.checked = preferenceEnabled(value);
}

watch([unreadOnly, category], () => {
  if (!resettingFilters) void loadInbox(true);
});

watch(
  [organizationId, organizationType, canView],
  async () => {
    ++contextGeneration;
    resetWorkspace();
    if (!canView.value) {
      loading.value = false;
      preferencesLoading.value = false;
      return;
    }
    await Promise.all([loadInbox(true), loadPreferences(), shell?.refreshUnreadCount()]);
  },
  { immediate: true },
);
</script>

<template>
  <section class="notifications-view" aria-labelledby="notification-inbox-heading">
    <header>
      <p class="eyebrow">Private {{ terminology.kindLabel }} delivery</p>
      <h2 id="notification-inbox-heading">Notifications</h2>
      <p>
        Your inbox contains recipient-specific in-app deliveries. Announcements remain authored,
        immutable content in the separate announcement feed.
      </p>
    </header>

    <p v-if="!canView" class="notice">Notifications are not enabled for this organization.</p>
    <template v-else>
      <div class="toolbar" aria-label="Notification inbox controls">
        <label>
          Status
          <select v-model="unreadOnly" data-test="notification-status-filter">
            <option :value="false">All</option>
            <option :value="true">Unread</option>
          </select>
        </label>
        <label>
          Category
          <select v-model="category" data-test="notification-category-filter">
            <option value="">All categories</option>
            <option v-for="option in categories" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <button type="button" class="secondary" data-test="refresh-notifications" @click="refresh">
          Refresh
        </button>
      </div>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      <p v-if="loading" role="status">Loading notifications…</p>
      <section v-else aria-label="Notification inbox">
        <p v-if="items.length === 0" class="notice">No notifications match these filters.</p>
        <article
          v-for="item in items"
          :key="item.id"
          class="notification-card"
          :class="{ unread: !item.read_at }"
          :data-test="`notification-${item.id}`"
          :aria-label="`${item.read_at ? 'Read' : 'Unread'} notification: ${item.title}`"
        >
          <div class="notification-content">
            <p class="eyebrow">{{ categoryLabel(item.category) }} · {{ sourceLabel(item) }}</p>
            <h3>{{ item.title }}</h3>
            <p class="summary">{{ item.summary }}</p>
            <p class="metadata">
              <strong data-test="notification-read-state">{{
                item.read_at ? 'Read' : 'Unread'
              }}</strong>
              ·
              <time :datetime="item.created_at">{{
                new Date(item.created_at).toLocaleString()
              }}</time>
            </p>
          </div>
          <button
            v-if="!item.read_at"
            type="button"
            :data-test="`mark-read-${item.id}`"
            :disabled="markingIds.has(item.id)"
            @click="markRead(item)"
          >
            {{ markingIds.has(item.id) ? 'Marking…' : 'Mark read' }}
          </button>
        </article>
        <button
          v-if="hasMore"
          type="button"
          class="load-more"
          data-test="load-more-notifications"
          :disabled="loadingMore"
          @click="loadInbox(false)"
        >
          {{ loadingMore ? 'Loading…' : 'Load more' }}
        </button>
      </section>

      <section class="preferences" aria-labelledby="notification-preferences-heading">
        <h2 id="notification-preferences-heading">In-app preferences</h2>
        <p>
          Preferences affect future logical deliveries only. Re-enabling a category does not restore
          notifications that were previously suppressed. Existing inbox history is never deleted by
          a preference change.
        </p>
        <p v-if="preferenceError" class="error" role="alert">{{ preferenceError }}</p>
        <p v-if="preferencesLoading" role="status">Loading notification preferences…</p>
        <fieldset v-else>
          <legend>Future in-app deliveries</legend>
          <label v-for="option in categories" :key="option.value" class="preference-row">
            <input
              type="checkbox"
              :data-test="`preference-${option.value}`"
              :checked="preferenceEnabled(option.value)"
              :disabled="updatingCategories.has(option.value)"
              @change="onPreferenceChange(option.value, $event)"
            />
            <span>{{ option.label }}</span>
          </label>
        </fieldset>
      </section>
    </template>
  </section>
</template>

<style scoped>
.notifications-view {
  min-width: 0;
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
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.8rem;
  margin: 1rem 0;
}
.toolbar label {
  display: grid;
  gap: 0.35rem;
}
select,
button {
  min-height: 2.5rem;
}
select {
  max-width: 100%;
}
button {
  padding: 0.5rem 0.8rem;
  border: 0;
  border-radius: 7px;
  background: #70d7b0;
  color: #10201b;
  font-weight: 700;
  cursor: pointer;
}
button:focus-visible,
select:focus-visible,
input:focus-visible {
  outline: 3px solid #f3ca72;
  outline-offset: 2px;
}
button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.secondary {
  background: #9fb4dc;
}
.notification-card,
.preferences,
.notice,
.error {
  margin-top: 0.85rem;
  padding: 1rem;
  border: 1px solid #3b4768;
  border-radius: 10px;
  background: #182036;
}
.notification-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  overflow-wrap: anywhere;
}
.notification-card.unread {
  border-left: 0.45rem solid #70d7b0;
}
.notification-content {
  min-width: 0;
  flex: 1;
}
.notification-card h3 {
  margin: 0.25rem 0;
}
.summary {
  white-space: pre-wrap;
}
.metadata {
  color: #cbd5ee;
}
.preferences fieldset {
  display: grid;
  gap: 0.7rem;
  min-width: 0;
  border: 1px solid #465475;
  border-radius: 8px;
}
.preference-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 2.25rem;
}
.preference-row input {
  width: 1.15rem;
  height: 1.15rem;
}
.load-more {
  width: 100%;
  margin-top: 1rem;
}
.error {
  border-color: #d56b6b;
}
@media (max-width: 640px) {
  .toolbar,
  .notification-card {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar label,
  .toolbar select,
  .toolbar button,
  .notification-card button {
    width: 100%;
  }
}
</style>
