import { highlightMitigations } from './highlightMitigations'
<template>
  <div class="admin-agents-view">
    <h1>Admin: Run Agents</h1>
    <div v-if="!isAdmin">You must be an admin to access this page.</div>
    <div v-else>
      <section v-if="usage" class="usage-panel">
        <h2>Usage</h2>
        <div>Today's tokens: <b>{{ usage.todayTokens }}</b></div>
        <table class="usage-table">
          <thead>
            <tr><th>Time</th><th>Agent</th><th>User</th><th>Tokens</th><th>Model</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="run in usage.recent" :key="run.id">
              <td>{{ run.createdAt }}</td>
              <td>{{ run.agentKey }}</td>
              <td>{{ run.userId }}</td>
              <td>{{ run.tokensOut }}</td>
              <td>{{ run.model }}</td>
              <td>{{ run.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <div class="agent-cards">
        <div v-for="agent in agents" :key="agent.key" class="agent-card">
          <h2>{{ agent.name }}</h2>
          <p>{{ agent.description }}</p>
          <div class="inputs">
            <label>Since: <input v-model="agent.since" type="date" /></label>
            <label>Until: <input v-model="agent.until" type="date" /></label>
            <span v-if="agent.quickPresets">
              <button v-for="preset in agent.quickPresets" :key="preset.label" @click="() => { agent.since = preset.since(); agent.until = preset.until(); }">{{ preset.label }}</button>
            </span>
          </div>
          <button :disabled="agent.loading" @click="runAgent(agent)">Run Agent</button>
          <div v-if="agent.result" class="result-panel">
            <h3>Result</h3>
            <div class="markdown" v-html="highlightMitigations(renderMarkdown(agent.result.markdownReport), agent.key)"></div>
            <div class="meta">Model: {{ agent.result.modelUsed }} | Tokens: {{ agent.result.tokenUsage }}</div>
            <button @click="copyResult(agent.result.markdownReport)">Copy to Clipboard</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">

import { marked } from 'marked'
import { ref, computed, onMounted } from 'vue'

import { highlightMitigations } from './highlightMitigations'

import { apiRequest } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
const usage = ref<any>(null)
async function fetchUsage() {
  usage.value = await apiRequest('/admin/agents/usage')
}

onMounted(() => {
  fetchUsage()
})

const agents = ref([
  {
    key: 'feedback_digest',
    name: 'Feedback Digest',
    description: 'Groups user feedback by theme and severity, proposes next actions.',
    since: '',
    until: '',
    loading: false,
    result: null as any,
  },
  {
    key: 'ai_usage_tracker',
    name: 'AI Usage Tracker',
    description: 'Summarizes daily AI token spend, detects abuse, suggests cost optimizations.',
    since: '',
    until: '',
    loading: false,
    result: null as any,
  },
  {
    key: 'error_watcher',
    name: 'Error Watcher',
    description: 'Summarizes recurring backend errors and slow endpoints.',
    since: '',
    until: '',
    loading: false,
    result: null as any,
  },
  {
    key: 'beta_ux_analyzer',
    name: 'Beta UX Analyzer',
    description: 'Combines feedback and page views to identify top friction points.',
    since: '',
    until: '',
    loading: false,
    result: null as any,
  },
  {
    key: 'cyber_security_watcher',
    name: 'Cybersecurity Watcher',
    description: 'Detects suspicious logins, spikes, and errors. Inputs: auth, request, rate-limit, error logs. Outputs: findings, evidence, mitigations.',
    since: '',
    until: '',
    loading: false,
    result: null as any,
    quickPresets: [
      { label: 'Last 1h', since: () => new Date(Date.now() - 60*60*1000).toISOString().slice(0,10), until: () => new Date().toISOString().slice(0,10) },
      { label: 'Last 24h', since: () => new Date(Date.now() - 24*60*60*1000).toISOString().slice(0,10), until: () => new Date().toISOString().slice(0,10) },
      { label: 'Last 7d', since: () => new Date(Date.now() - 7*24*60*60*1000).toISOString().slice(0,10), until: () => new Date().toISOString().slice(0,10) },
    ],
  },
])

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'superuser' || auth.user?.role === 'org_pro')

function renderMarkdown(md: string) {
  return marked.parse(md || '') as string;
}

async function runAgent(agent: any) {
  agent.loading = true
  agent.result = null
  try {
    const resp = await apiRequest('/admin/agents/run', {
      method: 'POST',
      body: JSON.stringify({
        agentKey: agent.key,
        since: agent.since,
        until: agent.until,
      }),
    })
    agent.result = resp
    await fetchUsage()
  } catch {
    agent.result = { markdownReport: 'Error running agent.' }
  } finally {
    agent.loading = false
  }
}

function copyResult(md: string) {
  navigator.clipboard.writeText(md)
}
</script>

<style scoped>
.usage-panel { background: #f6f8fa; border-radius: 8px; padding: 1rem; margin-bottom: 2rem; }
.usage-table { width: 100%; font-size: 0.95em; border-collapse: collapse; margin-top: 0.5em; }
.usage-table th, .usage-table td { border: 1px solid #ddd; padding: 0.3em 0.5em; }
.usage-table th { background: #f0f0f0; }
.admin-agents-view { max-width: 900px; margin: 0 auto; }
.agent-cards { display: flex; flex-wrap: wrap; gap: 2rem; }
.agent-card { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; width: 350px; background: #fafbfc; }
.inputs { margin-bottom: 0.5rem; }
.result-panel { background: #f6f8fa; border-radius: 6px; padding: 0.5rem; margin-top: 0.5rem; }
.markdown { font-size: 0.95em; }
.meta { color: #888; font-size: 0.85em; margin-top: 0.5em; }
button { margin-top: 0.5em; }
</style>
