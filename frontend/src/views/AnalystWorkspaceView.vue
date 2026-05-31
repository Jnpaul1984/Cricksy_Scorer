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
        <ExportUI :data="filteredMatches" :match-id="exportContextMatchId" />
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
                <p
                  v-if="cleanupMessage"
                  class="aw-inline-status"
                  :class="{ 'aw-inline-status--error': cleanupMessageKind === 'error' }"
                  :role="cleanupMessageKind === 'error' ? 'alert' : 'status'"
                >
                  {{ cleanupMessage }}
                </p>
              </div>

              <!-- Loading state -->
              <div v-if="matchesLoading" class="aw-matches-loading" role="status" aria-live="polite">
                <p>Loading completed matches…</p>
              </div>

              <!-- Error state -->
              <div v-else-if="matchesError" class="aw-matches-error" role="alert">
                <p>Unable to load completed matches right now.</p>
                <p class="aw-inline-error-detail">{{ matchesError }}</p>
                <BaseButton variant="ghost" size="sm" @click="loadMatches">
                  Retry
                </BaseButton>
              </div>

              <!-- Empty state -->
              <div v-else-if="filteredMatches.length === 0" class="aw-matches-empty">
                <p>No completed matches match the current filters.</p>
                <p class="aw-matches-empty-hint">
                  Try adjusting your search or filter criteria, or refresh data.
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
                  :class="{ 'aw-matches-row--selected': selectedMatchId === match.id }"
                  role="button"
                  tabindex="0"
                  :aria-pressed="selectedMatchId === match.id"
                  :aria-label="'Open match intelligence for ' + (match.teams || 'this match')"
                  @click="selectMatch(match.id)"
                  @keydown.enter.prevent="selectMatch(match.id)"
                  @keydown.space.prevent="selectMatch(match.id)"
                >
                  <!-- Main info column -->
                  <div class="aw-matches-col aw-matches-col--main">
                    <div class="aw-match-title">{{ match.teams }}</div>
                    <div class="aw-match-meta">
                      <span>{{ match.format }}</span>
                      <span>• {{ match.date }}</span>
                      <span>• {{ normalizeResultDisplayText(match.result) || match.result }}</span>
                      <span v-if="match.venue">• {{ match.venue }}</span>
                      <BaseBadge v-if="match.isHistorical" variant="neutral" :uppercase="false">
                        Imported
                      </BaseBadge>
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
                    <BaseButton
                      v-if="canCleanupImportedMatch(match)"
                      class="aw-cleanup-imported-btn"
                      variant="ghost"
                      size="sm"
                      :disabled="cleanupPendingMatchId === match.id"
                      @click.stop="cleanupImportedMatch(match)"
                    >
                      {{ cleanupPendingMatchId === match.id ? 'Removing imported match…' : 'Remove imported match' }}
                    </BaseButton>
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

              <!-- Match Intelligence Panel - shown when a match is selected -->
              <div
                v-if="selectedMatchId"
                id="aw-match-detail"
                class="aw-match-detail"
              >
                <div class="aw-detail-header">
                  <div>
                    <h3 class="aw-detail-title">Match Intelligence</h3>
                    <p class="aw-detail-meta">
                      {{ matchDetail?.match?.teams_label ?? '—' }}
                    </p>
                  </div>
                  <div class="aw-detail-actions">
                    <BaseButton
                      variant="primary"
                      size="sm"
                      @click="openFullCaseStudy"
                    >
                      View full case study →
                    </BaseButton>
                    <BaseButton
                      variant="ghost"
                      size="sm"
                      @click="selectedMatchId = null; registryData = null"
                    >
                      Close
                    </BaseButton>
                  </div>
                </div>

                <!-- Loading state -->
                <div v-if="detailLoading" class="aw-detail-loading" role="status" aria-live="polite">
                  <p>Loading Match Intelligence…</p>
                </div>

                <!-- Error state -->
                <div v-else-if="detailError" class="aw-detail-error" role="alert">
                  <p>Unable to load Match Intelligence for this match.</p>
                  <p class="aw-inline-error-detail">{{ detailError }}</p>
                  <BaseButton
                    variant="ghost"
                    size="sm"
                    @click="selectedMatchId && loadMatchDetail(selectedMatchId)"
                  >
                    Retry
                  </BaseButton>
                </div>

                <!-- Detail content -->
                <template v-else-if="matchDetail">
                  <!-- Match header -->
                  <section class="aw-detail-summary">
                    <div class="aw-detail-row">
                      <span class="aw-detail-label">Result</span>
                      <span class="aw-detail-value">{{ normalizeResultDisplayText(matchDetail.match.result) || matchDetail.match.result || '—' }}</span>
                    </div>
                    <div class="aw-detail-row">
                      <span class="aw-detail-label">Format</span>
                      <span class="aw-detail-value">{{ matchDetail.match.format }}</span>
                    </div>
                    <div class="aw-detail-row">
                      <span class="aw-detail-label">Date</span>
                      <span class="aw-detail-value">{{ matchDetail.match.date }}</span>
                    </div>
                    <div v-if="matchDetail.match.venue" class="aw-detail-row">
                      <span class="aw-detail-label">Venue</span>
                      <span class="aw-detail-value">{{ matchDetail.match.venue }}</span>
                    </div>
                  </section>

                  <!-- Innings scorecard -->
                  <section class="aw-detail-innings">
                    <h4 class="aw-detail-section-title">Innings</h4>
                    <div
                      v-if="matchDetail.match.innings.length === 0"
                      class="aw-detail-empty-hint"
                    >
                      Innings data not available yet.
                    </div>
                    <table v-else class="aw-innings-table">
                      <thead>
                        <tr>
                          <th>Team</th>
                          <th>Runs</th>
                          <th>Wkts</th>
                          <th>Overs</th>
                          <th>RR</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="(inns, idx) in matchDetail.match.innings"
                          :key="idx"
                        >
                          <td>{{ inns.team }}</td>
                          <td>{{ inns.runs }}</td>
                          <td>{{ inns.wickets }}</td>
                          <td>{{ inns.overs }}</td>
                          <td>{{ inns.run_rate != null ? inns.run_rate.toFixed(2) : '—' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </section>

                  <!-- Momentum summary -->
                  <section
                    v-if="matchDetail.momentum_summary"
                    class="aw-detail-momentum"
                  >
                    <h4 class="aw-detail-section-title">Momentum verdict</h4>
                    <p class="aw-detail-momentum-title">
                      {{ matchDetail.momentum_summary.title }}
                    </p>
                    <p class="aw-detail-momentum-sub">
                      {{ matchDetail.momentum_summary.subtitle }}
                    </p>
                  </section>

                  <!-- Key phase -->
                  <section
                    v-if="matchDetail.key_phase"
                    class="aw-detail-keyphase"
                  >
                    <h4 class="aw-detail-section-title">
                      {{ matchDetail.analysis_mode === 'test_multi_day' ? 'Innings focus' : 'Key phase' }}
                    </h4>
                    <p class="aw-detail-keyphase-title">
                      {{ matchDetail.key_phase.title }}
                    </p>
                    <p class="aw-detail-keyphase-detail">
                      {{ matchDetail.key_phase.detail }}
                    </p>
                  </section>

                  <!-- Phase breakdown -->
                  <section class="aw-detail-phases">
                    <h4 class="aw-detail-section-title">
                      {{ matchDetail.analysis_mode === 'test_multi_day' ? 'Innings breakdown' : 'Phase breakdown' }}
                    </h4>
                    <p v-if="matchDetail.analysis_mode === 'test_multi_day'" class="aw-detail-empty-hint">
                      {{
                        matchDetail.multi_day_summary?.notice
                          || 'Test/multi-day analysis is currently limited and uses innings/session-safe summaries.'
                      }}
                    </p>
                    <div
                      v-if="matchDetail.analysis_mode === 'test_multi_day'"
                      class="aw-detail-empty-hint"
                    >
                      Phase labels are hidden for Test/multi-day matches to avoid misleading limited-overs framing.
                    </div>
                    <div
                      v-else-if="!matchDetail.phases || matchDetail.phases.length === 0"
                      class="aw-detail-empty-hint"
                    >
                      No phase data available yet.
                    </div>
                    <table v-else class="aw-phases-table">
                      <thead>
                        <tr>
                          <th>Phase</th>
                          <th>Overs</th>
                          <th>Runs</th>
                          <th>Wkts</th>
                          <th>RR</th>
                          <th>vs Par</th>
                          <th>Impact</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="phase in matchDetail.phases"
                          :key="phase.id"
                          :class="`aw-phase-impact--${phase.impact}`"
                        >
                          <td>{{ phase.label }}</td>
                          <td>{{ phase.start_over }}–{{ phase.end_over }}</td>
                          <td>{{ phase.runs }}</td>
                          <td>{{ phase.wickets }}</td>
                          <td>{{ phase.run_rate != null ? phase.run_rate.toFixed(2) : '—' }}</td>
                          <td>{{ phase.net_swing_vs_par >= 0 ? '+' : '' }}{{ phase.net_swing_vs_par }}</td>
                          <td>
                            <span :class="`aw-phase-badge aw-phase-badge--${phase.impact}`">
                              {{ phase.impact_label }}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </section>

                  <!-- Key players -->
                  <section class="aw-detail-keyplayers">
                    <h4 class="aw-detail-section-title">Key players</h4>
                    <div
                      v-if="!matchDetail.key_players || matchDetail.key_players.length === 0"
                      class="aw-detail-empty-hint"
                    >
                      No key player data available yet.
                    </div>
                    <ul v-else class="aw-keyplayers-list">
                      <li
                        v-for="player in matchDetail.key_players"
                        :key="player.id"
                        class="aw-keyplayer-card"
                      >
                        <div class="aw-keyplayer-header">
                          <span class="aw-keyplayer-name">{{ player.name }}</span>
                          <span class="aw-keyplayer-team">{{ player.team }}</span>
                          <span :class="`aw-keyplayer-impact aw-keyplayer-impact--${player.impact}`">
                            {{ player.impact_label }}
                          </span>
                        </div>
                        <div class="aw-keyplayer-stats">
                          <template v-if="player.batting">
                            <span class="aw-keyplayer-stat">
                              {{ player.batting.runs }} runs
                              (SR {{ player.batting.strike_rate != null ? player.batting.strike_rate.toFixed(1) : '—' }})
                            </span>
                          </template>
                          <template v-if="player.bowling">
                            <span class="aw-keyplayer-stat">
                              {{ player.bowling.wickets }}/{{ player.bowling.runs }}
                              (Eco {{ player.bowling.economy != null ? player.bowling.economy.toFixed(2) : '—' }})
                            </span>
                          </template>
                        </div>
                      </li>
                    </ul>
                  </section>

                  <!-- AI Insight Panel -->
                  <section class="aw-detail-ai" aria-label="AI Insight Panel">
                    <h4 class="aw-detail-section-title">AI Insight Panel</h4>
                    <p class="aw-detail-ai-note">
                      Advisory insights for analyst workflow. This does not alter official cricket truth.
                    </p>
                    <p v-if="matchAiStatusLabel" class="aw-detail-ai-note">{{ matchAiStatusLabel }}</p>

                    <div v-if="matchAiLoading" class="aw-detail-loading" role="status" aria-live="polite">
                      <p>Loading AI insights…</p>
                    </div>

                    <div v-else-if="matchAiError" class="aw-detail-error" role="alert">
                      <p>Unable to load AI insights for this match.</p>
                      <p class="aw-inline-error-detail">{{ matchAiError }}</p>
                      <BaseButton
                        variant="ghost"
                        size="sm"
                        @click="selectedMatchId && loadMatchAiSummary(selectedMatchId, true)"
                      >
                        Retry
                      </BaseButton>
                    </div>

                    <div v-else-if="matchAiFallback" class="aw-detail-empty-hint">
                      <p>AI insight unavailable. Showing deterministic match summary.</p>
                      <p class="aw-detail-ai-body">{{ matchAiFallback.summary }}</p>
                      <ul v-if="matchAiFallback.bullets.length" class="aw-detail-ai-list">
                        <li v-for="(item, idx) in matchAiFallback.bullets" :key="`fallback-${idx}`">{{ item }}</li>
                      </ul>
                    </div>

                    <div v-else-if="matchAiInsufficientData" class="aw-detail-empty-hint">
                      Insufficient match data for AI or deterministic summary.
                    </div>

                    <div v-else-if="!matchAiSummary" class="aw-detail-empty-hint">
                      AI insight data is unavailable for this match.
                    </div>

                    <div v-else class="aw-detail-ai-grid">
                      <AiInsightReviewCard
                        class="aw-detail-ai-review"
                        insight-type="summary"
                        :insight-id="selectedMatchId ?? matchAiSummary.match_id"
                        title="AI Insight Review"
                        :explanation="matchAiSummary.overall_summary"
                        :confidence="matchAiSummary.ai_metadata?.confidence_score ?? null"
                        :limitations="aiLimitations"
                        :source-refs="aiSourceRefs"
                        :can-review="canReviewAiInsights"
                      />

                      <section v-if="matchAiSummary.overall_summary" class="aw-detail-ai-block">
                        <h5 class="aw-detail-ai-title">Match Intelligence Summary</h5>
                        <p class="aw-detail-ai-body">{{ matchAiSummary.overall_summary }}</p>
                        <p v-if="aiConfidenceLabel" class="aw-detail-ai-confidence">
                          Confidence: {{ aiConfidenceLabel }} ({{ aiConfidencePct }}%)
                        </p>
                      </section>

                      <section v-if="matchAiSummary.momentum_shifts.length" class="aw-detail-ai-block">
                        <h5 class="aw-detail-ai-title">Momentum / Tactical Notes</h5>
                        <ul class="aw-detail-ai-list">
                          <li v-for="shift in matchAiSummary.momentum_shifts" :key="shift.shift_id">
                            Over {{ shift.over }} (innings {{ shift.innings }}): {{ shift.description }}
                          </li>
                        </ul>
                      </section>

                      <section v-if="matchAiSummary.player_highlights.length" class="aw-detail-ai-block">
                        <h5 class="aw-detail-ai-title">Key Player Insights</h5>
                        <ul class="aw-detail-ai-list">
                          <li v-for="player in matchAiSummary.player_highlights" :key="player.player_id">
                            <strong>{{ player.player_name }}</strong> ({{ player.role }}): {{ player.summary }}
                          </li>
                        </ul>
                      </section>

                      <section v-if="matchAiSummary.decisive_phases.length" class="aw-detail-ai-block">
                        <h5 class="aw-detail-ai-title">Phase-by-Phase Notes</h5>
                        <ul class="aw-detail-ai-list">
                          <li v-for="phase in matchAiSummary.decisive_phases" :key="phase.phase_id">
                            <strong>{{ phase.label }}</strong> (innings {{ phase.innings }}, overs {{ phase.over_range[0] }}-{{ phase.over_range[1] }}): {{ phase.narrative }}
                          </li>
                        </ul>
                      </section>

                      <section class="aw-detail-ai-block">
                        <h5 class="aw-detail-ai-title">Explainability & Citations</h5>
                        <MatchInsightEvidence
                          :source-refs="aiSourceRefs"
                          :limitations="aiLimitations"
                          :grounding-summary="aiGroundingSummary"
                          :confidence-score="matchAiSummary.ai_metadata?.confidence_score ?? null"
                          :decisive-phases="matchAiSummary.decisive_phases"
                          :momentum-shifts="matchAiSummary.momentum_shifts"
                          :teams="matchAiSummary.teams"
                        />
                      </section>

                      <section class="aw-detail-ai-block">
                        <BaseButton
                          variant="ghost"
                          size="sm"
                          :disabled="matchAiLoading"
                          @click="selectedMatchId && loadMatchAiSummary(selectedMatchId, true)"
                        >
                          Refresh insight
                        </BaseButton>
                      </section>
                    </div>
                  </section>

                  <!-- Podcast Prep Package -->
                  <section
                    v-if="podcastPrepPackage"
                    id="aw-podcast-prep"
                    class="aw-podcast-prep"
                  >
                    <div class="aw-podcast-prep-header">
                      <h4 class="aw-detail-section-title">Podcast prep package</h4>
                      <BaseButton
                        variant="ghost"
                        size="sm"
                        class="aw-podcast-copy-btn"
                        :disabled="!canCopyPodcastPrep"
                        :title="canCopyPodcastPrep ? 'Copy package text to clipboard' : 'Copy is unavailable until enough real match data is present'"
                        @click="copyPodcastPrep"
                      >
                        {{
                          podcastCopyStatus === 'copied'
                            ? 'Copied!'
                            : podcastCopyStatus === 'error'
                              ? 'Copy failed — see text below'
                              : 'Copy package text'
                        }}
                      </BaseButton>
                    </div>

                    <div
                      v-if="!podcastPrepPackage.hasEnoughData"
                      class="aw-podcast-insufficient"
                    >
                      Add more completed match data to generate this section.
                    </div>

                    <!-- Episode title -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Episode title</p>
                      <p class="aw-podcast-block-value">{{ podcastPrepPackage.episodeTitle }}</p>
                    </div>

                    <!-- Match context -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Match context</p>
                      <p class="aw-podcast-block-value">
                        {{ podcastPrepPackage.matchContext ?? 'Not available yet' }}
                      </p>
                    </div>

                    <!-- Scoreboard facts -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Scoreboard facts</p>
                      <ul
                        v-if="podcastPrepPackage.scoreboardFacts.length > 0"
                        class="aw-podcast-list"
                      >
                        <li
                          v-for="(fact, i) in podcastPrepPackage.scoreboardFacts"
                          :key="i"
                        >
                          {{ fact }}
                        </li>
                      </ul>
                      <p v-else class="aw-podcast-empty">Not available yet</p>
                    </div>

                    <!-- Talking points -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Talking points</p>
                      <ul class="aw-podcast-talking-points">
                        <li
                          v-for="tp in podcastPrepPackage.talkingPoints"
                          :key="tp.id"
                          class="aw-podcast-tp"
                        >
                          <span class="aw-podcast-tp-label">{{ tp.label }}</span>
                          <span
                            v-if="tp.text"
                            class="aw-podcast-tp-text"
                          >{{ tp.text }}</span>
                          <span
                            v-else
                            class="aw-podcast-tp-empty"
                          >Insufficient data for this talking point</span>
                        </li>
                      </ul>
                    </div>

                    <!-- Coach discussion prompts -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Coach discussion prompts</p>
                      <ul class="aw-podcast-list">
                        <li
                          v-for="(prompt, i) in podcastPrepPackage.coachPrompts"
                          :key="i"
                        >
                          {{ prompt }}
                        </li>
                      </ul>
                    </div>

                    <!-- Suggested visuals -->
                    <div class="aw-podcast-block">
                      <p class="aw-podcast-block-label">Suggested visuals</p>
                      <ul
                        v-if="podcastPrepPackage.suggestedVisuals.length > 0"
                        class="aw-podcast-list"
                      >
                        <li
                          v-for="(visual, i) in podcastPrepPackage.suggestedVisuals"
                          :key="i"
                        >
                          {{ visual }}
                        </li>
                      </ul>
                      <p v-else class="aw-podcast-empty">
                        Add more completed match data to generate this section
                      </p>
                    </div>
                  </section>
                </template>

                <!-- No data state -->
                <div v-else class="aw-detail-empty-hint">
                  No detail available for this match yet.
                </div>

                <!-- Registry & Provenance panel (Phase 5M) — always shown when a match is selected -->
                <section class="aw-detail-registry" aria-label="Registry and Provenance">
                  <h4 class="aw-detail-section-title">Registry &amp; Provenance</h4>

                  <div v-if="registryLoading" class="aw-registry-loading" role="status">
                    <p>Loading registry data…</p>
                  </div>

                  <div v-else-if="registryData" class="aw-registry-grid">
                    <!-- Competition context -->
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Competition</span>
                      <span class="aw-registry-value">{{ registryData.competition ?? 'Unknown' }}</span>
                    </div>
                    <div v-if="registryData.competition_type" class="aw-registry-row">
                      <span class="aw-registry-label">Competition type</span>
                      <span class="aw-registry-value">{{ humanizeRegistryToken(registryData.competition_type) }}</span>
                    </div>
                    <div v-if="registryData.competition_name && registryData.competition_name !== registryData.competition" class="aw-registry-row">
                      <span class="aw-registry-label">Competition name</span>
                      <span class="aw-registry-value">{{ registryData.competition_name }}</span>
                    </div>
                    <div v-if="registryData.match_format" class="aw-registry-row">
                      <span class="aw-registry-label">Match format</span>
                      <span class="aw-registry-value">{{ registryData.match_format }}</span>
                    </div>
                    <div v-if="registryData.tournament_name" class="aw-registry-row">
                      <span class="aw-registry-label">Tournament</span>
                      <span class="aw-registry-value">{{ registryData.tournament_name }}</span>
                    </div>
                    <div v-if="registryData.tournament_round" class="aw-registry-row">
                      <span class="aw-registry-label">Tournament round</span>
                      <span class="aw-registry-value">{{ registryData.tournament_round }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Season</span>
                      <span class="aw-registry-value">{{ registryData.season ?? 'Unknown' }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Venue</span>
                      <span class="aw-registry-value">{{ registryData.venue ?? 'Unknown' }}</span>
                    </div>
                    <div v-if="registryData.venue_context" class="aw-registry-row">
                      <span class="aw-registry-label">Venue context</span>
                      <span class="aw-registry-value">
                        {{
                          [
                            (registryData.venue_context as Record<string, unknown>)['venue_name'] as string | undefined,
                            (registryData.venue_context as Record<string, unknown>)['city'] as string | undefined,
                            (registryData.venue_context as Record<string, unknown>)['country'] as string | undefined,
                          ].filter(Boolean).join(', ') || 'Unknown'
                        }}
                      </span>
                    </div>
                    <div v-if="registryData.match_number != null" class="aw-registry-row">
                      <span class="aw-registry-label">Match no.</span>
                      <span class="aw-registry-value">{{ registryData.match_number }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Player registry</span>
                      <span class="aw-registry-value">
                        {{ registryData.player_count > 0 ? `${registryData.player_count} players found` : 'Not registered yet' }}
                      </span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Roster snapshot</span>
                      <span class="aw-registry-value">{{ registryData.roster_snapshot_available ? 'Available' : 'Not available' }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Innings imported</span>
                      <span class="aw-registry-value">{{ registryData.innings_count }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Deliveries imported</span>
                      <span class="aw-registry-value">{{ registryData.has_deliveries ? 'Yes' : 'No' }}</span>
                    </div>

                    <!-- Import batch / source provenance -->
                    <div class="aw-registry-divider" />
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Import batch ID</span>
                      <span class="aw-registry-value aw-registry-mono">{{ registryData.import_batch_id ?? 'Not available' }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Source file</span>
                      <span class="aw-registry-value">{{ registryData.source_filename ?? 'Unknown' }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Source type</span>
                      <span class="aw-registry-value">{{ registryData.source_format ?? registryData.source_type }}</span>
                    </div>
                    <div v-if="registryData.source_schema" class="aw-registry-row">
                      <span class="aw-registry-label">Source schema</span>
                      <span class="aw-registry-value aw-registry-mono">{{ registryData.source_schema }}</span>
                    </div>
                    <div v-if="registryData.source_schema_version" class="aw-registry-row">
                      <span class="aw-registry-label">Schema version</span>
                      <span class="aw-registry-value aw-registry-mono">{{ registryData.source_schema_version }}</span>
                    </div>
                    <div v-if="registryData.adapter_id" class="aw-registry-row">
                      <span class="aw-registry-label">Adapter</span>
                      <span class="aw-registry-value aw-registry-mono">{{ registryData.adapter_id }}</span>
                    </div>
                    <div v-if="registryData.adapter_version" class="aw-registry-row">
                      <span class="aw-registry-label">Adapter version</span>
                      <span class="aw-registry-value aw-registry-mono">{{ registryData.adapter_version }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Imported at</span>
                      <span class="aw-registry-value">{{ registryData.imported_at ? new Date(registryData.imported_at).toLocaleString() : 'Unknown' }}</span>
                    </div>

                    <!-- Validation / registration / training eligibility -->
                    <div class="aw-registry-divider" />
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Validation status</span>
                      <span
                        class="aw-registry-value aw-registry-status"
                        :class="{
                          'aw-registry-status--ok': registryData.validation_status === 'valid',
                          'aw-registry-status--warn': registryData.validation_status === 'unknown',
                          'aw-registry-status--bad': registryData.validation_status === 'invalid' || registryData.validation_status === 'unsupported',
                          'aw-registry-status--neutral': registryData.validation_status === 'not_applicable',
                        }"
                      >
                        {{ registryData.validation_status === 'valid' ? 'Valid'
                          : registryData.validation_status === 'invalid' ? 'Invalid'
                          : registryData.validation_status === 'unsupported' ? 'Unsupported format'
                          : registryData.validation_status === 'not_applicable' ? 'Not applicable'
                          : 'Unknown' }}
                      </span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Registration status</span>
                      <span
                        class="aw-registry-value aw-registry-status"
                        :class="{
                          'aw-registry-status--ok': registryData.registration_status === 'registered',
                          'aw-registry-status--warn': registryData.registration_status === 'not_registered',
                        }"
                      >
                        {{ registryData.registration_status === 'registered' ? 'Registered' : 'Not registered yet' }}
                      </span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Training eligible</span>
                      <span
                        class="aw-registry-value aw-registry-status"
                        :class="{
                          'aw-registry-status--ok': registryData.training_eligible,
                          'aw-registry-status--warn': !registryData.training_eligible,
                        }"
                      >
                        {{ registryData.training_eligible ? 'Eligible' : 'Not eligible' }}
                      </span>
                    </div>
                    <div v-if="registryData.blocking_reason && !registryData.training_eligible" class="aw-registry-row">
                      <span class="aw-registry-label">Blocking reason</span>
                      <span class="aw-registry-value aw-registry-blocking">{{ registryData.blocking_reason }}</span>
                    </div>
                  </div>

                  <!-- Registry not loaded state -->
                  <div v-else class="aw-registry-empty">
                    Registry data unavailable for this match.
                  </div>
                </section>
              </div>
            </div>

            <!-- Players tab -->
            <div v-else-if="activeTab === 'players'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Players</h3>
                <p class="aw-table-subtitle">
                  Player-level aggregates for the selected scope.
                </p>
              </div>

              <!-- Players scope filters -->
              <div class="aw-player-filters">
                <div class="aw-player-filter-row">
                  <label class="aw-filter-label" for="player-comp-select">Competition</label>
                  <select id="player-comp-select" v-model="playerCompetitionFilter" class="aw-select" aria-label="Filter by competition">
                    <option value="all">All competitions</option>
                    <option v-for="comp in competitionOptions" :key="comp" :value="comp">{{ comp }}</option>
                  </select>
                  <label class="aw-filter-label" for="player-season-select">Season</label>
                  <select id="player-season-select" v-model="playerSeasonFilter" class="aw-select" aria-label="Filter by season">
                    <option value="all">All seasons</option>
                    <option v-for="s in playerSeasonOptions" :key="s" :value="s">{{ s }}</option>
                  </select>
                  <label class="aw-filter-label" for="player-view-toggle">View</label>
                  <div class="aw-chip-row">
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': playerViewMode === 'all-time' }"
                      :aria-pressed="playerViewMode === 'all-time'"
                      @click="playerViewMode = 'all-time'"
                    >All-time</button>
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': playerViewMode === 'season' }"
                      :aria-pressed="playerViewMode === 'season'"
                      @click="playerViewMode = 'season'"
                    >Season scope</button>
                  </div>
                </div>
              </div>

              <!-- Player completeness diagnostics -->
              <div class="aw-diagnostics-row" role="note" aria-label="Data completeness diagnostics">
                <span class="aw-diagnostics-item">
                  <strong>{{ filteredPlayers.length }}</strong> players shown
                </span>
                <span class="aw-diagnostics-sep">·</span>
                <span class="aw-diagnostics-item">
                  Scope:
                  <strong>{{
                    playerViewMode === 'season' && playerSeasonFilter !== 'all'
                      ? playerSeasonFilter
                      : playerCompetitionFilter !== 'all'
                        ? playerCompetitionFilter + ' (all seasons)'
                        : 'All-time'
                  }}</strong>
                </span>
                <span class="aw-diagnostics-sep">·</span>
                <span class="aw-diagnostics-item">
                  Completeness: <strong>{{ playerDataCompleteness }}</strong>
                </span>
                <span v-if="playerDataCompleteness === 'metadata_only'" class="aw-diagnostics-warn">
                  ⚠ Totals reflect metadata-only matches. Import delivery data for full batting/bowling stats.
                </span>
              </div>

              <div class="aw-table-scroll">
                <table class="aw-table">
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Role</th>
                      <th>Matches</th>
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
                      <td>{{ player.matches }}</td>
                      <td>{{ player.innings }}</td>
                      <td>{{ player.runs }}</td>
                      <td>{{ player.strikeRate }}</td>
                      <td>{{ player.wickets }}</td>
                      <td>{{ player.economy }}</td>
                    </tr>
                    <tr v-if="filteredPlayers.length === 0">
                      <td colspan="8" class="aw-empty">
                        No players found for the current filters.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Deliveries tab -->
            <div v-else-if="activeTab === 'deliveries'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Deliveries</h3>
                <p class="aw-table-subtitle">
                  Select a match to view ball-by-ball delivery data.
                </p>
              </div>

              <!-- Deliveries match selector -->
              <div class="aw-match-selector" role="group" aria-label="Select match for delivery data">
                <div class="aw-match-selector-row">
                  <div class="aw-match-selector-group">
                    <label class="aw-filter-label" for="delivery-comp-select">Competition</label>
                    <select
                      id="delivery-comp-select"
                      v-model="deliveryCompetitionFilter"
                      class="aw-select"
                      aria-label="Select competition"
                      @change="deliverySeasonFilter = 'all'; deliveryFilterMatchId = ''"
                    >
                      <option value="all">All competitions</option>
                      <option v-for="comp in competitionOptions" :key="comp" :value="comp">{{ comp }}</option>
                    </select>
                  </div>
                  <div class="aw-match-selector-group">
                    <label class="aw-filter-label" for="delivery-season-select">Season</label>
                    <select
                      id="delivery-season-select"
                      v-model="deliverySeasonFilter"
                      class="aw-select"
                      aria-label="Select season"
                      @change="deliveryFilterMatchId = ''"
                    >
                      <option value="all">All seasons</option>
                      <option v-for="s in deliverySeasonOptions" :key="s" :value="s">{{ s }}</option>
                    </select>
                  </div>
                  <div class="aw-match-selector-group">
                    <label class="aw-filter-label" for="delivery-match-select">Match</label>
                    <select
                      id="delivery-match-select"
                      v-model="deliveryFilterMatchId"
                      class="aw-select aw-select--wide"
                      aria-label="Select match"
                      @change="onDeliveryMatchSelected"
                    >
                      <option value="">— select a match —</option>
                      <option v-for="m in deliveryMatchOptions" :key="m.id" :value="m.id">
                        {{ m.teams }}{{ m.date ? ' · ' + m.date : '' }}{{ m.season ? ' · ' + m.season : '' }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Empty state: no match selected -->
              <div v-if="!deliveryFilterMatchId" class="aw-delivery-empty-state" role="status">
                <p class="aw-delivery-empty-msg">Select a match to view delivery-level data.</p>
                <p class="aw-delivery-empty-hint">
                  Use the dropdowns above to narrow by competition and season, then select a match.
                </p>
              </div>

              <!-- Loading state -->
              <div v-else-if="deliveriesLoading" class="aw-matches-loading" role="status" aria-live="polite">
                <p>Loading deliveries…</p>
              </div>

              <!-- Deliveries table -->
              <div v-else>
                <div class="aw-diagnostics-row" role="note" aria-label="Delivery data completeness">
                  <span class="aw-diagnostics-item">
                    <strong>{{ filteredDeliveries.length }}</strong> deliveries
                  </span>
                  <span class="aw-diagnostics-sep">·</span>
                  <span class="aw-diagnostics-item">
                    Completeness: <strong>{{ deliveryDataCompleteness }}</strong>
                  </span>
                </div>
                <div class="aw-table-scroll">
                  <table class="aw-table">
                    <thead>
                      <tr>
                        <th>Over.Ball</th>
                        <th>Innings</th>
                        <th>Batting team</th>
                        <th>Batter</th>
                        <th>Bowler</th>
                        <th>Runs</th>
                        <th>Extras</th>
                        <th>Wicket</th>
                        <th>Dismissal</th>
                        <th>Phase</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="delivery in filteredDeliveries" :key="delivery.id">
                        <td>{{ delivery.overNumber }}.{{ delivery.ballNumber }}</td>
                        <td>{{ delivery.innings ?? '—' }}</td>
                        <td>{{ delivery.team || '—' }}</td>
                        <td>{{ delivery.batter || '—' }}</td>
                        <td>{{ delivery.bowler || '—' }}</td>
                        <td>{{ delivery.runsOffBat }}</td>
                        <td>{{ delivery.extraRuns }}<span v-if="delivery.extraType"> ({{ delivery.extraType }})</span></td>
                        <td>{{ delivery.wicket ? 'Yes' : 'No' }}</td>
                        <td>{{ delivery.dismissalType || '—' }}</td>
                        <td>{{ delivery.phase || '—' }}</td>
                        <td class="aw-dl-muted">{{ delivery.dataCompleteness || '—' }}</td>
                      </tr>
                      <tr v-if="filteredDeliveries.length === 0">
                        <td colspan="11" class="aw-empty">
                          No delivery rows found for the selected match.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                 </div>
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

            <!-- Data Library Tab -->
            <div v-else-if="activeTab === 'data-library'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Data Library</h3>
                <p class="aw-table-subtitle">
                  Browse available match datasets organised by competition and season.
                  Historical imports are clearly labelled. Select a match to open the case study.
                </p>
              </div>

              <!-- Data Library controls: search + filters + sort -->
              <div class="aw-dl-controls">
                <BaseInput
                  v-model="dlSearch"
                  placeholder="Search by team, competition, venue, season…"
                  aria-label="Search data library"
                  class="aw-dl-search"
                />
                <div class="aw-dl-filter-row">
                  <span class="aw-filter-label">Source</span>
                  <div class="aw-chip-row">
                    <button
                      v-for="opt in [
                        { label: 'All', value: 'all' },
                        { label: 'Imported', value: 'imported' },
                        { label: 'Live', value: 'live' },
                      ]"
                      :key="opt.value"
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlSourceFilter === opt.value }"
                      :aria-pressed="dlSourceFilter === opt.value"
                      @click="dlSourceFilter = (opt.value as 'all' | 'imported' | 'live')"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <span class="aw-filter-label">Format</span>
                  <div class="aw-chip-row">
                    <button
                      v-for="opt in [
                        { label: 'All', value: 'all' },
                        { label: 'T20', value: 't20' },
                        { label: 'ODI', value: 'odi' },
                        { label: 'Custom', value: 'custom' },
                      ]"
                      :key="opt.value"
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlFormatFilter === opt.value }"
                      :aria-pressed="dlFormatFilter === opt.value"
                      @click="dlFormatFilter = (opt.value as 'all' | 't20' | 'odi' | 'custom')"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <span class="aw-filter-label">Sort</span>
                  <div class="aw-chip-row">
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlSortOrder === 'recent' }"
                      :aria-pressed="dlSortOrder === 'recent'"
                      @click="dlSortOrder = 'recent'"
                    >
                      Most recent
                    </button>
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlSortOrder === 'date-asc' }"
                      :aria-pressed="dlSortOrder === 'date-asc'"
                      @click="dlSortOrder = 'date-asc'"
                    >
                      Oldest first
                    </button>
                  </div>
                  <span class="aw-filter-label">View</span>
                  <div class="aw-chip-row">
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlViewMode === 'collections' }"
                      :aria-pressed="dlViewMode === 'collections'"
                      @click="dlViewMode = 'collections'"
                    >Collections</button>
                    <button
                      class="aw-chip"
                      :class="{ 'aw-chip--active': dlViewMode === 'flat' }"
                      :aria-pressed="dlViewMode === 'flat'"
                      @click="dlViewMode = 'flat'"
                    >Flat list</button>
                  </div>
                </div>
              </div>

              <!-- Loading state -->
              <div v-if="matchesLoading" class="aw-matches-loading" role="status" aria-live="polite">
                <p>Loading data library…</p>
              </div>

              <!-- Error state -->
              <div v-else-if="matchesError" class="aw-matches-error" role="alert">
                <p>Unable to load match data right now.</p>
                <p class="aw-inline-error-detail">{{ matchesError }}</p>
                <BaseButton variant="ghost" size="sm" @click="loadMatches">
                  Retry
                </BaseButton>
              </div>

              <!-- Empty state -->
              <div v-else-if="libraryMatches.length === 0" class="aw-matches-empty">
                <p>No analyst-ready match data is available yet.</p>
                <p class="aw-matches-empty-hint">
                  Import historical matches from the Import Data tab, or adjust
                  your search and filter criteria.
                </p>
              </div>

              <!-- Collections view -->
              <div v-else-if="dlViewMode === 'collections'" class="aw-dl-collections" role="tree" aria-label="Data library collections">
                <div
                  v-for="collection in libraryCollections"
                  :key="collection.competition"
                  class="aw-dl-collection"
                  role="treeitem"
                  :aria-expanded="!dlCollapsedCompetitions.has(collection.competition)"
                >
                  <!-- Competition header -->
                  <button
                    class="aw-dl-collection-header"
                    :aria-expanded="!dlCollapsedCompetitions.has(collection.competition)"
                    @click="toggleDlCompetition(collection.competition)"
                  >
                    <span class="aw-dl-collection-chevron">
                      {{ dlCollapsedCompetitions.has(collection.competition) ? '▶' : '▼' }}
                    </span>
                    <span class="aw-dl-collection-name">{{ collection.competition }}</span>
                    <span class="aw-dl-collection-count">{{ collection.totalMatches }} match{{ collection.totalMatches === 1 ? '' : 'es' }}</span>
                  </button>

                  <!-- Seasons under this competition -->
                  <div v-if="!dlCollapsedCompetitions.has(collection.competition)" class="aw-dl-seasons">
                    <div
                      v-for="seasonGroup in collection.seasons"
                      :key="seasonGroup.season"
                      class="aw-dl-season"
                      role="treeitem"
                      :aria-expanded="!dlCollapsedSeasons.has(collection.competition + '::' + seasonGroup.season)"
                    >
                      <button
                        class="aw-dl-season-header"
                        :aria-expanded="!dlCollapsedSeasons.has(collection.competition + '::' + seasonGroup.season)"
                        @click="toggleDlSeason(collection.competition, seasonGroup.season)"
                      >
                        <span class="aw-dl-season-chevron">
                          {{ dlCollapsedSeasons.has(collection.competition + '::' + seasonGroup.season) ? '▶' : '▼' }}
                        </span>
                        <span class="aw-dl-season-name">{{ seasonGroup.season }}</span>
                        <span class="aw-dl-season-count">{{ seasonGroup.matches.length }} match{{ seasonGroup.matches.length === 1 ? '' : 'es' }}</span>
                      </button>

                      <!-- Match list under this season -->
                      <div v-if="!dlCollapsedSeasons.has(collection.competition + '::' + seasonGroup.season)" class="aw-dl-season-matches">
                        <div
                          v-for="match in seasonGroup.matches"
                          :key="match.id"
                          class="aw-dl-match-row"
                          role="button"
                          tabindex="0"
                          :aria-label="'Open analyst detail for ' + match.teams"
                          @click="openLibraryMatch(match.id)"
                          @keydown.enter.prevent="openLibraryMatch(match.id)"
                          @keydown.space.prevent="openLibraryMatch(match.id)"
                        >
                          <span class="aw-dl-match-teams">{{ match.teams }}</span>
                          <span class="aw-dl-match-date">{{ match.date }}</span>
                          <span v-if="match.venue" class="aw-dl-match-venue aw-dl-muted">{{ match.venue }}</span>
                          <span
                            class="aw-dl-badge"
                            :class="match.isHistorical ? 'aw-dl-badge--imported' : 'aw-dl-badge--live'"
                          >{{ match.isHistorical ? 'Imported' : 'Live' }}</span>
                          <BaseButton
                            variant="ghost"
                            size="sm"
                            class="aw-dl-match-open"
                            :aria-label="'Open ' + match.teams"
                            @click.stop="openLibraryMatch(match.id)"
                          >View</BaseButton>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Flat list view -->
              <div v-else class="aw-dl-table-wrap">
                <table class="aw-dl-table" aria-label="Data Library match list">
                  <thead>
                    <tr>
                      <th>Match</th>
                      <th>Date</th>
                      <th>Format</th>
                      <th>Venue</th>
                      <th>Competition</th>
                      <th>Season</th>
                      <th>Source</th>
                      <th class="aw-dl-col-action">Open</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="match in libraryMatches"
                      :key="match.id"
                      class="aw-dl-row"
                      role="button"
                      tabindex="0"
                      :aria-label="'Open analyst detail for ' + match.teams"
                      @click="openLibraryMatch(match.id)"
                      @keydown.enter.prevent="openLibraryMatch(match.id)"
                      @keydown.space.prevent="openLibraryMatch(match.id)"
                    >
                      <td class="aw-dl-cell-main">
                        <span class="aw-dl-teams">{{ match.teams }}</span>
                        <span
                          v-if="match.isHistorical"
                          class="aw-dl-badge aw-dl-badge--imported"
                        >Imported</span>
                      </td>
                      <td>{{ match.date }}</td>
                      <td>{{ match.format }}</td>
                      <td class="aw-dl-muted">{{ match.venue || '—' }}</td>
                      <td class="aw-dl-muted">{{ match.eventName || '—' }}</td>
                      <td class="aw-dl-muted">{{ match.season || '—' }}</td>
                      <td>
                        <span
                          class="aw-dl-badge"
                          :class="match.isHistorical ? 'aw-dl-badge--imported' : 'aw-dl-badge--live'"
                        >
                          {{ match.isHistorical ? 'Historical import' : 'Live scored' }}
                        </span>
                      </td>
                      <td class="aw-dl-col-action">
                        <BaseButton
                          variant="ghost"
                          size="sm"
                          :aria-label="'Open ' + match.teams"
                          @click.stop="openLibraryMatch(match.id)"
                        >
                          View
                        </BaseButton>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p class="aw-dl-count">
                  Showing {{ libraryMatches.length }} of {{ matches.length }} match{{ matches.length === 1 ? '' : 'es' }}
                </p>
              </div>
            </div>

            <!-- CPL Podcast & Social Dashboard Tab -->
            <div v-else-if="activeTab === 'cpl-dashboard'" class="aw-table-wrapper">
              <CplPodcastDashboard />
            </div>

            <!-- Analytics Tab -->
            <div v-else-if="activeTab === 'analytics'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Analytics</h3>
                <p class="aw-table-subtitle">
                  Select a match to generate phase-level analytics visuals.
                </p>
              </div>

              <!-- Analytics match selector -->
              <div class="aw-match-selector" role="group" aria-label="Select match for analytics">
                <div class="aw-match-selector-row">
                  <div class="aw-match-selector-group">
                    <label class="aw-filter-label">Match source</label>
                    <div class="aw-chip-row">
                      <button
                        class="aw-chip"
                        :class="{ 'aw-chip--active': analyticsMatchSource === 'historical' }"
                        :aria-pressed="analyticsMatchSource === 'historical'"
                        @click="analyticsMatchSource = 'historical'; analyticsMatchId = ''"
                      >Historical</button>
                      <button
                        class="aw-chip"
                        :class="{ 'aw-chip--active': analyticsMatchSource === 'live' }"
                        :aria-pressed="analyticsMatchSource === 'live'"
                        @click="analyticsMatchSource = 'live'; analyticsMatchId = ''"
                      >Live</button>
                    </div>
                  </div>
                  <div class="aw-match-selector-group">
                    <label class="aw-filter-label" for="analytics-match-select">Match</label>
                    <select
                      id="analytics-match-select"
                      v-model="analyticsMatchId"
                      class="aw-select aw-select--wide"
                      aria-label="Select match for analytics"
                    >
                      <option value="">— select a match —</option>
                      <option v-for="m in analyticsMatchOptions" :key="m.id" :value="m.id">
                        {{ m.teams }}{{ m.date ? ' · ' + m.date : '' }}{{ m.season ? ' · ' + m.season : '' }}
                      </option>
                    </select>
                  </div>
                </div>
                <p v-if="analyticsMatchOptions.length === 0 && analyticsMatchSource === 'live'" class="aw-match-selector-hint">
                  No live-scored matches available.
                </p>
                <p v-else-if="analyticsMatchOptions.length === 0 && analyticsMatchSource === 'historical'" class="aw-match-selector-hint">
                  No historical matches imported yet. Use the Import Data tab to add match data.
                </p>
              </div>

              <!-- Empty state: no match selected -->
              <div v-if="!analyticsMatchId" class="aw-delivery-empty-state" role="status">
                <p class="aw-delivery-empty-msg">Select a match to generate analytics visuals.</p>
                <p class="aw-delivery-empty-hint">
                  Choose a match source above, then select a match to load phase-level visuals including
                  Manhattan, Worm, and scoring-distribution charts.
                </p>
              </div>

              <!-- Analytics visuals - shown once a match is selected -->
              <div v-else class="aw-analytics-content">
                <AnalyticsTablesWidget
                  :profile="null"
                  :match-id="analyticsMatchId"
                  :match-source="analyticsMatchSource"
                  :match-title="analyticsSelectedMatch?.teams ?? analyticsSelectedRegistryEntry?.match_title ?? null"
                  :match-date="analyticsSelectedMatch?.date ?? analyticsSelectedRegistryEntry?.match_date ?? null"
                  :result="normalizeResultDisplayText(analyticsSelectedMatch?.result ?? analyticsSelectedRegistryEntry?.result ?? null)"
                  :data-completeness="analyticsSelectedRegistryEntry?.data_completeness ?? null"
                  :registry-entry="analyticsSelectedRegistryEntry ?? null"
                />
              </div>
            </div>

            <!-- Import Data Tab -->
            <div v-else-if="activeTab === 'import'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Import Historical Data</h3>
                <p class="aw-table-subtitle">
                  Upload either a single historical JSON file or a bulk ZIP bundle.
                  Imports are validated before match data is saved.
                </p>
              </div>
              <div class="aw-import-panels">
                <HistoricalImportPanel @import-done="onImportDone" />
                <HistoricalImportBulkZipPanel @import-done="onImportDone" />
                <HistoricalMetadataOnlyMatchesPanel />
                <HistoricalCplResetReimportPanel />
                <HistoricalOcrReviewPanel />
                <HistoricalSourcePayloadReattachPanel />
                <BulkZipSourcePayloadRecoveryPanel />
                <HistoricalBackfillReprocessPanel />
                <HistoricalIdentityMappingReviewPanel />
              </div>
            </div>

            <!-- Match Registry Tab (Phase 10M) -->
            <div v-else-if="activeTab === 'registry'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Match Registry</h3>
                <p class="aw-table-subtitle">
                  Unified registry of all available matches classified by competition, gender,
                  source type, and data completeness. Use filters to explore the data foundation.
                </p>
              </div>

              <!-- Loading state -->
              <div v-if="matchRegistryLoading" class="aw-matches-loading" role="status" aria-live="polite">
                <p>Loading match registry…</p>
              </div>

              <!-- Error state -->
              <div v-else-if="matchRegistryError" class="aw-matches-error" role="alert">
                <p>Unable to load match registry.</p>
                <p class="aw-inline-error-detail">{{ matchRegistryError }}</p>
                <BaseButton variant="ghost" size="sm" @click="loadAnalystRegistry">Retry</BaseButton>
              </div>

              <template v-else>
                <!-- Diagnostics panel -->
                <div v-if="matchRegistry" class="aw-registry-diagnostics" aria-label="Registry diagnostics">
                  <div class="aw-registry-diag-grid">
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Total matches</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.total ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Historical imports</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.historical_import ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Live scored</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.cricksy_completed_scored ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">CPL Men</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.CPL_MEN ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">WCPL (Women)</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.WCPL ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Unknown competition</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.unknown_competition ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Delivery complete</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.delivery_complete ?? 0 }}</span>
                    </div>
                    <div class="aw-registry-diag-item">
                      <span class="aw-registry-diag-label">Analyst ready</span>
                      <span class="aw-registry-diag-val">{{ matchRegistry.diagnostics.analyst_ready ?? 0 }}</span>
                    </div>
                  </div>
                </div>

                <!-- Registry Filters -->
                <div class="aw-registry-filters" role="group" aria-label="Registry filters">
                  <div class="aw-registry-filter-row">
                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-competition-filter">Competition</label>
                      <select id="reg-competition-filter" class="aw-select" v-model="registryFilterCompetition">
                        <option value="all">All competitions</option>
                        <option value="CPL_MEN">CPL Men</option>
                        <option value="WCPL">WCPL (Women)</option>
                        <option value="unknown">Unknown</option>
                        <option
                          v-for="code in registryCompetitionOptions.filter(c => !['CPL_MEN','WCPL','unknown'].includes(c))"
                          :key="code"
                          :value="code"
                        >{{ registryCompetitionCodeLabel(code) }}</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-season-filter">Season</label>
                      <select id="reg-season-filter" class="aw-select" v-model="registryFilterSeason">
                        <option value="all">All seasons</option>
                        <option v-for="season in registrySeasonOptions" :key="season" :value="season">{{ season }}</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-gender-filter">Gender</label>
                      <select id="reg-gender-filter" class="aw-select" v-model="registryFilterGender">
                        <option value="all">All</option>
                        <option value="men">Men</option>
                        <option value="women">Women</option>
                        <option value="mixed">Mixed</option>
                        <option value="unknown">Unknown</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-source-filter">Source</label>
                      <select id="reg-source-filter" class="aw-select" v-model="registryFilterSource">
                        <option value="all">All sources</option>
                        <option value="historical_import">Historical import</option>
                        <option value="cricksy_completed_scored">Cricksy scored</option>
                        <option value="unknown">Unknown</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-completeness-filter">Data completeness</label>
                      <select id="reg-completeness-filter" class="aw-select" v-model="registryFilterCompleteness">
                        <option value="all">All levels</option>
                        <option value="delivery_complete">Delivery complete</option>
                        <option value="phase_level">Phase level</option>
                        <option value="innings_totals">Innings totals</option>
                        <option value="metadata_only">Metadata only</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group">
                      <label class="aw-filter-label" for="reg-sort-filter">Sort by</label>
                      <select id="reg-sort-filter" class="aw-select" v-model="registrySortOrder" aria-label="Sort registry rows">
                        <option value="newest">Newest first</option>
                        <option value="oldest">Oldest first</option>
                        <option value="competition">Competition</option>
                        <option value="season">Season</option>
                        <option value="completeness">Data completeness</option>
                      </select>
                    </div>

                    <div class="aw-registry-filter-group aw-registry-filter-group--reset">
                      <BaseButton
                        variant="ghost"
                        size="sm"
                        @click="registryFilterCompetition = 'all'; registryFilterSeason = 'all'; registryFilterGender = 'all'; registryFilterSource = 'all'; registryFilterCompleteness = 'all'"
                      >
                        Reset filters
                      </BaseButton>
                    </div>
                  </div>
                </div>

                <!-- Registry Table -->
                <div v-if="registryFilteredEntries.length === 0" class="aw-matches-empty">
                  <p>No matches match the current registry filters.</p>
                </div>

                <div v-else class="aw-registry-table-wrap">
                  <table class="aw-registry-table" role="table" aria-label="Match registry">
                    <thead>
                      <tr>
                        <th class="aw-registry-col-match">Match</th>
                        <th>Competition</th>
                        <th>Season</th>
                        <th>Gender</th>
                        <th>Source</th>
                        <th>Completeness</th>
                        <th>Analyst ready</th>
                        <th class="aw-registry-col-actions">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="entry in registryFilteredEntries"
                        :key="entry.match_id"
                        class="aw-registry-row"
                      >
                        <td class="aw-registry-cell-main aw-registry-col-match">
                          <span class="aw-registry-match-title">{{ entry.match_title }}</span>
                          <span class="aw-registry-match-date">{{ entry.match_date || 'Date unavailable' }}</span>
                          <span v-if="entry.result" class="aw-registry-match-result">{{ normalizeResultDisplayText(entry.result) }}</span>
                        </td>
                        <td>
                          <span class="aw-registry-badge" :class="`aw-registry-badge--${entry.competition_code.toLowerCase()}`">
                            {{ registryCompetitionLabel(entry) }}
                          </span>
                        </td>
                        <td>{{ entry.season || '—' }}</td>
                        <td>
                          <span class="aw-registry-gender" :class="`aw-registry-gender--${entry.gender_category}`">
                            {{ entry.gender_category }}
                          </span>
                        </td>
                        <td>
                          <span class="aw-registry-source">{{ registrySourceLabel(entry.source_type) }}</span>
                        </td>
                        <td>
                          <span class="aw-registry-completeness" :class="`aw-registry-completeness--${entry.data_completeness.replace(/_/g, '-')}`">
                            {{ registryCompletenessLabel(entry.data_completeness) }}
                          </span>
                        </td>
                        <td>
                          <span v-if="entry.analyst_ready" class="aw-registry-ready aw-registry-ready--yes">✓ Ready</span>
                          <span v-else class="aw-registry-ready aw-registry-ready--no">—</span>
                        </td>
                        <td class="aw-registry-actions">
                          <BaseButton
                            variant="ghost"
                            size="sm"
                            class="aw-registry-action aw-registry-action--analytics"
                            @click.stop="openRegistryAnalytics(entry)"
                          >
                            View in Analytics
                          </BaseButton>
                          <BaseButton
                            variant="ghost"
                            size="sm"
                            class="aw-registry-action aw-registry-action--story"
                            @click.stop="openRegistryMatchStory(entry)"
                          >
                            View Match Story
                          </BaseButton>
                          <BaseButton
                            variant="ghost"
                            size="sm"
                            class="aw-registry-action aw-registry-action--dashboard"
                            :disabled="!canOpenRegistryDashboard(entry)"
                            @click.stop="openRegistryDashboard(entry)"
                          >
                            CPL Dashboard
                          </BaseButton>
                          <BaseButton
                            variant="ghost"
                            size="sm"
                            class="aw-registry-action aw-registry-action--case-study"
                            disabled
                          >
                            Case study next
                          </BaseButton>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <p class="aw-dl-count">Showing {{ registryFilteredEntries.length }} of {{ matchRegistry?.total ?? 0 }} match{{ (matchRegistry?.total ?? 0) === 1 ? '' : 'es' }}</p>
                </div>
              </template>
            </div>


            <!-- Tournament Intelligence Tab (Phase 10S.1) -->
            <div v-else-if="activeTab === 'tournament'" class="aw-table-wrapper">
              <TournamentIntelligencePanel />
            </div>

            <div v-else-if="activeTab === 'archive'" class="aw-table-wrapper">
              <HistoricalArchiveExplorerPanel />
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
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, BaseInput, ImpactBar, MiniSparkline, AiCalloutsPanel, AiInsightReviewCard, MatchInsightEvidence } from '@/components'
import type { AiCallout } from '@/components'
import AnalyticsTablesWidget from '@/components/AnalyticsTablesWidget.vue'
import CplPodcastDashboard from '@/components/CplPodcastDashboard.vue'
import ExportUI from '@/components/ExportUI.vue'
import HistoricalImportPanel from '@/components/HistoricalImportPanel.vue'
import HistoricalImportBulkZipPanel from '@/components/HistoricalImportBulkZipPanel.vue'
import HistoricalMetadataOnlyMatchesPanel from '@/components/HistoricalMetadataOnlyMatchesPanel.vue'
import HistoricalCplResetReimportPanel from '@/components/HistoricalCplResetReimportPanel.vue'
import HistoricalOcrReviewPanel from '@/components/HistoricalOcrReviewPanel.vue'
import HistoricalSourcePayloadReattachPanel from '@/components/HistoricalSourcePayloadReattachPanel.vue'
import HistoricalBackfillReprocessPanel from '@/components/HistoricalBackfillReprocessPanel.vue'
import BulkZipSourcePayloadRecoveryPanel from '@/components/BulkZipSourcePayloadRecoveryPanel.vue'
import HistoricalIdentityMappingReviewPanel from '@/components/HistoricalIdentityMappingReviewPanel.vue'
import TournamentIntelligencePanel from '@/components/TournamentIntelligencePanel.vue'
import HistoricalArchiveExplorerPanel from '@/components/HistoricalArchiveExplorerPanel.vue'
import { readAiInsightCache, writeAiInsightCache } from '@/services/aiInsightCache'
import { useAuthStore } from '@/stores/authStore'
import { normalizeResultDisplayText } from '@/utils/resultDisplay'
import {
  getAnalystDeliveries,
  getAnalystMatches,
  getAnalystPlayers,
  getMatchCaseStudy,
  getMatchAiSummary,
  getMatchRegistry,
  getAnalystRegistry,
  historicalImportRollback,
  type AnalystDeliveryRow,
  type AnalystMatchListItem,
  type AnalystPlayerAggregateItem,
  type MatchCaseStudyResponse,
  type MatchAiSummary,
  type MatchRegistryResponse,
  type AnalystRegistryEntry,
  type AnalystMatchRegistryListResponse,
} from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

// Types
type AnalystTab = 'matches' | 'players' | 'deliveries' | 'case-studies' | 'analytics' | 'import' | 'data-library' | 'cpl-dashboard' | 'registry' | 'tournament' | 'archive'
type RegistrySortOption = 'newest' | 'oldest' | 'competition' | 'season' | 'completeness'

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
  { value: 'data-library', label: 'Data Library' },
  { value: 'players', label: 'Players' },
  { value: 'deliveries', label: 'Deliveries' },
  { value: 'case-studies', label: 'Case studies' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'cpl-dashboard', label: 'CPL Dashboard' },
  { value: 'registry', label: 'Match Registry' },
  { value: 'tournament', label: 'Tournament Intelligence' },
  { value: 'archive', label: 'Historical Archive' },
  { value: 'import', label: 'Import Data' }
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
  venue?: string | null
  eventName?: string | null
  season?: string | null
  matchNumber?: number | null
  sourceDates?: string[]
  isHistorical?: boolean
  source?: string
  historicalBatchId?: string | null
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
const cleanupMessage = ref<string | null>(null)
const cleanupMessageKind = ref<'success' | 'error'>('success')
const cleanupPendingMatchId = ref<string | null>(null)

// Data Library state — search/filter/sort controls
const dlSearch = ref('')
const dlSourceFilter = ref<'all' | 'imported' | 'live'>('all')
const dlFormatFilter = ref<'all' | 't20' | 'odi' | 'custom'>('all')
const dlSortOrder = ref<'recent' | 'date-asc'>('recent')
const dlViewMode = ref<'collections' | 'flat'>('collections')
const dlCollapsedCompetitions = ref(new Set<string>())
const dlCollapsedSeasons = ref(new Set<string>())

// Players tab filters
const playerCompetitionFilter = ref<string>('all')
const playerSeasonFilter = ref<string>('all')
const playerViewMode = ref<'all-time' | 'season'>('all-time')

// Deliveries tab match selector state
const deliveryCompetitionFilter = ref<string>('all')
const deliverySeasonFilter = ref<string>('all')
const deliveryFilterMatchId = ref<string>('')
const deliveriesLoading = ref(false)

// Analytics tab match selector state
const analyticsMatchSource = ref<'historical' | 'live'>('historical')
const analyticsMatchId = ref<string>('')

// Match detail state - loaded when a match is selected
const selectedMatchId = ref<string | null>(null)
const matchDetail = ref<MatchCaseStudyResponse | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const matchAiSummary = ref<MatchAiSummary | null>(null)
const matchAiLoading = ref(false)
const matchAiError = ref<string | null>(null)
const matchAiFallback = ref<{ summary: string; bullets: string[] } | null>(null)
const matchAiInsufficientData = ref(false)
const matchAiCacheStatus = ref<'none' | 'live' | 'cached' | 'stale' | 'fallback' | 'insufficient'>('none')

// Registry & Provenance state - loaded for historical matches (Phase 5M)
const registryData = ref<MatchRegistryResponse | null>(null)
const registryLoading = ref(false)

// Match Registry (Phase 10M) — unified registry with classification metadata
const matchRegistry = ref<AnalystMatchRegistryListResponse | null>(null)
const matchRegistryLoading = ref(false)
const matchRegistryError = ref<string | null>(null)
// Registry filters
const registryFilterCompetition = ref<string>('all')
const registryFilterSeason = ref<string>('all')
const registryFilterGender = ref<string>('all')
const registryFilterSource = ref<string>('all')
const registryFilterCompleteness = ref<string>('all')
const registrySortOrder = ref<RegistrySortOption>('newest')
// Players list - NO FAKE DATA
// Required: GET /analyst/players
const players = ref<Array<{ id: string; name: string; role: string; innings: number; runs: number; strikeRate: number; wickets: number; economy: number; matches: number }>>([])
const playerDataCompleteness = ref('metadata_only')

// Deliveries list - NO FAKE DATA
const deliveries = ref<Array<{ id: string; matchId: string; innings: number | null; team: string | null; overNumber: number | null; ballNumber: number | null; batter: string | null; bowler: string | null; nonStriker: string | null; runsOffBat: number; extraRuns: number; totalRuns: number; extraType: string | null; wicket: boolean; dismissalType: string | null; playerOut: string | null; fielders: string[]; phase: string | null; dataCompleteness: string }>>([])
const deliveryDataCompleteness = ref('metadata_only')

// Computed
const filteredMatches = computed(() => {
  const term = filters.search.toLowerCase()
  return matches.value.filter((m) => {
    const matchesTerm =
      !term ||
      m.teams.toLowerCase().includes(term) ||
      m.result.toLowerCase().includes(term) ||
      (m.venue || '').toLowerCase().includes(term)
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

const filteredDeliveries = computed(() => {
  const term = filters.search.toLowerCase()
  return deliveries.value.filter((d) => {
    if (!term) return true
    return [
      d.team ?? '',
      d.batter ?? '',
      d.bowler ?? '',
      d.nonStriker ?? '',
      d.dismissalType ?? '',
      d.playerOut ?? '',
      d.phase ?? '',
    ].some(value => value.toLowerCase().includes(term))
  })
})

// Data Library: filtered and sorted match list derived from the shared `matches` list.
const libraryMatches = computed(() => {
  const term = dlSearch.value.toLowerCase().trim()
  let result = matches.value.filter((m) => {
    // Source filter
    if (dlSourceFilter.value === 'imported' && !m.isHistorical) return false
    if (dlSourceFilter.value === 'live' && m.isHistorical) return false
    // Format filter
    if (dlFormatFilter.value === 't20' && m.format !== 'T20') return false
    if (dlFormatFilter.value === 'odi' && m.format !== 'ODI') return false
    if (dlFormatFilter.value === 'custom' && m.format !== 'CUSTOM') return false
    // Search term — match against teams, venue, competition, season, result
    if (term) {
      const haystack = [
        m.teams,
        m.venue ?? '',
        m.eventName ?? '',
        m.season ?? '',
        m.result,
      ].join(' ').toLowerCase()
      if (!haystack.includes(term)) return false
    }
    return true
  })
  // Sort
  result = [...result].sort((a, b) => {
    const da = new Date(a.date).getTime()
    const db = new Date(b.date).getTime()
    return dlSortOrder.value === 'date-asc' ? da - db : db - da
  })
  return result
})

const exportContextMatchId = computed(() => filteredMatches.value[0]?.id ?? null)

// Competition options derived from matches (for cross-tab filters)
const competitionOptions = computed(() => {
  const comps = new Set<string>()
  matches.value.forEach(m => { if (m.eventName) comps.add(m.eventName) })
  return [...comps].sort()
})

// Players tab: season options filtered by selected competition
const playerSeasonOptions = computed(() => {
  const seasons = new Set<string>()
  matches.value
    .filter(m => playerCompetitionFilter.value === 'all' || m.eventName === playerCompetitionFilter.value)
    .forEach(m => { if (m.season) seasons.add(m.season) })
  return [...seasons].sort().reverse()
})

// Deliveries tab: season options filtered by selected competition
const deliverySeasonOptions = computed(() => {
  const seasons = new Set<string>()
  matches.value
    .filter(m => deliveryCompetitionFilter.value === 'all' || m.eventName === deliveryCompetitionFilter.value)
    .forEach(m => { if (m.season) seasons.add(m.season) })
  return [...seasons].sort().reverse()
})

// Deliveries tab: match options filtered by competition and season
const deliveryMatchOptions = computed(() =>
  matches.value
    .filter(m => {
      if (deliveryCompetitionFilter.value !== 'all' && m.eventName !== deliveryCompetitionFilter.value) return false
      if (deliverySeasonFilter.value !== 'all' && m.season !== deliverySeasonFilter.value) return false
      return true
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
)

// Analytics tab: match options based on source selection
const analyticsMatchOptions = computed(() =>
  matches.value
    .filter(m => {
      if (analyticsMatchSource.value === 'historical') return Boolean(m.isHistorical)
      if (analyticsMatchSource.value === 'live') return !m.isHistorical
      return true
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
)

const analyticsSelectedMatch = computed(() =>
  matches.value.find(match => match.id === analyticsMatchId.value) ?? null
)

const analyticsSelectedRegistryEntry = computed(() =>
  matchRegistry.value?.entries.find(entry => entry.match_id === analyticsMatchId.value) ?? null
)

// Data Library: collections grouped by competition → season
const libraryCollections = computed(() => {
  const groups = new Map<string, Map<string, AnalystMatch[]>>()
  for (const match of libraryMatches.value) {
    const comp = match.eventName || 'Uncategorised'
    const season = match.season || 'Unknown season'
    if (!groups.has(comp)) groups.set(comp, new Map())
    const compGroup = groups.get(comp)!
    if (!compGroup.has(season)) compGroup.set(season, [])
    compGroup.get(season)!.push(match)
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([competition, seasons]) => ({
      competition,
      totalMatches: [...seasons.values()].reduce((s, ms) => s + ms.length, 0),
      seasons: [...seasons.entries()]
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([season, ms]) => ({ season, matches: ms })),
    }))
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

// Match Registry (Phase 10M) computed properties
const registryCompetitionOptions = computed(() => {
  const codes = new Set<string>()
  matchRegistry.value?.entries.forEach(e => { if (e.competition_code) codes.add(e.competition_code) })
  return [...codes].sort()
})

const registrySeasonOptions = computed(() => {
  const seasons = new Set<string>()
  matchRegistry.value?.entries.forEach(e => { if (e.season) seasons.add(e.season) })
  return [...seasons].sort().reverse()
})

function registryCompetitionLabel(entry: AnalystRegistryEntry): string {
  if (entry.competition_code === 'CPL_MEN') return 'CPL Men'
  if (entry.competition_code === 'WCPL') return 'WCPL'
  return entry.competition_name || registryCompetitionCodeLabel(entry.competition_code)
}

function registryCompetitionCodeLabel(code: string): string {
  const compact = code.trim()
  if (!compact) return 'unknown'
  if (compact === 'unknown') return 'unknown'
  const special: Record<string, string> = {
    ONE_DAY_CUP: 'One-Day Cup',
    T20_BLAST: 'T20 Blast',
    THE_HUNDRED_MEN: 'The Hundred Men',
    THE_HUNDRED_WOMEN: 'The Hundred Women',
    IPL: 'IPL',
    WPL: 'WPL',
    BBL: 'BBL',
    WBBL: 'WBBL',
    PSL: 'PSL',
    SA20: 'SA20',
    ILT20: 'ILT20',
    ICC_T20_WORLD_CUP: 'ICC T20 World Cup',
    ICC_CRICKET_WORLD_CUP: 'ICC Cricket World Cup',
    ICC_CHAMPIONS_TROPHY: 'ICC Champions Trophy',
  }
  if (special[compact]) return special[compact]
  return compact
    .toLowerCase()
    .split('_')
    .map(token => token ? token[0].toUpperCase() + token.slice(1) : token)
    .join(' ')
}

function humanizeRegistryToken(value: string | null | undefined): string {
  if (!value) return 'unknown'
  return value.replace(/_/g, ' ')
}

function registrySourceLabel(sourceType: string): string {
  return sourceType.replace(/_/g, ' ')
}

function registryCompletenessLabel(completeness: string): string {
  return completeness.replace(/_/g, ' ')
}

function registryDateSortValue(entry: AnalystRegistryEntry): number | null {
  if (!entry.match_date) return null
  const parsed = Date.parse(`${entry.match_date}T00:00:00Z`)
  return Number.isNaN(parsed) ? null : parsed
}

function registrySeasonSortValue(entry: AnalystRegistryEntry): number {
  if (typeof entry.season_year === 'number') return entry.season_year
  if (!entry.season) return Number.MIN_SAFE_INTEGER
  const numericSeason = Number.parseInt(entry.season, 10)
  return Number.isNaN(numericSeason) ? Number.MIN_SAFE_INTEGER : numericSeason
}

function compareRegistryDates(
  a: AnalystRegistryEntry,
  b: AnalystRegistryEntry,
  direction: 'asc' | 'desc',
): number {
  const aDate = registryDateSortValue(a)
  const bDate = registryDateSortValue(b)
  if (aDate === null && bDate === null) return 0
  if (aDate === null) return 1
  if (bDate === null) return -1
  return direction === 'asc' ? aDate - bDate : bDate - aDate
}

const registryFilteredEntries = computed<AnalystRegistryEntry[]>(() => {
  if (!matchRegistry.value) return []
  const filtered = matchRegistry.value.entries.filter(e => {
    if (registryFilterCompetition.value !== 'all' && e.competition_code !== registryFilterCompetition.value) return false
    if (registryFilterSeason.value !== 'all' && e.season !== registryFilterSeason.value) return false
    if (registryFilterGender.value !== 'all' && e.gender_category !== registryFilterGender.value) return false
    if (registryFilterSource.value !== 'all' && e.source_type !== registryFilterSource.value) return false
    if (registryFilterCompleteness.value !== 'all' && e.data_completeness !== registryFilterCompleteness.value) return false
    return true
  })
  const completenessRank: Record<string, number> = {
    delivery_complete: 0,
    phase_level: 1,
    innings_totals: 2,
    metadata_only: 3,
  }
  const sorted = [...filtered]
  sorted.sort((a, b) => {
    if (registrySortOrder.value === 'oldest') {
      return compareRegistryDates(a, b, 'asc')
    }
    if (registrySortOrder.value === 'competition') {
      return registryCompetitionLabel(a).localeCompare(registryCompetitionLabel(b))
    }
    if (registrySortOrder.value === 'season') {
      const seasonDelta = registrySeasonSortValue(b) - registrySeasonSortValue(a)
      if (seasonDelta !== 0) return seasonDelta
      return (b.season || '').localeCompare(a.season || '')
    }
    if (registrySortOrder.value === 'completeness') {
      return (completenessRank[a.data_completeness] ?? 99) - (completenessRank[b.data_completeness] ?? 99)
    }
    return compareRegistryDates(a, b, 'desc')
  })
  return sorted
})


const currentTabLabel = computed(() => {
  const tab = tabs.find((t) => t.value === activeTab.value)
  return tab?.label ?? ''
})

const canReviewAiInsights = computed(() => authStore.canAnalyze)

const aiConfidencePct = computed<number | null>(() => {
  const score = matchAiSummary.value?.ai_metadata?.confidence_score
  if (typeof score !== 'number') {
    return null
  }
  return Math.round(score * 100)
})

const aiConfidenceLabel = computed<string | null>(() => {
  const pct = aiConfidencePct.value
  if (pct === null) return null
  if (pct >= 80) return 'High'
  if (pct >= 50) return 'Medium'
  return 'Low'
})

const aiLimitations = computed<string[]>(() => matchAiSummary.value?.ai_metadata?.limitations ?? [])
const aiSourceRefs = computed(() => matchAiSummary.value?.ai_metadata?.source_refs ?? [])
const aiGroundingSummary = computed(() => {
  const summary = matchAiSummary.value?.ai_metadata?.grounding_summary
  return typeof summary === 'string' ? summary.trim() : ''
})
const matchAiStatusLabel = computed(() => {
  if (matchAiCacheStatus.value === 'cached') return 'Cached insight'
  if (matchAiCacheStatus.value === 'stale') return 'Stale cache'
  if (matchAiCacheStatus.value === 'fallback') return 'Deterministic fallback'
  if (matchAiCacheStatus.value === 'insufficient') return 'Insufficient data'
  return null
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

watch(analyticsMatchId, (matchId) => {
  selectedMatchId.value = matchId || null
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
      venue: item.venue ?? null,
      eventName: item.event_name ?? null,
      season: item.season ?? null,
      matchNumber: item.match_number ?? null,
      sourceDates: item.source_dates ?? [],
      isHistorical: Boolean(item.is_historical),
      source: item.source ?? 'live',
      historicalBatchId: item.historical_batch_id ?? null,
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

async function loadPlayers() {
  try {
    const response = await getAnalystPlayers()
    playerDataCompleteness.value = response.data_completeness
    players.value = response.items.map((item: AnalystPlayerAggregateItem) => ({
      id: item.player,
      name: item.player,
      role: item.role || 'Unknown',
      innings: item.innings ?? 0,
      matches: item.matches ?? 0,
      runs: item.runs ?? 0,
      strikeRate: Number((item.strike_rate ?? 0).toFixed(2)),
      wickets: item.wickets ?? 0,
      economy: Number((item.economy ?? 0).toFixed(2)),
    }))
  } catch (err) {
    console.error('[AnalystWorkspace] Failed to load players:', err)
    players.value = []
    playerDataCompleteness.value = 'metadata_only'
  }
}

async function loadDeliveries(matchId?: string) {
  if (!matchId) {
    deliveries.value = []
    deliveryDataCompleteness.value = 'metadata_only'
    return
  }
  deliveriesLoading.value = true
  try {
    const response = await getAnalystDeliveries(matchId)
    deliveryDataCompleteness.value = response.data_completeness
    deliveries.value = response.items.map((row: AnalystDeliveryRow, index: number) => ({
      id: `${row.match_id}-${row.innings ?? 'x'}-${row.over_number ?? 0}-${row.ball_number ?? 0}-${index}`,
      matchId: row.match_id,
      innings: row.innings,
      team: row.team,
      overNumber: row.over_number,
      ballNumber: row.ball_number,
      batter: row.batter,
      bowler: row.bowler,
      nonStriker: row.non_striker,
      runsOffBat: row.runs_off_bat ?? 0,
      extraRuns: row.extra_runs ?? 0,
      totalRuns: row.total_runs ?? 0,
      extraType: row.extra_type,
      wicket: row.wicket,
      dismissalType: row.dismissal_type,
      playerOut: row.player_out,
      fielders: row.fielders ?? [],
      phase: row.phase,
      dataCompleteness: row.data_completeness ?? 'metadata_only',
    }))
  } catch (err) {
    console.error('[AnalystWorkspace] Failed to load deliveries:', err)
    deliveries.value = []
    deliveryDataCompleteness.value = 'metadata_only'
  } finally {
    deliveriesLoading.value = false
  }
}

async function onDeliveryMatchSelected() {
  if (deliveryFilterMatchId.value) {
    await loadDeliveries(deliveryFilterMatchId.value)
  } else {
    deliveries.value = []
    deliveryDataCompleteness.value = 'metadata_only'
  }
}

function toggleDlCompetition(competition: string) {
  const next = new Set(dlCollapsedCompetitions.value)
  if (next.has(competition)) {
    next.delete(competition)
  } else {
    next.add(competition)
  }
  dlCollapsedCompetitions.value = next
}

function toggleDlSeason(competition: string, season: string) {
  const key = `${competition}::${season}`
  const next = new Set(dlCollapsedSeasons.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  dlCollapsedSeasons.value = next
}


async function selectMatch(matchId: string) {
  selectedMatchId.value = matchId
  registryData.value = null
  matchAiFallback.value = null
  matchAiInsufficientData.value = false
  matchAiCacheStatus.value = 'none'
  const selectedMatch = matches.value.find(m => m.id === matchId)
  await Promise.all([loadMatchDetail(matchId), loadMatchAiSummary(matchId)])
  // Registry data is loaded independently of match detail to avoid blocking the main detail
  // load. The "Registry & Provenance" panel reactively updates once this resolves.
  if (selectedMatch) {
    void loadMatchRegistry(matchId)
  }
  await nextTick()
  document.getElementById('aw-match-detail')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

function openLibraryMatch(matchId: string) {
  router.push({ name: 'MatchCaseStudy', params: { matchId } })
}

async function loadMatchDetail(matchId: string) {
  detailLoading.value = true
  detailError.value = null
  matchDetail.value = null
  try {
    matchDetail.value = await getMatchCaseStudy(matchId)
  } catch (err) {
    detailError.value = err instanceof Error ? err.message : 'Failed to load match detail'
    console.error('[AnalystWorkspace] Failed to load match detail:', err)
  } finally {
    detailLoading.value = false
  }
}

async function loadMatchAiSummary(matchId: string, forceRefresh = false) {
  const contextHash = `match:${matchId}`
  const staleAfterMs = 5 * 60 * 1000
  if (!forceRefresh) {
    const cached = readAiInsightCache<MatchAiSummary>({
      scope: 'match-summary',
      key: matchId,
      contextHash,
      staleAfterMs,
    })
    if (cached.entry) {
      matchAiSummary.value = cached.entry.value
      matchAiError.value = null
      matchAiFallback.value = null
      matchAiInsufficientData.value = false
      matchAiCacheStatus.value = cached.status === 'stale' ? 'stale' : 'cached'
      return
    }
  }

  matchAiLoading.value = true
  matchAiError.value = null
  matchAiSummary.value = null
  matchAiFallback.value = null
  matchAiInsufficientData.value = false
  try {
    const summary = await getMatchAiSummary(matchId)
    if (summary) {
      matchAiSummary.value = summary
      matchAiCacheStatus.value = 'live'
      writeAiInsightCache({
        scope: 'match-summary',
        key: matchId,
        contextHash,
        value: summary,
      })
    } else {
      const fallback = buildDeterministicMatchFallback(matchDetail.value)
      if (fallback) {
        matchAiFallback.value = fallback
        matchAiCacheStatus.value = 'fallback'
      } else {
        matchAiInsufficientData.value = true
        matchAiCacheStatus.value = 'insufficient'
      }
    }
  } catch (err) {
    console.error('[AnalystWorkspace] Failed to load AI insights:', err)
    const fallback = buildDeterministicMatchFallback(matchDetail.value)
    if (fallback) {
      matchAiFallback.value = fallback
      matchAiCacheStatus.value = 'fallback'
      matchAiError.value = null
    } else {
      matchAiInsufficientData.value = true
      matchAiCacheStatus.value = 'insufficient'
      matchAiError.value = null
    }
  } finally {
    matchAiLoading.value = false
  }
}

function buildDeterministicMatchFallback(detail: MatchCaseStudyResponse | null): { summary: string; bullets: string[] } | null {
  const match = detail?.match
  if (!match) return null
  const innings = match.innings ?? []
  const hasResult = Boolean(match.result?.trim())
  if (!hasResult && innings.length === 0) return null
  const bullets = innings
    .map((inn) => `${inn.team}: ${inn.runs}/${inn.wickets} in ${inn.overs} overs`)
    .slice(0, 2)
  if (detail?.momentum_summary?.title) {
    bullets.push(detail.momentum_summary.title)
  }
  if (detail?.key_phase?.title) {
    bullets.push(detail.key_phase.title)
  }
  return {
    summary: `${match.teams_label}: ${normalizeResultDisplayText(match.result) || match.result || 'Result unavailable'}`,
    bullets: bullets.slice(0, 4),
  }
}

async function loadMatchRegistry(matchId: string) {
  registryLoading.value = true
  try {
    registryData.value = await getMatchRegistry(matchId)
  } catch (err) {
    // Registry loading failure is non-fatal; panel will show empty state
    registryData.value = null
    console.error('[AnalystWorkspace] Failed to load registry data:', err)
  } finally {
    registryLoading.value = false
  }
}

// Phase 10M: load unified analyst match registry
async function loadAnalystRegistry() {
  matchRegistryLoading.value = true
  matchRegistryError.value = null
  try {
    matchRegistry.value = await getAnalystRegistry()
  } catch (err) {
    matchRegistryError.value = err instanceof Error ? err.message : 'Unable to load match registry'
    matchRegistry.value = null
  } finally {
    matchRegistryLoading.value = false
  }
}

function registryMatchSource(entry: AnalystRegistryEntry): 'historical' | 'live' {
  const linkedMatch = matches.value.find(match => match.id === entry.match_id)
  if (linkedMatch) {
    return linkedMatch.isHistorical ? 'historical' : 'live'
  }
  return entry.source_type === 'historical_import' ? 'historical' : 'live'
}

function canOpenRegistryDashboard(entry: AnalystRegistryEntry): boolean {
  return entry.competition_code === 'CPL_MEN' || entry.competition_code === 'WCPL'
}

function openRegistryAnalytics(entry: AnalystRegistryEntry) {
  selectedMatchId.value = entry.match_id
  analyticsMatchSource.value = registryMatchSource(entry)
  analyticsMatchId.value = entry.match_id
  activeTab.value = 'analytics'
}

function openRegistryMatchStory(entry: AnalystRegistryEntry) {
  selectedMatchId.value = entry.match_id
  router.push({ name: 'MatchCaseStudy', params: { matchId: entry.match_id } })
}

function openRegistryDashboard(entry: AnalystRegistryEntry) {
  if (!canOpenRegistryDashboard(entry)) return
  selectedMatchId.value = entry.match_id
  activeTab.value = 'cpl-dashboard'
}


function openFullCaseStudy() {
  if (selectedMatchId.value) {
    router.push({ name: 'MatchCaseStudy', params: { matchId: selectedMatchId.value } })
  }
}

async function refreshData() {
  await loadMatches()
  await loadPlayers()
  await loadAnalystRegistry()
  // Deliveries are loaded on demand via the match selector
  if (deliveryFilterMatchId.value) {
    await loadDeliveries(deliveryFilterMatchId.value)
  }
}

function canCleanupImportedMatch(match: AnalystMatch): boolean {
  return Boolean(
    match.isHistorical &&
    match.source === 'historical_import' &&
    match.historicalBatchId,
  )
}

async function cleanupImportedMatch(match: AnalystMatch) {
  if (!canCleanupImportedMatch(match) || !match.historicalBatchId) {
    return
  }
  const confirmed = window.confirm(
    `Remove imported match "${match.teams}" from Analyst Workspace? This only removes the imported historical match and keeps live/current matches protected.`,
  )
  if (!confirmed) return

  cleanupPendingMatchId.value = match.id
  cleanupMessage.value = null
  try {
    await historicalImportRollback(match.historicalBatchId)
    cleanupMessageKind.value = 'success'
    cleanupMessage.value = 'Imported match removed successfully.'
    if (selectedMatchId.value === match.id) {
      selectedMatchId.value = null
      matchDetail.value = null
      detailError.value = null
      registryData.value = null
    }
    await loadMatches()
  } catch (err) {
    cleanupMessageKind.value = 'error'
    cleanupMessage.value = err instanceof Error ? err.message : 'Failed to remove imported match'
  } finally {
    cleanupPendingMatchId.value = null
  }
}

function onImportDone(_gameId: string | null) {
  // Switch to the matches tab and refresh so the newly imported match appears
  activeTab.value = 'matches'
  void Promise.all([loadMatches(), loadPlayers()])
}

function resetFilters() {
  filters.search = ''
  filters.format = 'all'
  filters.phase = 'all'
  filters.perspective = 'all'
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

// --- Podcast Prep Package ---

interface PodcastTalkingPoint {
  id: string
  label: string
  text: string | null
}

interface PodcastPrepPackage {
  episodeTitle: string
  matchContext: string | null
  scoreboardFacts: string[]
  talkingPoints: PodcastTalkingPoint[]
  coachPrompts: string[]
  suggestedVisuals: string[]
  hasEnoughData: boolean
}

function buildPodcastPrepPackage(detail: MatchCaseStudyResponse): PodcastPrepPackage {
  const match = detail.match

  // Episode title — derived from real fields only
  const episodeTitle = match.teams_label
    ? `${match.teams_label} — ${match.format} (${match.date})`
    : 'Episode title not available'

  // Match context — result string from real data
  const matchContext = normalizeResultDisplayText(match.result) || match.result || null

  // Scoreboard facts — from innings array
  const scoreboardFacts: string[] = []
  for (const inns of match.innings) {
    const rr = inns.run_rate != null ? ` (RR: ${inns.run_rate.toFixed(2)})` : ''
    scoreboardFacts.push(`${inns.team}: ${inns.runs}/${inns.wickets} in ${inns.overs} overs${rr}`)
  }

  // Talking points — derived from real loaded fields, null when data is missing
  const talkingPoints: PodcastTalkingPoint[] = []

  // TP1: Momentum verdict
  if (detail.momentum_summary?.title && detail.momentum_summary?.subtitle) {
    talkingPoints.push({
      id: 'momentum',
      label: 'Momentum verdict',
      text: `${detail.momentum_summary.title}. ${detail.momentum_summary.subtitle}`,
    })
  } else {
    talkingPoints.push({ id: 'momentum', label: 'Momentum verdict', text: null })
  }

  // TP2: Key phase
  if (detail.key_phase?.title && detail.key_phase?.detail) {
    talkingPoints.push({
      id: 'key-phase',
      label: 'Key phase',
      text: `${detail.key_phase.title}: ${detail.key_phase.detail}`,
    })
  } else {
    talkingPoints.push({ id: 'key-phase', label: 'Key phase', text: null })
  }

  // TP3: Best phase by net swing vs par
  if (detail.phases && detail.phases.length > 0) {
    const best = [...detail.phases].sort(
      (a, b) => (b.net_swing_vs_par ?? 0) - (a.net_swing_vs_par ?? 0)
    )[0]
    const sign = (best.net_swing_vs_par ?? 0) >= 0 ? '+' : ''
    const rrStr = best.run_rate != null ? best.run_rate.toFixed(2) : '—'
    talkingPoints.push({
      id: 'phase-performance',
      label: 'Phase performance',
      text: `The ${best.label} phase yielded ${best.runs}/${best.wickets} at ${rrStr} runs per over (${sign}${best.net_swing_vs_par} vs par). ${best.impact_label}.`,
    })
  } else {
    talkingPoints.push({ id: 'phase-performance', label: 'Phase performance', text: null })
  }

  // TP4: Player spotlight (top-impact player from real key_players)
  if (detail.key_players && detail.key_players.length > 0) {
    const top = detail.key_players[0]
    const batStr = top.batting
      ? `${top.batting.runs} runs (SR ${top.batting.strike_rate != null ? top.batting.strike_rate.toFixed(1) : '—'})`
      : null
    const bowlStr = top.bowling
      ? `${top.bowling.wickets}/${top.bowling.runs} (Eco ${top.bowling.economy != null ? top.bowling.economy.toFixed(2) : '—'})`
      : null
    const stats = [batStr, bowlStr].filter(Boolean).join(', ')
    talkingPoints.push({
      id: 'player-spotlight',
      label: 'Player spotlight',
      text: `${top.name} (${top.team}) — ${top.impact_label}${stats ? `. Key figures: ${stats}` : ''}.`,
    })
  } else {
    talkingPoints.push({ id: 'player-spotlight', label: 'Player spotlight', text: null })
  }

  // Coach discussion prompts — only generated from available fields
  const coachPrompts: string[] = []
  if (detail.key_phase?.title) {
    coachPrompts.push(`What tactical decisions shaped the ${detail.key_phase.title.toLowerCase()}?`)
  }
  if (detail.key_players && detail.key_players.length > 0) {
    coachPrompts.push(
      `How do you plan for a player like ${detail.key_players[0].name} in future matches?`
    )
  }
  if (detail.phases && detail.phases.length > 0) {
    const weak = [...detail.phases].sort(
      (a, b) => (a.net_swing_vs_par ?? 0) - (b.net_swing_vs_par ?? 0)
    )[0]
    coachPrompts.push(
      `What adjustments would improve the ${weak.label.toLowerCase()} performance?`
    )
  }
  if (coachPrompts.length === 0) {
    coachPrompts.push('Add more completed match data to generate discussion prompts.')
  }

  // Suggested visuals — only based on sections already rendered in this panel
  const suggestedVisuals: string[] = []
  if (match.innings.length > 0) suggestedVisuals.push('Innings scorecard comparison')
  if (detail.momentum_summary) suggestedVisuals.push('Momentum verdict summary')
  if (detail.phases && detail.phases.length > 0) suggestedVisuals.push('Phase breakdown table')
  if (detail.key_players && detail.key_players.length > 0) suggestedVisuals.push('Key player impact cards')

  // Has enough data for a meaningful package?
  const dataScore =
    (match.innings.length > 0 ? 1 : 0) +
    (detail.key_phase ? 1 : 0) +
    (detail.momentum_summary ? 1 : 0)
  const hasEnoughData = dataScore >= 2

  return {
    episodeTitle,
    matchContext,
    scoreboardFacts,
    talkingPoints,
    coachPrompts,
    suggestedVisuals,
    hasEnoughData,
  }
}

const podcastPrepPackage = computed<PodcastPrepPackage | null>(() => {
  if (!matchDetail.value) return null
  return buildPodcastPrepPackage(matchDetail.value)
})

const canCopyPodcastPrep = computed(() => Boolean(podcastPrepPackage.value?.hasEnoughData))

const podcastCopyStatus = ref<'idle' | 'copied' | 'error'>('idle')

async function copyPodcastPrep() {
  if (!podcastPrepPackage.value || !canCopyPodcastPrep.value) return
  const pkg = podcastPrepPackage.value

  const lines: string[] = [
    '=== PODCAST PREP PACKAGE ===',
    `Episode: ${pkg.episodeTitle}`,
    '',
    'MATCH CONTEXT',
    pkg.matchContext ?? 'Not available yet',
    '',
    'SCOREBOARD FACTS',
  ]
  if (pkg.scoreboardFacts.length > 0) {
    lines.push(...pkg.scoreboardFacts)
  } else {
    lines.push('Not available yet')
  }
  lines.push('', 'TALKING POINTS')
  for (const tp of pkg.talkingPoints) {
    lines.push(`• ${tp.label}: ${tp.text ?? 'Insufficient data for this talking point'}`)
  }
  lines.push('', 'COACH DISCUSSION PROMPTS')
  for (const prompt of pkg.coachPrompts) {
    lines.push(`• ${prompt}`)
  }
  lines.push('', 'SUGGESTED VISUALS')
  if (pkg.suggestedVisuals.length > 0) {
    for (const v of pkg.suggestedVisuals) {
      lines.push(`• ${v}`)
    }
  } else {
    lines.push('Add more completed match data to generate this section')
  }

  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    podcastCopyStatus.value = 'copied'
    setTimeout(() => { podcastCopyStatus.value = 'idle' }, 2000)
  } catch {
    podcastCopyStatus.value = 'error'
    setTimeout(() => { podcastCopyStatus.value = 'idle' }, 3000)
  }
}

// Lifecycle - load data on mount
onMounted(() => {
  void Promise.all([loadMatches(), loadPlayers(), loadAnalystRegistry()])
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
  flex-wrap: wrap;
  justify-content: flex-end;
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

.aw-inline-completeness {
  display: inline-block;
  margin-left: var(--space-2);
  font-weight: var(--font-medium);
}

.aw-import-panels {
  display: grid;
  gap: var(--space-4);
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

.aw-inline-error-detail {
  margin: 0;
  color: var(--color-text-muted);
}

.aw-matches-empty {
  padding: var(--space-5);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  background: var(--color-surface-raised, #f8fafc);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
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

.aw-matches-row:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.aw-matches-row.aw-match--highlight {
  box-shadow: 0 0 0 2px var(--color-primary-soft);
  background-color: var(--color-primary-subtle);
  transition: box-shadow 160ms ease-out, transform 160ms ease-out, background-color 160ms ease-out;
  transform: translateY(-1px);
}

.aw-matches-row--selected {
  background-color: var(--color-primary-subtle);
  border-left: 3px solid var(--color-primary);
}

/* MATCH INTELLIGENCE PANEL */
.aw-match-detail {
  margin-top: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  display: grid;
  gap: var(--space-3);
}

.aw-detail-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.aw-detail-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-detail-meta {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.aw-detail-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.aw-detail-loading,
.aw-detail-error {
  padding: var(--space-3) 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.aw-detail-summary {
  display: grid;
  gap: var(--space-2);
}

.aw-detail-row {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.aw-detail-label {
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  min-width: 72px;
}

.aw-detail-value {
  color: var(--color-text);
}

.aw-detail-section-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.aw-detail-innings {
  display: grid;
  gap: var(--space-2);
}

.aw-innings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.aw-innings-table th {
  text-align: left;
  padding: var(--space-1) var(--space-2);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
}

.aw-innings-table td {
  padding: var(--space-2);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-subtle);
}

.aw-detail-empty-hint {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.aw-detail-momentum,
.aw-detail-keyphase {
  display: grid;
  gap: var(--space-1);
}

.aw-detail-momentum-title,
.aw-detail-keyphase-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-detail-momentum-sub,
.aw-detail-keyphase-detail {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* PHASE BREAKDOWN */
.aw-detail-phases {
  display: grid;
  gap: var(--space-2);
}

.aw-phases-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.aw-phases-table th {
  text-align: left;
  padding: var(--space-1) var(--space-2);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
}

.aw-phases-table td {
  padding: var(--space-2);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-subtle);
}

.aw-phase-badge {
  display: inline-block;
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.aw-phase-badge--positive {
  background: var(--color-success-subtle, #dcfce7);
  color: var(--color-success, #16a34a);
}

.aw-phase-badge--negative {
  background: var(--color-danger-subtle, #fee2e2);
  color: var(--color-danger, #dc2626);
}

.aw-phase-badge--neutral {
  background: var(--color-surface-raised, #f1f5f9);
  color: var(--color-text-muted);
}

/* KEY PLAYERS */
.aw-detail-keyplayers {
  display: grid;
  gap: var(--space-2);
}

.aw-keyplayers-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2);
}

.aw-keyplayer-card {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised, #f8fafc);
  display: grid;
  gap: var(--space-1);
}

.aw-keyplayer-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.aw-keyplayer-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-keyplayer-team {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-keyplayer-impact {
  margin-left: auto;
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.aw-keyplayer-impact--high {
  background: var(--color-success-subtle, #dcfce7);
  color: var(--color-success, #16a34a);
}

.aw-keyplayer-impact--medium {
  background: var(--color-warning-subtle, #fef9c3);
  color: var(--color-warning, #ca8a04);
}

.aw-keyplayer-impact--low {
  background: var(--color-surface-raised, #f1f5f9);
  color: var(--color-text-muted);
}

.aw-keyplayer-stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.aw-keyplayer-stat {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-detail-ai {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised, #f8fafc);
  display: grid;
  gap: var(--space-3);
}

.aw-detail-ai-note {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-detail-ai-grid {
  display: grid;
  gap: var(--space-3);
}

.aw-detail-ai-review {
  border: 1px solid var(--color-border-subtle);
}

.aw-detail-ai-block {
  display: grid;
  gap: var(--space-2);
}

.aw-detail-ai-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-detail-ai-body {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.5;
}

.aw-detail-ai-confidence {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-medium);
}

.aw-detail-ai-list {
  margin: 0;
  padding-left: var(--space-4);
  display: grid;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.aw-detail-ai-muted {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
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

  .aw-header-actions {
    justify-content: flex-start;
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

/* PODCAST PREP PACKAGE */
.aw-podcast-prep {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised, #f8fafc);
}

.aw-podcast-prep-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.aw-podcast-copy-btn {
  white-space: nowrap;
}

.aw-podcast-insufficient {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
  padding: var(--space-2) 0;
}

.aw-podcast-block {
  display: grid;
  gap: var(--space-1);
}

.aw-podcast-block-label {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.aw-podcast-block-value {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.aw-podcast-list {
  margin: 0;
  padding-left: var(--space-4);
  display: grid;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.aw-podcast-empty {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.aw-podcast-talking-points {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2);
}

.aw-podcast-tp {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
}

.aw-podcast-tp-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.aw-podcast-tp-text {
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.5;
}

.aw-podcast-tp-empty {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

/* ── Registry & Provenance panel (Phase 5M) ─────────────────────────────── */

.aw-detail-registry {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.aw-registry-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.aw-registry-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.aw-registry-label {
  min-width: 10rem;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}

.aw-registry-value {
  color: var(--color-text);
  word-break: break-word;
}

.aw-registry-mono {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-registry-divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.aw-registry-status--ok {
  color: var(--color-success, #22c55e);
  font-weight: var(--font-semibold);
}

.aw-registry-status--warn {
  color: var(--color-warning, #f59e0b);
  font-weight: var(--font-semibold);
}

.aw-registry-status--bad {
  color: var(--color-error, #ef4444);
  font-weight: var(--font-semibold);
}

.aw-registry-status--neutral {
  color: var(--color-text-muted);
}

.aw-registry-blocking {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs);
  color: var(--color-warning, #f59e0b);
}

.aw-registry-loading,
.aw-registry-empty {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
  padding: var(--space-2) 0;
}

/* =====================================================
   DATA LIBRARY TAB
   ===================================================== */

.aw-dl-controls {
  display: grid;
  gap: var(--space-3);
}

.aw-dl-search {
  max-width: 480px;
}

.aw-dl-filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}

.aw-dl-table-wrap {
  display: grid;
  gap: var(--space-2);
  overflow-x: auto;
}

.aw-dl-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.aw-dl-table th,
.aw-dl-table td {
  padding: var(--space-3) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.aw-dl-table th {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-surface-hover);
}

.aw-dl-row {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.aw-dl-row:hover {
  background: var(--color-surface-hover);
}

.aw-dl-row:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.aw-dl-cell-main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.aw-dl-teams {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.aw-dl-muted {
  color: var(--color-text-muted);
}

.aw-dl-badge {
  display: inline-block;
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.aw-dl-badge--imported {
  background: var(--color-primary-soft, rgba(99, 102, 241, 0.12));
  color: var(--color-primary, #6366f1);
}

.aw-dl-badge--live {
  background: var(--color-success-soft, rgba(34, 197, 94, 0.12));
  color: var(--color-success, #22c55e);
}

.aw-dl-col-action {
  width: 80px;
  text-align: center;
}

.aw-dl-count {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: right;
}

/* =====================================================
   DATA LIBRARY COLLECTIONS VIEW
   ===================================================== */

.aw-dl-collections {
  display: grid;
  gap: var(--space-3);
}

.aw-dl-collection {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.aw-dl-collection-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3);
  background: var(--color-surface-hover);
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.aw-dl-collection-header:hover {
  background: var(--color-surface-raised, #f1f5f9);
}

.aw-dl-collection-chevron {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.aw-dl-collection-name {
  flex: 1;
}

.aw-dl-collection-count {
  font-size: var(--text-xs);
  font-weight: var(--font-normal);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.aw-dl-seasons {
  padding: var(--space-2) var(--space-3) var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.aw-dl-season {
  border: 1px solid var(--color-border-subtle, var(--color-border));
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.aw-dl-season-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary, var(--color-text));
}

.aw-dl-season-header:hover {
  background: var(--color-surface-hover);
}

.aw-dl-season-chevron {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.aw-dl-season-name {
  flex: 1;
}

.aw-dl-season-count {
  font-size: var(--text-xs);
  font-weight: var(--font-normal);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.aw-dl-season-matches {
  display: grid;
  gap: 0;
}

.aw-dl-match-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--color-border-subtle, var(--color-border));
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text);
  flex-wrap: wrap;
}

.aw-dl-match-row:hover {
  background: var(--color-surface-hover);
}

.aw-dl-match-row:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.aw-dl-match-teams {
  flex: 1;
  font-weight: var(--font-medium);
  min-width: 0;
}

.aw-dl-match-date {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.aw-dl-match-venue {
  font-size: var(--text-xs);
  white-space: nowrap;
}

.aw-dl-match-open {
  margin-left: auto;
  flex-shrink: 0;
}

/* =====================================================
   PLAYERS TAB FILTERS & DIAGNOSTICS
   ===================================================== */

.aw-player-filters {
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.aw-player-filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}

.aw-select {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg, #ffffff);
  color: var(--color-text);
  font-size: var(--text-sm);
  min-width: 120px;
}

.aw-select--wide {
  min-width: 260px;
}

.aw-diagnostics-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-subtle, var(--color-border));
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.aw-diagnostics-item {
  color: var(--color-text-muted);
}

.aw-diagnostics-sep {
  color: var(--color-text-muted);
  opacity: 0.4;
}

.aw-diagnostics-warn {
  color: var(--color-warning, #ca8a04);
  font-weight: var(--font-medium);
}

/* =====================================================
   DELIVERIES TAB MATCH SELECTOR
   ===================================================== */

.aw-match-selector {
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  display: grid;
  gap: var(--space-2);
}

.aw-match-selector-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-3);
}

.aw-match-selector-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.aw-match-selector-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

.aw-delivery-empty-state {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

.aw-delivery-empty-msg {
  margin: 0 0 var(--space-2);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.aw-delivery-empty-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 440px;
  margin-inline: auto;
}

/* =====================================================
   ANALYTICS TAB
   ===================================================== */

.aw-analytics-content {
  display: grid;
  gap: var(--space-4);
}

/* ── Match Registry (Phase 10M) ─────────────────────────── */
.aw-registry-diagnostics {
  background: color-mix(in srgb, var(--color-surface-elevated, #f8f9fa) 90%, transparent);
  border: 1px solid var(--color-border, #dee2e6);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  margin-bottom: var(--space-4, 16px);
}

.aw-registry-diag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3, 12px);
}

.aw-registry-diag-item {
  display: flex;
  flex-direction: column;
  min-width: 110px;
}

.aw-registry-diag-label {
  font-size: 0.72rem;
  color: var(--color-text-muted, #6c757d);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.aw-registry-diag-val {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary, #212529);
}

.aw-registry-filters {
  margin-bottom: var(--space-4, 16px);
}

.aw-registry-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3, 12px);
  align-items: flex-end;
}

.aw-registry-filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}

.aw-registry-filter-group--reset {
  justify-content: flex-end;
}

.aw-select {
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border: 1px solid var(--color-border, #dee2e6);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface, #fff);
  font-size: 0.875rem;
  color: var(--color-text-primary, #212529);
}

.aw-registry-table-wrap {
  border: 1px solid var(--color-border, #dee2e6);
  border-radius: var(--radius-md, 8px);
  background: color-mix(in srgb, var(--color-surface, #fff) 94%, transparent);
  overflow-x: auto;
}

.aw-registry-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  min-width: 980px;
}

.aw-registry-table th,
.aw-registry-table td {
  padding: var(--space-3, 12px) var(--space-3, 12px);
  text-align: left;
  border-bottom: 1px solid var(--color-border, #dee2e6);
  vertical-align: top;
}

.aw-registry-table th {
  font-weight: 600;
  color: var(--color-text-muted, #6c757d);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: color-mix(in srgb, var(--color-surface-elevated, #f8f9fa) 92%, transparent);
  position: sticky;
  top: 0;
  z-index: 1;
}

.aw-registry-row:hover {
  background: color-mix(in srgb, var(--color-surface-hover, #f1f3f5) 88%, transparent);
}

.aw-registry-cell-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.aw-registry-match-title {
  font-weight: 600;
  line-height: 1.35;
}

.aw-registry-match-date {
  font-size: 0.75rem;
  color: var(--color-text-muted, #6c757d);
}

.aw-registry-match-result {
  font-size: 0.78rem;
  color: var(--color-text-secondary, #495057);
}

.aw-registry-col-match {
  min-width: 260px;
  width: 30%;
}

.aw-registry-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 100px;
  font-size: 0.72rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--color-surface-elevated, #f8f9fa) 92%, transparent);
  color: var(--color-text-secondary, #495057);
  border: 1px solid var(--color-border, #dee2e6);
}

.aw-registry-badge--cpl_men {
  background: rgba(0, 102, 204, 0.12);
  color: #6eb6ff;
  border-color: rgba(0, 102, 204, 0.32);
}

.aw-registry-badge--wcpl {
  background: rgba(168, 58, 159, 0.16);
  color: #f0a6f3;
  border-color: rgba(168, 58, 159, 0.3);
}

.aw-registry-badge--unknown {
  background: rgba(108, 117, 125, 0.14);
  color: var(--color-text-muted, #6c757d);
  border-color: rgba(108, 117, 125, 0.28);
}

.aw-registry-gender {
  font-size: 0.8rem;
  font-weight: 500;
}

.aw-registry-gender--men { color: #0066cc; }
.aw-registry-gender--women { color: #8b008b; }
.aw-registry-gender--unknown,
.aw-registry-gender--mixed { color: var(--color-text-muted, #6c757d); }

.aw-registry-source {
  font-size: 0.8rem;
  color: var(--color-text-secondary, #495057);
}

.aw-registry-completeness {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 500;
  border: 1px solid transparent;
}

.aw-registry-completeness--delivery-complete {
  background: rgba(46, 160, 67, 0.14);
  color: #8dde9d;
  border-color: rgba(46, 160, 67, 0.28);
}

.aw-registry-completeness--phase-level {
  background: rgba(56, 139, 253, 0.14);
  color: #7fc7ff;
  border-color: rgba(56, 139, 253, 0.28);
}

.aw-registry-completeness--innings-totals {
  background: rgba(210, 153, 34, 0.16);
  color: #f0c46c;
  border-color: rgba(210, 153, 34, 0.28);
}

.aw-registry-completeness--metadata-only {
  background: rgba(108, 117, 125, 0.14);
  color: var(--color-text-muted, #6c757d);
  border-color: rgba(108, 117, 125, 0.28);
}

.aw-registry-ready--yes {
  color: #8dde9d;
  font-weight: 600;
}

.aw-registry-ready--no {
  color: var(--color-text-muted, #6c757d);
}

.aw-registry-col-actions {
  min-width: 260px;
}

.aw-registry-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.aw-registry-action {
  white-space: nowrap;
}

</style>
