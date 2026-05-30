<template>
  <div class="case-study" data-testid="match-case-study-page">
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
          <p class="cs-footnote">
            {{ momentumSummary.subtitle }}
            <span v-if="momentumSummary.level === 'match'"> • Match-level</span>
            <span v-else> • Innings {{ selectedInningsIndex + 1 }}</span>
          </p>
        </BaseCard>

        <BaseCard v-if="keyPhase" padding="md" class="cs-summary-card">
          <p class="cs-label">{{ isTestMultiDay ? 'Innings focus' : 'Key phase' }}</p>
          <p class="cs-value">{{ keyPhase.title }}</p>
          <p class="cs-footnote">
            {{ keyPhase.detail }}
            <span v-if="keyPhase.level === 'match'"> • Match-level</span>
            <span v-else> • Innings {{ selectedInningsIndex + 1 }}</span>
          </p>
        </BaseCard>

        <BaseCard v-if="selectedInningsAnalysis?.deterministic_summary" padding="md" class="cs-summary-card">
          <p class="cs-label">Deterministic summary</p>
          <p class="cs-value">{{ selectedInningsAnalysis.deterministic_summary }}</p>
          <p class="cs-footnote">Innings {{ selectedInningsIndex + 1 }} story</p>
        </BaseCard>
      </section>

      <section v-if="isTestMultiDay" class="cs-summary">
        <BaseCard padding="md" class="cs-summary-card">
          <p class="cs-label">Analysis mode</p>
          <p class="cs-value">Test / multi-day</p>
          <p class="cs-footnote">
            {{
              caseStudy?.multi_day_summary?.notice
                || 'Test/multi-day match. Analysis uses innings-safe bands; limited-overs phase labels are disabled.'
            }}
          </p>
        </BaseCard>

        <!-- First-innings lead note -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.first_innings_lead_note"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">First-innings lead</p>
          <p class="cs-value">{{ caseStudy.multi_day_summary.first_innings_lead_note }}</p>
        </BaseCard>

        <!-- Lead/deficit swing notes -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.lead_swing_notes?.length"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">Lead / deficit swing</p>
          <ul class="cs-lead-swing-list">
            <li
              v-for="(note, idx) in caseStudy.multi_day_summary.lead_swing_notes"
              :key="`lead-note-${idx}`"
              class="cs-footnote"
            >{{ note }}</li>
          </ul>
        </BaseCard>

        <!-- Fourth-innings chase structured -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.fourth_innings_chase"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">Fourth-innings chase</p>
          <p class="cs-value">
            {{ caseStudy.multi_day_summary.fourth_innings_chase.chasing_team }}
            chasing {{ caseStudy.multi_day_summary.fourth_innings_chase.target }}
          </p>
          <div class="cs-phase-numbers">
            <div class="cs-phase-number">
              <span class="cs-phase-number-label">Runs scored</span>
              <span class="cs-phase-number-value">{{ caseStudy.multi_day_summary.fourth_innings_chase.runs_scored }}</span>
            </div>
            <div class="cs-phase-number">
              <span class="cs-phase-number-label">Wickets in hand</span>
              <span class="cs-phase-number-value">{{ caseStudy.multi_day_summary.fourth_innings_chase.wickets_in_hand }}</span>
            </div>
            <div class="cs-phase-number">
              <span class="cs-phase-number-label">Result</span>
              <span class="cs-phase-number-value">{{ caseStudy.multi_day_summary.fourth_innings_chase.chase_result.replace('_', ' ') }}</span>
            </div>
          </div>
          <p
            v-if="caseStudy.multi_day_summary.fourth_innings_chase.pressure_note"
            class="cs-footnote"
          >{{ caseStudy.multi_day_summary.fourth_innings_chase.pressure_note }}</p>
        </BaseCard>

        <!-- Wicket clusters -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.wicket_clusters?.length"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">Wicket clusters</p>
          <ul class="cs-lead-swing-list">
            <li
              v-for="(cluster, idx) in caseStudy.multi_day_summary.wicket_clusters"
              :key="`cluster-${idx}`"
              class="cs-footnote"
            >
              {{ cluster.label.charAt(0).toUpperCase() + cluster.label.slice(1) }}:
              {{ cluster.wickets }} wickets, overs {{ cluster.overs_start }}–{{ cluster.overs_end }}
              (innings {{ cluster.innings_number }})
            </li>
          </ul>
        </BaseCard>

        <!-- Recovery windows -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.recovery_windows?.length"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">Recovery periods</p>
          <ul class="cs-lead-swing-list">
            <li
              v-for="(rw, idx) in caseStudy.multi_day_summary.recovery_windows"
              :key="`recovery-${idx}`"
              class="cs-footnote"
            >
              Recovery (innings {{ rw.innings_number }}, overs {{ rw.overs_start }}–{{ rw.overs_end }}):
              {{ rw.runs_scored }} runs, {{ rw.wickets_fell }} wicket(s) lost
            </li>
          </ul>
        </BaseCard>

        <!-- Match turning point -->
        <BaseCard
          v-if="caseStudy?.multi_day_summary?.match_turning_point"
          padding="md"
          class="cs-summary-card"
        >
          <p class="cs-label">Match turning point candidate</p>
          <p class="cs-footnote">{{ caseStudy.multi_day_summary.match_turning_point }}</p>
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
              <h2 class="cs-panel-title">{{ isTestMultiDay ? 'Innings breakdown' : 'Phase breakdown' }}</h2>
              <p class="cs-panel-subtitle">
                {{
                  isTestMultiDay
                    ? 'Runs, wickets, overs, and lead/deficit context by innings.'
                    : 'Runs, wickets, and momentum by over segment.'
                }}
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
              <div v-if="!isTestMultiDay" class="cs-phases-impact-filters">
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
          <div v-if="!isTestMultiDay && phaseBreakdown.length === 0" class="cs-empty-state">
            <p>No phase analytics available for this match yet.</p>
            <p class="cs-empty-hint">Try re-running analytics once the scorecard and ball-by-ball data are complete.</p>
          </div>

          <!-- Empty state for filtered results -->
          <div v-else-if="!isTestMultiDay && filteredPhases.length === 0" class="cs-empty-state">
            <p>No phase data for this selection.</p>
            <p class="cs-empty-hint">Try a different innings or impact filter.</p>
          </div>

          <div v-else-if="isTestMultiDay" class="cs-phase-grid">
            <BaseCard
              v-for="innings in testMultiDayInningsCards"
              :key="`test-innings-${innings.inningsNumber}`"
              class="cs-phase-card"
              padding="md"
            >
              <header class="cs-phase-header">
                <div>
                  <h3 class="cs-phase-title">Innings {{ innings.inningsNumber }} · {{ innings.team }}</h3>
                  <p class="cs-phase-meta">{{ innings.runs }}/{{ innings.wickets }} in {{ innings.overs }} overs</p>
                </div>
                <BaseBadge variant="neutral" :uppercase="false">
                  RR {{ innings.runRate }}
                </BaseBadge>
              </header>
              <div class="cs-phase-numbers">
                <div class="cs-phase-number">
                  <span class="cs-phase-number-label">Deliveries</span>
                  <span class="cs-phase-number-value">{{ innings.deliveries }}</span>
                </div>
                <div class="cs-phase-number">
                  <span class="cs-phase-number-label">Lead/deficit</span>
                  <span class="cs-phase-number-value">{{ innings.leadDeficit }}</span>
                </div>
              </div>
            </BaseCard>
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

        <BaseCard v-if="selectedInningsAnalysis?.story_blocks" padding="lg" class="cs-panel">
          <h2 class="cs-panel-title">Innings story</h2>
          <p class="cs-panel-subtitle">
            {{
              isTestMultiDay
                ? `Innings/session-safe narrative for innings ${selectedInningsIndex + 1}.`
                : `Deterministic phase narrative for innings ${selectedInningsIndex + 1}.`
            }}
          </p>
          <ul class="cs-story-list">
            <li>{{ selectedInningsAnalysis.story_blocks.opening_story }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.middle_overs_story }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.death_overs_story }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.scoring_acceleration }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.wickets_by_phase }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.strongest_phase }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.weakest_phase }}</li>
            <li>{{ selectedInningsAnalysis.story_blocks.innings_outcome_contribution }}</li>
          </ul>
        </BaseCard>

        <BaseCard padding="lg" class="cs-panel">
          <h2 class="cs-panel-title">Key players</h2>
          <p class="cs-panel-subtitle">Highest impact performers. {{ keyPlayersScopeLabel }}.</p>

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

        <BaseCard padding="lg" class="cs-panel cs-podcast-panel" id="cs-podcast-prep">
          <div class="cs-podcast-header">
            <div>
              <h2 class="cs-panel-title">Podcast Match Prep Assistant</h2>
              <p class="cs-panel-subtitle">
                AI wording only. Facts come from deterministic match data and require human review before use.
              </p>
            </div>
            <BaseButton
              variant="secondary"
              size="sm"
              data-testid="podcast-generate-btn"
              :disabled="podcastFactBundle.length === 0"
              @click="generatePodcastPrep"
            >
              Generate talking points
            </BaseButton>
          </div>

          <p class="cs-footnote">
            Fact bundle: {{ podcastFactBundle.length }} deterministic fact{{ podcastFactBundle.length === 1 ? '' : 's' }}.
            <span v-if="podcastUsesTemplateFallback">Template fallback active (AI provider unavailable).</span>
            <span v-else>Guarded draft mode active. All items still require review.</span>
          </p>

          <div v-if="podcastFactBundle.length" class="cs-podcast-fact-tags">
            <BaseBadge
              v-for="fact in podcastFactBundle"
              :key="fact.id"
              variant="neutral"
              :uppercase="false"
              class="cs-podcast-fact-tag"
              :title="fact.value"
            >
              {{ fact.source }}
            </BaseBadge>
          </div>
          <p v-else class="cs-empty-hint">No deterministic facts available for podcast prep yet.</p>

          <p v-if="podcastGeneratedAt" class="cs-footnote">Draft generated {{ podcastGeneratedAt }}</p>
          <p v-if="podcastCopyStatus" class="cs-footnote">{{ podcastCopyStatus }}</p>

          <div v-if="podcastCards.length" class="cs-podcast-review-grid">
            <section class="cs-podcast-review-column">
              <h3 class="cs-ai-section-title">Needs review / rejected ({{ unapprovedPodcastCards.length }})</h3>
              <article
                v-for="card in unapprovedPodcastCards"
                :key="`pending-${card.id}`"
                class="cs-podcast-card"
                :data-testid="`podcast-card-${card.id}`"
              >
                <div class="cs-podcast-card-header">
                  <p class="cs-podcast-card-title">{{ card.title }}</p>
                  <BaseBadge
                    :variant="card.status === 'rejected' ? 'danger' : 'warning'"
                    :uppercase="false"
                  >
                    {{ card.status === 'rejected' ? 'Rejected' : 'Needs review' }}
                  </BaseBadge>
                </div>

                <textarea
                  v-if="card.editing"
                  v-model="card.draftText"
                  class="cs-podcast-editor"
                  rows="4"
                />
                <p v-else class="cs-podcast-card-text">{{ card.text }}</p>

                <div class="cs-podcast-meta">
                  <p class="cs-footnote">Sources:</p>
                  <div class="cs-podcast-source-list">
                    <BaseBadge
                      v-for="source in card.sources"
                      :key="`${card.id}-${source}`"
                      variant="neutral"
                      :uppercase="false"
                    >
                      {{ source }}
                    </BaseBadge>
                  </div>
                  <p class="cs-footnote">
                    Confidence:
                    {{ card.confidence != null ? `${Math.round(card.confidence * 100)}%` : 'Unavailable' }}
                  </p>
                  <ul v-if="card.limitations.length" class="cs-podcast-limitations">
                    <li v-for="(limitation, idx) in card.limitations" :key="`${card.id}-limit-${idx}`">
                      {{ limitation }}
                    </li>
                  </ul>
                </div>

                <label class="cs-podcast-segment-label">
                  Segment
                  <select v-model="card.segment" class="cs-podcast-segment-select">
                    <option v-for="segment in podcastSegments" :key="segment.value" :value="segment.value">
                      {{ segment.label }}
                    </option>
                  </select>
                </label>

                <div class="cs-podcast-actions">
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    :data-testid="`podcast-approve-${card.id}`"
                    @click="approvePodcastCard(card.id)"
                  >
                    Approve
                  </BaseButton>
                  <BaseButton
                    v-if="!card.editing"
                    variant="ghost"
                    size="sm"
                    :data-testid="`podcast-edit-${card.id}`"
                    @click="startEditingPodcastCard(card.id)"
                  >
                    Edit
                  </BaseButton>
                  <BaseButton
                    v-else
                    variant="ghost"
                    size="sm"
                    :data-testid="`podcast-save-${card.id}`"
                    @click="saveEditingPodcastCard(card.id)"
                  >
                    Save
                  </BaseButton>
                  <BaseButton
                    v-if="card.editing"
                    variant="ghost"
                    size="sm"
                    @click="cancelEditingPodcastCard(card.id)"
                  >
                    Cancel
                  </BaseButton>
                  <BaseButton
                    variant="ghost"
                    size="sm"
                    :data-testid="`podcast-reject-${card.id}`"
                    @click="rejectPodcastCard(card.id)"
                  >
                    Reject
                  </BaseButton>
                  <BaseButton
                    variant="ghost"
                    size="sm"
                    :data-testid="`podcast-copy-${card.id}`"
                    @click="copyPodcastCard(card)"
                  >
                    Copy
                  </BaseButton>
                </div>
              </article>
            </section>

            <section class="cs-podcast-review-column">
              <h3 class="cs-ai-section-title">Approved ({{ approvedPodcastCards.length }})</h3>
              <article
                v-for="card in approvedPodcastCards"
                :key="`approved-${card.id}`"
                class="cs-podcast-card cs-podcast-card--approved"
              >
                <div class="cs-podcast-card-header">
                  <p class="cs-podcast-card-title">{{ card.title }}</p>
                  <BaseBadge variant="success" :uppercase="false">Approved</BaseBadge>
                </div>
                <p class="cs-podcast-card-text">{{ card.text }}</p>
                <label class="cs-podcast-segment-label">
                  Segment
                  <select v-model="card.segment" class="cs-podcast-segment-select">
                    <option v-for="segment in podcastSegments" :key="segment.value" :value="segment.value">
                      {{ segment.label }}
                    </option>
                  </select>
                </label>
                <div class="cs-podcast-actions">
                  <BaseButton variant="ghost" size="sm" @click="startEditingPodcastCard(card.id)">Edit</BaseButton>
                  <BaseButton variant="ghost" size="sm" @click="rejectPodcastCard(card.id)">Reject</BaseButton>
                  <BaseButton variant="ghost" size="sm" @click="copyPodcastCard(card)">Copy</BaseButton>
                </div>
              </article>
            </section>
          </div>

          <section v-if="podcastCards.length" class="cs-podcast-export">
            <h3 class="cs-ai-section-title">Segment builder & rundown export</h3>
            <label class="cs-podcast-export-toggle">
              <input v-model="includeUnreviewedPodcastCards" type="checkbox">
              Include needs-review drafts in export/copy
            </label>
            <div class="cs-podcast-actions">
              <BaseButton
                variant="secondary"
                size="sm"
                data-testid="podcast-copy-markdown"
                :disabled="!canExportPodcastRundown"
                @click="copyPodcastRundown('markdown')"
              >
                Copy Markdown rundown
              </BaseButton>
              <BaseButton
                variant="secondary"
                size="sm"
                data-testid="podcast-copy-text"
                :disabled="!canExportPodcastRundown"
                @click="copyPodcastRundown('text')"
              >
                Copy plain text rundown
              </BaseButton>
              <BaseButton
                variant="ghost"
                size="sm"
                :disabled="!canExportPodcastRundown"
                @click="downloadPodcastRundown('markdown')"
              >
                Export markdown
              </BaseButton>
              <BaseButton
                variant="ghost"
                size="sm"
                :disabled="!canExportPodcastRundown"
                @click="downloadPodcastRundown('text')"
              >
                Export text
              </BaseButton>
            </div>
            <div class="cs-podcast-rundown-preview">
              <article v-for="segment in podcastRundownSegments" :key="segment.value" class="cs-podcast-rundown-segment">
                <h4>{{ segment.label }}</h4>
                <ul v-if="segment.items.length">
                  <li v-for="entry in segment.items" :key="`${segment.value}-${entry.id}`">
                    <strong>{{ entry.title }}:</strong> {{ entry.text }}
                  </li>
                </ul>
                <p v-else class="cs-empty-hint">No selected items.</p>
              </article>
            </div>
          </section>
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
              <small v-else-if="aiSummaryStatusLabel" class="cs-ai-timestamp">
                {{ aiSummaryStatusLabel }}
              </small>
            </div>
              <BaseBadge variant="neutral" :uppercase="false" class="cs-ai-badge">
                Experimental
              </BaseBadge>
            </header>
            <div class="cs-ai-advisory">
              <p class="cs-ai-advisory-label">AI Advisory · {{ aiAdvisoryConfidenceLabel }}</p>
              <p class="cs-ai-advisory-note">
                This insight is advisory and does not change official scoring or match records.
              </p>
              <MatchInsightEvidence
                v-if="aiSummary"
                class="cs-ai-evidence"
                :source-refs="aiSourceRefs"
                :limitations="aiLimitations"
                :grounding-summary="aiGroundingSummary"
                :confidence-score="aiSummary.ai_metadata?.confidence_score ?? null"
                :decisive-phases="aiSummary.decisive_phases"
                :momentum-shifts="aiSummary.momentum_shifts"
                :teams="aiSummary.teams"
              />
            </div>

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

          <div v-else-if="aiSummaryFallback" class="cs-ai-empty">
            <p>AI insight unavailable. Showing deterministic match summary.</p>
            <p class="cs-ai-overall">{{ aiSummaryFallback.summary }}</p>
            <ul v-if="aiSummaryFallback.bullets.length" class="cs-ai-theme-list">
              <li v-for="(item, idx) in aiSummaryFallback.bullets" :key="`fallback-${idx}`">• {{ item }}</li>
            </ul>
          </div>

          <div v-else-if="aiSummaryInsufficientData" class="cs-ai-empty">
            <p>Insufficient match data for AI or deterministic summary.</p>
          </div>

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
            <AiInsightReviewCard
              v-if="aiSummary"
              class="cs-ai-review-card"
              insight-type="summary"
              :insight-id="matchId"
              title="AI Insight Review"
              :explanation="aiOverallSummary || aiOverview"
              :confidence="aiSummary.ai_metadata?.confidence_score ?? null"
              :limitations="aiLimitations"
              :source-refs="aiSourceRefs"
              :can-review="canReviewAiInsights"
            />

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
          <div v-if="caseStudy" class="cs-ai-actions">
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
            Deterministic wicket analysis for the selected innings.
          </p>
          <div v-if="!selectedDismissalPatterns" class="cs-empty-state">
            <p>No dismissal data available.</p>
          </div>
          <div v-else class="cs-dismissal-panel">
            <p class="cs-footnote">{{ selectedDismissalPatterns.summary }}</p>
            <p v-if="selectedDismissalPatterns.fallback_reason" class="cs-footnote">
              {{ selectedDismissalPatterns.fallback_reason }}
            </p>
            <p v-if="selectedDismissalPatterns.wicket_cluster_callout" class="cs-footnote">
              {{ selectedDismissalPatterns.wicket_cluster_callout }}
            </p>

            <div class="cs-dismissal-grid">
              <div>
                <h4>Wickets by phase</h4>
                <ul>
                  <li
                    v-for="row in selectedDismissalPatterns.wickets_by_phase ?? []"
                    :key="`phase-${row.phase_id}`"
                  >
                    {{ row.phase_id }}: {{ row.wickets }}
                  </li>
                </ul>
              </div>
              <div>
                <h4>Wickets by over band</h4>
                <ul>
                  <li
                    v-for="row in selectedDismissalPatterns.wickets_by_over_band ?? []"
                    :key="`band-${row.band}`"
                  >
                    {{ row.band }}: {{ row.wickets }}
                  </li>
                </ul>
              </div>
              <div>
                <h4>Dismissal types</h4>
                <ul>
                  <li
                    v-for="row in selectedDismissalPatterns.dismissal_types ?? []"
                    :key="`type-${row.type}`"
                  >
                    {{ row.type }}: {{ row.wickets }}
                  </li>
                </ul>
              </div>
              <div>
                <h4>Wicket timeline</h4>
                <ul>
                  <li
                    v-for="event in selectedDismissalPatterns.wicket_timeline ?? []"
                    :key="`wkt-${event.wicket_number}-${event.over}`"
                  >
                    W{{ event.wicket_number }} · Ov {{ event.over }} · {{ event.dismissal_type || 'Unknown' }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </BaseCard>

        <!-- AI Callouts Panel -->
        <AiCalloutsPanel
          :callouts="matchAiCallouts"
          :loading="matchAiLoading"
          :max-items="5"
          dense
          title="Analyst callouts"
          description="Deterministic innings and match-level callouts with evidence."
          @select="handleCalloutSelect"
        />
      </div>
      </section>
    </template>
  </div>
</template><script setup lang="ts">
import { computed, ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, ImpactBar, MiniSparkline, AiCalloutsPanel, AiInsightReviewCard, MatchInsightEvidence } from '@/components'
import type { AiCallout, CalloutSeverity } from '@/components'
import { readAiInsightCache, writeAiInsightCache } from '@/services/aiInsightCache'
import { useAuthStore } from '@/stores/authStore'
import {
  getMatchCaseStudy,
  getMatchAiSummary,
  type MatchCaseStudyResponse,
  type MatchAiSummary,
  type CaseStudyPhase as ApiCaseStudyPhase,
  type CaseStudyKeyPlayer,
  type CaseStudyInningsAnalysis,
  type CaseStudyDismissalPatterns,
  type CaseStudyAnalystCallout,
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
type PodcastReviewStatus = 'needs_review' | 'approved' | 'rejected'
type PodcastSegment =
  | 'intro'
  | 'match_setup'
  | 'innings_1'
  | 'innings_2'
  | 'innings_3'
  | 'innings_4'
  | 'tactical_discussion'
  | 'player_focus'
  | 'closing_question'

interface PodcastFactItem {
  id: string
  source: string
  value: string
}

interface PodcastTalkingPointCard {
  id: string
  title: string
  text: string
  status: PodcastReviewStatus
  sources: string[]
  segment: PodcastSegment
  confidence: number | null
  limitations: string[]
  editing: boolean
  draftText: string
}

const podcastSegments: Array<{ value: PodcastSegment; label: string }> = [
  { value: 'intro', label: 'Intro' },
  { value: 'match_setup', label: 'Match setup' },
  { value: 'innings_1', label: 'Innings 1' },
  { value: 'innings_2', label: 'Innings 2' },
  { value: 'innings_3', label: 'Innings 3' },
  { value: 'innings_4', label: 'Innings 4' },
  { value: 'tactical_discussion', label: 'Tactical discussion' },
  { value: 'player_focus', label: 'Player focus' },
  { value: 'closing_question', label: 'Closing question' },
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const matchId = computed(() => route.params.matchId as string)

// Reactive state for API data
const loading = ref(true)
const error = ref<string | null>(null)
const caseStudy = ref<MatchCaseStudyResponse | null>(null)
const selectedInningsIndex = ref<number>(0)
const selectedImpactFilter = ref<ImpactFilter>('all')

// AI Summary state (dedicated endpoint)
const aiSummary = ref<MatchAiSummary | null>(null)
const aiSummaryLoading = ref(false)
const aiSummaryError = ref<string | null>(null)
const aiSummaryFallback = ref<{ summary: string; bullets: string[] } | null>(null)
const aiSummaryInsufficientData = ref(false)
const aiSummaryCacheStatus = ref<'none' | 'live' | 'cached' | 'stale' | 'fallback' | 'insufficient'>('none')

// Derived view-model bindings from caseStudy
const match = computed(() => caseStudy.value?.match ?? null)
const analysisMode = computed(() => caseStudy.value?.analysis_mode ?? 'unknown')
const isTestMultiDay = computed(() => analysisMode.value === 'test_multi_day')
const inningsAnalyses = computed<CaseStudyInningsAnalysis[]>(() => caseStudy.value?.innings_analysis ?? [])
const selectedInningsAnalysis = computed<CaseStudyInningsAnalysis | null>(() => {
  const analyses = inningsAnalyses.value
  if (!analyses.length) return null
  const selected = analyses.find((entry) => entry.innings_index === selectedInningsIndex.value)
  return selected ?? analyses[0]
})
const momentumSummary = computed(() => selectedInningsAnalysis.value?.momentum_summary ?? caseStudy.value?.momentum_summary ?? null)
const keyPhase = computed(() => selectedInningsAnalysis.value?.key_phase ?? caseStudy.value?.key_phase ?? null)
const phaseBreakdown = computed<CaseStudyPhase[]>(() => {
  const inningsPhases = selectedInningsAnalysis.value?.phases ?? []
  if (inningsPhases.length) return inningsPhases as CaseStudyPhase[]
  return (caseStudy.value?.phases ?? []) as CaseStudyPhase[]
})
const keyPlayers = computed<CaseStudyKeyPlayer[]>(() => {
  const inningsPlayers = selectedInningsAnalysis.value?.key_players ?? []
  if (inningsPlayers.length) return inningsPlayers
  return caseStudy.value?.key_players ?? []
})
const keyPlayersScopeLabel = computed(() =>
  selectedInningsAnalysis.value?.key_players_scope === 'match' ? 'Match-level' : 'Innings-level'
)
const selectedDismissalPatterns = computed<CaseStudyDismissalPatterns | null>(() =>
  selectedInningsAnalysis.value?.dismissal_patterns ?? caseStudy.value?.dismissal_patterns ?? null
)
const testMultiDayInningsCards = computed(() =>
  (caseStudy.value?.match?.innings ?? []).map((inn, index) => {
    const summaryRow = caseStudy.value?.multi_day_summary?.innings?.find(
      (entry) => entry.innings_number === index + 1
    )
    const deliveries =
      summaryRow?.deliveries ?? Math.max(0, Math.round(Math.trunc(inn.overs) * 6 + (inn.overs % 1) * 10))
    return {
      inningsNumber: index + 1,
      team: inn.team,
      runs: inn.runs,
      wickets: inn.wickets,
      overs: inn.overs,
      runRate: inn.run_rate.toFixed(2),
      deliveries,
      leadDeficit:
        typeof summaryRow?.lead_deficit_after_innings === 'number'
          ? `${summaryRow.lead_deficit_after_innings >= 0 ? '+' : ''}${summaryRow.lead_deficit_after_innings}`
          : 'N/A',
    }
  })
)
const podcastCards = ref<PodcastTalkingPointCard[]>([])
const podcastGeneratedAt = ref<string | null>(null)
const podcastCopyStatus = ref<string>('')
const includeUnreviewedPodcastCards = ref(false)

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
const aiAdvisoryConfidenceLabel = computed(() => {
  const confidence = aiSummary.value?.ai_metadata?.confidence_score
  if (typeof confidence === 'number') {
    return `Confidence: ${(confidence * 100).toFixed(0)}%`
  }
  return 'Confidence unavailable'
})
const aiLimitations = computed(() => aiSummary.value?.ai_metadata?.limitations ?? [])
const aiSourceRefs = computed(() => aiSummary.value?.ai_metadata?.source_refs ?? [])
const aiGroundingSummary = computed(() => {
  const summary = aiSummary.value?.ai_metadata?.grounding_summary
  return typeof summary === 'string' ? summary.trim() : ''
})
const canReviewAiInsights = computed(() => authStore.canAnalyze)
const aiSummaryStatusLabel = computed(() => {
  if (aiSummaryCacheStatus.value === 'cached') return 'Cached insight'
  if (aiSummaryCacheStatus.value === 'stale') return 'Stale cache'
  if (aiSummaryCacheStatus.value === 'fallback') return 'Deterministic fallback'
  if (aiSummaryCacheStatus.value === 'insufficient') return 'Insufficient data'
  return null
})
const podcastUsesTemplateFallback = computed(() => !aiSummary.value)
const podcastConfidence = computed(() => {
  const confidence = aiSummary.value?.ai_metadata?.confidence_score
  return typeof confidence === 'number' ? confidence : null
})
const podcastLimitations = computed(() => {
  if (aiLimitations.value.length) return aiLimitations.value
  return ['AI wording is advisory only and requires analyst review before use.']
})

function buildPodcastFactBundle(detail: MatchCaseStudyResponse): PodcastFactItem[] {
  const facts: PodcastFactItem[] = []
  const matchData = detail.match
  facts.push({ id: 'match-result', source: 'match.result', value: matchData.result || 'Result unavailable' })

  const contextBits = [
    matchData.teams_label,
    matchData.date ? `Date ${matchData.date}` : null,
    matchData.venue ? `Venue ${matchData.venue}` : null,
    matchData.season ? `Season ${matchData.season}` : null,
    matchData.event_name ? `Competition ${matchData.event_name}` : null,
  ].filter(Boolean)
  if (contextBits.length) {
    facts.push({
      id: 'match-context',
      source: 'match.context',
      value: contextBits.join(' • '),
    })
  }

  const isTestMode = detail.analysis_mode === 'test_multi_day'
  const multiDaySummary = detail.multi_day_summary

  // Test/multi-day specific facts
  if (isTestMode && multiDaySummary) {
    if (multiDaySummary.first_innings_lead_note) {
      facts.push({
        id: 'test-first-innings-lead',
        source: 'multi_day_summary.first_innings_lead',
        value: multiDaySummary.first_innings_lead_note,
      })
    }
    ;(multiDaySummary.lead_swing_notes ?? []).slice(1).forEach((note, idx) => {
      facts.push({
        id: `test-lead-swing-${idx + 2}`,
        source: 'multi_day_summary.lead_swing',
        value: note,
      })
    })
    if (multiDaySummary.fourth_innings_chase) {
      const chase = multiDaySummary.fourth_innings_chase
      facts.push({
        id: 'test-fourth-innings-chase',
        source: 'multi_day_summary.fourth_innings_chase',
        value: `Fourth-innings chase: ${chase.chasing_team} scored ${chase.runs_scored}/${chase.wickets_lost} `
          + `chasing ${chase.target} (${chase.chase_result.replace('_', ' ')}, `
          + `${chase.wickets_in_hand} wicket(s) in hand).`,
      })
    }
    ;(multiDaySummary.wicket_clusters ?? []).forEach((cluster, idx) => {
      facts.push({
        id: `test-wicket-cluster-${idx + 1}`,
        source: 'multi_day_summary.wicket_clusters',
        value: `${cluster.label.charAt(0).toUpperCase() + cluster.label.slice(1)}: `
          + `${cluster.wickets} wickets in overs ${cluster.overs_start}–${cluster.overs_end} `
          + `(innings ${cluster.innings_number}).`,
      })
    })
    ;(multiDaySummary.recovery_windows ?? []).forEach((rw, idx) => {
      facts.push({
        id: `test-recovery-window-${idx + 1}`,
        source: 'multi_day_summary.recovery_windows',
        value: `Recovery period (innings ${rw.innings_number}, overs ${rw.overs_start}–${rw.overs_end}): `
          + `${rw.runs_scored} runs, ${rw.wickets_fell} wicket(s) lost.`,
      })
    })
    if (multiDaySummary.match_turning_point) {
      facts.push({
        id: 'test-turning-point',
        source: 'multi_day_summary.match_turning_point',
        value: multiDaySummary.match_turning_point,
      })
    }
  }

  const tournamentOutcome =
    (detail.match_callouts ?? []).find((callout) => callout.category === 'outcome')?.explanation ??
    (detail.innings_analysis ?? [])
      .flatMap((innings) => innings.callouts ?? [])
      .find((callout) => callout.category === 'outcome')?.explanation
  if (tournamentOutcome) {
    facts.push({
      id: 'tournament-outcome-context',
      source: 'tournament_outcome.champion_context',
      value: tournamentOutcome,
    })
  }

  ;(matchData.innings ?? []).forEach((innings, index) => {
    facts.push({
      id: `innings-summary-${index + 1}`,
      source: `innings_summary.innings_${index + 1}`,
      value: `${innings.team}: ${innings.runs}/${innings.wickets} in ${innings.overs} overs (RR ${innings.run_rate.toFixed(2)})`,
    })
  })

  ;(detail.innings_analysis ?? []).forEach((innings, index) => {
    if (!isTestMode) {
      // For limited-overs: include phase breakdown and vs-par
      ;(innings.phases ?? []).forEach((phase) => {
        facts.push({
          id: `phase-${index + 1}-${phase.id}`,
          source: `phase_breakdown.${phase.id}`,
          value: `Innings ${index + 1} ${phase.label}: ${phase.runs} runs, ${phase.wickets} wickets, ${phase.net_swing_vs_par} vs par.`,
        })
      })
    } else {
      // For Test/multi-day: include band-based phase breakdown without vs-par
      ;(innings.phases ?? []).forEach((phase) => {
        facts.push({
          id: `test-band-${index + 1}-${phase.id}`,
          source: `innings_band.innings_${index + 1}`,
          value: `Innings ${index + 1} ${phase.label}: ${phase.runs} runs, ${phase.wickets} wickets at ${phase.run_rate} RPO.`,
        })
      })
    }

    const blocks = innings.story_blocks
    facts.push({
      id: `innings-opening-${index + 1}`,
      source: 'innings_story.opening',
      value: blocks.opening_story,
    })
    facts.push({
      id: `innings-middle-${index + 1}`,
      source: 'innings_story.middle',
      value: blocks.middle_overs_story,
    })
    facts.push({
      id: `innings-death-${index + 1}`,
      source: 'innings_story.death',
      value: blocks.death_overs_story,
    })
    facts.push({
      id: `dismissal-pattern-${index + 1}`,
      source: 'dismissal_patterns.wicket_cluster',
      value:
        innings.dismissal_patterns.wicket_cluster_callout ||
        innings.dismissal_patterns.summary ||
        `Innings ${index + 1} dismissal patterns unavailable.`,
    })
    ;(innings.callouts ?? []).forEach((callout, calloutIndex) => {
      facts.push({
        id: `callout-${index + 1}-${calloutIndex}`,
        source: `analyst_callouts.${callout.category}`,
        value: callout.explanation,
      })
    })
  })

  ;(detail.key_players ?? []).slice(0, 3).forEach((player, index) => {
    facts.push({
      id: `key-player-${index + 1}`,
      source: 'key_players.impact',
      value: `${player.name} (${player.team}) impact: ${player.impact_label}.`,
    })
  })

  if (detail.momentum_summary?.title) {
    facts.push({
      id: 'analytics-momentum',
      source: 'analytics_insight.momentum',
      value: `${detail.momentum_summary.title}. ${detail.momentum_summary.subtitle}`,
    })
  }
  if (detail.key_phase?.title) {
    facts.push({
      id: 'analytics-key-phase',
      source: 'analytics_insight.key_phase',
      value: `${detail.key_phase.title}: ${detail.key_phase.detail}`,
    })
  }

  return facts
}

const podcastFactBundle = computed<PodcastFactItem[]>(() => {
  if (!caseStudy.value) return []
  return buildPodcastFactBundle(caseStudy.value)
})

function createPodcastCard(
  id: string,
  title: string,
  text: string,
  segment: PodcastSegment,
  sources: string[],
): PodcastTalkingPointCard {
  return {
    id,
    title,
    text,
    status: 'needs_review',
    sources,
    segment,
    confidence: podcastConfidence.value,
    limitations: podcastLimitations.value,
    editing: false,
    draftText: text,
  }
}

/** Returns "1 wicket" or "N wickets" with correct pluralization. */
function pluralizeWickets(n: number): string {
  return n === 1 ? '1 wicket' : `${n} wickets`
}

function extractOppositionTeam(teamsLabel: string | null | undefined, knownTeam: string): string | null {
  if (!teamsLabel || !knownTeam) return null
  const parts = teamsLabel.split(/\s+vs\s+/i).map((team) => team.trim()).filter(Boolean)
  if (parts.length !== 2) return null
  const knownLower = knownTeam.trim().toLowerCase()
  if (parts[0].toLowerCase() === knownLower) return parts[1]
  if (parts[1].toLowerCase() === knownLower) return parts[0]
  return null
}

function extractResultMargin(result: string | null | undefined): string | null {
  if (!result) return null
  const match = result.match(/\bwon by\s+(.+)$/i)
  return match?.[1] ? `by ${match[1].trim()}` : null
}

function formatSafeTestInningsScore(
  runs: number | null | undefined,
  wickets: number | null | undefined,
  options: {
    completed: boolean
    allowCompletedWicketNotation?: boolean
  },
): string {
  const safeRuns = typeof runs === 'number' ? runs : 0
  const safeWickets = typeof wickets === 'number' ? wickets : null
  const allowCompletedWicketNotation = options.allowCompletedWicketNotation ?? false

  if (safeWickets === 10) return `${safeRuns} all out`
  if (safeWickets === null || safeWickets < 0) {
    return options.completed ? `${safeRuns}, based on recorded innings data` : `${safeRuns}`
  }
  if (safeWickets === 0) {
    if (options.completed && !allowCompletedWicketNotation) {
      return `${safeRuns}, based on recorded innings data`
    }
    return `${safeRuns}/0`
  }
  if (safeWickets >= 1 && safeWickets <= 9) {
    if (!options.completed || allowCompletedWicketNotation) {
      return `${safeRuns}/${safeWickets}`
    }
    return `${safeRuns}, based on recorded innings data`
  }
  return `${safeRuns}`
}

/**
 * Generates a presenter-ready player spotlight sentence from batting and/or
 * bowling facts. Combines both when available; mentions only the supported side
 * when only one exists. Falls back to a generic impact phrase.
 */
function buildPlayerSpotlightText(player: CaseStudyKeyPlayer): string {
  const name = player.name
  const team = player.team
  const hasBatting = player.batting != null && player.batting.runs > 0
  const hasBowling = player.bowling != null && player.bowling.wickets > 0
  if (hasBatting && hasBowling) {
    const runsDesc = `${player.batting!.runs} runs off ${player.batting!.balls} balls`
    return (
      `${name} (${team}) made an all-round contribution: ${runsDesc} ` +
      `with the bat and ${pluralizeWickets(player.bowling!.wickets)} with the ball.`
    )
  }
  if (hasBatting) {
    return `${name} (${team}) provided batting control with ${player.batting!.runs} runs off ${player.batting!.balls} balls.`
  }
  if (hasBowling) {
    return `${name} (${team}) added bowling impact with ${pluralizeWickets(player.bowling!.wickets)}.`
  }
  return `${name} (${team}) was a key influence on the match.`
}

function generatePodcastPrep() {
  if (!caseStudy.value) return
  const detail = caseStudy.value
  const innings1 = detail.innings_analysis?.[0]
  const innings2 = detail.innings_analysis?.[1]
  const leadPlayer = detail.key_players?.[0]
  const selectedDismissals =
    innings1?.dismissal_patterns ?? detail.dismissal_patterns ?? null
  const isTestMode = detail.analysis_mode === 'test_multi_day'
  const multiDaySummary = detail.multi_day_summary

  if (isTestMode) {
    // Test/multi-day specific podcast cards
    const chase = multiDaySummary?.fourth_innings_chase
    const clusters = multiDaySummary?.wicket_clusters ?? []
    const recoveries = multiDaySummary?.recovery_windows ?? []
    const leadNote = multiDaySummary?.first_innings_lead_note
    const turningPoint = multiDaySummary?.match_turning_point
    const mdInnings = multiDaySummary?.innings ?? []

    // Build opening hook: venue-aware narrative sentence
    const openingHookText = (() => {
      const result = detail.match.result
      if (chase?.chase_result === 'completed' && detail.match.venue) {
        const opposition = extractOppositionTeam(detail.match.teams_label, chase.chasing_team)
        const margin = extractResultMargin(result)
        if (opposition && margin) {
          return `${chase.chasing_team} completed a controlled fourth-innings chase to beat ${opposition} ${margin} at ${detail.match.venue}.`
        }
        return `${result} at ${detail.match.venue}.`
      }
      if (detail.match.venue) {
        return `${result} at ${detail.match.venue}.`
      }
      return `${detail.match.teams_label}: ${result}.`
    })()

    // Build first innings story from multi_day_summary.innings[0]
    const firstInningsCtx = mdInnings[0]
    const firstInningsText = firstInningsCtx
      ? `${firstInningsCtx.team} posted ${formatSafeTestInningsScore(firstInningsCtx.runs, firstInningsCtx.wickets, { completed: mdInnings.length > 1 })} in the first innings.`
      : innings1?.deterministic_summary || 'First innings story unavailable.'

    // Build reply + lead card: innings[1] data combined with lead note
    const replyCtx = mdInnings[1]
    const firstInningsLeadText = (() => {
      if (replyCtx && leadNote) {
        const score = formatSafeTestInningsScore(replyCtx.runs, replyCtx.wickets, { completed: mdInnings.length > 2 })
        return `${replyCtx.team} replied with ${score}. ${leadNote}`
      }
      if (leadNote) return leadNote
      if (replyCtx) {
        const score = formatSafeTestInningsScore(replyCtx.runs, replyCtx.wickets, { completed: mdInnings.length > 2 })
        return `${replyCtx.team} replied with ${score}.`
      }
      return innings1?.story_blocks?.opening_story || innings1?.deterministic_summary || 'First-innings lead story unavailable.'
    })()

    // Build third innings (target-setting) story from innings[2]
    const thirdInningsCtx = mdInnings[2]
    const thirdInningsText = (() => {
      if (thirdInningsCtx && chase) {
        const score = formatSafeTestInningsScore(thirdInningsCtx.runs, thirdInningsCtx.wickets, { completed: true })
        return (
          `${thirdInningsCtx.team} made ${score} ` +
          `in their second innings, setting ${chase.chasing_team} a target of ${chase.target}.`
        )
      }
      if (thirdInningsCtx) {
        const score = formatSafeTestInningsScore(thirdInningsCtx.runs, thirdInningsCtx.wickets, { completed: mdInnings.length > 3 })
        return `${thirdInningsCtx.team} made ${score} in their second innings.`
      }
      return innings2?.deterministic_summary || 'Third innings story unavailable.'
    })()

    // Build fourth innings chase: concise, no duplication, proper pluralization
    const chaseText = (() => {
      if (!chase) return 'No fourth-innings chase context available.'
      if (chase.chase_result === 'completed') {
        return (
          `${chase.chasing_team} completed the chase at ${chase.runs_scored}/${chase.wickets_lost}, ` +
          `with ${pluralizeWickets(chase.wickets_in_hand)} in hand.`
        )
      }
      if (chase.chase_result === 'fell_short') {
        const deficit = chase.target - chase.runs_scored
        return (
          `${chase.chasing_team} fell ${deficit} run${deficit === 1 ? '' : 's'} short of the ` +
          `target of ${chase.target}, finishing at ${chase.runs_scored}/${chase.wickets_lost}.`
        )
      }
      return (
        `${chase.chasing_team} chased ${chase.target}, ` +
        `scoring ${chase.runs_scored}/${chase.wickets_lost} with ${pluralizeWickets(chase.wickets_in_hand)} remaining.`
      )
    })()

    // Build collapse/recovery tactical note with why-it-matters context
    const collapseRecoveryText = (() => {
      if (clusters.length) {
        const c = clusters[0]
        const clusterDesc =
          `A wicket cluster of ${pluralizeWickets(c.wickets)} in overs ${c.overs_start}–${c.overs_end} ` +
          `(innings ${c.innings_number}) was a key pressure point in the match.`
        const recoveryDesc = recoveries.length
          ? ` The batting side recovered with ${recoveries[0].runs_scored} runs ` +
            `in overs ${recoveries[0].overs_start}–${recoveries[0].overs_end}.`
          : ''
        return clusterDesc + recoveryDesc
      }
      return selectedDismissals?.wicket_cluster_callout || 'No collapse/recovery patterns detected in recorded data.'
    })()

    // Build bowling impact note with why-it-matters context
    const bowlingCallout = (detail.innings_analysis ?? [])
      .flatMap((inn) => inn.callouts ?? [])
      .find((c) => c.category === 'bowling')
    const bowlingImpactText = bowlingCallout?.why_it_matters
      || bowlingCallout?.explanation
      || 'Bowling impact data unavailable from deterministic sources.'

    // Build turning point note with context
    const turningPointText = (() => {
      if (leadNote && chase?.chase_result === 'completed') {
        const leadMatch = leadNote.match(/^(.+?) took an? (.+?) first-innings lead\.?$/i)
        if (leadMatch) {
          return `${leadMatch[1]}’s ${leadMatch[2]} first-innings lead gave them control before the fourth-innings chase confirmed the result.`
        }
        return `${leadNote.replace(/\.$/, '')} gave them control before the fourth-innings chase confirmed the result.`
      }
      if (turningPoint) return turningPoint
      return detail.key_phase?.detail || 'Match turning point unavailable.'
    })()

    // Build player spotlight using batting and bowling facts
    const playerSpotlightText = leadPlayer
      ? buildPlayerSpotlightText(leadPlayer)
      : 'Player impact unavailable.'

    // Build closing question: more discussion-ready
    const closingQuestionText = (() => {
      if (leadNote && chase?.chase_result === 'completed') {
        const chasingTeam = chase.chasing_team
        return `Was the first-innings lead the decisive moment, or did ${chasingTeam}'s chase simply confirm control already established?`
      }
      if (leadNote) {
        return `Did the first-innings lead ultimately decide this Test, or did the bowling attack prove equally influential?`
      }
      return `Which aspect of the winning team's performance was most decisive in shaping this Test result?`
    })()

    podcastCards.value = [
      createPodcastCard(
        'opening-hook',
        'Opening hook',
        openingHookText,
        'intro',
        ['match.result', 'match.venue'],
      ),
      createPodcastCard(
        'match-context',
        'Match context',
        [
          detail.match.date ? `Date: ${detail.match.date}` : null,
          detail.match.venue ? `Venue: ${detail.match.venue}` : null,
          detail.match.season ? `Season: ${detail.match.season}` : null,
          detail.match.event_name ? `Competition: ${detail.match.event_name}` : null,
        ]
          .filter(Boolean)
          .join(' • ') || 'Match context unavailable.',
        'match_setup',
        ['match.context'],
      ),
      createPodcastCard(
        'test-first-innings-story',
        'First innings',
        firstInningsText,
        'innings_1',
        ['multi_day_summary.innings', 'innings_summary.innings_1'],
      ),
      createPodcastCard(
        'test-first-innings-lead',
        'First-innings lead story',
        firstInningsLeadText,
        'innings_2',
        ['multi_day_summary.first_innings_lead', 'multi_day_summary.innings'],
      ),
      createPodcastCard(
        'test-third-innings-story',
        'Third innings',
        thirdInningsText,
        'innings_3',
        ['multi_day_summary.innings', 'innings_summary.innings_3'],
      ),
      createPodcastCard(
        'test-fourth-innings-chase',
        'Fourth-innings chase story',
        chaseText,
        'innings_4',
        ['multi_day_summary.fourth_innings_chase'],
      ),
      createPodcastCard(
        'test-collapse-recovery',
        'Collapse / recovery talking point',
        collapseRecoveryText,
        'tactical_discussion',
        ['multi_day_summary.wicket_clusters', 'multi_day_summary.recovery_windows'],
      ),
      createPodcastCard(
        'test-bowling-impact',
        'Bowling impact note',
        bowlingImpactText,
        'tactical_discussion',
        ['analyst_callouts.bowling'],
      ),
      createPodcastCard(
        'test-turning-point',
        'Match turning point candidate',
        turningPointText,
        'tactical_discussion',
        ['multi_day_summary.match_turning_point', 'analytics_insight.key_phase'],
      ),
      createPodcastCard(
        'test-player-impact',
        'Top innings impact player',
        playerSpotlightText,
        'player_focus',
        ['key_players.batting', 'key_players.bowling'],
      ),
      createPodcastCard(
        'closing-question',
        'Closing question',
        closingQuestionText,
        'closing_question',
        ['multi_day_summary.first_innings_lead', 'multi_day_summary.fourth_innings_chase'],
      ),
    ]
  } else {
    podcastCards.value = [
      createPodcastCard(
        'opening-hook',
        'Opening hook',
        `${detail.match.teams_label}: ${detail.match.result}.`,
        'intro',
        ['match.result'],
      ),
      createPodcastCard(
        'match-context',
        'Match context',
        [
          detail.match.date ? `Date: ${detail.match.date}` : null,
          detail.match.venue ? `Venue: ${detail.match.venue}` : null,
          detail.match.season ? `Season: ${detail.match.season}` : null,
          detail.match.event_name ? `Competition: ${detail.match.event_name}` : null,
        ]
          .filter(Boolean)
          .join(' • ') || 'Match context unavailable.',
        'match_setup',
        ['match.context'],
      ),
      createPodcastCard(
        'first-innings-story',
        'First innings story',
        innings1?.story_blocks?.opening_story || innings1?.deterministic_summary || 'First innings story unavailable.',
        'innings_1',
        ['innings_story.opening', 'innings_summary.innings_1'],
      ),
      createPodcastCard(
        'second-innings-story',
        'Second innings story',
        innings2?.story_blocks?.opening_story || innings2?.deterministic_summary || 'Second innings story unavailable.',
        'innings_2',
        ['innings_story.opening', 'innings_summary.innings_2'],
      ),
      createPodcastCard(
        'turning-point',
        'Turning point',
        detail.key_phase?.detail || detail.momentum_summary?.subtitle || 'Turning point unavailable from deterministic data.',
        'tactical_discussion',
        ['analytics_insight.key_phase', 'phase_breakdown.middle'],
      ),
      createPodcastCard(
        'player-spotlight',
        'Player spotlight',
        leadPlayer
          ? `${leadPlayer.name} (${leadPlayer.team}) delivered ${leadPlayer.impact_label.toLowerCase()} impact.`
          : 'Player spotlight unavailable.',
        'player_focus',
        ['key_players.impact'],
      ),
      createPodcastCard(
        'dismissal-pattern',
        'Dismissal pattern',
        selectedDismissals?.wicket_cluster_callout || selectedDismissals?.summary || 'Dismissal pattern unavailable.',
        'tactical_discussion',
        ['dismissal_patterns.wicket_cluster'],
      ),
      createPodcastCard(
        'tactical-lesson',
        'Tactical lesson',
        innings1?.story_blocks?.weakest_phase || detail.match_callouts?.[0]?.why_it_matters || 'Tactical lesson unavailable.',
        'tactical_discussion',
        ['innings_story.middle', 'analyst_callouts.momentum'],
      ),
      createPodcastCard(
        'closing-question',
        'Closing question',
        detail.key_phase?.title
          ? `How should teams adapt when the match swings in phases like ${detail.key_phase.title}?`
          : 'What deterministic trend from this match should teams prepare for next?',
        'closing_question',
        ['analytics_insight.key_phase'],
      ),
    ]
  }
  podcastGeneratedAt.value = new Date().toLocaleString()
  includeUnreviewedPodcastCards.value = false
  podcastCopyStatus.value = ''
}

function updatePodcastCard(
  cardId: string,
  updater: (card: PodcastTalkingPointCard) => void,
) {
  const card = podcastCards.value.find((entry) => entry.id === cardId)
  if (!card) return
  updater(card)
}

function approvePodcastCard(cardId: string) {
  updatePodcastCard(cardId, (card) => {
    card.status = 'approved'
    card.editing = false
  })
}

function rejectPodcastCard(cardId: string) {
  updatePodcastCard(cardId, (card) => {
    card.status = 'rejected'
    card.editing = false
  })
}

function startEditingPodcastCard(cardId: string) {
  updatePodcastCard(cardId, (card) => {
    card.editing = true
    card.draftText = card.text
  })
}

function saveEditingPodcastCard(cardId: string) {
  updatePodcastCard(cardId, (card) => {
    const trimmed = card.draftText.trim()
    if (!trimmed) return
    card.text = trimmed
    card.status = 'needs_review'
    card.editing = false
  })
}

function cancelEditingPodcastCard(cardId: string) {
  updatePodcastCard(cardId, (card) => {
    card.draftText = card.text
    card.editing = false
  })
}

async function copyText(value: string) {
  if (!value.trim()) return
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
    } else {
      throw new Error('Clipboard API unavailable')
    }
    podcastCopyStatus.value = 'Copied to clipboard.'
  } catch {
    podcastCopyStatus.value = 'Clipboard copy failed in this browser.'
  }
}

async function copyPodcastCard(card: PodcastTalkingPointCard) {
  await copyText(card.text)
}

const approvedPodcastCards = computed(() =>
  podcastCards.value.filter((card) => card.status === 'approved'),
)
const unapprovedPodcastCards = computed(() =>
  podcastCards.value.filter((card) => card.status !== 'approved'),
)
const exportablePodcastCards = computed(() => {
  if (includeUnreviewedPodcastCards.value) {
    return podcastCards.value.filter((card) => card.status !== 'rejected')
  }
  return approvedPodcastCards.value
})
const canExportPodcastRundown = computed(() => exportablePodcastCards.value.length > 0)

const podcastRundownSegments = computed(() =>
  podcastSegments.map((segment) => ({
    ...segment,
    items: exportablePodcastCards.value.filter((card) => card.segment === segment.value),
  })),
)

function buildPodcastRundownMarkdown() {
  const lines = [
    '# Podcast Match Prep Rundown',
    '',
    `Match: ${match.value?.teams_label ?? 'Unknown match'}`,
    '',
  ]
  for (const segment of podcastRundownSegments.value) {
    if (!segment.items.length) continue
    lines.push(`## ${segment.label}`)
    for (const card of segment.items) {
      lines.push(`- **${card.title}**: ${card.text}`)
    }
    lines.push('')
  }
  return lines.join('\n').trim()
}

function buildPodcastRundownText() {
  const lines = ['Podcast Match Prep Rundown', '']
  for (const segment of podcastRundownSegments.value) {
    if (!segment.items.length) continue
    lines.push(`${segment.label.toUpperCase()}:`)
    for (const card of segment.items) {
      lines.push(`  - ${card.title}: ${card.text}`)
    }
    lines.push('')
  }
  return lines.join('\n').trim()
}

async function copyPodcastRundown(format: 'markdown' | 'text') {
  const output = format === 'markdown' ? buildPodcastRundownMarkdown() : buildPodcastRundownText()
  await copyText(output)
}

function downloadPodcastRundown(format: 'markdown' | 'text') {
  const output = format === 'markdown' ? buildPodcastRundownMarkdown() : buildPodcastRundownText()
  const extension = format === 'markdown' ? 'md' : 'txt'
  const blob = new Blob([output], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `podcast-rundown-${matchId.value}.${extension}`
  link.click()
  URL.revokeObjectURL(url)
}

// Per-match AI callouts derived from case study data
const matchAiLoading = computed(() => loading.value)

const matchAiCallouts = computed<AiCallout[]>(() => {
  const cs = caseStudy.value
  if (!cs) return []
  const inningsCallouts = selectedInningsAnalysis.value?.callouts ?? []
  const matchCallouts = cs.match_callouts ?? []
  const structured = [...inningsCallouts, ...matchCallouts]

  const mapStructuredCallout = (callout: CaseStudyAnalystCallout, idx: number): AiCallout => ({
    id: `${callout.level}-${callout.phase}-${idx}`,
    title: callout.title,
    body: callout.explanation,
    innings: callout.innings ? `Innings ${callout.innings}` : callout.level === 'match' ? 'Match-level' : undefined,
    phase: callout.phase,
    category: callout.category,
    severity: callout.severity as CalloutSeverity,
    sourceMetrics: callout.source_metrics,
    confidence: callout.confidence,
    whyItMatters: callout.why_it_matters,
    scope: callout.level === 'match' ? 'Match-level' : undefined,
  })

  if (structured.length) {
    return structured.map(mapStructuredCallout)
  }
  return []
})

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
const AI_SUMMARY_STALE_AFTER_MS = 5 * 60 * 1000

function buildDeterministicMatchFallback() {
  const matchData = caseStudy.value?.match
  if (!matchData) {
    return null
  }
  const innings = matchData.innings ?? []
  const hasResult = Boolean(matchData.result?.trim())
  if (!hasResult && innings.length === 0) {
    return null
  }
  const inningsSummary = innings
    .map((inn) => `${inn.team}: ${inn.runs}/${inn.wickets} in ${inn.overs} overs`)
    .slice(0, 2)
  const bullets: string[] = []
  if (caseStudy.value?.momentum_summary?.title) {
    bullets.push(caseStudy.value.momentum_summary.title)
  }
  if (caseStudy.value?.key_phase?.title) {
    bullets.push(caseStudy.value.key_phase.title)
  }
  return {
    summary: `${matchData.teams_label}: ${matchData.result || 'Result unavailable'}`,
    bullets: [...inningsSummary, ...bullets].slice(0, 4),
  }
}

async function loadAiSummary(forceRefresh = false) {
  if (!matchId.value) return

  const contextHash = `match:${matchId.value}`
  if (!forceRefresh) {
    const cached = readAiInsightCache<MatchAiSummary>({
      scope: 'match-summary',
      key: matchId.value,
      contextHash,
      staleAfterMs: AI_SUMMARY_STALE_AFTER_MS,
    })
    if (cached.entry) {
      aiSummary.value = cached.entry.value
      aiSummaryError.value = null
      aiSummaryFallback.value = null
      aiSummaryInsufficientData.value = false
      aiSummaryCacheStatus.value = cached.status === 'stale' ? 'stale' : 'cached'
      return
    }
  }

  aiSummaryLoading.value = true
  aiSummaryError.value = null

  try {
    const summary = await getMatchAiSummary(matchId.value)
    aiSummary.value = summary
    aiSummaryFallback.value = null
    aiSummaryInsufficientData.value = false
    aiSummaryCacheStatus.value = 'live'
    writeAiInsightCache({
      scope: 'match-summary',
      key: matchId.value,
      contextHash,
      value: summary,
    })
  } catch (e: any) {
    console.error('Failed to load AI summary:', e)
    aiSummary.value = null
    const fallback = buildDeterministicMatchFallback()
    if (fallback) {
      aiSummaryFallback.value = fallback
      aiSummaryInsufficientData.value = false
      aiSummaryCacheStatus.value = 'fallback'
      aiSummaryError.value = null
    } else {
      aiSummaryFallback.value = null
      aiSummaryInsufficientData.value = true
      aiSummaryCacheStatus.value = 'insufficient'
      aiSummaryError.value = null
    }
  } finally {
    aiSummaryLoading.value = false
  }
}

// Load on mount and when matchId changes
onMounted(async () => {
  await loadCaseStudy()
  await loadAiSummary()
})

watch(matchId, async () => {
  podcastCards.value = []
  podcastGeneratedAt.value = null
  podcastCopyStatus.value = ''
  includeUnreviewedPodcastCards.value = false
  await loadCaseStudy()
  await loadAiSummary()
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
  loadAiSummary(true)
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

.cs-story-list,
.cs-dismissal-grid ul {
  margin: 0;
  padding-left: 1rem;
  display: grid;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.cs-dismissal-panel {
  display: grid;
  gap: var(--space-2);
}

.cs-dismissal-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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

.cs-ai-advisory {
  margin-top: var(--space-2);
}

.cs-ai-advisory-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.cs-ai-advisory-note {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-evidence {
  margin-top: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-hover);
}

.cs-ai-evidence-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cs-ai-evidence-summary {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-evidence-list {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-ai-limitations {
  margin-top: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-warning-soft, #facc15);
  background: var(--color-warning-bg, #fffbeb);
}

.cs-ai-limitations-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.cs-ai-limitations-list {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
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

.cs-podcast-panel {
  border: 1px solid var(--color-border);
}

.cs-podcast-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.cs-podcast-fact-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.cs-podcast-fact-tag {
  font-size: var(--text-xs);
}

.cs-podcast-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.cs-podcast-review-column {
  display: grid;
  gap: var(--space-2);
}

.cs-podcast-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
  background: var(--color-surface-hover);
}

.cs-podcast-card--approved {
  border-color: var(--color-success-soft, #86efac);
}

.cs-podcast-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.cs-podcast-card-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.cs-podcast-card-text {
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

.cs-podcast-meta {
  display: grid;
  gap: var(--space-1);
}

.cs-podcast-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.cs-podcast-limitations {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-podcast-editor {
  width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  padding: var(--space-2);
  font: inherit;
}

.cs-podcast-segment-label {
  display: grid;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-podcast-segment-select {
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  padding: var(--space-1) var(--space-2);
}

.cs-podcast-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.cs-podcast-export {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.cs-podcast-export-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cs-podcast-rundown-preview {
  display: grid;
  gap: var(--space-2);
}

.cs-podcast-rundown-segment {
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
}

.cs-podcast-rundown-segment h4 {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
}

.cs-podcast-rundown-segment ul {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-xs);
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

  .cs-podcast-review-grid {
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
