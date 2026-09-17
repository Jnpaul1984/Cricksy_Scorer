<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { getErrorMessage } from '@/services/api';
import { listSchools } from '@/services/schoolAdminApi';
import type { SchoolOrganization } from '@/types/schoolAdmin';

const schools = ref<SchoolOrganization[]>([]);
const loading = ref(true);
const error = ref('');

onMounted(async () => {
  try {
    schools.value = await listSchools();
  } catch (reason) {
    error.value = getErrorMessage(reason);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <main class="school-page">
    <header class="page-heading">
      <p class="eyebrow">School Free</p>
      <h1>Your schools</h1>
      <p>Choose a School workspace. Access is based on your active School membership.</p>
    </header>
    <p v-if="loading" role="status">Loading your schools…</p>
    <div v-else-if="error" class="notice error" role="alert">{{ error }}</div>
    <div v-else-if="!schools.length" class="notice">
      You do not have an active School membership.
    </div>
    <ul v-else class="school-grid" aria-label="Available schools">
      <li v-for="school in schools" :key="school.id" class="school-card">
        <div>
          <h2>{{ school.name }}</h2>
          <p><strong>Role:</strong> {{ school.membership_role }}</p>
          <p><strong>Status:</strong> {{ school.status }}</p>
        </div>
        <RouterLink :to="`/schools/${school.id}`" class="action-link">Open School</RouterLink>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.school-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem;
  color: #eef2ff;
}
.page-heading {
  margin-bottom: 1.5rem;
}
.eyebrow {
  color: #70d7b0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.school-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  padding: 0;
  list-style: none;
}
.school-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid #3c4768;
  border-radius: 12px;
  background: #1b2235;
}
.action-link {
  align-self: flex-start;
  padding: 0.65rem 0.9rem;
  border-radius: 8px;
  color: #0d1b18;
  background: #70d7b0;
  font-weight: 700;
  text-decoration: none;
}
.notice {
  padding: 1rem;
  border: 1px solid #52607e;
  border-radius: 8px;
  background: #20283d;
}
.error {
  border-color: #e17979;
}
</style>
