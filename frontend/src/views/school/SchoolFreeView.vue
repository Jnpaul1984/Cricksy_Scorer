<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { useAuthStore } from '@/stores/authStore';
import type { FreeOrganizationType } from '@/types/schoolAdmin';

const route = useRoute();
const auth = useAuthStore();
const organizationType = computed(
  () => (route.meta.organizationType === 'club' ? 'club' : 'school') as FreeOrganizationType,
);
const terminology = computed(() => organizationTerminology(organizationType.value));
const createPath = computed(() => `${organizationBasePath(organizationType.value)}/create`);
const registerPath = computed(() => `/register?redirect=${encodeURIComponent(createPath.value)}`);
const loginPath = computed(() => `/login?redirect=${encodeURIComponent(createPath.value)}`);
const primaryPath = computed(() => (auth.isLoggedIn ? createPath.value : registerPath.value));
</script>
<template>
  <main class="school-free">
    <p class="eyebrow">Cricksy for {{ terminology.kindLabelPlural }}</p>
    <h1>{{ terminology.freePlanLabel }}, built for match day and beyond.</h1>
    <p>
      Give your {{ terminology.kindLabel }} one reusable cricket workspace—without a credit card.
    </p>
    <div class="actions">
      <RouterLink :to="primaryPath" class="primary">Get {{ terminology.freePlanLabel }}</RouterLink
      ><RouterLink :to="loginPath">Sign In</RouterLink>
    </div>
    <section>
      <h2>Included with {{ terminology.freePlanLabel }}</h2>
      <ul>
        <li>
          Reusable {{ terminology.kindLabel }} master roster and spreadsheet player upload
        </li>
        <li>Persistent {{ terminology.kindLabel }} Teams and reusable Team rosters</li>
        <li>Saved-Team match setup and playing XI selection</li>
        <li>Live scoring, basic player and Team statistics</li>
        <li>
          Fixtures, results, {{ terminology.kindLabel }} competitions, and governed live/public
          scorecards
        </li>
      </ul>
    </section>
  </main>
</template>
<style scoped>.school-free{max-width:850px;margin:0 auto;padding:4rem 1.25rem;color:#eef2ff}.eyebrow{color:#70d7b0;font-weight:700;text-transform:uppercase}.actions{display:flex;gap:1rem;margin:2rem 0}.actions a{padding:.75rem 1rem;border:1px solid #70d7b0;border-radius:8px;color:#eef2ff;text-decoration:none}.actions .primary{background:#70d7b0;color:#0d1b18;font-weight:700}section{background:#1b2235;padding:1.5rem;border-radius:12px}li{margin:.75rem 0}</style>
