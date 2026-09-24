<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { getErrorMessage } from '@/services/api';
import { listOrganizations } from '@/services/schoolAdminApi';
import type { FreeOrganizationType, SchoolOrganization } from '@/types/schoolAdmin';

const route = useRoute();
const organizationType = computed(
  () => (route.meta.organizationType === 'club' ? 'club' : 'school') as FreeOrganizationType,
);
const terminology = computed(() => organizationTerminology(organizationType.value));
const basePath = computed(() => organizationBasePath(organizationType.value));
const organizations = ref<SchoolOrganization[]>([]);
const loading = ref(true);
const error = ref('');

async function load() {
  organizations.value = [];
  error.value = '';
  loading.value = true;
  try {
    organizations.value = await listOrganizations(organizationType.value);
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

watch(organizationType, load, { immediate: true });
</script>

<template>
  <main class="school-page">
    <header class="page-heading">
      <p class="eyebrow">{{ terminology.freePlanLabel }}</p>
      <h1>{{ terminology.directoryLabel }}</h1>
      <p>
        Choose a {{ terminology.kindLabel }} workspace. Access is based on your active
        {{ terminology.kindLabel }} membership.
      </p>
    </header>
    <p v-if="loading" role="status">Loading your {{ terminology.kindLabelPluralLower }}…</p>
    <div v-else-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="!organizations.length" class="notice">
      <p>
        You do not have an active {{ terminology.kindLabel }} membership. If you are joining an
        existing {{ terminology.kindLabel }}, ask its administrator for access.
      </p>
      <RouterLink :to="`${basePath}/create`" class="action-link"
        >Create {{ terminology.freePlanLabel }}</RouterLink
      >
    </div>
    <ul v-else class="school-grid" :aria-label="`Available ${terminology.kindLabelPluralLower}`">
      <li v-for="organization in organizations" :key="organization.id" class="school-card">
        <div>
          <h2>{{ organization.name }}</h2>
          <p><strong>Role:</strong> {{ organization.membership_role }}</p>
          <p><strong>Status:</strong> {{ organization.status }}</p>
        </div>
        <RouterLink :to="`${basePath}/${organization.id}`" class="action-link"
          >Open {{ terminology.kindLabel }}</RouterLink
        >
      </li>
    </ul>
    <RouterLink
      v-if="organizations.length"
      :to="`${basePath}/create`"
      class="action-link create-school"
      >Create {{ terminology.kindLabel }}</RouterLink
    >
  </main>
</template>

<style scoped>
.school-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
  color: #eef2ff;
}
.page-heading {
  margin-bottom: 1.5rem;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.school-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  padding: 0;
  list-style: none;
}
.school-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid #3c4768;
  border-radius: 12px;
  background: #1b2235;
}
.action-link {
  align-self: flex-start;
  padding: 0.65rem 0.9rem;
  border-radius: 8px;
  color: #0d1b18;
  background: #70d7b0;
  font-weight: 700;
  text-decoration: none;
}
.notice {
  padding: 1rem;
  border: 1px solid #52607e;
  border-radius: 8px;
  background: #20283d;
}
.error {
  border-color: #e17979;
}
.create-school{margin-top:1rem}
</style>
