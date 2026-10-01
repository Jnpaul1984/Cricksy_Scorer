<script setup lang="ts">
import { ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { getPublicTeam } from '@/services/schoolAdminApi';
import type { PublicTeam } from '@/types/schoolAdmin';

const props = defineProps<{ publicIdentifier: string; teamPublicIdentifier: string }>();
const team = ref<PublicTeam | null>(null);
const unavailable = ref(false);
const loading = ref(true);
let generation = 0;

async function load() {
  const currentGeneration = ++generation;
  const currentOrganization = props.publicIdentifier;
  const currentTeam = props.teamPublicIdentifier;
  loading.value = true;
  unavailable.value = false;
  team.value = null;
  try {
    const response = await getPublicTeam(currentOrganization, currentTeam);
    if (generation !== currentGeneration || props.publicIdentifier !== currentOrganization || props.teamPublicIdentifier !== currentTeam) return;
    team.value = response;
  } catch {
    if (generation === currentGeneration && props.publicIdentifier === currentOrganization && props.teamPublicIdentifier === currentTeam) unavailable.value = true;
  } finally {
    if (generation === currentGeneration && props.publicIdentifier === currentOrganization && props.teamPublicIdentifier === currentTeam) loading.value = false;
  }
}
watch(() => [props.publicIdentifier, props.teamPublicIdentifier], load, { immediate: true });
</script>

<template>
  <main class="public-team">
    <p v-if="loading" role="status">Loading team.</p>
    <section v-else-if="unavailable" role="alert">
      <h1>Team page not found</h1>
      <p>This page is unavailable or private.</p>
      <RouterLink :to="{ name: 'organization-community', params: { publicIdentifier } }">Return to community</RouterLink>
    </section>
    <section v-else-if="team">
      <p class="eyebrow">Public team</p>
      <h1>{{ team.display_name }}</h1>
      <dl aria-label="Published game aggregates">
        <div><dt>Published games</dt><dd>{{ team.aggregate_stats.published_games }}</dd></div>
      </dl>
      <p class="privacy-note">Only approved team-level aggregates are shown. Rosters and player identities remain private.</p>
      <RouterLink :to="{ name: 'organization-community', params: { publicIdentifier } }">Back to community</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.public-team { width: min(100% - 2rem, 48rem); margin: 0 auto; padding: 3rem 0; }
.eyebrow { color: #3d596b; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
dl { display: grid; max-width: 20rem; } dl div { border: 1px solid #d7e0e8; padding: 1rem; border-radius: .75rem; }
dt { color: #3d596b; } dd { font-size: 2rem; font-weight: 700; margin: .25rem 0 0; }
.privacy-note { color: #3d596b; }
</style>
