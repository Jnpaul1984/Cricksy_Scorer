<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

import { schoolContextKey } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import { getMySchoolMembership, getSchool, getSchoolEntitlement } from '@/services/schoolAdminApi';
import type { SchoolEntitlement, SchoolMembership, SchoolOrganization } from '@/types/schoolAdmin';

const route = useRoute();
const organizationId = computed(() => String(route.params.organizationId || ''));
const routeViewKey = computed(() => String(route.fullPath || organizationId.value));
const organization = ref<SchoolOrganization | null>(null);
const membership = ref<SchoolMembership | null>(null);
const entitlement = ref<SchoolEntitlement | null>(null);
const loading = ref(true);
const error = ref('');

const role = computed(() => membership.value?.role);
const canManageTeams = computed(() => ['owner', 'admin', 'coach'].includes(role.value || ''));
const canManageRosterMetadata = computed(() =>
  ['owner', 'admin', 'coach'].includes(role.value || ''),
);
const canManageRosterLifecycle = computed(() => ['owner', 'admin'].includes(role.value || ''));
const canManageTeamRoster = computed(() => ['owner', 'admin', 'coach'].includes(role.value || ''));
const canImport = computed(() => ['owner', 'admin', 'coach'].includes(role.value || ''));

provide(schoolContextKey, {
  organizationId,
  organization,
  membership,
  entitlement,
  canManageTeams,
  canManageRosterMetadata,
  canManageRosterLifecycle,
  canManageTeamRoster,
  canImport,
});

async function loadContext() {
  organization.value = null;
  membership.value = null;
  entitlement.value = null;
  error.value = '';
  loading.value = true;
  try {
    const [school, currentMembership, currentEntitlement] = await Promise.all([
      getSchool(organizationId.value),
      getMySchoolMembership(organizationId.value),
      getSchoolEntitlement(organizationId.value),
    ]);
    if (
      school.id !== organizationId.value ||
      currentMembership.organization_id !== organizationId.value
    ) {
      throw new Error('School context could not be verified');
    }
    organization.value = school;
    membership.value = currentMembership;
    entitlement.value = currentEntitlement;
  } catch (reason) {
    const status = (reason as { status?: number })?.status;
    error.value =
      status === 404 ? 'School not found or you do not have access.' : getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}

watch(organizationId, loadContext, { immediate: true });
</script>

<template>
  <main class="school-shell">
    <p v-if="loading" class="shell-state" role="status">Loading School workspace…</p>
    <section v-else-if="error" class="shell-state error" role="alert">
      <h1>School workspace unavailable</h1>
      <p>{{ error }}</p>
      <RouterLink to="/schools">Back to your schools</RouterLink>
    </section>
    <template v-else-if="organization && membership && entitlement">
      <header class="school-header">
        <div>
          <RouterLink to="/schools" class="back-link">← Your schools</RouterLink>
          <p class="eyebrow">School Administration</p>
          <h1>{{ organization.name }}</h1>
          <p class="context-line">
            <span>Status: {{ organization.status }}</span>
            <span>Role: {{ membership.role }}</span>
            <span>Plan: {{ entitlement.plan_key }}</span>
          </p>
        </div>
      </header>
      <nav class="school-nav" aria-label="School administration">
        <RouterLink :to="`/schools/${organizationId}`">Overview</RouterLink>
        <RouterLink :to="`/schools/${organizationId}/teams`">Teams</RouterLink>
        <RouterLink :to="`/schools/${organizationId}/players`">Players</RouterLink>
        <RouterLink v-if="canImport" :to="`/schools/${organizationId}/imports`">Import</RouterLink>
      </nav>
      <RouterView :key="routeViewKey" />
    </template>
  </main>
</template>

<style scoped>
.school-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
  color: #eef2ff;
}
.school-header {
  padding: 1.35rem;
  border: 1px solid #3b4768;
  border-radius: 14px 14px 0 0;
  background: linear-gradient(135deg, #1c2942, #182036);
}
.school-header h1 {
  margin: 0.2rem 0 0.6rem;
}
.eyebrow {
  margin: 0.7rem 0 0;
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.back-link {
  color: #b9c8ed;
}
.context-line {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 1.4rem;
  margin: 0;
  text-transform: capitalize;
}
.school-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.65rem;
  border: 1px solid #3b4768;
  border-top: 0;
  background: #151c2c;
}
.school-nav a {
  padding: 0.55rem 0.8rem;
  border-radius: 7px;
  color: #cbd5ee;
  text-decoration: none;
}
.school-nav a.router-link-exact-active {
  color: #0d1b18;
  background: #70d7b0;
  font-weight: 700;
}
.shell-state {
  margin: 2rem 0;
  padding: 1.25rem;
  border: 1px solid #506080;
  border-radius: 10px;
  background: #1b2235;
}
.error {
  border-color: #d56b6b;
}
@media (max-width: 700px) {
  .school-shell {
    padding-inline: 0.6rem;
  }
  .school-nav a {
    flex: 1;
    text-align: center;
  }
}
</style>
