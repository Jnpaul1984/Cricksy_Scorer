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
              <small v-if="aiSummary?.generated_at" class="cs-ai-timestamp">
                Updated {{ new Date(aiSummary.generated_at).toLocaleString() }}
              </small>
            </div>
            <BaseBadge variant="primary" :uppercase="true">
              Beta
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
            <p>No AI summary is available for this match yet.</p>
            <p class="cs-ai-empty-hint">
              Once this match has full ball-by-ball data and processing is completed,
              Cricksy AI will generate a narrative summary here.
            </p>
          </div>

          <!-- When AI summary exists -->
          <div v-else class="cs-ai-layout">
            <!-- Left column: Headline + Narrative + themes -->
            <div class="cs-ai-main">
              <!-- Headline -->
              <section v-if="aiHeadline" class="cs-ai-section">
                <p class="cs-ai-headline">{{ aiHeadline }}</p>
              </section>

              <!-- Narrative -->
              <section v-if="aiNarrative" class="cs-ai-section">
                <h3>Summary</h3>
                <p class="cs-ai-narrative">{{ aiNarrative }}</p>
              </section>

              <!-- Fallback overview if no headline/narrative -->
              <section v-if="!aiHeadline && !aiNarrative && aiOverview" class="cs-ai-section">
                <h3>Overview</h3>
                <p class="cs-ai-overview">{{ aiOverview }}</p>
                <p v-if="aiMomentumSummary" class="cs-ai-momentum">
                  {{ aiMomentumSummary }}
                </p>
              </section>

              <!-- Tactical themes -->
              <section v-if="aiTacticalThemes.length" class="cs-ai-section">
                <h3>Tactical Themes</h3>
                <ul class="cs-ai-bullet-list">
                  <li v-for="(theme, idx) in aiTacticalThemes" :key="idx">
                    {{ theme }}
                  </li>
                </ul>
              </section>

              <!-- Key moments -->
              <section v-if="aiKeyMoments.length" class="cs-ai-section">
                <h3>Key Moments</h3>
                <ul class="cs-ai-bullet-list cs-ai-key-moments">
                  <li v-for="(moment, idx) in aiKeyMoments" :key="idx">
                    {{ moment }}
                  </li>
                </ul>
              </section>
            </div>

            <!-- Right column: Player highlights + Tags -->
            <aside class="cs-ai-side">
              <!-- Player highlights (now string[]) -->
              <section v-if="aiPlayerHighlights.length" class="cs-ai-section cs-ai-highlights">
                <h3>Player Highlights</h3>
                <ul class="cs-ai-bullet-list">
                  <li v-for="(highlight, idx) in aiPlayerHighlights" :key="idx">
                    {{ highlight }}
                  </li>
                </ul>
              </section>

              <!-- Innings summaries (from derived data) -->
              <section v-if="aiInningsSummaries.length" class="cs-ai-section cs-ai-innings">
                <h3>Innings Breakdown</h3>
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
              <section v-if="aiTags.length" class="cs-ai-section cs-ai-tags">
                <h3>Tags</h3>
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
            </aside>
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
import { computed, ref, onMounted, watch } from 'vue'
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

// TODO: Replace this mock with real ai_summary from backend when available.
// For now, we derive a rich AI summary structure from existing case study data for UX purposes.
const aiSummaryData = computed<MatchAISummary | null>(() => {
  const cs = caseStudy.value
  if (!cs) return null

  // If backend provides ai.match_summary, use it as the overview
  const backendSummary = cs.ai?.match_summary ?? ''

  // Build a rich mock structure from available data
  const m = cs.match
  const phases = (cs.phases ?? []) as CaseStudyPhase[]
  const players = cs.key_players ?? []

  // Generate overview from backend summary or create a placeholder
  const overview = backendSummary
    || `${m?.teams_label ?? 'This match'} was a ${m?.format ?? 'limited-overs'} contest that saw momentum shift across key phases. ${m?.result ?? 'The result was decided by crucial performances in pivotal moments.'}`

  // Derive momentum summary from case study momentum_summary
  const momentumSummary = cs.momentum_summary
    ? `${cs.momentum_summary.title}. ${cs.momentum_summary.subtitle}`
    : null

  // Derive key moments from key phase and high-impact phases
  const keyMoments: string[] = []
  if (cs.key_phase) {
    keyMoments.push(`${cs.key_phase.title}: ${cs.key_phase.detail}`)
  }
  phases
    .filter((p) => p.impact === 'positive' || p.impact === 'negative')
    .slice(0, 3)
    .forEach((p) => {
      const swing = p.net_swing_vs_par >= 0 ? `+${p.net_swing_vs_par}` : `${p.net_swing_vs_par}`
      keyMoments.push(`${p.label}: ${p.runs} runs, ${p.wickets} wickets (${swing} vs par)`)
    })

  // Derive tactical themes from phase impacts
  const tacticalThemes: string[] = []
  const positivePhases = phases.filter((p) => p.impact === 'positive')
  const negativePhases = phases.filter((p) => p.impact === 'negative')
  if (positivePhases.length > 0) {
    tacticalThemes.push(
      `Strong ${positivePhases.map((p) => p.label.toLowerCase()).join(' and ')} phases`
    )
  }
  if (negativePhases.length > 0) {
    tacticalThemes.push(
      `Pressure during ${negativePhases.map((p) => p.label.toLowerCase()).join(' and ')}`
    )
  }
  if (phases.some((p) => p.wickets >= 3)) {
    tacticalThemes.push('Significant wicket clusters in key overs')
  }

  // Derive innings summaries from match innings
  const inningsSummaries: MatchAISummary['innings_summaries'] = []
  if (m?.innings && m.innings.length > 0) {
    m.innings.forEach((inn, idx) => {
      const innPhases = phases.filter((p) => (p.innings_index ?? 0) === idx)
      const totalRuns = innPhases.reduce((sum, p) => sum + p.runs, 0) || inn.runs
      const totalWickets = innPhases.reduce((sum, p) => sum + p.wickets, 0) || inn.wickets
      inningsSummaries.push({
        innings: idx + 1,
        team_name: inn.team ?? `Team ${idx + 1}`,
        summary: `${inn.team ?? 'The batting side'} scored ${totalRuns} runs for ${totalWickets} wickets. ${innPhases.length > 0 ? `Key contributions came during the ${innPhases[0]?.label?.toLowerCase() ?? 'middle'} overs.` : ''}`
      })
    })
  }

  // Derive player highlights from key players
  const playerHighlights: MatchAISummary['player_highlights'] = players
    .filter((p) => p.impact === 'high' || p.impact === 'medium')
    .slice(0, 4)
    .map((p) => {
      let summary = ''
      if (p.batting && p.batting.runs > 0) {
        summary += `Scored ${p.batting.runs} runs at a strike rate of ${p.batting.strike_rate?.toFixed(1) ?? '—'}.`
      }
      if (p.bowling && p.bowling.wickets > 0) {
        summary += ` Took ${p.bowling.wickets} wickets at an economy of ${p.bowling.economy?.toFixed(1) ?? '—'}.`
      }
      if (!summary) {
        summary = `Made a ${p.impact} impact contribution to the match.`
      }
      return {
        player_id: p.id,
        player_name: p.name,
        team_name: p.team,
        role: p.role,
        impact_label: p.impact === 'high' ? 'Match-defining' : p.impact === 'medium' ? 'Key contributor' : null,
        summary: summary.trim()
      }
    })

  return {
    overview,
    momentum_summary: momentumSummary,
    key_moments: keyMoments.length > 0 ? keyMoments : undefined,
    tactical_themes: tacticalThemes.length > 0 ? tacticalThemes : undefined,
    innings_summaries: inningsSummaries.length > 0 ? inningsSummaries : undefined,
    player_highlights: playerHighlights.length > 0 ? playerHighlights : undefined
  }
})

// Computed helpers for AI summary template - prefer dedicated endpoint, fallback to derived
const hasAISummary = computed(() => !!aiSummary.value || !!aiSummaryData.value)
const aiHeadline = computed(() => aiSummary.value?.headline ?? '')
const aiNarrative = computed(() => aiSummary.value?.narrative ?? '')
const aiOverview = computed(() => aiSummary.value?.headline || aiSummaryData.value?.overview || '')
const aiMomentumSummary = computed(() => aiSummaryData.value?.momentum_summary ?? '')
const aiKeyMoments = computed(() => aiSummaryData.value?.key_moments ?? [])
const aiTacticalThemes = computed(() => aiSummary.value?.tactical_themes ?? aiSummaryData.value?.tactical_themes ?? [])
const aiInningsSummaries = computed(() => aiSummaryData.value?.innings_summaries ?? [])
const aiPlayerHighlights = computed<string[]>(() => {
  // Prefer dedicated endpoint's string[] format
  if (aiSummary.value?.player_highlights?.length) {
    return aiSummary.value.player_highlights
  }
  // Fallback to derived format (convert to strings)
  return (aiSummaryData.value?.player_highlights ?? []).map(h =>
    `${h.player_name}: ${h.summary}`
  )
})
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
 */
function handleCalloutSelect(callout: AiCallout) {
  const domId = callout.targetDomId
  if (!domId) return

  // Small delay to ensure any DOM updates complete (e.g., if accordion was collapsed)
  window.setTimeout(() => {
    const el = document.getElementById(domId)
    if (!el) return

    // Scroll smoothly into view
    el.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })

    // Try to flash the ImpactBar inside this phase card
    const impactBarWrapper = el.querySelector('.impact-bar-wrapper')
    if (impactBarWrapper) {
      impactBarWrapper.classList.add('impact-bar-wrapper--flash')
      window.setTimeout(() => {
        impactBarWrapper.classList.remove('impact-bar-wrapper--flash')
      }, 1800)
    } else {
      // Fallback: highlight the whole card
      el.classList.add('cs-phase-card--highlight')
      window.setTimeout(() => {
        el.classList.remove('cs-phase-card--highlight')
      }, 1800)
    }
  }, 80)
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
