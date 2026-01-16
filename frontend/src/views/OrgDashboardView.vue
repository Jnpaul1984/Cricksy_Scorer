<template>
  <div class="org-dashboard">
    <!-- Header -->
    <header class="org-header">
      <div class="org-header-text">
        <div class="org-title-row">
          <h1>Organization Dashboard</h1>
          <BaseBadge variant="primary" :uppercase="false">Beta</BaseBadge>
        </div>
        <p class="org-subtitle">
          High-level overview of all teams, matches, and performance trends across your organization.
        </p>
      </div>

      <div class="org-header-actions">
        <BaseButton variant="ghost" size="sm" @click="refreshData">
          Refresh data
        </BaseButton>
        <BaseBadge variant="neutral" :uppercase="false">
          Last sync: {{ lastSyncLabel }}
        </BaseBadge>
      </div>
    </header>

    <!-- Main grid layout -->
    <div class="org-dashboard-grid">
      <!-- Main content column -->
      <div class="org-main-column">
        <!-- Summary metrics -->
        <section class="org-summary">
          <BaseCard padding="md" class="org-summary-card">
            <p class="org-summary-label">Total Teams</p>
            <p class="org-summary-value">{{ orgStats?.totalTeams ?? '—' }}</p>
            <p class="org-summary-footnote">Active this season</p>
          </BaseCard>

          <BaseCard padding="md" class="org-summary-card">
            <p class="org-summary-label">Total Matches</p>
            <p class="org-summary-value">{{ orgStats?.totalMatches ?? '—' }}</p>
            <p class="org-summary-footnote">Played this season</p>
          </BaseCard>

          <BaseCard padding="md" class="org-summary-card">
            <p class="org-summary-label">Win Rate</p>
            <p class="org-summary-value">{{ orgStats?.seasonWinRate ?? '—' }}{{ orgStats?.seasonWinRate ? '%' : '' }}</p>
            <p class="org-summary-footnote">Across all teams</p>
          </BaseCard>

          <BaseCard padding="md" class="org-summary-card">
            <p class="org-summary-label">Avg Run Rate</p>
            <p class="org-summary-value">{{ orgStats?.avgRunRate ?? '—' }}</p>
            <p class="org-summary-footnote">Runs per over</p>
          </BaseCard>
        </section>

        <!-- Teams performance table -->
        <BaseCard padding="lg" class="org-panel">
          <div class="org-panel-header">
            <div>
              <h2 class="org-panel-title">Team Performance</h2>
              <p class="org-panel-subtitle">Season standings and key metrics by team.</p>
            </div>
          </div>

          <div v-if="teams.length === 0" class="org-empty-state">
            <p>No team data available yet.</p>
            <p class="org-empty-hint">Once teams are registered and matches are played, performance data will appear here.</p>
          </div>

          <div v-else class="org-table-scroll">
            <table class="org-table">
              <thead>
                <tr>
                  <th>Team</th>
                  <th>Played</th>
                  <th>Won</th>
                  <th>Lost</th>
                  <th>Win %</th>
                  <th>Avg Score</th>
                  <th>NRR</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="team in teams" :key="team.id">
                  <td>{{ team.name }}</td>
                  <td>{{ team.played }}</td>
                  <td>{{ team.won }}</td>
                  <td>{{ team.lost }}</td>
                  <td>{{ team.winPercent }}%</td>
                  <td>{{ team.avgScore }}</td>
                  <td :class="team.nrr >= 0 ? 'org-positive' : 'org-negative'">
                    {{ team.nrr >= 0 ? '+' : '' }}{{ team.nrr.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </BaseCard>

        <!-- Recent matches -->
        <BaseCard padding="lg" class="org-panel">
          <div class="org-panel-header">
            <div>
              <h2 class="org-panel-title">Recent Matches</h2>
              <p class="org-panel-subtitle">Latest results across your organization.</p>
            </div>
            <BaseButton variant="ghost" size="sm" @click="viewAllMatches">
              View all
            </BaseButton>
          </div>

          <div v-if="recentMatches.length === 0" class="org-empty-state">
            <p>No recent matches.</p>
            <p class="org-empty-hint">Matches will appear here once games are completed.</p>
          </div>

          <div v-else class="org-matches-list">
            <div v-for="match in recentMatches" :key="match.id" class="org-match-item">
              <div class="org-match-info">
                <span class="org-match-teams">{{ match.teams }}</span>
                <span class="org-match-date">{{ match.date }}</span>
              </div>
              <div class="org-match-result">
                <BaseBadge :variant="match.won ? 'success' : 'danger'" :uppercase="false">
                  {{ match.result }}
                </BaseBadge>
              </div>
            </div>
          </div>
        </BaseCard>
      </div>

      <!-- Sidebar column -->
      <aside class="org-side-column">
        <AiCalloutsPanel
          :callouts="orgAiCallouts"
          :loading="orgLoading"
          :max-items="5"
          dense
          show-view-all-button
          title="AI Org Callouts"
          description="High-level patterns and risks across your teams this season."
          @view-all="handleViewAllInsights"
        />

        <!-- Phase breakdown summary -->
        <BaseCard v-if="orgStats" padding="md" class="org-phase-summary">
          <h3 class="org-phase-title">Phase Performance</h3>
          <p class="org-phase-subtitle">Average net runs vs par by match phase.</p>

          <div class="org-phase-list">
            <div class="org-phase-item">
              <span class="org-phase-label">Powerplay</span>
              <span
                class="org-phase-value"
                :class="(orgStats.powerplayNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative'"
              >
                {{ (orgStats.powerplayNetRuns ?? 0) >= 0 ? '+' : '' }}{{ orgStats.powerplayNetRuns ?? 0 }}
              </span>
            </div>
            <div class="org-phase-item">
              <span class="org-phase-label">Middle overs</span>
              <span
                class="org-phase-value"
                :class="(orgStats.middleNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative'"
              >
                {{ (orgStats.middleNetRuns ?? 0) >= 0 ? '+' : '' }}{{ orgStats.middleNetRuns ?? 0 }}
              </span>
            </div>
            <div class="org-phase-item">
              <span class="org-phase-label">Death overs</span>
              <span
                class="org-phase-value"
                :class="(orgStats.deathNetRuns ?? 0) >= 0 ? 'org-positive' : 'org-negative'"
              >
                {{ (orgStats.deathNetRuns ?? 0) >= 0 ? '+' : '' }}{{ orgStats.deathNetRuns ?? 0 }}
              </span>
            </div>
          </div>
        </BaseCard>

        <!-- Standout player -->
        <BaseCard v-if="orgStats?.standoutPlayerName" padding="md" class="org-standout">
          <h3 class="org-standout-title">Standout Performer</h3>
          <div class="org-standout-player">
            <p class="org-standout-name">{{ orgStats.standoutPlayerName }}</p>
            <p class="org-standout-team">{{ orgStats.standoutPlayerTeam }}</p>
          </div>
          <div class="org-standout-stats">
            <BaseBadge variant="success" :uppercase="false">
              {{ orgStats.standoutPlayerImpact }}
            </BaseBadge>
          </div>
        </BaseCard>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, AiCalloutsPanel } from '@/components'
import type { AiCallout, CalloutSeverity } from '@/components'

const router = useRouter()

// Loading state
// FIX A4: Remove ALL mock org data - show unavailable state
const orgLoading = ref(false)
const lastSyncLabel = ref('—')
const backendEndpointsAvailable = ref(false)
const requiredEndpoints = [
  'GET /organizations/{orgId}/stats',
  'GET /organizations/{orgId}/teams',
  'GET /organizations/{orgId}/recent-matches'
]

// Define type for org stats structure
interface OrgStats {
  totalTeams: number
  totalMatches: number
  seasonWinRate: number
  avgRunRate: number
  powerplayNetRuns: number
  middleNetRuns: number
  deathNetRuns: number
  standoutPlayerName?: string
  standoutPlayerTeam?: string
  standoutPlayerImpact?: string
}

// NO MOCK DATA - return null when backend unavailable
const orgStats = computed<OrgStats | null>(() => {
  if (!backendEndpointsAvailable.value) return null
  // TODO: Fetch from API when endpoint ready
  // const data = await apiRequest('/organizations/{orgId}/stats')
  return null
})

// NO MOCK DATA - empty array when backend unavailable
const teams = ref<any[]>([])

// NO MOCK DATA - empty array when backend unavailable
const recentMatches = ref<any[]>([])

// NO MOCK DATA - callouts derived from real data only
const orgAiCallouts = computed<AiCallout[]>(() => {
  const stats = orgStats.value
  if (!stats) return []
  
  const callouts: AiCallout[] = []

  // Only generate callouts from REAL data
  if (stats.seasonWinRate >= 65) {
    callouts.push({
      id: 'high-win-rate',
      title: 'Strong season performance',
      body: `Your teams have won around ${Math.round(stats.seasonWinRate)}% of their games this season.`,
      category: 'Org',
      severity: 'positive' as CalloutSeverity,
      scope: 'All teams',
    })
  }

  // Powerplay strength
  if (stats.powerplayNetRuns > 0) {
    callouts.push({
      id: 'powerplay-advantage',
      title: 'Powerplay advantage',
      body: `On average, your sides are ${Math.round(stats.powerplayNetRuns)} runs ahead of par during the powerplay.`,
      category: 'Org',
      severity: 'positive' as CalloutSeverity,
      scope: 'All teams',
    })
  }

  // All other callouts removed - they were based on mock data
  // When backend provides real stats, add callout logic here

  return callouts
})

// Actions
function refreshData() {
  // TODO: Hook into real data refresh when backend is ready
  lastSyncLabel.value = 'Just now'
}

function viewAllMatches() {
  router.push({ name: 'AnalystWorkspace' })
}

function handleViewAllInsights() {
  // TODO: Navigate to a dedicated insights page when available
  console.log('View all insights clicked')
}
</script>

<style scoped>
/* =====================================================
   ORG DASHBOARD VIEW - Using Design System Tokens
   ===================================================== */

.org-dashboard {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 100vh;
  background: var(--color-bg);
}

/* HEADER */
.org-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.org-header-text {
  display: grid;
  gap: var(--space-2);
}

.org-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.org-title-row h1 {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--font-extrabold);
  color: var(--color-text);
}

.org-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 600px;
}

.org-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* MAIN GRID LAYOUT */
.org-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(0, 1.2fr);
  gap: var(--space-4);
}

.org-main-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.org-side-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* SUMMARY CARDS */
.org-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-3);
}

.org-summary-card {
  display: grid;
  gap: var(--space-1);
  text-align: center;
}

.org-summary-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.org-summary-value {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--font-extrabold);
  color: var(--color-text);
}

.org-summary-footnote {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* PANELS */
.org-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.org-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.org-panel-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.org-panel-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* EMPTY STATE */
.org-empty-state {
  padding: var(--space-4) var(--space-3);
  text-align: left;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.org-empty-state p {
  margin: 0;
}

.org-empty-hint {
  margin-top: var(--space-1) !important;
  font-size: var(--text-xs);
  opacity: 0.8;
}

/* TABLE */
.org-table-scroll {
  overflow-x: auto;
}

.org-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.org-table th,
.org-table td {
  padding: var(--space-3) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.org-table th {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-surface-hover);
}

.org-table tbody tr:hover {
  background: var(--color-surface-hover);
}

.org-table td {
  color: var(--color-text);
}

.org-positive {
  color: var(--color-success);
  font-weight: var(--font-semibold);
}

.org-negative {
  color: var(--color-danger);
  font-weight: var(--font-semibold);
}

/* MATCHES LIST */
.org-matches-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.org-match-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
}

.org-match-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.org-match-teams {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.org-match-date {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* PHASE SUMMARY */
.org-phase-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.org-phase-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.org-phase-subtitle {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.org-phase-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.org-phase-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
}

.org-phase-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.org-phase-value {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

/* STANDOUT PLAYER */
.org-standout {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.org-standout-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.org-standout-player {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.org-standout-name {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text);
}

.org-standout-team {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.org-standout-stats {
  display: flex;
  gap: var(--space-2);
}

/* RESPONSIVE */
@media (max-width: 960px) {
  .org-dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .org-side-column {
    order: 2;
  }

  .org-main-column {
    order: 1;
  }
}

@media (max-width: 600px) {
  .org-dashboard {
    padding: var(--space-3);
  }

  .org-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .org-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
