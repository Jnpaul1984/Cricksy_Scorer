<template>
  <div class="analyst-workspace">
    <!-- HEADER -->
    <section class="aw-header">
      <div class="aw-header-text">
        <div class="aw-title-row">
          <h1>Analyst Workspace</h1>
          <BaseBadge variant="primary" :uppercase="false">Beta</BaseBadge>
        </div>
        <p class="aw-subtitle">
          Slice ball-by-ball data by phase, player, and match context to find patterns, trends, and weaknesses.
        </p>
      </div>

      <!-- View / context controls -->
      <div class="aw-header-actions">
        <ExportUI :data="filteredMatches" />
        <BaseButton variant="ghost" size="sm" @click="refreshData">
          Refresh data
        </BaseButton>
        <BaseBadge variant="neutral" :uppercase="false">
          Last sync: {{ lastSyncLabel }}
        </BaseBadge>
      </div>
    </section>

    <!-- MAIN LAYOUT -->
    <section class="aw-main">
      <!-- LEFT: FILTER PANEL -->
      <aside class="aw-filters">
        <BaseCard padding="lg" class="aw-filters-card">
          <h2 class="aw-section-title">Filters</h2>

          <div class="aw-filter-group">
            <BaseInput
              v-model="filters.search"
              label="Search"
              placeholder="Player, team, opponent, venue..."
            />
          </div>

          <div class="aw-filter-group">
            <p class="aw-filter-label">Format</p>
            <div class="aw-chip-row">
              <BaseButton
                v-for="format in formatOptions"
                :key="format.value"
                variant="ghost"
                size="sm"
                class="aw-chip"
                :class="{ 'aw-chip--active': filters.format === format.value }"
                @click="filters.format = format.value"
              >
                {{ format.label }}
              </BaseButton>
            </div>
          </div>

          <div class="aw-filter-group">
            <p class="aw-filter-label">Match phase</p>
            <div class="aw-chip-row">
              <BaseButton
                v-for="phase in phaseOptions"
                :key="phase.value"
                variant="ghost"
                size="sm"
                class="aw-chip"
                :class="{ 'aw-chip--active': filters.phase === phase.value }"
                @click="filters.phase = phase.value"
              >
                {{ phase.label }}
              </BaseButton>
            </div>
          </div>

          <div class="aw-filter-group">
            <p class="aw-filter-label">Perspective</p>
            <div class="aw-chip-row">
              <BaseButton
                v-for="perspective in perspectiveOptions"
                :key="perspective.value"
                variant="ghost"
                size="sm"
                class="aw-chip"
                :class="{ 'aw-chip--active': filters.perspective === perspective.value }"
                @click="filters.perspective = perspective.value"
              >
                {{ perspective.label }}
              </BaseButton>
            </div>
          </div>

          <div class="aw-filter-footer">
            <BaseButton variant="ghost" size="sm" @click="resetFilters">
              Reset filters
            </BaseButton>
          </div>
        </BaseCard>

        <!-- AI Callouts Panel -->
        <AiCalloutsPanel
          v-if="workspaceCallouts.length > 0"
          title="AI Insights"
          description="Patterns detected across your matches."
          :callouts="workspaceCallouts"
          :max-items="4"
          @select="handleCalloutSelect"
        />
      </aside>

      <!-- RIGHT: CONTENT -->
      <div class="aw-content">
        <!-- SUMMARY CARDS -->
        <section class="aw-summary">
          <BaseCard padding="md" class="aw-summary-card">
            <p class="aw-summary-label">Avg runs per over</p>
            <p class="aw-summary-value">{{ summary.avgRunsPerOver }}</p>
            <p class="aw-summary-footnote">Filtered matches</p>
          </BaseCard>

          <BaseCard padding="md" class="aw-summary-card">
            <p class="aw-summary-label">Wickets in selected phase</p>
            <p class="aw-summary-value">{{ summary.wicketsInPhase }}</p>
            <p class="aw-summary-footnote">{{ currentPhaseLabel }}</p>
          </BaseCard>

          <BaseCard padding="md" class="aw-summary-card">
            <p class="aw-summary-label">Top impact bowler</p>
            <p class="aw-summary-value">{{ summary.topBowler || '—' }}</p>
            <p class="aw-summary-footnote">By wickets + economy</p>
          </BaseCard>
        </section>

        <!-- TABS -->
        <section class="aw-tabs">
          <nav class="aw-tabs-nav">
            <BaseButton
              v-for="tab in tabs"
              :key="tab.value"
              variant="ghost"
              size="sm"
              class="aw-tab-btn"
              :class="{ 'aw-tab-btn--active': activeTab === tab.value }"
              @click="activeTab = tab.value"
            >
              {{ tab.label }}
            </BaseButton>
          </nav>

          <!-- TAB PANELS -->
          <BaseCard padding="lg" class="aw-tab-panel">
            <!-- Matches tab -->
            <div v-if="activeTab === 'matches'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Matches</h3>
                <p class="aw-table-subtitle">
                  Recent matches matching your filters. Click a row to open the case study.
                </p>
              </div>

              <!-- Loading state -->
              <div v-if="matchesLoading" class="aw-matches-loading">
                <p>Loading matches...</p>
              </div>

              <!-- Error state -->
              <div v-else-if="matchesError" class="aw-matches-error">
                <p>{{ matchesError }}</p>
                <BaseButton variant="ghost" size="sm" @click="loadMatches">
                  Retry
                </BaseButton>
              </div>

              <!-- Empty state -->
              <div v-else-if="filteredMatches.length === 0" class="aw-matches-empty">
                <p>No matches found for the current filters.</p>
                <p class="aw-matches-empty-hint">
                  Try adjusting your search or filter criteria.
                </p>
              </div>

              <!-- Enhanced match list -->
              <div v-else class="aw-matches-list">
                <div class="aw-matches-head">
                  <div class="aw-matches-col aw-matches-col--main">Match</div>
                  <div class="aw-matches-col aw-matches-col--impact">Impact</div>
                  <div class="aw-matches-col aw-matches-col--trend">Trend</div>
                  <div class="aw-matches-col aw-matches-col--tags">Tags</div>
                </div>

                <div
                  v-for="match in filteredMatches"
                  :id="`aw-match-${match.id}`"
                  :key="match.id"
                  class="aw-matches-row"
                  @click="openMatchCaseStudy(match.id)"
                >
                  <!-- Main info column -->
                  <div class="aw-matches-col aw-matches-col--main">
                    <div class="aw-match-title">{{ match.teams }}</div>
                    <div class="aw-match-meta">
                      <span>{{ match.format }}</span>
                      <span>• {{ match.date }}</span>
                      <span>• {{ match.result }}</span>
                    </div>
                  </div>

                  <!-- Impact column -->
                  <div class="aw-matches-col aw-matches-col--impact">
                    <ImpactBar
                      :value="match.netImpact ?? 0"
                      :min="-20"
                      :max="20"
                      size="sm"
                      :label="formatImpactLabel(match)"
                      :positive-label="'Favouring ' + (match.primaryTeam || match.teams.split(' vs ')[0])"
                      :negative-label="'Pressure on ' + (match.primaryTeam || match.teams.split(' vs ')[0])"
                    />
                  </div>

                  <!-- Trend column -->
                  <div class="aw-matches-col aw-matches-col--trend">
                    <div v-if="match.winProbSeries?.length" class="aw-trend-wrap">
                      <MiniSparkline
                        :points="match.winProbSeries"
                        :highlight-last="true"
                        :variant="getSparklineVariant(match)"
                      />
                      <span class="aw-trend-label">Win probability</span>
                    </div>
                    <div v-else-if="match.runRateSeries?.length" class="aw-trend-wrap">
                      <MiniSparkline
                        :points="match.runRateSeries"
                        :highlight-last="true"
                        variant="neutral"
                      />
                      <span class="aw-trend-label">Run rate trend</span>
                    </div>
                    <span v-else class="aw-trend-none">No trend data</span>
                  </div>

                  <!-- Tags column -->
                  <div class="aw-matches-col aw-matches-col--tags">
                    <div class="aw-tag-badges">
                      <BaseBadge v-if="match.tagged" variant="primary" :uppercase="false">
                        Tagged
                      </BaseBadge>
                      <BaseBadge v-if="match.caseStudyId" variant="success" :uppercase="false">
                        Case Study
                      </BaseBadge>
                    </div>
                  </div>

                  <!-- Analytics row (ImpactBar + MiniSparkline) -->
                  <div class="aw-match-analytics">
                    <ImpactBar
                      class="aw-impact"
                      :class="[
                        match.key_flag === 'dominant' && 'aw-impact--good',
                        match.key_flag === 'under_pressure' && 'aw-impact--bad',
                        match.key_flag === 'volatile' && 'aw-impact--warn',
                      ]"
                      :value="match.impact_score ?? 0"
                      :label="match.key_flag ? match.key_flag : 'Impact'"
                    />

                    <MiniSparkline
                      class="aw-trend"
                      :points="match.phase_impact_trend?.length ? match.phase_impact_trend : [0]"
                      :height="28"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Players tab -->
            <div v-else-if="activeTab === 'players'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Players</h3>
                <p class="aw-table-subtitle">
                  Player-level aggregates for the current filters.
                </p>
              </div>
              <div class="aw-table-scroll">
                <table class="aw-table">
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Role</th>
                      <th>Innings</th>
                      <th>Runs</th>
                      <th>SR</th>
                      <th>Wkts</th>
                      <th>Eco</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="player in filteredPlayers" :key="player.id">
                      <td>{{ player.name }}</td>
                      <td>{{ player.role }}</td>
                      <td>{{ player.innings }}</td>
                      <td>{{ player.runs }}</td>
                      <td>{{ player.strikeRate }}</td>
                      <td>{{ player.wickets }}</td>
                      <td>{{ player.economy }}</td>
                    </tr>
                    <tr v-if="filteredPlayers.length === 0">
                      <td colspan="7" class="aw-empty">
                        No players found for the current filters.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Case studies / coming soon -->
            <div v-else-if="activeTab === 'case-studies'" class="aw-table-wrapper">
              <div class="aw-empty-large">
                <h3>{{ currentTabLabel }}</h3>
                <p>
                  This area will show deeper breakdowns (case studies, AI pattern reports)
                  in a future version.
                </p>
              </div>
            </div>

            <!-- Analytics Tab -->
            <div v-else-if="activeTab === 'analytics'" class="aw-table-wrapper">
              <AnalyticsTablesWidget :profile="null" />
            </div>

            <!-- Default fallback -->
            <div v-else class="aw-table-wrapper">
              <div class="aw-empty-large">
                <h3>{{ currentTabLabel }}</h3>
                <p>
                  Coming soon...
                </p>
              </div>
            </div>
          </BaseCard>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, BaseInput, ImpactBar, MiniSparkline, AiCalloutsPanel } from '@/components'
import type { AiCallout } from '@/components'
import AnalyticsTablesWidget from '@/components/AnalyticsTablesWidget.vue'
import ExportUI from '@/components/ExportUI.vue'
import {
  getAnalystMatches,
  type AnalystMatchListItem,
} from '@/services/api'

const router = useRouter()

// Types
type AnalystTab = 'matches' | 'players' | 'deliveries' | 'case-studies' | 'analytics'

// State
const activeTab = ref<AnalystTab>('matches')

const filters = reactive({
  search: '',
  format: 'all' as 'all' | 't20' | 'odi' | 'custom',
  phase: 'all' as 'all' | 'powerplay' | 'middle' | 'death',
  perspective: 'all' as 'all' | 'batting' | 'bowling'
})

const formatOptions = [
  { label: 'All', value: 'all' },
  { label: 'T20', value: 't20' },
  { label: 'ODI', value: 'odi' },
  { label: 'Custom', value: 'custom' }
] as const

const phaseOptions = [
  { label: 'All', value: 'all' },
  { label: 'Powerplay', value: 'powerplay' },
  { label: 'Middle', value: 'middle' },
  { label: 'Death', value: 'death' }
] as const

const perspectiveOptions = [
  { label: 'All', value: 'all' },
  { label: 'Batting', value: 'batting' },
  { label: 'Bowling', value: 'bowling' }
] as const

const tabs: { value: AnalystTab; label: string }[] = [
  { value: 'matches', label: 'Matches' },
  { value: 'players', label: 'Players' },
  { value: 'deliveries', label: 'Deliveries' },
  { value: 'case-studies', label: 'Case studies' },
  { value: 'analytics', label: 'Analytics' }
]

const lastSyncLabel = ref('Just now')

// Summary metrics - NO FAKE DATA
// Required: GET /analyst/summary
const summary = reactive({
  avgRunsPerOver: null as number | null,
  wicketsInPhase: null as number | null,
  topBowler: null as string | null
})

// Match type with trend data for visualization (extends backend schema)
interface AnalystMatch {
  id: string
  date: string
  format: string
  teams: string
  result: string
  runRate: number
  phaseSwing: string
  netImpact?: number | null
  winProbSeries?: number[] | null
  runRateSeries?: number[] | null
  tagged?: boolean
  caseStudyId?: string | null
  primaryTeam?: string | null
  // Analytics fields for ImpactBar + MiniSparkline
  impact_score?: number | null
  phase_impact_trend?: number[] | null
  key_flag?: 'dominant' | 'under_pressure' | 'volatile' | null
  // Tags for AI callouts
  tags?: string[] | null
}

// Matches state - wired to backend
const matches = ref<AnalystMatch[]>([])
const matchesLoading = ref(false)
const matchesError = ref<string | null>(null)

// Players list - NO FAKE DATA
// Required: GET /analyst/players
const players = ref<any[]>([])

// Computed
const filteredMatches = computed(() => {
  const term = filters.search.toLowerCase()
  return matches.value.filter((m) => {
    const matchesTerm =
      !term ||
      m.teams.toLowerCase().includes(term) ||
      m.result.toLowerCase().includes(term)
    const matchesFormat =
      filters.format === 'all' ||
      (filters.format === 't20' && m.format === 'T20') ||
      (filters.format === 'odi' && m.format === 'ODI')
    return matchesTerm && matchesFormat
  })
})

const filteredPlayers = computed(() => {
  const term = filters.search.toLowerCase()
  return players.value.filter((p) => {
    const matchesTerm =
      !term || p.name.toLowerCase().includes(term) || p.role.toLowerCase().includes(term)
    return matchesTerm
  })
})

const currentPhaseLabel = computed(() => {
  const map: Record<string, string> = {
    all: 'All phases',
    powerplay: 'Powerplay overs',
    middle: 'Middle overs',
    death: 'Death overs'
  }
  return map[filters.phase] ?? 'All phases'
})

const currentTabLabel = computed(() => {
  const tab = tabs.find((t) => t.value === activeTab.value)
  return tab?.label ?? ''
})

// Workspace-level AI callouts derived from matches
const workspaceCallouts = computed<AiCallout[]>(() => {
  if (!matches.value.length) return []

  const list: AiCallout[] = []
  const recent = matches.value.slice(0, 6)

  // Check for death overs collapses
  const deathCollapses = recent.filter(m =>
    m.tags?.includes('death overs collapse')
  )
  if (deathCollapses.length >= 2) {
    list.push({
      id: 'death-collapse',
      title: 'Death overs collapses',
      body: `Detected collapses in ${deathCollapses.length} of last ${recent.length} matches.`,
      severity: 'warning',
      targetDomId: `aw-match-${deathCollapses[0].id}`,
      category: 'death overs',
    })
  }

  // Check for powerplay dominance
  const strongPowerplay = recent.filter(m =>
    m.tags?.includes('powerplay dominance')
  )
  if (strongPowerplay.length >= 2) {
    list.push({
      id: 'powerplay-dominance',
      title: 'Powerplay dominance',
      body: `Strong starts in ${strongPowerplay.length} recent matches.`,
      severity: 'positive',
      targetDomId: `aw-match-${strongPowerplay[0].id}`,
      category: 'powerplay',
    })
  }

  // Check for volatile matches
  const volatileMatches = recent.filter(m =>
    m.key_flag === 'volatile'
  )
  if (volatileMatches.length >= 2) {
    list.push({
      id: 'volatility',
      title: 'Inconsistent phases',
      body: `Volatile phase patterns in ${volatileMatches.length} matches.`,
      severity: 'warning',
      targetDomId: `aw-match-${volatileMatches[0].id}`,
      category: 'consistency',
    })
  }

  // Check for dominant performances
  const dominantMatches = recent.filter(m =>
    m.key_flag === 'dominant'
  )
  if (dominantMatches.length >= 2) {
    list.push({
      id: 'dominant-form',
      title: 'Dominant form',
      body: `Strong performances in ${dominantMatches.length} recent matches.`,
      severity: 'positive',
      targetDomId: `aw-match-${dominantMatches[0].id}`,
      category: 'form',
    })
  }

  // Check for pressure situations
  const pressureMatches = recent.filter(m =>
    m.key_flag === 'under_pressure'
  )
  if (pressureMatches.length >= 2) {
    list.push({
      id: 'under-pressure',
      title: 'Under pressure',
      body: `Pressure situations in ${pressureMatches.length} matches require attention.`,
      severity: 'critical',
      targetDomId: `aw-match-${pressureMatches[0].id}`,
      category: 'pressure',
    })
  }

  return list
})

// Actions
async function loadMatches() {
  matchesLoading.value = true
  matchesError.value = null
  try {
    const response = await getAnalystMatches()
    // Map backend schema to frontend AnalystMatch interface
    matches.value = response.items.map((item: AnalystMatchListItem): AnalystMatch => ({
      id: item.id,
      date: item.date,
      format: item.format,
      teams: item.teams,
      result: item.result,
      runRate: item.run_rate,
      phaseSwing: item.phase_swing,
      // These fields are not in the backend yet - derive or leave null
      netImpact: null,
      winProbSeries: null,
      runRateSeries: null,
      tagged: false,
      caseStudyId: null,
      primaryTeam: item.teams.split(' vs ')[0] || null,
    }))
  } catch (err) {
    matchesError.value = err instanceof Error ? err.message : 'Failed to load matches'
    console.error('[AnalystWorkspace] Failed to load matches:', err)
  } finally {
    matchesLoading.value = false
    lastSyncLabel.value = 'Just now'
  }
}

async function refreshData() {
  await loadMatches()
}

function resetFilters() {
  filters.search = ''
  filters.format = 'all'
  filters.phase = 'all'
  filters.perspective = 'all'
}

function openMatchCaseStudy(matchId: string) {
  router.push({
    name: 'MatchCaseStudy',
    params: { matchId }
  })
}

function handleCalloutSelect(callout: AiCallout) {
  if (!callout.targetDomId) return

  const el = document.getElementById(callout.targetDomId)
  if (!el) return

  // Scroll to the element
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })

  // Add highlight effect
  el.classList.add('aw-match--highlight')
  window.setTimeout(() => {
    el.classList.remove('aw-match--highlight')
  }, 1400)
}

// Helper functions for display formatting
function formatImpactLabel(match: AnalystMatch): string {
  const v = match.netImpact ?? 0
  if (v > 10) return 'Strong positive'
  if (v > 3) return 'Slightly positive'
  if (v < -10) return 'Strong negative'
  if (v < -3) return 'Slightly negative'
  return 'Around par'
}

function getSparklineVariant(match: AnalystMatch): 'positive' | 'negative' | 'neutral' | 'default' {
  const impact = match.netImpact ?? 0
  if (impact > 5) return 'positive'
  if (impact < -5) return 'negative'
  return 'default'
}

// Lifecycle - load data on mount
onMounted(() => {
  loadMatches()
})
</script>

<style scoped>
/* =====================================================
   ANALYST WORKSPACE VIEW - Using Design System Tokens
   ===================================================== */

.analyst-workspace {
  padding: var(--space-4);
  display: grid;
  gap: var(--space-4);
  min-height: 100vh;
  background: var(--color-bg);
}

/* HEADER */
.aw-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.aw-header-text {
  display: grid;
  gap: var(--space-2);
}

.aw-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.aw-title-row h1 {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--font-extrabold);
  color: var(--color-text);
}

.aw-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 600px;
}

.aw-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* MAIN LAYOUT */
.aw-main {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--space-4);
  align-items: start;
}

/* FILTER PANEL */
.aw-filters {
  position: sticky;
  top: var(--space-4);
}

.aw-filters-card {
  display: grid;
  gap: var(--space-4);
}

.aw-section-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-filter-group {
  display: grid;
  gap: var(--space-2);
}

.aw-filter-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.aw-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.aw-chip {
  border-radius: var(--radius-pill);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.aw-chip:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-strong);
}

.aw-chip--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.aw-chip--active:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.aw-filter-footer {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

/* CONTENT AREA */
.aw-content {
  display: grid;
  gap: var(--space-4);
}

/* SUMMARY CARDS */
.aw-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
}

.aw-summary-card {
  display: grid;
  gap: var(--space-1);
  text-align: center;
}

.aw-summary-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.aw-summary-value {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--font-extrabold);
  color: var(--color-text);
}

.aw-summary-footnote {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* TABS */
.aw-tabs {
  display: grid;
  gap: var(--space-3);
}

.aw-tabs-nav {
  display: flex;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.aw-tab-btn {
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  background: transparent;
  border: none;
  transition: all var(--transition-fast);
}

.aw-tab-btn:hover {
  color: var(--color-text);
  background: var(--color-surface-hover);
}

.aw-tab-btn--active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.aw-tab-btn--active:hover {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.aw-tab-panel {
  min-height: 300px;
}

/* TABLE WRAPPER */
.aw-table-wrapper {
  display: grid;
  gap: var(--space-3);
}

.aw-table-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-table-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.aw-table-scroll {
  overflow-x: auto;
}

.aw-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.aw-table th,
.aw-table td {
  padding: var(--space-3) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.aw-table th {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-surface-hover);
}

.aw-table tbody tr:hover {
  background: var(--color-surface-hover);
}

.aw-table td {
  color: var(--color-text);
}

.aw-row--clickable {
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.aw-row--clickable:hover {
  background-color: var(--color-surface-hover);
}

.aw-actions {
  text-align: right;
  white-space: nowrap;
}

.aw-empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-6) var(--space-4);
}

.aw-empty-large {
  display: grid;
  place-items: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  text-align: center;
}

.aw-empty-large h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-empty-large p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 400px;
}

/* ENHANCED MATCHES LIST */
.aw-matches-loading {
  padding: var(--space-5) 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-align: center;
}

.aw-matches-error {
  padding: var(--space-5);
  font-size: var(--text-sm);
  color: var(--color-danger);
  background: var(--color-danger-subtle);
  border-radius: var(--radius-md);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.aw-matches-empty {
  padding: var(--space-5) 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.aw-matches-empty-hint {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  opacity: 0.8;
}

.aw-matches-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.aw-matches-head,
.aw-matches-row {
  display: grid;
  grid-template-columns: 2.4fr 1.6fr 1.6fr 1.2fr;
  gap: var(--space-3);
  align-items: center;
}

.aw-matches-head {
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.aw-matches-row {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background-color 140ms ease-out;
}

.aw-matches-row:hover {
  background-color: var(--color-surface-hover);
}

.aw-matches-row.aw-match--highlight {
  box-shadow: 0 0 0 2px var(--color-primary-soft);
  background-color: var(--color-primary-subtle);
  transition: box-shadow 160ms ease-out, transform 160ms ease-out, background-color 160ms ease-out;
  transform: translateY(-1px);
}

.aw-matches-col {
  min-width: 0;
}

.aw-match-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-match-meta {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-matches-col--impact {
  display: flex;
  align-items: center;
}

.aw-matches-col--trend {
  display: flex;
  align-items: center;
}

.aw-trend-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
}

.aw-trend-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-trend-none {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-tag-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  justify-content: flex-start;
}

/* MATCH ANALYTICS ROW (ImpactBar + MiniSparkline) */
.aw-match-analytics {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-2);
  grid-column: 1 / -1; /* Span full width of the row */
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-subtle);
}

.aw-impact {
  flex: 1.1;
}

.aw-trend {
  flex: 0.9;
  min-width: 80px;
}

.aw-impact--good {
  --impact-color: var(--color-success);
}

.aw-impact--bad {
  --impact-color: var(--color-danger);
}

.aw-impact--warn {
  --impact-color: var(--color-warning);
}

/* RESPONSIVE */
@media (max-width: 900px) {
  .aw-main {
    grid-template-columns: 1fr;
  }

  .aw-filters {
    position: static;
  }

  .aw-summary {
    grid-template-columns: 1fr;
  }

  .aw-matches-head {
    display: none;
  }

  .aw-matches-row {
    grid-template-columns: 1.8fr 1.2fr;
    grid-template-rows: auto auto;
    row-gap: var(--space-2);
  }

  .aw-matches-col--main {
    grid-column: 1 / -1;
  }

  .aw-matches-col--impact {
    grid-column: 1 / 2;
  }

  .aw-matches-col--trend {
    grid-column: 2 / 3;
  }

  .aw-matches-col--tags {
    grid-column: 1 / -1;
  }
}

@media (max-width: 600px) {
  .analyst-workspace {
    padding: var(--space-3);
  }

  .aw-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .aw-tabs-nav {
    flex-wrap: wrap;
  }
}
</style>
