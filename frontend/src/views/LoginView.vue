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
import { useRouter } from 'vue-router';

import { login } from '@/services/auth';
import { getErrorMessage } from '@/services/api';

const router = useRouter();
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
    await login(email.value.trim(), password.value);
    successMessage.value = 'Signed in successfully.';
    router.push('/');
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
