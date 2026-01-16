<template>
  <div class="case-study">
    <!-- Loading skeleton state -->
    <template v-if="loading">
      <!-- Skeleton header -->
      <header class="cs-header">
        <div class="cs-header-left">
          <BaseCard class="cs-skeleton-card cs-skeleton-card--inline" padding="sm">
            <div class="cs-skeleton-line cs-skeleton-line--sm" />
          </BaseCard>
          <div class="cs-title-block">
            <div class="cs-skeleton-line cs-skeleton-line--lg" />
            <div class="cs-skeleton-line cs-skeleton-line--md" />
          </div>
        </div>
        <div class="cs-header-right">
          <BaseCard class="cs-skeleton-card cs-skeleton-card--badge" padding="sm">
            <div class="cs-skeleton-line cs-skeleton-line--sm" />
          </BaseCard>
        </div>
      </header>

      <!-- Skeleton summary strip -->
      <section class="cs-summary">
        <BaseCard class="cs-skeleton-card" padding="md">
          <div class="cs-skeleton-line cs-skeleton-line--sm" />
          <div class="cs-skeleton-line cs-skeleton-line--lg" />
          <div class="cs-skeleton-line cs-skeleton-line--md" />
        </BaseCard>
        <BaseCard class="cs-skeleton-card" padding="md">
          <div class="cs-skeleton-line cs-skeleton-line--sm" />
          <div class="cs-skeleton-line cs-skeleton-line--lg" />
          <div class="cs-skeleton-line cs-skeleton-line--md" />
        </BaseCard>
        <BaseCard class="cs-skeleton-card" padding="md">
          <div class="cs-skeleton-line cs-skeleton-line--sm" />
          <div class="cs-skeleton-line cs-skeleton-line--lg" />
          <div class="cs-skeleton-line cs-skeleton-line--md" />
        </BaseCard>
      </section>

      <!-- Skeleton main layout -->
      <section class="cs-main">
        <div class="cs-main-left">
          <!-- Skeleton phase breakdown -->
          <BaseCard class="cs-skeleton-card" padding="lg">
            <div class="cs-skeleton-line cs-skeleton-line--md" />
            <div class="cs-skeleton-line cs-skeleton-line--lg" />
            <div class="cs-skeleton-phase-grid">
              <div class="cs-skeleton-phase-card">
                <div class="cs-skeleton-line cs-skeleton-line--md" />
                <div class="cs-skeleton-line cs-skeleton-line--lg" />
                <div class="cs-skeleton-line cs-skeleton-line--sm" />
              </div>
              <div class="cs-skeleton-phase-card">
                <div class="cs-skeleton-line cs-skeleton-line--md" />
                <div class="cs-skeleton-line cs-skeleton-line--lg" />
                <div class="cs-skeleton-line cs-skeleton-line--sm" />
              </div>
              <div class="cs-skeleton-phase-card">
                <div class="cs-skeleton-line cs-skeleton-line--md" />
                <div class="cs-skeleton-line cs-skeleton-line--lg" />
                <div class="cs-skeleton-line cs-skeleton-line--sm" />
              </div>
            </div>
          </BaseCard>

          <!-- Skeleton key players -->
          <BaseCard class="cs-skeleton-card" padding="lg">
            <div class="cs-skeleton-line cs-skeleton-line--md" />
            <div class="cs-skeleton-line cs-skeleton-line--lg" />
            <div class="cs-skeleton-table">
              <div v-for="i in 4" :key="i" class="cs-skeleton-row">
                <div class="cs-skeleton-line cs-skeleton-line--md" />
              </div>
            </div>
          </BaseCard>
        </div>

        <div class="cs-main-right">
          <!-- Skeleton AI summary -->
          <BaseCard class="cs-skeleton-card" padding="lg">
            <div class="cs-skeleton-line cs-skeleton-line--md" />
            <div class="cs-skeleton-line cs-skeleton-line--sm" />
            <div class="cs-skeleton-ai-block">
              <div class="cs-skeleton-line cs-skeleton-line--full" />
              <div class="cs-skeleton-line cs-skeleton-line--full" />
              <div class="cs-skeleton-line cs-skeleton-line--lg" />
            </div>
          </BaseCard>

          <!-- Skeleton dismissal patterns -->
          <BaseCard class="cs-skeleton-card" padding="lg">
            <div class="cs-skeleton-line cs-skeleton-line--md" />
            <div class="cs-skeleton-line cs-skeleton-line--lg" />
            <div class="cs-skeleton-dismissal">
              <div class="cs-skeleton-line cs-skeleton-line--full" />
            </div>
          </BaseCard>
        </div>
      </section>
    </template>

    <!-- Error state -->
    <BaseCard v-else-if="error" padding="lg" class="cs-error">
      {{ error }}
    </BaseCard>

    <template v-else>
      <!-- Topbar / breadcrumb -->
      <header class="cs-header">
        <div class="cs-header-left">
          <BaseButton variant="ghost" size="sm" @click="goBack">
            ← Back to Analyst Workspace
          </BaseButton>

          <div class="cs-title-block">
            <h1>Match case study</h1>
            <p class="cs-subtitle">
              Deep-dive into momentum swings, key players, and dismissal patterns.
            </p>
          </div>
        </div>

        <div class="cs-header-right">
          <BaseBadge variant="neutral" :uppercase="false">
            Match ID: {{ matchId }}
          </BaseBadge>
          <BaseBadge v-if="match" variant="primary" :uppercase="false">
            {{ match.teams_label }}
          </BaseBadge>
        </div>
      </header>

      <!-- Match summary strip -->
      <section v-if="match" class="cs-summary">
        <BaseCard padding="md" class="cs-summary-card">
          <p class="cs-label">Result</p>
          <p class="cs-value">{{ match.result }}</p>
          <p class="cs-footnote">{{ match.date }} • {{ match.format }}</p>
        </BaseCard>

        <BaseCard v-if="momentumSummary" padding="md" class="cs-summary-card">
          <p class="cs-label">Momentum verdict</p>
          <p class="cs-value">{{ momentumSummary.title }}</p>
          <p class="cs-footnote">{{ momentumSummary.subtitle }}</p>
        </BaseCard>

        <BaseCard v-if="keyPhase" padding="md" class="cs-summary-card">
          <p class="cs-label">Key phase</p>
          <p class="cs-value">{{ keyPhase.title }}</p>
          <p class="cs-footnote">{{ keyPhase.detail }}</p>
        </BaseCard>
      </section>

      <!-- No match found state -->
      <section v-else class="cs-not-found">
        <BaseCard padding="lg" class="cs-not-found-card">
          <h2>Match not found</h2>
          <p>No match data available for ID: {{ matchId }}</p>
          <BaseButton variant="primary" size="sm" @click="goBack">
            Return to Analyst Workspace
          </BaseButton>
        </BaseCard>
      </section>

      <!-- Main layout -->
      <section v-if="match" class="cs-main">
      <!-- Left column: phase breakdown + players -->
      <div class="cs-main-left">
        <BaseCard padding="lg" class="cs-panel">
          <div class="cs-phases-header">
            <div>
              <h2 class="cs-panel-title">Phase breakdown</h2>
              <p class="cs-panel-subtitle">
                Runs, wickets, and momentum by over segment.
              </p>
            </div>

            <div class="cs-phases-filters">
              <!-- Innings tabs -->
              <div v-if="inningsOptions.length > 1" class="cs-phases-innings-tabs">
                <BaseButton
                  v-for="opt in inningsOptions"
                  :key="opt.index"
                  size="sm"
                  :variant="opt.index === selectedInningsIndex ? 'primary' : 'ghost'"
                  @click="selectedInningsIndex = opt.index"
                >
                  {{ opt.label }}
                </BaseButton>
              </div>

              <!-- Impact filter pills -->
              <div class="cs-phases-impact-filters">
                <BaseButton
                  size="sm"
                  :variant="selectedImpactFilter === 'all' ? 'secondary' : 'ghost'"
                  @click="selectedImpactFilter = 'all'"
                >
                  All
                </BaseButton>
                <BaseButton
                  size="sm"
                  :variant="selectedImpactFilter === 'positive' ? 'secondary' : 'ghost'"
                  @click="selectedImpactFilter = 'positive'"
                >
                  Positive
                </BaseButton>
                <BaseButton
                  size="sm"
                  :variant="selectedImpactFilter === 'negative' ? 'secondary' : 'ghost'"
                  @click="selectedImpactFilter = 'negative'"
                >
                  Negative
                </BaseButton>
                <BaseButton
                  size="sm"
                  :variant="selectedImpactFilter === 'neutral' ? 'secondary' : 'ghost'"
                  @click="selectedImpactFilter = 'neutral'"
                >
                  Even
                </BaseButton>
              </div>
            </div>
          </div>

          <!-- Empty state for phases (no data at all) -->
          <div v-if="phaseBreakdown.length === 0" class="cs-empty-state">
            <p>No phase analytics available for this match yet.</p>
            <p class="cs-empty-hint">Try re-running analytics once the scorecard and ball-by-ball data are complete.</p>
          </div>

          <!-- Empty state for filtered results -->
          <div v-else-if="filteredPhases.length === 0" class="cs-empty-state">
            <p>No phase data for this selection.</p>
            <p class="cs-empty-hint">Try a different innings or impact filter.</p>
          </div>

          <!-- Phase cards -->
          <div v-else class="cs-phase-grid">
            <BaseCard
              v-for="phase in filteredPhases"
              :id="getPhaseCardDomId(phase)"
              :key="`${phase.id}-${phase.start_over}-${phase.end_over}`"
              class="cs-phase-card"
              padding="md"
              :data-phase="phase.id"
              :data-innings="phase.innings_index"
            >
              <!-- Header row -->
              <header class="cs-phase-header">
                <div>
                  <h3 class="cs-phase-title">{{ phase.label }}</h3>
                  <p class="cs-phase-meta">
                    Overs {{ phase.start_over }}–{{ phase.end_over }} •
                    {{ phase.runs }} runs • {{ phase.wickets }} wkts
                  </p>
                </div>
                <BaseBadge
                  :variant="
                    phase.impact === 'positive'
                      ? 'success'
                      : phase.impact === 'negative'
                        ? 'danger'
                        : 'neutral'
                  "
                  :uppercase="true"
                >
                  {{ phase.id.toUpperCase() }}
                </BaseBadge>
              </header>

              <!-- Metrics row (Impact Bar + Sparkline) -->
              <div class="cs-phase-metrics">
                <div class="cs-phase-metrics-main impact-bar-wrapper">
                  <ImpactBar
                    :value="phase.net_swing_vs_par"
                    :min="-20"
                    :max="20"
                    size="sm"
                    :label="phase.impact_label || deriveImpactLabel(phase)"
                    :positive-label="'Batting in control'"
                    :negative-label="'Bowling pressure'"
                  />
                </div>

                <div v-if="phase.run_rate_series?.length" class="cs-phase-metrics-trend">
                  <MiniSparkline
                    :points="phase.run_rate_series"
                    :highlight-last="true"
                    :variant="getSparklineVariant(phase)"
                  />
                  <p class="cs-phase-trend-label">Run rate trend</p>
                </div>
              </div>

              <!-- Key numbers row -->
              <div class="cs-phase-numbers">
                <div class="cs-phase-number">
                  <span class="cs-phase-number-label">Run rate</span>
                  <span class="cs-phase-number-value">{{ phase.run_rate.toFixed(2) }}</span>
                </div>
                <div class="cs-phase-number">
                  <span class="cs-phase-number-label">Net vs par</span>
                  <span class="cs-phase-number-value">{{ formatSigned(phase.net_swing_vs_par) }}</span>
                </div>
                <div v-if="phase.win_prob_delta != null" class="cs-phase-number">
                  <span class="cs-phase-number-label">Win prob Δ</span>
                  <span class="cs-phase-number-value">{{ formatSignedPercent(phase.win_prob_delta) }}</span>
                </div>
              </div>

              <!-- Key moments (if available) -->
              <div v-if="phase.key_moments?.length" class="cs-phase-moments">
                <h4>Key moments</h4>
                <ul>
                  <li v-for="(moment, idx) in phase.key_moments" :key="idx">{{ moment }}</li>
                </ul>
              </div>

              <!-- Tags (if available) -->
              <div v-if="phase.tags?.length" class="cs-phase-tags">
                <BaseBadge
                  v-for="tag in phase.tags"
                  :key="tag"
                  variant="neutral"
                >
                  {{ tag }}
                </BaseBadge>
              </div>
            </BaseCard>
          </div>
        </BaseCard>

        <BaseCard padding="lg" class="cs-panel">
          <h2 class="cs-panel-title">Key players</h2>
          <p class="cs-panel-subtitle">Highest impact performers in this match.</p>

          <!-- Empty state for key players -->
          <div v-if="keyPlayers.length === 0" class="cs-empty-state">
            <p>No key player impact data yet.</p>
            <p class="cs-empty-hint">Once more matches are analysed, player impact will appear here.</p>
          </div>

          <!-- Players table -->
          <div v-else class="cs-table-scroll">
            <table class="cs-table">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Role</th>
                  <th>Runs</th>
                  <th>SR</th>
                  <th>Wkts</th>
                  <th>Eco</th>
                  <th>Impact</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in keyPlayers" :key="p.id">
                  <td>
                    <button
                      v-if="p.id"
                      class="cs-player-pill"
                      @click.stop="goToPlayerProfile(p.id)"
                    >
                      {{ p.name }}
                    </button>
                    <span v-else class="cs-player-pill cs-player-pill--static">
                      {{ p.name }}
                    </span>
                  </td>
                  <td>{{ p.role }}</td>
                  <td>{{ p.batting?.runs ?? '—' }}</td>
                  <td>{{ p.batting?.strike_rate?.toFixed(1) ?? '—' }}</td>
                  <td>{{ p.bowling?.wickets ?? '—' }}</td>
                  <td>{{ p.bowling?.economy?.toFixed(1) ?? '—' }}</td>
                  <td>
                    <BaseBadge
                      :variant="
                        p.impact === 'high'
                          ? 'success'
                          : p.impact === 'medium'
                            ? 'primary'
                            : 'neutral'
                      "
                      :uppercase="false"
                    >
                      {{ p.impact_label }}
                    </BaseBadge>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </BaseCard>
      </div>

      <!-- Right column: AI summary + dismissal patterns -->
      <div class="cs-main-right">
        <!-- AI Match Summary Panel -->
        <BaseCard padding="lg" class="cs-panel cs-panel--ai">
          <header class="cs-ai-header">
            <div>
              <h2 class="cs-panel-title">AI Match Summary</h2>
              <p class="cs-panel-subtitle">
                Cricksy AI's view of how this match was won and where the key turning points were.
              </p>
              <small v-if="aiSummary?.created_at" class="cs-ai-timestamp">
                Updated {{ new Date(aiSummary.created_at).toLocaleString() }}
              </small>
            </div>
            <BaseBadge variant="neutral" :uppercase="false" class="cs-ai-badge">
              Experimental
            </BaseBadge>
          </header>

          <!-- Loading state -->
          <div v-if="aiSummaryLoading" class="cs-ai-loading">
            <div class="cs-skeleton-line cs-skeleton-line--lg" />
            <div class="cs-skeleton-line cs-skeleton-line--full" />
            <div class="cs-skeleton-line cs-skeleton-line--full" />
            <div class="cs-skeleton-line cs-skeleton-line--md" />
          </div>

          <!-- Error state -->
          <p v-else-if="aiSummaryError" class="cs-ai-error-text">
            {{ aiSummaryError }}
          </p>

          <!-- When no AI summary yet -->
          <div v-else-if="!hasAISummary" class="cs-ai-empty">
            <p>No AI summary available yet.</p>
            <p class="cs-ai-empty-hint">
              Once this match has full ball-by-ball data and processing is completed,
              Cricksy AI will generate a narrative summary here.
            </p>
          </div>

          <!-- When AI summary exists -->
          <div v-else class="cs-ai-body">
            <!-- Overall Summary -->
            <p v-if="aiOverallSummary || aiOverview" class="cs-ai-overall">
              {{ aiOverallSummary || aiOverview }}
            </p>

            <!-- Key Themes -->
            <section v-if="aiKeyThemes.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Key themes</h3>
              <ul class="cs-ai-theme-list">
                <li v-for="(theme, idx) in aiKeyThemes" :key="idx">
                  • {{ theme }}
                </li>
              </ul>
            </section>

            <!-- Decisive Phases -->
            <section v-if="aiDecisivePhases.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Decisive phases</h3>
              <div class="cs-ai-phases-list">
                <div
                  v-for="phase in aiDecisivePhases"
                  :id="`mc-phase-${phase.phase_id}`"
                  :key="phase.phase_id"
                  class="cs-ai-phase-item"
                >
                  <div class="cs-ai-phase-header">
                    <span class="cs-ai-phase-label">{{ phase.label }}</span>
                    <BaseBadge
                      :variant="phase.impact_score > 0 ? 'success' : phase.impact_score < 0 ? 'danger' : 'neutral'"
                      :uppercase="false"
                      class="cs-ai-phase-badge"
                    >
                      {{ phase.impact_score > 0 ? '+' : '' }}{{ phase.impact_score }}
                    </BaseBadge>
                  </div>
                  <span class="cs-ai-phase-overs">
                    Overs {{ phase.over_range[0] }}–{{ phase.over_range[1] }} · Innings {{ phase.innings }}
                  </span>
                  <p class="cs-ai-phase-narrative">{{ phase.narrative }}</p>
                </div>
              </div>
            </section>

            <!-- Player Highlights -->
            <section v-if="aiPlayerHighlightsRich.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Player highlights</h3>
              <ul class="cs-ai-player-list">
                <li
                  v-for="ph in aiPlayerHighlightsRich"
                  :key="ph.player_id ?? ph.player_name"
                  class="cs-ai-player-item"
                >
                  <span class="cs-ai-player-name">{{ ph.player_name }}</span>
                  <span class="cs-ai-player-role">{{ ph.role }} · {{ ph.highlight_type }}</span>
                  <span class="cs-ai-player-summary">{{ ph.summary }}</span>
                </li>
              </ul>
            </section>

            <!-- Momentum Shifts -->
            <section v-if="aiMomentumShifts.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Momentum shifts</h3>
              <ul class="cs-ai-momentum-list">
                <li
                  v-for="shift in aiMomentumShifts"
                  :key="shift.shift_id"
                  class="cs-ai-momentum-item"
                >
                  <span class="cs-ai-momentum-over">Over {{ shift.over }}</span>
                  <span class="cs-ai-momentum-desc">{{ shift.description }}</span>
                  <ImpactBar
                    :value="shift.impact_delta"
                    :min="-20"
                    :max="20"
                    size="sm"
                    class="cs-ai-momentum-bar"
                  />
                </li>
              </ul>
            </section>

            <!-- Team Summaries -->
            <section v-if="aiTeams.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Team summaries</h3>
              <div class="cs-ai-teams-grid">
                <div
                  v-for="team in aiTeams"
                  :key="team.team_id"
                  class="cs-ai-team-card"
                >
                  <div class="cs-ai-team-header">
                    <span class="cs-ai-team-name">{{ team.team_name }}</span>
                    <BaseBadge
                      :variant="team.result === 'won' ? 'success' : team.result === 'lost' ? 'danger' : 'neutral'"
                      :uppercase="false"
                    >
                      {{ team.result.replace('_', ' ') }}
                    </BaseBadge>
                  </div>
                  <p class="cs-ai-team-score">
                    {{ team.total_runs }}/{{ team.wickets_lost }} ({{ team.overs_faced }} ov)
                  </p>
                  <ul v-if="team.key_stats.length" class="cs-ai-team-stats">
                    <li v-for="(stat, idx) in team.key_stats" :key="idx">{{ stat }}</li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- Fallback: Tactical themes from derived data -->
            <section v-if="!aiKeyThemes.length && aiTacticalThemes.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Tactical themes</h3>
              <ul class="cs-ai-theme-list">
                <li v-for="(theme, idx) in aiTacticalThemes" :key="idx">
                  • {{ theme }}
                </li>
              </ul>
            </section>

            <!-- Fallback: Innings summaries from derived data -->
            <section v-if="!aiTeams.length && aiInningsSummaries.length" class="cs-ai-section">
              <h3 class="cs-ai-section-title">Innings breakdown</h3>
              <div
                v-for="innings in aiInningsSummaries"
                :key="innings.innings"
                class="cs-ai-innings-card"
              >
                <div class="cs-ai-innings-meta">
                  <BaseBadge variant="neutral" :uppercase="false">
                    Innings {{ innings.innings }}
                  </BaseBadge>
                  <span class="cs-ai-innings-team">{{ innings.team_name }}</span>
                </div>
                <p class="cs-ai-innings-summary">{{ innings.summary }}</p>
              </div>
            </section>

            <!-- Tags -->
            <section v-if="aiTags.length" class="cs-ai-section cs-ai-tags-section">
              <div class="cs-ai-tag-list">
                <BaseBadge
                  v-for="tag in aiTags"
                  :key="tag"
                  variant="neutral"
                  class="cs-ai-tag"
                >
                  {{ tag.replace(/_/g, ' ') }}
                </BaseBadge>
              </div>
            </section>
          </div>

          <!-- Regenerate action -->
          <div v-if="hasAISummary" class="cs-ai-actions">
            <BaseButton
              variant="ghost"
              size="sm"
              :disabled="aiSummaryLoading"
              @click="regenerateSummary"
            >
              <span v-if="aiSummaryLoading">Refreshing…</span>
              <span v-else>Refresh summary</span>
            </BaseButton>
          </div>
        </BaseCard>

        <BaseCard padding="lg" class="cs-panel">
          <h2 class="cs-panel-title">Dismissal patterns</h2>
          <p class="cs-panel-subtitle">
            Where and how wickets fell. This will later be powered by ball-by-ball tags.
          </p>

          <div class="cs-dismissal-placeholder">
            <p class="cs-empty">
              Visuals coming soon: wagon wheel + pitch map + dismissal clusters.
            </p>
          </div>
        </BaseCard>

        <!-- AI Callouts Panel -->
        <AiCalloutsPanel
          :callouts="matchAiCallouts"
          :loading="matchAiLoading"
          :max-items="5"
          dense
          title="AI Callouts"
          description="Per-match insights Cricksy AI has flagged as important."
          @select="handleCalloutSelect"
        />
      </div>
      </section>
    </template>
  </div>
</template><script setup lang="ts">
import { computed, ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, ImpactBar, MiniSparkline, AiCalloutsPanel } from '@/components'
import type { AiCallout, CalloutSeverity } from '@/components'
import {
  getMatchCaseStudy,
  getMatchAiSummary,
  type MatchCaseStudyResponse,
  type MatchAiSummary,
  type CaseStudyPhase as ApiCaseStudyPhase,
  type CaseStudyKeyPlayer
} from '@/services/api'

// Extend CaseStudyPhase with optional fields (backend may add these later)
type CaseStudyPhase = ApiCaseStudyPhase & {
  innings_index?: number | null
  team?: string | null
  run_rate_series?: number[] | null
  win_prob_delta?: number | null
  key_moments?: string[] | null
  tags?: string[] | null
}

// TODO: Replace this interface with real AI summary type from backend when available.
// This is a richer structure for UX purposes until the backend supports it.
interface MatchAISummary {
  overview: string
  momentum_summary?: string | null
  key_moments?: string[]
  tactical_themes?: string[]
  innings_summaries?: Array<{
    innings: number
    team_name: string
    summary: string
  }>
  player_highlights?: Array<{
    player_id: string
    player_name: string
    team_name: string
    role?: string
    impact_label?: string | null
    summary: string
  }>
}

type ImpactFilter = 'all' | 'positive' | 'negative' | 'neutral'

const route = useRoute()
const router = useRouter()

const matchId = computed(() => route.params.matchId as string)

// Reactive state for API data
const loading = ref(true)
const error = ref<string | null>(null)
const caseStudy = ref<MatchCaseStudyResponse | null>(null)

// AI Summary state (dedicated endpoint)
const aiSummary = ref<MatchAiSummary | null>(null)
const aiSummaryLoading = ref(false)
const aiSummaryError = ref<string | null>(null)

// Derived view-model bindings from caseStudy
const match = computed(() => caseStudy.value?.match ?? null)
const momentumSummary = computed(() => caseStudy.value?.momentum_summary ?? null)
const keyPhase = computed(() => caseStudy.value?.key_phase ?? null)
const phaseBreakdown = computed<CaseStudyPhase[]>(() => {
  return (caseStudy.value?.phases ?? []) as CaseStudyPhase[]
})
const keyPlayers = computed<CaseStudyKeyPlayer[]>(() => caseStudy.value?.key_players ?? [])

// FIX A7: Use real ai_summary from backend, show "unavailable" if missing
const aiSummaryData = computed<MatchAISummary | null>(() => {
  const cs = caseStudy.value
  if (!cs) return null

  // Check if backend provides ai_summary structure
  const backendAiSummary = cs.ai?.match_summary
  
  if (backendAiSummary && typeof backendAiSummary === 'object') {
    // Backend provides full AI summary structure - use it directly
    return backendAiSummary as MatchAISummary
  }
  
  // If only text summary available, wrap it
  if (backendAiSummary && typeof backendAiSummary === 'string') {
    return {
      overview: backendAiSummary,
      key_moments: [],
      tactical_themes: [],
      innings_summaries: [],
      player_highlights: []
    }
  }
  
  // No AI summary available - return null to show "unavailable" UI state
  return null
})

// Computed helpers for AI summary template - prefer dedicated endpoint, fallback to derived
const hasAISummary = computed(() => !!aiSummary.value || !!aiSummaryData.value)
const aiOverallSummary = computed(() => aiSummary.value?.overall_summary ?? '')
const aiOverview = computed(() => aiSummary.value?.overall_summary || aiSummary.value?.headline || aiSummaryData.value?.overview || '')
const aiKeyThemes = computed(() => aiSummary.value?.key_themes ?? [])
const aiTacticalThemes = computed(() => aiSummary.value?.tactical_themes ?? aiSummary.value?.key_themes ?? aiSummaryData.value?.tactical_themes ?? [])
const aiInningsSummaries = computed(() => aiSummaryData.value?.innings_summaries ?? [])
const aiDecisivePhases = computed(() => aiSummary.value?.decisive_phases ?? [])
const aiMomentumShifts = computed(() => aiSummary.value?.momentum_shifts ?? [])
const aiTeams = computed(() => aiSummary.value?.teams ?? [])
const aiPlayerHighlightsRich = computed(() => aiSummary.value?.player_highlights ?? [])
const aiTags = computed(() => aiSummary.value?.tags ?? [])

// Per-match AI callouts derived from case study data
const matchAiLoading = computed(() => loading.value)

const matchAiCallouts = computed<AiCallout[]>(() => {
  const cs = caseStudy.value
  if (!cs) return []

  const callouts: AiCallout[] = []
  const phases = (cs.phases ?? []) as CaseStudyPhase[]
  const players = cs.key_players ?? []

  // Find noteworthy phases by type
  const powerplayPhases = phases.filter((p) => p.id === 'powerplay')
  const deathPhases = phases.filter((p) => p.id === 'death')
  const middlePhases = phases.filter((p) => p.id === 'middle')

  // Powerplay dominance
  const strongPowerplay = powerplayPhases.find((p) => p.net_swing_vs_par >= 10)
  if (strongPowerplay) {
    const teamName = strongPowerplay.team ?? 'The batting side'
    const inningsIdx = strongPowerplay.innings_index ?? 0
    callouts.push({
      id: 'powerplay-domination',
      title: 'Powerplay domination',
      body: `${teamName} finished the powerplay about ${Math.round(strongPowerplay.net_swing_vs_par)} runs ahead of par, setting up the innings.`,
      category: 'Batting',
      severity: 'positive' as CalloutSeverity,
      scope: `Powerplay`,
      targetDomId: `phase-${inningsIdx}-powerplay`,
      targetGroupId: inningsIdx,
    })
  }

  // Powerplay struggle
  const weakPowerplay = powerplayPhases.find((p) => p.net_swing_vs_par <= -10)
  if (weakPowerplay) {
    const teamName = weakPowerplay.team ?? 'The batting side'
    const inningsIdx = weakPowerplay.innings_index ?? 0
    callouts.push({
      id: 'powerplay-struggle',
      title: 'Powerplay struggle',
      body: `${teamName} fell ${Math.abs(Math.round(weakPowerplay.net_swing_vs_par))} runs below par in the powerplay.`,
      category: 'Batting',
      severity: 'warning' as CalloutSeverity,
      scope: `Powerplay`,
      targetDomId: `phase-${inningsIdx}-powerplay`,
      targetGroupId: inningsIdx,
    })
  }

  // Death overs collapse
  const badDeathPhase = deathPhases.find(
    (p) => p.net_swing_vs_par <= -8 || p.wickets >= 3
  )
  if (badDeathPhase) {
    const teamName = badDeathPhase.team ?? 'The batting side'
    const inningsIdx = badDeathPhase.innings_index ?? 0
    callouts.push({
      id: 'death-overs-collapse',
      title: 'Death overs collapse',
      body: `${teamName} struggled at the death, with ${badDeathPhase.wickets} wickets and ${Math.abs(Math.round(badDeathPhase.net_swing_vs_par))} runs below par.`,
      category: 'Batting',
      severity: 'warning' as CalloutSeverity,
      scope: `Death overs`,
      targetDomId: `phase-${inningsIdx}-death`,
      targetGroupId: inningsIdx,
    })
  }

  // Death overs surge
  const goodDeathPhase = deathPhases.find((p) => p.net_swing_vs_par >= 10)
  if (goodDeathPhase) {
    const teamName = goodDeathPhase.team ?? 'The batting side'
    const inningsIdx = goodDeathPhase.innings_index ?? 0
    callouts.push({
      id: 'death-overs-surge',
      title: 'Death overs surge',
      body: `${teamName} accelerated brilliantly at the death, finishing ${Math.round(goodDeathPhase.net_swing_vs_par)} runs ahead of par.`,
      category: 'Batting',
      severity: 'positive' as CalloutSeverity,
      scope: `Death overs`,
      targetDomId: `phase-${inningsIdx}-death`,
      targetGroupId: inningsIdx,
    })
  }

  // Middle overs squeeze
  const middleSqueeze = middlePhases.find((p) => p.net_swing_vs_par <= -8)
  if (middleSqueeze) {
    const inningsIdx = middleSqueeze.innings_index ?? 0
    callouts.push({
      id: 'middle-overs-choke',
      title: 'Middle overs choke',
      body: `Scoring slowed significantly in the middle overs, with the run rate dipping ${Math.abs(Math.round(middleSqueeze.net_swing_vs_par))} below par.`,
      category: 'Bowling',
      severity: 'info' as CalloutSeverity,
      scope: `Middle overs`,
      targetDomId: `phase-${inningsIdx}-middle`,
      targetGroupId: inningsIdx,
    })
  }

  // High-impact player
  const impactPlayer = players.find((p) => p.impact === 'high')
  if (impactPlayer) {
    let contribution = ''
    if (impactPlayer.batting && impactPlayer.batting.runs >= 30) {
      contribution = `scored ${impactPlayer.batting.runs} runs`
    }
    if (impactPlayer.bowling && impactPlayer.bowling.wickets >= 2) {
      contribution += contribution ? ' and ' : ''
      contribution += `took ${impactPlayer.bowling.wickets} wickets`
    }
    if (contribution) {
      callouts.push({
        id: 'impact-player',
        title: 'Match-defining performance',
        body: `${impactPlayer.name} ${contribution}, producing a match-winning contribution.`,
        category: 'Players',
        severity: 'positive' as CalloutSeverity,
        scope: impactPlayer.name,
      })
    }
  }

  // Key tactical theme from AI summary
  const aiData = aiSummaryData.value
  if (aiData?.tactical_themes?.length) {
    callouts.push({
      id: 'tactical-theme',
      title: 'Key tactical theme',
      body: aiData.tactical_themes[0],
      category: 'Tactics',
      severity: 'info' as CalloutSeverity,
      scope: 'Full match',
    })
  }

  // --- Callouts from AI Summary endpoint (decisive phases) ---
  const aiSummaryVal = aiSummary.value
  if (aiSummaryVal?.decisive_phases?.length) {
    // Death overs collapse from AI summary
    const deathCollapsePhase = aiSummaryVal.decisive_phases.find(
      (p) => p.label.toLowerCase().includes('death') && p.impact_score < -20
    )
    if (deathCollapsePhase) {
      callouts.push({
        id: 'ai-death-collapse',
        title: 'Death overs collapse',
        body: deathCollapsePhase.narrative,
        category: 'Batting',
        severity: 'warning' as CalloutSeverity,
        scope: deathCollapsePhase.label,
        targetDomId: `mc-phase-${deathCollapsePhase.phase_id}`,
      })
    }

    // Powerplay dominance from AI summary
    const powerplayDominancePhase = aiSummaryVal.decisive_phases.find(
      (p) => p.label.toLowerCase().includes('powerplay') && p.impact_score > 20
    )
    if (powerplayDominancePhase) {
      callouts.push({
        id: 'ai-powerplay-dominance',
        title: 'Powerplay dominance',
        body: powerplayDominancePhase.narrative,
        category: 'Batting',
        severity: 'positive' as CalloutSeverity,
        scope: powerplayDominancePhase.label,
        targetDomId: `mc-phase-${powerplayDominancePhase.phase_id}`,
      })
    }

    // Middle overs control from AI summary
    const middleControlPhase = aiSummaryVal.decisive_phases.find(
      (p) => p.label.toLowerCase().includes('middle') && Math.abs(p.impact_score) > 15
    )
    if (middleControlPhase) {
      const isPositive = middleControlPhase.impact_score > 0
      callouts.push({
        id: 'ai-middle-control',
        title: isPositive ? 'Middle overs control' : 'Middle overs squeeze',
        body: middleControlPhase.narrative,
        category: isPositive ? 'Batting' : 'Bowling',
        severity: isPositive ? 'positive' as CalloutSeverity : 'warning' as CalloutSeverity,
        scope: middleControlPhase.label,
        targetDomId: `mc-phase-${middleControlPhase.phase_id}`,
      })
    }
  }

  // --- Callouts from momentum shifts ---
  if (aiSummaryVal?.momentum_shifts?.length) {
    // Multiple momentum swings
    if (aiSummaryVal.momentum_shifts.length >= 3) {
      callouts.push({
        id: 'ai-momentum-swings',
        title: 'Multiple momentum swings',
        body: `This match saw ${aiSummaryVal.momentum_shifts.length} key momentum shifts, making it a closely contested affair.`,
        category: 'Match Flow',
        severity: 'info' as CalloutSeverity,
        scope: 'Full match',
      })
    }

    // Biggest momentum shift
    const biggestShift = aiSummaryVal.momentum_shifts.reduce((max, s) =>
      Math.abs(s.impact_delta) > Math.abs(max.impact_delta) ? s : max
    , aiSummaryVal.momentum_shifts[0])
    if (biggestShift && Math.abs(biggestShift.impact_delta) >= 15) {
      callouts.push({
        id: 'ai-big-momentum-shift',
        title: 'Critical turning point',
        body: `Over ${biggestShift.over}: ${biggestShift.description}`,
        category: 'Match Flow',
        severity: biggestShift.impact_delta > 0 ? 'positive' as CalloutSeverity : 'warning' as CalloutSeverity,
        scope: `Over ${biggestShift.over}`,
      })
    }
  }

  return callouts
})

// Filter state for phases
const selectedInningsIndex = ref<number>(0)
const selectedImpactFilter = ref<ImpactFilter>('all')

// Derive innings options from match.innings
const inningsOptions = computed(() => {
  const m = match.value
  if (!m || !m.innings || m.innings.length === 0) {
    return []
  }

  return m.innings.map((inn, index) => {
    const labelParts: string[] = []
    if (inn.team) labelParts.push(inn.team)
    labelParts.push(`Innings ${index + 1}`)
    return {
      index,
      label: labelParts.join(' • ')
    }
  })
})

// Compute filtered phases based on selected innings and impact filter
const filteredPhases = computed<CaseStudyPhase[]>(() => {
  const phases = phaseBreakdown.value
  if (!phases.length) return []

  const inningsIndex = selectedInningsIndex.value

  // Filter by innings if any phase has innings_index
  let result = phases
  const anyHasInningsIndex = phases.some((p) => typeof p.innings_index === 'number')
  if (anyHasInningsIndex) {
    result = result.filter((p) => (p.innings_index ?? 0) === inningsIndex)
  }

  // Filter by impact
  const impactFilter = selectedImpactFilter.value
  if (impactFilter !== 'all') {
    result = result.filter((p) => p.impact === impactFilter)
  }

  return result
})

// Reset selectedInningsIndex if it goes out of range when innings options change
watch(inningsOptions, (newOptions) => {
  if (newOptions.length > 0 && selectedInningsIndex.value >= newOptions.length) {
    selectedInningsIndex.value = 0
  }
})

// Fetch case study data from API
async function loadCaseStudy() {
  if (!matchId.value) return

  loading.value = true
  error.value = null

  try {
    const data = await getMatchCaseStudy(matchId.value)
    caseStudy.value = data
  } catch (e: any) {
    console.error('Failed to load case study:', e)
    error.value = e?.message || 'Could not load match case study.'
  } finally {
    loading.value = false
  }
}

// Fetch AI summary from dedicated endpoint
async function loadAiSummary() {
  if (!matchId.value) return

  aiSummaryLoading.value = true
  aiSummaryError.value = null

  try {
    aiSummary.value = await getMatchAiSummary(matchId.value)
  } catch (e: any) {
    console.error('Failed to load AI summary:', e)
    aiSummaryError.value = 'AI summary not available yet.'
    aiSummary.value = null
  } finally {
    aiSummaryLoading.value = false
  }
}

// Load on mount and when matchId changes
onMounted(() => {
  loadCaseStudy()
  loadAiSummary()
})

watch(matchId, () => {
  loadCaseStudy()
  loadAiSummary()
})

// Actions
function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push({ name: 'AnalystWorkspace' })
  }
}

function goToPlayerProfile(playerId: string) {
  if (!playerId) return
  router.push({
    name: 'PlayerProfile',
    params: { playerId },
  })
}

function regenerateSummary() {
  // Reload the AI summary from the backend
  loadAiSummary()
}

// Helper functions for phase display
function deriveImpactLabel(phase: CaseStudyPhase): string {
  const impact = phase.net_swing_vs_par ?? 0
  if (impact > 1) return 'Above par'
  if (impact < -1) return 'Below par'
  return 'Around par'
}

function formatSigned(value?: number | null): string {
  if (value == null) return '—'
  const rounded = Math.round(value * 10) / 10
  return (rounded > 0 ? '+' : '') + rounded.toString()
}

function formatSignedPercent(value?: number | null): string {
  if (value == null) return '—'
  const pct = Math.round(value * 10) / 10
  return (pct > 0 ? '+' : '') + pct.toString() + '%'
}

function getSparklineVariant(phase: CaseStudyPhase): 'positive' | 'negative' | 'neutral' | 'default' {
  if (phase.impact === 'positive') return 'positive'
  if (phase.impact === 'negative') return 'negative'
  return 'default'
}

/**
 * Generate a stable DOM id for a phase card based on phase id and innings.
 * This allows the AI Callouts panel to scroll to the relevant phase card.
 */
function getPhaseCardDomId(phase: CaseStudyPhase): string {
  const inningsIdx = phase.innings_index ?? 0
  const phaseKey = phase.id.toLowerCase().replace(/\s+/g, '-')
  return `phase-${inningsIdx}-${phaseKey}`
}

/**
 * Handle AI callout selection - scroll to the relevant phase card and flash the ImpactBar.
 * 1) Switch to correct innings tab if targetGroupId is provided
 * 2) Wait for DOM update with nextTick
 * 3) Scroll to the phase card
 * 4) Flash the ImpactBar or highlight the card
 */
function handleCalloutSelect(callout: AiCallout) {
  // Switch innings tab first if targetGroupId (innings index) is provided
  if (typeof callout.targetGroupId === 'number') {
    selectedInningsIndex.value = callout.targetGroupId
  }

  const domId = callout.targetDomId
  if (!domId) return

  // Use nextTick to ensure DOM is updated after switching innings tab
  nextTick(() => {
    const el = document.getElementById(domId)
    if (!el) return

    // Scroll smoothly into view
    el.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })

    // Highlight the whole phase card
    el.classList.add('mc-phase--highlight')

    // Also flash the ImpactBar inside, if present
    const impactBarWrapper = el.querySelector('.impact-bar-wrapper')
    if (impactBarWrapper) {
      impactBarWrapper.classList.add('mc-phase-impact--flash')
      window.setTimeout(() => {
        impactBarWrapper.classList.remove('mc-phase-impact--flash')
      }, 1200)
    }

    // Check if it's an AI summary phase item (different styling)
    if (el.classList.contains('cs-ai-phase-item')) {
      el.classList.add('cs-ai-phase-item--highlight')
      window.setTimeout(() => {
        el.classList.remove('cs-ai-phase-item--highlight')
      }, 1400)
    }

    // Remove highlight after animation
    window.setTimeout(() => {
      el.classList.remove('mc-phase--highlight')
    }, 1400)
  })
}
</script>

<style scoped>
/* =====================================================
   MATCH CASE STUDY VIEW - Using Design System Tokens
   ===================================================== */

.case-study {
  padding: var(--space-4);
  display: grid;
  gap: var(--space-4);
  min-height: 100vh;
  background: var(--color-bg);
}

/* LOADING & ERROR STATES */
.cs-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  font-size: var(--text-base);
  color: var(--color-danger);
}

/* SKELETON STYLES */
.cs-skeleton-card {
  position: relative;
  overflow: hidden;
  background: var(--color-surface);
}

.cs-skeleton-card--inline {
  display: inline-block;
  width: auto;
}

.cs-skeleton-card--badge {
  display: inline-block;
  min-width: 100px;
}

.cs-skeleton-line {
  height: 0.85rem;
  border-radius: var(--radius-full);
  margin-bottom: var(--space-2);
  background: linear-gradient(
    90deg,
    var(--color-surface-hover),
    var(--color-border),
    var(--color-surface-hover)
  );
  background-size: 200% 100%;
  animation: cs-skeleton-shimmer 1.4s infinite linear;
}

.cs-skeleton-line:last-child {
  margin-bottom: 0;
}

.cs-skeleton-line--full { width: 100%; }
.cs-skeleton-line--lg { width: 70%; }
.cs-skeleton-line--md { width: 50%; }
.cs-skeleton-line--sm { width: 35%; }

.cs-skeleton-phase-grid {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.cs-skeleton-phase-card {
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.cs-skeleton-table {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.cs-skeleton-row {
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
}

.cs-skeleton-ai-block {
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-top: var(--space-3);
}

.cs-skeleton-dismissal {
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-top: var(--space-3);
}

@keyframes cs-skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* EMPTY STATES */
.cs-empty-state {
  padding: var(--space-4) var(--space-3);
  text-align: left;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.cs-empty-state p {
  margin: 0;
}

.cs-empty-hint {
  margin-top: var(--space-1) !important;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  opacity: 0.8;
}

.cs-empty-action {
  margin-top: var(--space-3);
}

.cs-panel--ai-empty .cs-empty-state {
  border-style: solid;
  border-color: var(--color-primary-soft);
}

/* HEADER */
.cs-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.cs-header-left {
  display: grid;
  gap: var(--space-3);
}

.cs-title-block {
  display: grid;
  gap: var(--space-1);
}

.cs-title-block h1 {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--font-extrabold);
  color: var(--color-text);
}

.cs-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 500px;
}

.cs-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* SUMMARY STRIP */
.cs-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3);
}

.cs-summary-card {
  display: grid;
  gap: var(--space-1);
}

.cs-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cs-value {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text);
}

.cs-footnote {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* NOT FOUND STATE */
.cs-not-found {
  display: grid;
  place-items: center;
  padding: var(--space-8);
}

.cs-not-found-card {
  text-align: center;
  max-width: 400px;
}

.cs-not-found-card h2 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-not-found-card p {
  margin: 0 0 var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* MAIN LAYOUT */
.cs-main {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: var(--space-4);
  align-items: start;
}

.cs-main-left,
.cs-main-right {
  display: grid;
  gap: var(--space-4);
}

/* PANELS */
.cs-panel {
  display: grid;
  gap: var(--space-4);
}

.cs-panel-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-panel-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* PHASE BREAKDOWN */
.cs-phases-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.cs-phases-filters {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-2);
}

.cs-phases-innings-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  justify-content: flex-end;
}

.cs-phases-impact-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  justify-content: flex-end;
}

.cs-phase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}

.cs-phase-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  transition: box-shadow 160ms ease, transform 160ms ease;
}

.cs-phase-card--highlight {
  box-shadow: 0 0 0 2px var(--color-primary-soft),
              var(--shadow-card-strong, 0 4px 12px rgba(0, 0, 0, 0.15));
  transform: translateY(-2px);
}

/* Phase card highlight from callout selection */
.mc-phase--highlight {
  box-shadow: 0 0 0 2px var(--color-primary-soft);
  transform: translateY(-1px);
  transition: box-shadow 160ms ease-out, transform 160ms ease-out;
}

/* ImpactBar flash from callout selection */
.mc-phase-impact--flash {
  box-shadow: 0 0 0 2px var(--color-primary-soft);
  transform: scale(1.02);
  transition: transform 160ms ease-out, box-shadow 160ms ease-out;
}

.cs-phase-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.cs-phase-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-phase-meta {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-phase-metrics {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.cs-phase-metrics-main {
  flex: 1;
}

/* ImpactBar flash animation for AI callout selection */
.impact-bar-wrapper {
  border-radius: var(--radius-sm);
  transition: box-shadow 160ms ease, transform 160ms ease;
}

.impact-bar-wrapper--flash {
  animation: impactBarFlash 1.4s ease-out;
}

@keyframes impactBarFlash {
  0% {
    box-shadow: 0 0 0 0 var(--color-primary-soft);
    transform: scale(0.98);
  }
  20% {
    box-shadow: 0 0 0 4px var(--color-primary-soft);
    transform: scale(1.02);
  }
  60% {
    box-shadow: 0 0 0 2px var(--color-primary-soft);
    transform: scale(1);
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
    transform: scale(1);
  }
}

.cs-phase-metrics-trend {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-1);
  min-width: 120px;
}

.cs-phase-trend-label {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-phase-numbers {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.cs-phase-number {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-xs);
}

.cs-phase-number-label {
  color: var(--color-text-muted);
}

.cs-phase-number-value {
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-phase-moments {
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.cs-phase-moments h4 {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-phase-moments ul {
  list-style: disc;
  padding-left: var(--space-4);
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-phase-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

/* TABLE */
.cs-table-scroll {
  overflow-x: auto;
}

.cs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.cs-table th,
.cs-table td {
  padding: var(--space-3) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.cs-table th {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-surface-hover);
}

.cs-table tbody tr:hover {
  background: var(--color-surface-hover);
}

.cs-table td {
  color: var(--color-text);
}

/* PLAYER PILLS - Clickable player names */
.cs-player-pill {
  display: inline-flex;
  align-items: center;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-primary);
  background: transparent;
  border: none;
  border-radius: var(--radius-pill);
  padding: calc(var(--space-1) * 0.5) var(--space-2);
  cursor: pointer;
  transition: background-color 120ms ease-out, color 120ms ease-out;
}

.cs-player-pill:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary-strong);
}

.cs-player-pill:focus-visible {
  outline: 2px solid var(--color-primary-soft);
  outline-offset: 2px;
}

.cs-player-pill--static {
  color: var(--color-text);
  background: var(--color-surface-alt);
  cursor: default;
}

.cs-player-pill--static:hover {
  background: var(--color-surface-alt);
  color: var(--color-text);
}

/* AI BLOCK */
.cs-panel--ai {
  background: var(--color-surface);
  border: 1px solid var(--color-primary-soft);
}

.cs-ai-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.cs-ai-timestamp {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-loading {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
}

.cs-ai-error-text {
  font-size: var(--text-sm);
  color: var(--color-error, var(--color-danger, #dc2626));
  padding: var(--space-3);
  background: var(--color-error-soft, rgba(220, 38, 38, 0.1));
  border-radius: var(--radius-md);
  margin: 0;
}

.cs-ai-empty {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  padding: var(--space-4);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.cs-ai-empty p {
  margin: 0;
}

.cs-ai-empty-hint {
  margin-top: var(--space-2) !important;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  opacity: 0.8;
}

.cs-ai-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.2fr);
  gap: var(--space-5);
}

.cs-ai-main,
.cs-ai-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cs-ai-section h3 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cs-ai-headline {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  color: var(--color-text);
}

.cs-ai-narrative {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text);
}

.cs-ai-overview {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text);
}

.cs-ai-momentum {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.cs-ai-bullet-list {
  list-style: disc;
  padding-left: var(--space-5);
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.cs-ai-key-moments li {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.cs-ai-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.cs-ai-tag {
  text-transform: capitalize;
}

.cs-ai-innings-card {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cs-ai-innings-card + .cs-ai-innings-card {
  margin-top: var(--space-2);
}

.cs-ai-innings-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cs-ai-innings-team {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-innings-summary {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
}

.cs-ai-highlight-card {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cs-ai-highlight-card + .cs-ai-highlight-card {
  margin-top: var(--space-2);
}

.cs-ai-highlight-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.cs-ai-highlight-name {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-ai-highlight-meta {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-highlight-summary {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
}

.cs-ai-actions {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.cs-ai-block {
  display: grid;
  gap: var(--space-3);
}

.cs-ai-text {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text);
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.cs-ai-refresh {
  justify-self: start;
}

/* AI SUMMARY BODY */
.cs-ai-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.cs-ai-overall {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
  margin: 0 0 var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.cs-ai-section-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-1);
}

.cs-ai-theme-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.cs-ai-player-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cs-ai-player-item {
  display: flex;
  flex-direction: column;
  gap: calc(var(--space-1) * 0.5);
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
}

.cs-ai-player-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-ai-player-role {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: capitalize;
}

.cs-ai-player-summary {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
}

/* AI Decisive Phases */
.cs-ai-phases-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cs-ai-phase-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
  transition: box-shadow 200ms ease, transform 200ms ease;
}

.cs-ai-phase-item--highlight {
  box-shadow: 0 0 0 2px var(--color-primary-soft),
              0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  animation: cs-ai-phase-pulse 1.8s ease-out;
}

@keyframes cs-ai-phase-pulse {
  0% { box-shadow: 0 0 0 2px var(--color-primary-soft), 0 4px 12px rgba(0, 0, 0, 0.15); }
  50% { box-shadow: 0 0 0 4px var(--color-primary-soft), 0 6px 16px rgba(0, 0, 0, 0.2); }
  100% { box-shadow: none; }
}

.cs-ai-phase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.cs-ai-phase-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-ai-phase-badge {
  font-size: var(--text-xs);
}

.cs-ai-phase-overs {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-phase-narrative {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
}

/* AI Momentum Shifts */
.cs-ai-momentum-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cs-ai-momentum-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
}

.cs-ai-momentum-over {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-ai-momentum-desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-momentum-bar {
  margin-top: var(--space-1);
}

/* AI Team Summaries */
.cs-ai-teams-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-2);
}

.cs-ai-team-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
}

.cs-ai-team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.cs-ai-team-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.cs-ai-team-score {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text);
}

.cs-ai-team-stats {
  list-style: disc;
  padding-left: var(--space-4);
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-tags-section {
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.cs-ai-badge {
  flex-shrink: 0;
}

/* DISMISSAL PLACEHOLDER */
.cs-dismissal-placeholder {
  display: grid;
  place-items: center;
  min-height: 200px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

/* RESPONSIVE */
@media (max-width: 1024px) {
  .cs-main {
    grid-template-columns: 1fr;
  }

  .cs-ai-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .cs-phases-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .cs-phases-filters {
    align-items: flex-start;
    width: 100%;
  }

  .cs-phases-innings-tabs,
  .cs-phases-impact-filters {
    justify-content: flex-start;
  }

  .cs-phase-metrics {
    flex-direction: column;
    align-items: stretch;
  }

  .cs-phase-metrics-trend {
    align-items: flex-start;
  }
}

@media (max-width: 600px) {
  .case-study {
    padding: var(--space-3);
  }

  .cs-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .cs-summary {
    grid-template-columns: 1fr;
  }
}
</style>
