<script setup lang="ts">
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { ref, computed, onMounted, watch } from 'vue'
import { Bar, Pie } from 'vue-chartjs'

import { API_BASE, getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const auth = useAuthStore()

// Types
interface FeatureUsage {
  feature: string
  tokens: number
  request_count: number
}

interface MonthlyUsage {
  month: string
  tokens: number
  request_count: number
}

interface TopUser {
  user_id: string
  email: string
  tokens: number
  request_count: number
}

interface UsageQuota {
  used: number
  limit: number | null
  percentage: number
}

interface UsageStats {
  total_tokens: number
  total_requests: number
  by_feature: FeatureUsage[]
  by_month: MonthlyUsage[]
  top_users: TopUser[]
  quota: UsageQuota
}

// State
const loading = ref(true)
const error = ref<string | null>(null)
const stats = ref<UsageStats | null>(null)

// Filters
const filterYear = ref<number | null>(new Date().getFullYear())
const filterMonth = ref<number | null>(null)
const filterUserId = ref<string | null>(null)
const filterOrgId = ref<string | null>(null)

// Auth checks
const isLoggedIn = computed(() => !!auth.token)
const canViewOrgStats = computed(() => {
  const role = auth.role?.toLowerCase() || ''
  return ['org_pro', 'superuser'].includes(role)
})

// Chart colors
const featureColors = [
  '#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
]

// Computed chart data
const monthlyChartData = computed(() => {
  if (!stats.value) return { labels: [], datasets: [] }
  
  return {
    labels: stats.value.by_month.map(m => m.month),
    datasets: [
      {
        label: 'Tokens Used',
        data: stats.value.by_month.map(m => m.tokens),
        backgroundColor: '#4f46e5',
        borderRadius: 4,
      },
    ],
  }
})

const featurePieData = computed(() => {
  if (!stats.value || stats.value.by_feature.length === 0) {
    return { labels: [], datasets: [] }
  }
  
  return {
    labels: stats.value.by_feature.map(f => formatFeatureName(f.feature)),
    datasets: [
      {
        data: stats.value.by_feature.map(f => f.tokens),
        backgroundColor: stats.value.by_feature.map((_, i) => featureColors[i % featureColors.length]),
        borderWidth: 0,
      },
    ],
  }
})

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      callbacks: {
        label: (ctx: any) => `${ctx.parsed.y.toLocaleString()} tokens`,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        callback: (value: string | number) => {
          const num = typeof value === 'number' ? value : parseFloat(value)
          return num >= 1000 ? `${num / 1000}k` : num
        },
      },
    },
  },
}

const pieChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        padding: 15,
        usePointStyle: true,
        font: { size: 12 },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const value = ctx.parsed
          const total = ctx.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const pct = ((value / total) * 100).toFixed(1)
          return `${ctx.label}: ${value.toLocaleString()} tokens (${pct}%)`
        },
      },
    },
  },
}

// Helper functions
function formatFeatureName(feature: string): string {
  return feature
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}k`
  return tokens.toString()
}

// API
async function fetchUsageStats() {
  loading.value = true
  error.value = null

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const params = new URLSearchParams()
    if (filterYear.value) params.set('year', String(filterYear.value))
    if (filterMonth.value) params.set('month', String(filterMonth.value))
    if (filterUserId.value) params.set('user_id', filterUserId.value)
    if (filterOrgId.value) params.set('org_id', filterOrgId.value)

    const url = `${API_BASE}/api/ai-usage/stats?${params.toString()}`
    const res = await fetch(url, { headers })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Failed to fetch usage stats')
    }

    stats.value = await res.json()
  } catch (err: any) {
    error.value = err.message || 'An error occurred'
    console.error('Error fetching usage stats:', err)
  } finally {
    loading.value = false
  }
}

// Month options
const monthOptions = [
  { value: null, label: 'All Months' },
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
]

const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  return [
    { value: null, label: 'All Years' },
    ...Array.from({ length: 3 }, (_, i) => ({
      value: currentYear - i,
      label: String(currentYear - i),
    })),
  ]
})

// Watch filters
watch([filterYear, filterMonth, filterUserId, filterOrgId], () => {
  fetchUsageStats()
})

onMounted(() => {
  if (isLoggedIn.value) {
    fetchUsageStats()
  }
})
</script>

<template>
  <div class="usage-dashboard">
    <!-- Auth banner -->
    <div v-if="!isLoggedIn" class="banner info">
      Sign in to view your AI usage statistics.
      <RouterLink to="/login" class="link-inline">Sign in</RouterLink>
    </div>

    <!-- Header -->
    <div class="header">
      <div>
        <h1>AI Usage Dashboard</h1>
        <p class="subtitle">Track your AI feature usage and token consumption.</p>
      </div>
    </div>

    <!-- Filters -->
    <div v-if="isLoggedIn" class="filters">
      <div class="filter-group">
        <label>Year</label>
        <select v-model="filterYear" class="ds-input">
          <option
            v-for="opt in yearOptions"
            :key="opt.value ?? 'all'"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Month</label>
        <select v-model="filterMonth" class="ds-input">
          <option
            v-for="opt in monthOptions"
            :key="opt.value ?? 'all'"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>

      <button class="btn-secondary" @click="fetchUsageStats">
        🔄 Refresh
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && isLoggedIn" class="loading">
      <div class="spinner" />
      Loading usage data...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="banner error">
      {{ error }}
      <button class="btn-link" @click="fetchUsageStats">Retry</button>
    </div>

    <!-- Content -->
    <div v-else-if="stats && isLoggedIn" class="dashboard-content">
      <!-- Quota Progress -->
      <section class="quota-section">
        <h2>AI Usage Quota</h2>
        <div class="quota-card">
          <div class="quota-header">
            <span class="quota-label">Token Usage</span>
            <span class="quota-value">
              {{ formatTokens(stats.quota.used) }}
              <span v-if="stats.quota.limit">/ {{ formatTokens(stats.quota.limit) }}</span>
              <span v-else class="unlimited">Unlimited</span>
            </span>
          </div>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :class="{ warning: stats.quota.percentage > 75, danger: stats.quota.percentage > 90 }"
              :style="{ width: `${Math.min(stats.quota.percentage, 100)}%` }"
            />
          </div>
          <div class="quota-footer">
            <span v-if="stats.quota.limit">
              {{ stats.quota.percentage.toFixed(1) }}% used
            </span>
            <span v-else class="unlimited-note">
              No usage limits on your plan
            </span>
          </div>
        </div>
      </section>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">🤖</div>
          <div class="stat-info">
            <div class="stat-value">{{ formatTokens(stats.total_tokens) }}</div>
            <div class="stat-label">Total Tokens</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total_requests.toLocaleString() }}</div>
            <div class="stat-label">Total Requests</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.by_feature.length }}</div>
            <div class="stat-label">Features Used</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-info">
            <div class="stat-value">
              {{ stats.total_requests > 0 ? Math.round(stats.total_tokens / stats.total_requests) : 0 }}
            </div>
            <div class="stat-label">Avg Tokens/Request</div>
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <!-- Monthly Bar Chart -->
        <section class="chart-section">
          <h2>Usage by Month</h2>
          <div v-if="stats.by_month.length > 0" class="chart-container">
            <Bar :data="monthlyChartData" :options="barChartOptions" />
          </div>
          <div v-else class="empty-chart">
            <p>No monthly data available</p>
          </div>
        </section>

        <!-- Feature Pie Chart -->
        <section class="chart-section">
          <h2>Usage by Feature</h2>
          <div v-if="stats.by_feature.length > 0" class="chart-container pie">
            <Pie :data="featurePieData" :options="pieChartOptions" />
          </div>
          <div v-else class="empty-chart">
            <p>No feature data available</p>
          </div>
        </section>
      </div>

      <!-- Top Users (Admin only) -->
      <section v-if="canViewOrgStats && stats.top_users.length > 0" class="top-users-section">
        <h2>Top Users by Token Usage</h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>User</th>
                <th>Tokens Used</th>
                <th>Requests</th>
                <th>Avg/Request</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(user, idx) in stats.top_users" :key="user.user_id">
                <td class="rank">{{ idx + 1 }}</td>
                <td class="email">{{ user.email }}</td>
                <td class="tokens">{{ formatTokens(user.tokens) }}</td>
                <td class="requests">{{ user.request_count.toLocaleString() }}</td>
                <td class="avg">
                  {{ user.request_count > 0 ? Math.round(user.tokens / user.request_count) : 0 }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Feature Breakdown Table -->
      <section class="features-section">
        <h2>Feature Breakdown</h2>
        <div v-if="stats.by_feature.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Tokens</th>
                <th>Requests</th>
                <th>% of Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="feat in stats.by_feature" :key="feat.feature">
                <td class="feature-name">{{ formatFeatureName(feat.feature) }}</td>
                <td class="tokens">{{ formatTokens(feat.tokens) }}</td>
                <td class="requests">{{ feat.request_count.toLocaleString() }}</td>
                <td class="percentage">
                  {{ ((feat.tokens / stats.total_tokens) * 100).toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          <p>No feature data available for this period.</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.usage-dashboard {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Banners */
.banner {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.banner.info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.banner.error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.link-inline {
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
  margin-left: 0.5rem;
}

/* Header */
.header {
  margin-bottom: 1.5rem;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: var(--color-text, #fff);
}

.subtitle {
  margin: 0.25rem 0 0;
  color: var(--color-text-muted, #888);
}

/* Filters */
.filters {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--color-surface, #1a1a2e);
  border-radius: 12px;
  border: 1px solid var(--color-border, #333);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.filter-group label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-muted, #888);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ds-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border, #333);
  border-radius: 6px;
  background: var(--color-background, #0f0f1a);
  color: var(--color-text, #fff);
  font-size: 0.875rem;
  min-width: 140px;
}

.btn-secondary {
  background: var(--color-surface, #1a1a2e);
  color: var(--color-text, #fff);
  border: 1px solid var(--color-border, #333);
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: var(--color-surface-hover, #252540);
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary, #4f46e5);
  cursor: pointer;
  text-decoration: underline;
}

/* Loading */
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem;
  color: var(--color-text-muted, #888);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border, #333);
  border-top-color: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Content */
.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Quota Section */
.quota-section h2,
.chart-section h2,
.top-users-section h2,
.features-section h2 {
  margin: 0 0 1rem;
  font-size: 1.125rem;
  color: var(--color-text, #fff);
}

.quota-card {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  padding: 1.25rem;
}

.quota-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.quota-label {
  font-weight: 500;
  color: var(--color-text, #fff);
}

.quota-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text, #fff);
}

.unlimited {
  color: var(--color-primary, #4f46e5);
  font-weight: 500;
}

.progress-bar {
  height: 12px;
  background: var(--color-background, #0f0f1a);
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5, #7c3aed);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.progress-fill.warning {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.progress-fill.danger {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.quota-footer {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

.unlimited-note {
  color: var(--color-primary, #4f46e5);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  font-size: 2rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text, #fff);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

/* Charts */
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}

.chart-section {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  padding: 1.25rem;
}

.chart-container {
  height: 300px;
}

.chart-container.pie {
  height: 280px;
}

.empty-chart {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted, #888);
  font-style: italic;
}

/* Tables */
.table-wrapper {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.75rem 1rem;
  text-align: left;
}

.data-table th {
  background: var(--color-background, #0f0f1a);
  color: var(--color-text-muted, #888);
  font-weight: 500;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  border-top: 1px solid var(--color-border, #333);
  color: var(--color-text, #fff);
}

.data-table .rank {
  font-weight: 600;
  color: var(--color-primary, #4f46e5);
}

.data-table .email {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-table .tokens {
  font-weight: 600;
}

.data-table .feature-name {
  font-weight: 500;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 2rem;
  background: var(--color-surface, #1a1a2e);
  border: 1px dashed var(--color-border, #333);
  border-radius: 12px;
  color: var(--color-text-muted, #888);
}

/* Responsive */
@media (max-width: 768px) {
  .usage-dashboard {
    padding: 1rem;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .chart-container,
  .chart-container.pie {
    height: 250px;
  }

  .filters {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    width: 100%;
  }

  .ds-input {
    width: 100%;
  }
}
</style>
