<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { BaseBadge, BaseButton, BaseCard } from '@/components';
import {
  approvePlatformSponsorPlacement, getPlatformSponsorVisibility, listPlatformSponsorPlacements,
  setPlatformSponsorGlobalVisibility, setPlatformSponsorOrganizationVisibility,
  setPlatformSponsorPlacementVisibility, takedownPlatformSponsorPlacement,
  type PlatformPage, type PlatformSponsorPlacement, type PlatformSponsorVisibility,
} from '@/services/schoolAdminApi';
import { useAuthStore } from '@/stores/authStore';

const auth = useAuthStore();
const placements = ref<PlatformSponsorPlacement[]>([]);
const reviewPageData = ref<PlatformPage | null>(null);
const visibility = ref<PlatformSponsorVisibility | null>(null);
const loading = ref(false);
const visibilityLoading = ref(false);
const error = ref<string | null>(null);
const visibilityError = ref<string | null>(null);
const pendingId = ref<string | null>(null);
const visibilityPending = ref<string | null>(null);
const reviewPage = ref(1);
const organizationPage = ref(1);
const placementPage = ref(1);
const pageSize = 50;
let active = true;
let loadGeneration = 0;
let visibilityGeneration = 0;

const proposed = computed(() => placements.value.filter((placement) => placement.state === 'proposed'));
const approved = computed(() => placements.value.filter((placement) => placement.state === 'approved'));
const organizationGroups = computed(() => ['school', 'club'].map((type) => ({
  type: type as 'school' | 'club',
  organizations: visibility.value?.organizations.filter((organization) => organization.type === type) ?? [],
})));

function message(errorValue: unknown, fallback: string) {
  return errorValue instanceof Error && errorValue.message ? errorValue.message : fallback;
}

async function load() {
  const currentGeneration = ++loadGeneration;
  loading.value = true;
  error.value = null;
  try {
    const response = await listPlatformSponsorPlacements(reviewPage.value, pageSize);
    if (active && loadGeneration === currentGeneration) {
      placements.value = response.items;
      reviewPageData.value = response.page;
    }
  } catch (err) {
    if (active && loadGeneration === currentGeneration) error.value = message(err, 'Unable to load sponsor placements.');
  } finally {
    if (active && loadGeneration === currentGeneration) loading.value = false;
  }
}

async function loadVisibility() {
  const currentGeneration = ++visibilityGeneration;
  visibilityLoading.value = true;
  visibilityError.value = null;
  try {
    const response = await getPlatformSponsorVisibility(organizationPage.value, placementPage.value, pageSize);
    if (active && visibilityGeneration === currentGeneration) visibility.value = response;
  } catch (err) {
    if (active && visibilityGeneration === currentGeneration) visibilityError.value = message(err, 'Unable to load sponsor visibility controls.');
  } finally {
    if (active && visibilityGeneration === currentGeneration) visibilityLoading.value = false;
  }
}

function placementOrganizationLabel(organizationId: string) {
  const organization = visibility.value?.organizations.find((item) => item.id === organizationId);
  return organization?.label || `Organization ${organizationId}`;
}

function visibilityPageRequest() {
  return { organizationPage: organizationPage.value, placementPage: placementPage.value, pageSize };
}

function refresh() {
  void load();
  void loadVisibility();
}

function changeReviewPage(page: number) {
  reviewPage.value = page;
  void load();
}

function changeOrganizationPage(page: number) {
  organizationPage.value = page;
  void loadVisibility();
}

function changePlacementPage(page: number) {
  placementPage.value = page;
  void loadVisibility();
}

async function setVisibility(key: string, request: () => Promise<PlatformSponsorVisibility>) {
  if (visibilityPending.value) return;
  const currentGeneration = ++visibilityGeneration;
  visibilityPending.value = key;
  visibilityError.value = null;
  try {
    const response = await request();
    if (active && visibilityGeneration === currentGeneration) visibility.value = response;
  } catch (err) {
    if (active && visibilityGeneration === currentGeneration) visibilityError.value = message(err, 'Unable to update sponsor visibility.');
  } finally {
    if (active && visibilityPending.value === key) visibilityPending.value = null;
  }
}

async function act(placement: PlatformSponsorPlacement, action: 'approve' | 'takedown') {
  if (pendingId.value) return;
  pendingId.value = placement.id;
  error.value = null;
  try {
    await (action === 'approve'
      ? approvePlatformSponsorPlacement(placement.id)
      : takedownPlatformSponsorPlacement(placement.id));
    if (active) await Promise.all([load(), loadVisibility()]);
  } catch (err) {
    if (active) error.value = message(err, `Unable to ${action} sponsor placement.`);
  } finally {
    if (active) pendingId.value = null;
  }
}

onMounted(() => { if (auth.isSuper) refresh(); });
onBeforeUnmount(() => { active = false; });
</script>

<template>
  <main class="sponsor-review-page">
    <h1>Organization sponsor placements</h1>
    <BaseCard v-if="!auth.isSuper" padding="lg"><p role="alert">Platform administrator authority is required.</p></BaseCard>
    <template v-else>
      <p>Review organization proposals before one approved sponsor is shown on its public community page. Takedowns take effect immediately.</p>
      <BaseButton variant="secondary" :disabled="loading || visibilityLoading || !!pendingId || !!visibilityPending" @click="refresh">{{ loading || visibilityLoading ? 'Loading.' : 'Refresh' }}</BaseButton>
      <p v-if="error" role="alert" class="error-message">{{ error }}</p>
      <p v-if="loading" role="status">Loading sponsor placements.</p>

      <section class="visibility-controls" aria-labelledby="visibility-title">
        <h2 id="visibility-title">Sponsor visibility controls</h2>
        <p>Visibility is off by default. These switches never bypass Cricksy approval, category policy, public organization publication, or the environment backstop.</p>
        <p class="policy-note">Eligible categories: sports equipment, education, ordinary food businesses, and local services.</p>
        <p v-if="visibilityError" role="alert" class="error-message">{{ visibilityError }}</p>
        <p v-if="visibilityLoading" role="status">Loading visibility controls.</p>
        <template v-else-if="visibility">
          <BaseCard padding="md" class="visibility-card" data-test="visibility-global">
            <div><h3>Global visibility</h3><p>Controls the default public visibility gate for every organization and sponsor.</p></div>
            <BaseButton :variant="visibility.global_enabled ? 'danger' : 'primary'" :disabled="!!visibilityPending" @click="setVisibility('global', () => setPlatformSponsorGlobalVisibility(!visibility!.global_enabled, visibilityPageRequest()))">
              {{ visibilityPending === 'global' ? 'Saving.' : visibility.global_enabled ? 'Turn global visibility off' : 'Turn global visibility on' }}
            </BaseButton>
          </BaseCard>
          <nav v-if="visibility.page.organizations.pages > 1" class="pagination" aria-label="Organization visibility pages">
            <BaseButton size="sm" variant="secondary" :disabled="organizationPage <= 1 || !!visibilityPending" @click="changeOrganizationPage(organizationPage - 1)">Previous organizations</BaseButton>
            <span>Organizations page {{ visibility.page.organizations.page }} of {{ visibility.page.organizations.pages }}</span>
            <BaseButton size="sm" variant="secondary" :disabled="organizationPage >= visibility.page.organizations.pages || !!visibilityPending" @click="changeOrganizationPage(organizationPage + 1)">Next organizations</BaseButton>
          </nav>
          <section v-for="group in organizationGroups" :key="group.type" class="organization-group" :aria-labelledby="`${group.type}-visibility-title`">
            <h3 :id="`${group.type}-visibility-title`">{{ group.type === 'school' ? 'Schools' : 'Clubs' }}</h3>
            <p v-if="!group.organizations.length">No {{ group.type }} visibility controls are available.</p>
            <BaseCard v-for="organization in group.organizations" :key="organization.id" padding="md" class="visibility-card">
              <div><h4>{{ organization.label }}</h4><p>{{ organization.type }} visibility is {{ organization.enabled ? 'on' : 'off' }}.</p></div>
              <BaseButton :variant="organization.enabled ? 'danger' : 'primary'" :disabled="!!visibilityPending" @click="setVisibility(`organization:${organization.id}`, () => setPlatformSponsorOrganizationVisibility(organization.id, !organization.enabled, visibilityPageRequest()))">
                {{ visibilityPending === `organization:${organization.id}` ? 'Saving.' : organization.enabled ? 'Turn organization off' : 'Turn organization on' }}
              </BaseButton>
            </BaseCard>
          </section>
          <section class="individual-sponsors" aria-labelledby="individual-sponsors-title">
            <h3 id="individual-sponsors-title">Individual sponsor visibility</h3>
            <p>These controls are independently paged from organizations, so every sponsor on this page remains actionable.</p>
            <p v-if="!visibility.placements.length">No individual sponsor placements are available on this page.</p>
            <div v-for="placement in visibility.placements" :key="placement.id" class="placement-visibility-row">
              <span><strong>{{ placement.sponsor_name }}</strong> · {{ placementOrganizationLabel(placement.orgid) }} · {{ placement.category }} · {{ placement.state }}</span>
              <BaseButton size="sm" :variant="placement.enabled ? 'danger' : 'primary'" :disabled="!!visibilityPending || placement.state === 'taken_down'" @click="setVisibility(`placement:${placement.id}`, () => setPlatformSponsorPlacementVisibility(placement.id, !placement.enabled, visibilityPageRequest()))">
                {{ visibilityPending === `placement:${placement.id}` ? 'Saving.' : placement.state === 'taken_down' ? 'Taken down' : placement.enabled ? 'Turn sponsor off' : 'Turn sponsor on' }}
              </BaseButton>
            </div>
          </section>
          <nav v-if="visibility.page.placements.pages > 1" class="pagination" aria-label="Individual sponsor visibility pages">
            <BaseButton size="sm" variant="secondary" :disabled="placementPage <= 1 || !!visibilityPending" @click="changePlacementPage(placementPage - 1)">Previous sponsors</BaseButton>
            <span>Sponsors page {{ visibility.page.placements.page }} of {{ visibility.page.placements.pages }}</span>
            <BaseButton size="sm" variant="secondary" :disabled="placementPage >= visibility.page.placements.pages || !!visibilityPending" @click="changePlacementPage(placementPage + 1)">Next sponsors</BaseButton>
          </nav>
        </template>
      </section>

      <section v-if="!loading" aria-labelledby="proposed-title">
        <h2 id="proposed-title">Proposed</h2>
        <p v-if="!proposed.length">No sponsor proposals awaiting review.</p>
        <BaseCard v-for="placement in proposed" :key="placement.id" padding="md" class="placement-card">
          <div><strong>{{ placement.sponsor_name }}</strong><p>{{ placement.organization_label || placement.organization_id }} · {{ placement.category }}</p></div>
          <div class="actions"><BaseBadge variant="warning">Proposed</BaseBadge><BaseButton size="sm" variant="primary" :disabled="!!pendingId" @click="act(placement, 'approve')">{{ pendingId === placement.id ? 'Approving.' : 'Approve' }}</BaseButton></div>
        </BaseCard>
      </section>
      <section v-if="!loading" aria-labelledby="approved-title">
        <h2 id="approved-title">Approved</h2>
        <p v-if="!approved.length">No active sponsor placements.</p>
        <BaseCard v-for="placement in approved" :key="placement.id" padding="md" class="placement-card">
          <div><strong>{{ placement.sponsor_name }}</strong><p>{{ placement.organization_label || placement.organization_id }} · {{ placement.category }}</p></div>
          <div class="actions"><BaseBadge variant="success">Approved</BaseBadge><BaseButton size="sm" variant="danger" :disabled="!!pendingId" @click="act(placement, 'takedown')">{{ pendingId === placement.id ? 'Taking down.' : 'Take down' }}</BaseButton></div>
        </BaseCard>
      </section>
      <nav v-if="reviewPageData && reviewPageData.pages > 1" class="pagination" aria-label="Sponsor review pages">
        <BaseButton size="sm" variant="secondary" :disabled="reviewPage <= 1 || !!pendingId" @click="changeReviewPage(reviewPage - 1)">Previous review entries</BaseButton>
        <span>Review page {{ reviewPageData.page }} of {{ reviewPageData.pages }}</span>
        <BaseButton size="sm" variant="secondary" :disabled="reviewPage >= reviewPageData.pages || !!pendingId" @click="changeReviewPage(reviewPage + 1)">Next review entries</BaseButton>
      </nav>
    </template>
  </main>
</template>

<style scoped>
.sponsor-review-page { max-width: 64rem; margin: 0 auto; padding: var(--space-lg); }
.placement-card, .placement-visibility-row { align-items: center; display: flex; gap: var(--space-md); justify-content: space-between; }
.placement-card { margin: var(--space-sm) 0; }
.placement-card p, .visibility-card p { color: var(--color-text-secondary); margin: var(--space-xs) 0 0; }
.actions { align-items: center; display: flex; gap: var(--space-sm); }
.visibility-controls { margin: var(--space-xl) 0; }
.policy-note { font-size: var(--font-size-sm); }
.organization-group { margin-top: var(--space-lg); }
.visibility-card { margin: var(--space-sm) 0; }
.visibility-card h3, .visibility-card h4, .visibility-card h5 { margin: 0; }
.individual-sponsors { border-top: 1px solid var(--color-border); margin-top: var(--space-lg); padding-top: var(--space-md); }
.placement-visibility-row { margin-top: var(--space-sm); }
.error-message { color: var(--color-error); }
.pagination { align-items: center; display: flex; flex-wrap: wrap; gap: var(--space-sm); justify-content: center; margin: var(--space-md) 0; }
@media (max-width: 36rem) { .placement-card, .placement-visibility-row { align-items: flex-start; flex-direction: column; } }
</style>
