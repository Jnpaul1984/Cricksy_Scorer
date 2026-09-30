<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { useSchoolContext } from '@/composables/useSchoolContext';
import { getErrorMessage } from '@/services/api';
import {
  getOrganizationCommunitySettings,
  publishOrganizationCommunity,
  setOrganizationCompetitionCommunityPublication,
  unpublishOrganizationCommunity,
  updateOrganizationCommunityBranding,
} from '@/services/schoolAdminApi';
import type { OrganizationCommunitySettings } from '@/types/schoolAdmin';

const { organizationId, organizationType, terminology, canManageCommunity } = useSchoolContext();
const settings = ref<OrganizationCommunitySettings | null>(null);
const logoUrl = ref('');
const logoAltText = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const notice = ref('');
let generation = 0;

const communityPath = computed(() =>
  settings.value ? `/community/${settings.value.public_identifier}` : '',
);
const absoluteCommunityUrl = computed(() => {
  if (!communityPath.value) return '';
  if (typeof window === 'undefined') return communityPath.value;
  return new URL(communityPath.value, window.location.origin).toString();
});

function isCurrent(currentGeneration: number, currentId: string, currentType: string) {
  return (
    generation === currentGeneration &&
    organizationId.value === currentId &&
    organizationType.value === currentType
  );
}

async function load() {
  const currentGeneration = ++generation;
  const currentId = organizationId.value;
  const currentType = organizationType.value;
  settings.value = null;
  logoUrl.value = '';
  logoAltText.value = '';
  error.value = '';
  notice.value = '';
  loading.value = true;
  try {
    const response = await getOrganizationCommunitySettings(currentId);
    if (!isCurrent(currentGeneration, currentId, currentType)) return;
    if (response.organization_id !== currentId) {
      throw Object.assign(new Error('Organization context could not be verified'), { status: 404 });
    }
    settings.value = response;
    logoUrl.value = response.logo_url || '';
    logoAltText.value = response.logo_alt_text || '';
  } catch (reason) {
    if (isCurrent(currentGeneration, currentId, currentType)) error.value = getErrorMessage(reason);
  } finally {
    if (isCurrent(currentGeneration, currentId, currentType)) loading.value = false;
  }
}

async function mutate(action: (currentId: string) => Promise<unknown>, message: string) {
  const currentGeneration = ++generation;
  const currentId = organizationId.value;
  const currentType = organizationType.value;
  saving.value = true;
  error.value = '';
  notice.value = '';
  try {
    await action(currentId);
    if (!isCurrent(currentGeneration, currentId, currentType)) return;
    notice.value = message;
    const response = await getOrganizationCommunitySettings(currentId);
    if (!isCurrent(currentGeneration, currentId, currentType)) return;
    if (response.organization_id !== currentId) return;
    settings.value = response;
    logoUrl.value = response.logo_url || '';
    logoAltText.value = response.logo_alt_text || '';
  } catch (reason) {
    if (isCurrent(currentGeneration, currentId, currentType)) error.value = getErrorMessage(reason);
  } finally {
    if (isCurrent(currentGeneration, currentId, currentType)) saving.value = false;
  }
}

function setHomepagePublished(publish: boolean) {
  if (!canManageCommunity.value) return;
  void mutate(
    currentId =>
      publish
        ? publishOrganizationCommunity(currentId)
        : unpublishOrganizationCommunity(currentId),
    publish ? 'Community page published.' : 'Community page unpublished.',
  );
}

function saveBranding() {
  if (!canManageCommunity.value) return;
  void mutate(
    currentId =>
      updateOrganizationCommunityBranding(currentId, {
        logo_url: logoUrl.value.trim() || null,
        logo_alt_text: logoUrl.value.trim() ? logoAltText.value.trim() || null : null,
      }),
    'Community branding saved.',
  );
}

function removeLogo() {
  logoUrl.value = '';
  logoAltText.value = '';
  saveBranding();
}

function setCompetitionPublished(competitionId: string, publish: boolean) {
  if (!canManageCommunity.value) return;
  void mutate(
    currentId =>
      setOrganizationCompetitionCommunityPublication(currentId, competitionId, publish),
    publish ? 'Competition published to the community page.' : 'Competition unpublished.',
  );
}

async function copyLink() {
  if (!absoluteCommunityUrl.value) return;
  try {
    await navigator.clipboard.writeText(absoluteCommunityUrl.value);
    notice.value = 'Community link copied.';
  } catch {
    error.value = 'The link could not be copied. Select the link text instead.';
  }
}

watch([organizationId, organizationType], load, { immediate: true });
</script>

<template>
  <section class="community-settings" aria-labelledby="community-settings-title">
    <header>
      <p class="eyebrow">Public cricket</p>
      <h2 id="community-settings-title">{{ terminology.kindLabel }} community page</h2>
      <p>
        Publishing this page never publishes competitions, rosters, members, or scorecards by
        implication. Each competition and scorecard keeps its own publication state.
      </p>
    </header>

    <p v-if="loading" role="status">Loading community settings…</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <p v-if="notice" class="message success" role="status">{{ notice }}</p>

    <template v-if="settings && !loading">
      <article class="panel" data-test="community-publication-panel">
        <div>
          <h3>Homepage publication</h3>
          <p>
            Status:
            <strong>{{ settings.publication_state === 'published' ? 'Public' : 'Private' }}</strong>
          </p>
        </div>
        <div v-if="canManageCommunity" class="actions">
          <button
            v-if="settings.publication_state === 'unpublished'"
            type="button"
            :disabled="saving"
            @click="setHomepagePublished(true)"
          >
            Publish homepage
          </button>
          <button v-else type="button" class="secondary" :disabled="saving" @click="setHomepagePublished(false)">
            Unpublish homepage
          </button>
        </div>
        <p v-else class="read-only">Only a current Owner or Admin can change publication.</p>
        <div class="share-row">
          <label for="community-link">Stable community link</label>
          <input id="community-link" :value="absoluteCommunityUrl" readonly />
          <button type="button" class="secondary" @click="copyLink">Copy link</button>
          <RouterLink v-if="settings.publication_state === 'published'" :to="communityPath" target="_blank">
            Open public page
          </RouterLink>
        </div>
      </article>

      <article class="panel">
        <h3>Basic logo</h3>
        <p>HTTPS raster images only: PNG, JPEG, WebP, GIF, or AVIF. SVG and scripts are not accepted.</p>
        <form v-if="canManageCommunity" @submit.prevent="saveBranding">
          <label for="community-logo-url">Logo URL</label>
          <input
            id="community-logo-url"
            v-model="logoUrl"
            type="url"
            inputmode="url"
            maxlength="2048"
            placeholder="https://example.org/crest.png"
          />
          <label for="community-logo-alt">Logo description</label>
          <input
            id="community-logo-alt"
            v-model="logoAltText"
            maxlength="120"
            :required="Boolean(logoUrl.trim())"
            :placeholder="`${terminology.kindLabel} crest`"
          />
          <div class="actions">
            <button type="submit" :disabled="saving">Save logo</button>
            <button v-if="settings.logo_url" type="button" class="secondary" :disabled="saving" @click="removeLogo">
              Remove logo
            </button>
          </div>
        </form>
        <p v-else class="read-only">
          {{ settings.logo_url ? 'A logo is configured.' : 'No logo is configured.' }}
        </p>
      </article>

      <article class="panel">
        <h3>Public competitions</h3>
        <p>Only competitions marked Public contribute fixtures, results, and standings.</p>
        <p v-if="settings.competitions.length === 0">No eligible competitions yet.</p>
        <ul v-else class="competition-list">
          <li v-for="competition in settings.competitions" :key="competition.competition_id">
            <div>
              <strong>{{ competition.competition_name }}</strong>
              <span class="state-label">
                {{ competition.publication_state === 'published' ? 'Public' : 'Private' }}
              </span>
            </div>
            <button
              v-if="canManageCommunity"
              type="button"
              class="secondary"
              :disabled="saving"
              @click="setCompetitionPublished(competition.competition_id, competition.publication_state !== 'published')"
            >
              {{ competition.publication_state === 'published' ? 'Unpublish' : 'Publish' }}
            </button>
          </li>
        </ul>
      </article>
    </template>
  </section>
</template>

<style scoped>
.community-settings {
  display: grid;
  gap: 1rem;
  max-width: 72rem;
  min-width: 0;
}
.eyebrow { color: #52606d; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.panel { border: 1px solid #d7dee7; border-radius: 0.75rem; padding: 1rem; min-width: 0; }
.actions, .share-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.share-row { margin-top: 1rem; }
.share-row label { width: 100%; font-weight: 700; }
.share-row input { flex: 1 1 18rem; min-width: 0; }
form { display: grid; gap: 0.6rem; }
.competition-list { display: grid; gap: 0.75rem; list-style: none; padding: 0; }
.competition-list li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.75rem; border-top: 1px solid #e6ebf1; padding-top: 0.75rem; }
.state-label { display: block; color: #52606d; }
.message { border-radius: 0.5rem; padding: 0.75rem; }
.error { background: #fff1f0; color: #8f1d14; }
.success { background: #edf9f0; color: #145c2b; }
.read-only { color: #52606d; }
button:focus-visible, a:focus-visible, input:focus-visible { outline: 3px solid #1d70b8; outline-offset: 2px; }
@media (max-width: 38rem) {
  .actions > *, .share-row > *, .competition-list button { width: 100%; }
}
</style>
