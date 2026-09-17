<script setup lang="ts">
import { RouterLink } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';

const { organizationId, organization, membership, entitlement, canImport } = useSchoolContext();
</script>

<template>
  <section class="panel" aria-labelledby="overview-heading">
    <header>
      <p class="eyebrow">Overview</p>
      <h2 id="overview-heading">{{ organization?.name }}</h2>
      <p>Your access comes from this School’s active organization membership.</p>
    </header>
    <dl class="summary-grid">
      <div>
        <dt>Organization status</dt>
        <dd>{{ organization?.status }}</dd>
      </div>
      <div>
        <dt>Your School role</dt>
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
      <h3 id="capabilities-heading">Enabled School capabilities</h3>
      <ul class="capabilities">
        <li v-for="capability in entitlement?.capabilities" :key="capability">
          {{ capability.replace(/_/g, ' ') }}
        </li>
      </ul>
    </section>
    <nav class="quick-actions" aria-label="School actions">
      <RouterLink :to="`/schools/${organizationId}/teams`">Manage teams</RouterLink>
      <RouterLink :to="`/schools/${organizationId}/players`">View master roster</RouterLink>
      <RouterLink v-if="canImport" :to="`/schools/${organizationId}/imports`"
        >Import players</RouterLink
      >
    </nav>
    <p class="boundary-note">
      Advanced AI, video, advanced analytics, and premium coaching are not included in School Free.
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
</style>
