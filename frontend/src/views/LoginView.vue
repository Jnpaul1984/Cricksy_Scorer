<template>
  <section class="login-view">
    <h1>Sign in to Cricksy</h1>
    <form @submit.prevent="handleSubmit">
      <label>
        Email
        <input
          v-model="email"
          type="email"
          autocomplete="email"
          required
          placeholder="you@example.com"
        />
      </label>
      <label>
        Password
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          placeholder="********"
        />
      </label>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Signing in...' : 'Sign In' }}
      </button>
    </form>

    <p v-if="successMessage" class="success">{{ successMessage }}</p>
    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';

import { getErrorMessage } from '@/services/api';
import { login } from '@/services/auth';
import { useAuthStore } from '@/stores/authStore';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const email = ref('');
const password = ref('');
const loading = ref(false);
const successMessage = ref('');
const errorMessage = ref('');

async function handleSubmit() {
  errorMessage.value = '';
  successMessage.value = '';
  loading.value = true;
  try {
    const result = await login(email.value.trim(), password.value);
    // Update the auth store so the router guard knows we're logged in
    authStore.token = result.token;
    authStore.user = result.user;
    // If the router sent us here with a redirect query (saved destination), honor it.
    // Default to /setup (create game page) instead of / which loops back to login.
    const redirectTo = (route.query.redirect as string) || '/setup';
    await router.push(redirectTo);
  } catch (err) {
    errorMessage.value = getErrorMessage(err);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-view {
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  background: var(--pico-card-background-color, #fff);
  border-radius: 0.75rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

button[type='submit'] {
  width: 100%;
}

.success {
  color: #0a7d2b;
}

.error {
  color: #b42318;
}
</style>
