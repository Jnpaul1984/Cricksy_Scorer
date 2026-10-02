<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';

import PublicShareLinkButton from '@/components/PublicShareLinkButton.vue';
import { getPublicFixture } from '@/services/schoolAdminApi';
import type { PublicFixture } from '@/types/schoolAdmin';

const props = defineProps<{ publicIdentifier: string; competitionPublicKey: string; fixturePublicIdentifier: string; resultOnly?: boolean }>();
const fixture = ref<PublicFixture | null>(null);
const unavailable = ref(false);
async function load() {
  fixture.value = null; unavailable.value = false;
  try { fixture.value = await getPublicFixture(props.publicIdentifier, props.competitionPublicKey, props.fixturePublicIdentifier, Boolean(props.resultOnly)); }
  catch { unavailable.value = true; }
}
onMounted(load);
watch(() => [props.publicIdentifier, props.competitionPublicKey, props.fixturePublicIdentifier, props.resultOnly], load);
</script>

<template>
  <main class="page">
    <section v-if="unavailable" class="notice"><h1>{{ resultOnly ? 'Result' : 'Fixture' }} unavailable</h1><p>This page is unavailable or private.</p></section>
    <template v-else-if="fixture">
      <p><RouterLink :to="`/community/${publicIdentifier}/competitions/${competitionPublicKey}`">{{ fixture.competition_name }}</RouterLink></p>
      <h1>{{ fixture.team_a_name }} vs {{ fixture.team_b_name }}</h1>
      <p v-if="fixture.venue">{{ fixture.venue }}</p><p>{{ fixture.result || fixture.game_status || fixture.fixture_status }}</p>
      <PublicShareLinkButton :path="resultOnly ? (fixture.public_result_path || fixture.canonical_path) : fixture.canonical_path" :label="resultOnly ? 'Copy result link' : 'Copy fixture link'" />
      <p v-if="fixture.canonical_scorecard_path"><RouterLink :to="fixture.canonical_scorecard_path">View published scorecard</RouterLink> <PublicShareLinkButton :path="fixture.canonical_scorecard_path" label="Copy scorecard link" /></p>
    </template>
    <p v-else role="status">Loading public fixture.</p>
  </main>
</template>

<style scoped>.page { max-width: 58rem; margin: 2rem auto; padding: 1rem; } .notice { padding: 1rem; border: 1px solid #b44; }</style>
