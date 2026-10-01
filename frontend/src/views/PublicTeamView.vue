<script setup lang="ts">
import { ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { getPublicTeam } from '@/services/schoolAdminApi';
import { listAllMyPublicFavorites, removeMyPublicFavorite, saveMyPublicFavorite } from '@/services/schoolAdminApi';
import { useAuthStore } from '@/stores/authStore';
import type { PublicTeam } from '@/types/schoolAdmin';

const props = defineProps<{ publicIdentifier: string; teamPublicIdentifier: string }>();
const auth = useAuthStore();
const team = ref<PublicTeam | null>(null);
const favoriteId = ref<string | null>(null);
const favoriteError = ref('');
const unavailable = ref(false);
const loading = ref(true);
let generation = 0;
let favoriteGeneration = 0;

async function load() {
  const currentGeneration = ++generation;
  const currentOrganization = props.publicIdentifier;
  const currentTeam = props.teamPublicIdentifier;
  loading.value = true;
  unavailable.value = false;
  team.value = null;
  favoriteId.value = null;
  try {
    const response = await getPublicTeam(currentOrganization, currentTeam);
    if (generation !== currentGeneration || props.publicIdentifier !== currentOrganization || props.teamPublicIdentifier !== currentTeam) return;
    team.value = response;
    if (auth.user?.id) void refreshFavorite();
  } catch {
    if (generation === currentGeneration && props.publicIdentifier === currentOrganization && props.teamPublicIdentifier === currentTeam) unavailable.value = true;
  } finally {
    if (generation === currentGeneration && props.publicIdentifier === currentOrganization && props.teamPublicIdentifier === currentTeam) loading.value = false;
  }
}

async function refreshFavorite() {
  const current = ++favoriteGeneration;
  const teamKey = props.teamPublicIdentifier;
  if (!auth.user?.id) return;
  try {
    const favorites = await listAllMyPublicFavorites();
    if (current === favoriteGeneration && auth.user?.id && teamKey === props.teamPublicIdentifier) {
      favoriteId.value = favorites.find(item => item.subject_kind === 'team' && item.public_key === teamKey)?.id || null;
    }
  } catch { /* The server remains authoritative for private saved state. */ }
}

async function toggleFavorite() {
  if (!team.value) return;
  const current = favoriteGeneration;
  const teamKey = team.value.public_identifier;
  const isCurrent = () => current === favoriteGeneration && team.value?.public_identifier === teamKey && props.teamPublicIdentifier === teamKey;
  favoriteError.value = '';
  try {
    if (favoriteId.value) {
      await removeMyPublicFavorite(favoriteId.value);
      if (isCurrent()) favoriteId.value = null;
    } else {
      const favorite = await saveMyPublicFavorite('team', teamKey);
      if (isCurrent()) favoriteId.value = favorite.id;
    }
  } catch {
    if (isCurrent()) favoriteError.value = 'Sign in with an active staff membership to save public pages.';
  }
}
watch(() => [props.publicIdentifier, props.teamPublicIdentifier], load, { immediate: true });
watch(() => auth.user?.id, () => {
  ++favoriteGeneration;
  favoriteId.value = null;
  favoriteError.value = '';
  if (auth.user?.id && team.value?.public_identifier === props.teamPublicIdentifier) void refreshFavorite();
}, { immediate: true });
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
      <button type="button" class="favorite-button" @click="toggleFavorite">{{ favoriteId ? 'Saved' : 'Save this team' }}</button>
      <p v-if="favoriteError" class="favorite-error" role="status">{{ favoriteError }}</p>
      <p><RouterLink to="/saved-public-pages">View saved public pages</RouterLink></p>
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
.favorite-button { border: 1px solid #176b45; border-radius: .4rem; background: #fff; color: #176b45; cursor: pointer; font: inherit; font-weight: 700; padding: .4rem .65rem; }
.favorite-error { color: #8b1e1e; }
</style>
