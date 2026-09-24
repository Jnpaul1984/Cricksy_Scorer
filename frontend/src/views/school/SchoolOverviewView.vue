<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { listSchoolPlayers, listSchoolTeams } from '@/services/schoolAdminApi';

const {
  organizationId,
  organizationBasePath,
  terminology,
  organization,
  membership,
  entitlement,
  canImport,
  canCreateSchoolMatch,
  canViewStatistics,
  canViewFixturesResults,
  canViewCompetitions,
} = useSchoolContext();
const hasSetup = ref(true);
onMounted(async () => { try { const [players, teams] = await Promise.all([listSchoolPlayers(organizationId.value, 'active'), listSchoolTeams(organizationId.value)]); hasSetup.value = players.length > 0 || teams.length > 0 } catch { hasSetup.value = true } });
</script>

<template>
  <section class="panel" aria-labelledby="overview-heading">
    <header>
      <p class="eyebrow">Overview</p>
      <h2 id="overview-heading">{{ organization?.name }}</h2>
      <p>
        Your access comes from this {{ terminology.kindLabel }}’s active organization membership.
      </p>
    </header>
    <dl class="summary-grid">
      <div>
        <dt>Organization status</dt>
        <dd>{{ organization?.status }}</dd>
      </div>
      <div>
        <dt>Your {{ terminology.kindLabel }} role</dt>
        <dd>{{ membership?.role }}</dd>
      </div>
      <div>
        <dt>Plan</dt>
        <dd>{{ entitlement?.plan_key }}</dd>
      </div>
      <div>
        <dt>Entitlement status</dt>
        <dd>{{ entitlement?.status }}</dd>
      </div>
    </dl>
    <section aria-labelledby="capabilities-heading">
      <h3 id="capabilities-heading">Enabled {{ terminology.kindLabel }} capabilities</h3>
      <ul class="capabilities">
        <li v-for="capability in entitlement?.capabilities" :key="capability">
          {{ capability.replace(/_/g, ' ') }}
        </li>
      </ul>
    </section>
    <nav class="quick-actions" :aria-label="`${terminology.kindLabel} actions`">
      <RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">Manage teams</RouterLink>
      <RouterLink :to="`${organizationBasePath}/${organizationId}/players`"
        >View master roster</RouterLink
      >
      <RouterLink v-if="canImport" :to="`${organizationBasePath}/${organizationId}/imports`"
        >Import players</RouterLink
      >
      <RouterLink
        v-if="canCreateSchoolMatch"
        :to="`${organizationBasePath}/${organizationId}/matches/new`"
        >Create {{ terminology.kindLabel }} match</RouterLink
      >
      <RouterLink
        v-if="canViewStatistics"
        :to="`${organizationBasePath}/${organizationId}/statistics`"
        >View statistics</RouterLink
      >
      <RouterLink
        v-if="canViewFixturesResults"
        :to="`${organizationBasePath}/${organizationId}/fixtures-results`"
        >View fixtures and results</RouterLink
      >
      <RouterLink
        v-if="canViewCompetitions"
        :to="`${organizationBasePath}/${organizationId}/competitions`"
        >Manage competitions</RouterLink
      >
    </nav>
    <section v-if="!hasSetup" class="onboarding" aria-labelledby="onboarding-heading"><h3 id="onboarding-heading">Start your {{ terminology.kindLabel }} workspace</h3><ol><li><RouterLink v-if="canImport" :to="`${organizationBasePath}/${organizationId}/imports`">Upload Players</RouterLink></li><li><RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">Create Teams</RouterLink></li><li><RouterLink :to="`${organizationBasePath}/${organizationId}/teams`">Assign Players</RouterLink></li><li><RouterLink v-if="canCreateSchoolMatch" :to="`${organizationBasePath}/${organizationId}/matches/new`">Create First Match</RouterLink></li></ol></section>
    <p class="boundary-note">
      Advanced AI, video, advanced analytics, and premium coaching are not included in
      {{ terminology.freePlanLabel }}.
    </p>
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
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.8rem;
}
.summary-grid div {
  padding: 1rem;
  border: 1px solid #39445f;
  border-radius: 10px;
  background: #20283d;
}
dt {
  color: #aebbd7;
  font-size: 0.9rem;
}
dd {
  margin: 0.2rem 0 0;
  font-weight: 700;
  text-transform: capitalize;
}
.capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0;
  list-style: none;
}
.capabilities li {
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  background: #263550;
  text-transform: capitalize;
}
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-top: 1.2rem;
}
.quick-actions a {
  padding: 0.65rem 0.9rem;
  border-radius: 8px;
  color: #0d1b18;
  background: #70d7b0;
  font-weight: 700;
  text-decoration: none;
}
.boundary-note {
  margin-top: 1.4rem;
  padding: 0.8rem;
  border-left: 4px solid #f2bb5f;
  background: #292536;
}
.onboarding{margin-top:1.4rem;padding:1rem;border:1px solid #70d7b0;border-radius:10px;background:#20283d}.onboarding a{color:#70d7b0;font-weight:700}
</style>
