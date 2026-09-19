<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { getErrorMessage } from '@/services/api'
import { register } from '@/services/auth'
import { useAuthStore } from '@/stores/authStore'
import { authEntryRedirect } from '@/utils/safeRedirect'

const route = useRoute(); const router = useRouter(); const auth = useAuthStore()
const email = ref(''); const password = ref(''); const confirmPassword = ref(''); const error = ref(''); const loading = ref(false)
async function submit() {
  error.value = ''
  if (password.value !== confirmPassword.value) { error.value = 'Passwords do not match.'; return }
  loading.value = true
  try { const result = await register(email.value.trim(), password.value); auth.token = result.token; auth.user = result.user; await router.push(authEntryRedirect(route.query.redirect)) }
  catch (reason) { error.value = getErrorMessage(reason) } finally { loading.value = false }
}
</script>
<template><section class="auth-page"><h1>Create your Cricksy account</h1><p>Create an account, then set up your School Free workspace.</p><form @submit.prevent="submit"><label>Email<input v-model="email" type="email" autocomplete="email" required /></label><label>Password<input v-model="password" type="password" autocomplete="new-password" required /></label><label>Confirm password<input v-model="confirmPassword" type="password" autocomplete="new-password" required /></label><p v-if="error" role="alert">{{ error }}</p><button :disabled="loading">{{ loading ? 'Creating account…' : 'Create account' }}</button></form><p>Already have an account? <RouterLink :to="{ path: '/login', query: route.query }">Sign in</RouterLink></p></section></template>
<style scoped>.auth-page{max-width:28rem;margin:3rem auto;padding:2rem;background:#1b2235;border-radius:12px;color:#eef2ff}form{display:grid;gap:1rem}label{display:grid;gap:.35rem}input{padding:.65rem}button{padding:.75rem;background:#70d7b0;border:0;border-radius:8px;font-weight:700}</style>
