<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { listMyPublicFavorites, removeMyPublicFavorite } from '@/services/schoolAdminApi';
import { useAuthStore } from '@/stores/authStore';


const items = ref<Awaited<ReturnType<typeof listMyPublicFavorites>>['items']>([]);
const auth = useAuthStore();
const loading = ref(true);
const unavailable = ref(false);
const nextOffset = ref<number | null>(null);
const loadingMore = ref(false);
let generation = 0;
async function load(offset = 0, append = false) {
  const current = ++generation;
  if (append) loadingMore.value = true; else loading.value = true;
  unavailable.value = false;
  try { const result = await listMyPublicFavorites(offset); if (current === generation) { items.value = append ? [...items.value, ...result.items] : result.items; nextOffset.value = result.next_offset; } }
  catch { if (current === generation) unavailable.value = true; }
  finally { if (current === generation) { loading.value = false; loadingMore.value = false; } }
}
async function remove(id: string) { await removeMyPublicFavorite(id); await load(); }
async function loadMore() { if (nextOffset.value !== null) await load(nextOffset.value, true); }
onMounted(() => { if (auth.user?.id) void load(); else unavailable.value = true; });
watch(() => auth.user?.id, userId => {
  ++generation;
  items.value = [];
  nextOffset.value = null;
  loadingMore.value = false;
  if (userId) void load(); else { loading.value = false; unavailable.value = true; }
});
</script>

<template>
  <main class="saved-public-pages"><h1>Saved public pages</h1>
    <p v-if="loading" role="status">Loading saved public pages.</p>
    <section v-else-if="unavailable" role="alert"><p>Sign in with an active staff membership to view saved public pages.</p></section>
    <section v-else-if="!items.length"><p>No public pages saved.</p></section>
    <template v-else><ul><li v-for="item in items" :key="item.id"><RouterLink :to="item.canonical_path">{{ item.display_name }}</RouterLink> <span>({{ item.subject_kind }})</span> <button type="button" @click="remove(item.id)">Remove</button></li></ul><button v-if="nextOffset !== null" type="button" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? 'Loading…' : 'Load more' }}</button></template>
  </main>
</template>

<style scoped>.saved-public-pages { width: min(100% - 2rem, 52rem); margin: 0 auto; padding: 2rem 0; } li { margin: .75rem 0; } button { margin-left: .5rem; }</style>
