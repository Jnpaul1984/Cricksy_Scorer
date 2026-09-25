<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

import {
  organizationBasePath as organizationBasePathForType,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import { getMySchoolMembership, getSchool, getSchoolEntitlement } from '@/services/schoolAdminApi';
import type {
  FreeOrganizationType,
  SchoolEntitlement,
  SchoolMembership,
  SchoolOrganization,
} from '@/types/schoolAdmin';

const route = useRoute();
const organizationId = computed(() => String(route.params.organizationId || ''));
const organizationType = computed(
  () => (route.meta.organizationType === 'club' ? 'club' : 'school') as FreeOrganizationType,
);
const terminology = computed(() => organizationTerminology(organizationType.value));
const organizationBasePath = computed(() => organizationBasePathForType(organizationType.value));
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
const canCreateSchoolMatch = computed(() => {
  const capabilities = new Set(entitlement.value?.capabilities || []);
  return (
    ['owner', 'admin', 'coach', 'scorer'].includes(role.value || '') &&
    ['school_match_playing_xi', 'school_persistent_teams', 'school_team_rosters'].every(
      (capability) => capabilities.has(capability),
    )
  );
});
const capabilities = computed(() => new Set(entitlement.value?.capabilities || []));
const canViewStatistics = computed(() => capabilities.value.has('school_basic_statistics'));
const canViewFixturesResults = computed(() => capabilities.value.has('school_fixtures_results'));
const canViewCompetitions = computed(() => capabilities.value.has('school_competitions'));
const canManageCompetitions = computed(
  () => canViewCompetitions.value && ['owner', 'admin', 'coach'].includes(role.value || ''),
);
const canDeleteCompetitions = computed(
  () => canViewCompetitions.value && ['owner', 'admin'].includes(role.value || ''),
);
const canLinkFixtures = computed(
  () => canViewCompetitions.value && ['owner', 'admin', 'coach', 'scorer'].includes(role.value || ''),
);
const canPublishScorecards = computed(
  () =>
    canViewFixturesResults.value &&
    capabilities.value.has('school_live_scorecards') &&
    ['owner', 'admin', 'coach', 'scorer'].includes(role.value || ''),
);
const canViewEvents = computed(() => capabilities.value.has('organization_events'));
const canManageEvents = computed(
  () => canViewEvents.value && ['owner', 'admin', 'coach'].includes(role.value || ''),
);

provide(schoolContextKey, {
  organizationId,
  organizationType,
  organizationBasePath,
  terminology,
  organization,
  membership,
  entitlement,
  canManageTeams,
  canManageRosterMetadata,
  canManageRosterLifecycle,
  canManageTeamRoster,
  canImport,
  canCreateSchoolMatch,
  canViewStatistics,
  canViewFixturesResults,
  canViewCompetitions,
  canManageCompetitions,
  canDeleteCompetitions,
  canLinkFixtures,
  canPublishScorecards,
  canViewEvents,
  canManageEvents,
});

let loadGeneration = 0;
async function loadContext() {
  const generation = ++loadGeneration;
  organization.value = null;
  membership.value = null;
  entitlement.value = null;
  error.value = '';
  loading.value = true;
  try {
    const [currentOrganization, currentMembership, currentEntitlement] = await Promise.all([
      getSchool(organizationId.value),
      getMySchoolMembership(organizationId.value),
      getSchoolEntitlement(organizationId.value),
    ]);
    if (
      currentOrganization.id !== organizationId.value ||
      currentMembership.organization_id !== organizationId.value ||
      currentEntitlement.organization_id !== organizationId.value ||
      currentOrganization.organization_type !== organizationType.value
    ) {
      throw Object.assign(new Error('Organization context could not be verified'), { status: 404 });
    }
    if (generation !== loadGeneration) return;
    organization.value = currentOrganization;
    membership.value = currentMembership;
    entitlement.value = currentEntitlement;
  } catch (reason) {
    if (generation !== loadGeneration) return;
    const status = (reason as { status?: number })?.status;
    error.value =
      status === 404
        ? `${terminology.value.kindLabel} not found or you do not have access.`
        : getErrorMessage(reason);
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

watch([organizationId, organizationType], loadContext, { immediate: true });
</script>

<template>
  <main class="school-shell">
    <p v-if="loading" class="shell-state" role="status">
      Loading {{ terminology.kindLabel }} workspace…
    </p>
    <section v-else-if="error" class="shell-state error" role="alert">
      <h1>{{ terminology.kindLabel }} workspace unavailable</h1>
      <p>{{ error }}</p>
      <RouterLink :to="organizationBasePath"
        >Back to your {{ terminology.kindLabelPluralLower }}</RouterLink
      >
    </section>
    <template v-else-if="organization && membership && entitlement">
      <header class="school-header">
        <div>
          <RouterLink :to="organizationBasePath" class="back-link"
            >← {{ terminology.directoryLabel }}</RouterLink
          >
          <p class="eyebrow">{{ terminology.kindLabel }} Administration</p>
          <h1>{{ organization.name }}</h1>
          <p class="context-line">
            <span>Status: {{ organization.status }}</span>
            <span>Role: {{ membership.role }}</span>
            <span>Plan: {{ entitlement.plan_key }}</span>
          </p>
        </div>
      </header>
      <nav class="school-nav" :aria-label="`${terminology.kindLabel} administration`">
        <RouterLink :to="`${organizationBasePath}/${organizationId}`">Overview</RouterLink>
        <RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">Teams</RouterLink>
        <RouterLink :to="`${organizationBasePath}/${organizationId}/players`">Players</RouterLink>
        <RouterLink v-if="canImport" :to="`${organizationBasePath}/${organizationId}/imports`"
          >Import</RouterLink
        >
        <RouterLink
          v-if="canCreateSchoolMatch"
          :to="`${organizationBasePath}/${organizationId}/matches/new`"
          >Create match</RouterLink
        >
        <RouterLink
          v-if="canViewStatistics"
          :to="`${organizationBasePath}/${organizationId}/statistics`"
          >Statistics</RouterLink
        >
        <RouterLink
          v-if="canViewFixturesResults"
          :to="`${organizationBasePath}/${organizationId}/fixtures-results`"
          >Fixtures / Results</RouterLink
        >
        <RouterLink
          v-if="canViewCompetitions"
          :to="`${organizationBasePath}/${organizationId}/competitions`"
          >Competitions</RouterLink
        >
        <RouterLink v-if="canViewEvents" :to="`${organizationBasePath}/${organizationId}/events`"
          >Calendar</RouterLink
        >
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
