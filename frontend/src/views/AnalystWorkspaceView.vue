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
                      <span>• {{ match.result }}</span>
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
                      <span class="aw-detail-value">{{ matchDetail.match.result || '—' }}</span>
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
                    <h4 class="aw-detail-section-title">Key phase</h4>
                    <p class="aw-detail-keyphase-title">
                      {{ matchDetail.key_phase.title }}
                    </p>
                    <p class="aw-detail-keyphase-detail">
                      {{ matchDetail.key_phase.detail }}
                    </p>
                  </section>

                  <!-- Phase breakdown -->
                  <section class="aw-detail-phases">
                    <h4 class="aw-detail-section-title">Phase breakdown</h4>
                    <div
                      v-if="!matchDetail.phases || matchDetail.phases.length === 0"
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
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Season</span>
                      <span class="aw-registry-value">{{ registryData.season ?? 'Unknown' }}</span>
                    </div>
                    <div class="aw-registry-row">
                      <span class="aw-registry-label">Venue</span>
                      <span class="aw-registry-value">{{ registryData.venue ?? 'Unknown' }}</span>
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

            <!-- Data Library Tab -->
            <div v-else-if="activeTab === 'data-library'" class="aw-table-wrapper">
              <div class="aw-table-header">
                <h3>Data Library</h3>
                <p class="aw-table-subtitle">
                  Browse available match datasets for analysis. Historical imports are clearly
                  identified. Select a match to open the analyst match detail view.
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

              <!-- Data Library table -->
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

            <!-- Analytics Tab -->
            <div v-else-if="activeTab === 'analytics'" class="aw-table-wrapper">
              <AnalyticsTablesWidget :profile="null" />
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
                <HistoricalOcrReviewPanel />
              </div>
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
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, BaseInput, ImpactBar, MiniSparkline, AiCalloutsPanel } from '@/components'
import type { AiCallout } from '@/components'
import AnalyticsTablesWidget from '@/components/AnalyticsTablesWidget.vue'
import ExportUI from '@/components/ExportUI.vue'
import HistoricalImportPanel from '@/components/HistoricalImportPanel.vue'
import HistoricalImportBulkZipPanel from '@/components/HistoricalImportBulkZipPanel.vue'
import HistoricalOcrReviewPanel from '@/components/HistoricalOcrReviewPanel.vue'
import {
  getAnalystMatches,
  getMatchCaseStudy,
  getMatchRegistry,
  historicalImportRollback,
  type AnalystMatchListItem,
  type MatchCaseStudyResponse,
  type MatchRegistryResponse,
} from '@/services/api'

const router = useRouter()

// Types
type AnalystTab = 'matches' | 'players' | 'deliveries' | 'case-studies' | 'analytics' | 'import' | 'data-library'

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

// Match detail state - loaded when a match is selected
const selectedMatchId = ref<string | null>(null)
const matchDetail = ref<MatchCaseStudyResponse | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)

// Registry & Provenance state - loaded for historical matches (Phase 5M)
const registryData = ref<MatchRegistryResponse | null>(null)
const registryLoading = ref(false)

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

async function selectMatch(matchId: string) {
  selectedMatchId.value = matchId
  registryData.value = null
  const selectedMatch = matches.value.find(m => m.id === matchId)
  await loadMatchDetail(matchId)
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

function openFullCaseStudy() {
  if (selectedMatchId.value) {
    router.push({ name: 'MatchCaseStudy', params: { matchId: selectedMatchId.value } })
  }
}

async function refreshData() {
  await loadMatches()
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
  loadMatches()
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
  const matchContext = match.result || null

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
</style>
