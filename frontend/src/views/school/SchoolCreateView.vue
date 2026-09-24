<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { getErrorMessage } from '@/services/api';
import { createOrganization } from '@/services/schoolAdminApi';
import type { FreeOrganizationType } from '@/types/schoolAdmin';

const route = useRoute();
const router = useRouter();
const organizationType = computed(
  () => (route.meta.organizationType === 'club' ? 'club' : 'school') as FreeOrganizationType,
);
const terminology = computed(() => organizationTerminology(organizationType.value));
const name = ref('');
const error = ref('');
const loading = ref(false);

async function submit() {
  error.value = '';
  loading.value = true;
  try {
    const organization = await createOrganization({
      name: name.value,
      organization_type: organizationType.value,
    });
    await router.push(
      `${organizationBasePath(organizationType.value)}/${encodeURIComponent(organization.id)}`,
    );
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
}
</script>
<template>
  <section class="create">
    <p class="eyebrow">Cricksy for {{ terminology.kindLabelPlural }}</p>
    <h1>Create your {{ terminology.kindLabel }}</h1>
    <p>
      You will become the {{ terminology.ownerLabel }}. {{ terminology.freePlanLabel }} activates
      automatically—no credit card required.
    </p>
    <form @submit.prevent="submit">
      <label
        >{{ terminology.kindLabel }} name<input v-model="name" required maxlength="255"
      /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button :disabled="loading">
        {{ loading ? `Creating ${terminology.kindLabel}…` : `Create ${terminology.freePlanLabel}` }}
      </button>
    </form>
  </section>
</template>
<style scoped>.create{max-width:34rem;margin:3rem auto;padding:2rem;background:#1b2235;border-radius:12px;color:#eef2ff}.eyebrow{color:#70d7b0;font-weight:700;text-transform:uppercase}form,label{display:grid;gap:.75rem}input,button{padding:.75rem}button{background:#70d7b0;border:0;border-radius:8px;font-weight:700}</style>
