<script setup lang="ts">
import { ref } from 'vue'; import { useRouter } from 'vue-router'; import { getErrorMessage } from '@/services/api'; import { createSchool } from '@/services/schoolAdminApi'
const router = useRouter(); const name = ref(''); const error = ref(''); const loading = ref(false)
async function submit(){ error.value=''; loading.value=true; try { const school=await createSchool({name:name.value}); await router.push(`/schools/${encodeURIComponent(school.id)}`) } catch(reason){error.value=getErrorMessage(reason)} finally{loading.value=false} }
</script>
<template><section class="create"><p class="eyebrow">Cricksy for Schools</p><h1>Create your School</h1><p>You will become the School Owner. School Free activates automatically—no credit card required.</p><form @submit.prevent="submit"><label>School name<input v-model="name" required maxlength="255" /></label><p v-if="error" role="alert">{{ error }}</p><button :disabled="loading">{{ loading ? 'Creating School…' : 'Create School Free' }}</button></form></section></template>
<style scoped>.create{max-width:34rem;margin:3rem auto;padding:2rem;background:#1b2235;border-radius:12px;color:#eef2ff}.eyebrow{color:#70d7b0;font-weight:700;text-transform:uppercase}form,label{display:grid;gap:.75rem}input,button{padding:.75rem}button{background:#70d7b0;border:0;border-radius:8px;font-weight:700}</style>
