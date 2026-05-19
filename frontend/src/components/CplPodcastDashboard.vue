<template>
  <div class="cpld">
    <!-- Header -->
    <div class="cpld-header">
      <h3 class="cpld-title">🏏 CPL Podcast &amp; Social Dashboard</h3>
      <p class="cpld-subtitle">
        Deterministic visuals from imported Caribbean Premier League match data.
        All values are traceable to validated historical imports — no fabricated data.
      </p>
    </div>

    <!-- Provenance notice -->
    <div class="cpld-provenance-bar" role="note" aria-label="Data provenance notice">
      <span class="cpld-provenance-icon">🔒</span>
      <span>
        Source: validated historical import only.
        <span v-if="summary">
          {{ summary.total_eligible_matches }} eligible match{{ summary.total_eligible_matches === 1 ? '' : 'es' }} in archive.
          <span v-if="summary.excluded_metadata_only_count > 0" class="cpld-warn-inline">
            {{ summary.excluded_metadata_only_count }} metadata-only record{{ summary.excluded_metadata_only_count === 1 ? '' : 's' }} excluded.
          </span>
          <span v-if="summary.excluded_invalid_count > 0" class="cpld-warn-inline">
            {{ summary.excluded_invalid_count }} invalid/unvalidated record{{ summary.excluded_invalid_count === 1 ? '' : 's' }} excluded.
          </span>
        </span>
      </span>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="cpld-state cpld-state--loading" role="status" aria-live="polite">
      <p>Loading historical match data…</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="cpld-state cpld-state--error" role="alert">
      <p>⚠️ Unable to load historical stats: {{ error }}</p>
      <button class="cpld-retry-btn" @click="load">Retry</button>
    </div>

    <!-- No CPL data state -->
    <div v-else-if="cplMatches.length === 0 && !loading" class="cpld-state cpld-state--empty">
      <p class="cpld-empty-heading">No CPL data available</p>
      <p class="cpld-empty-body">
        No validated Caribbean Premier League matches have been imported yet.
        Import CPL historical data through the <strong>Import Data</strong> tab to populate this dashboard.
      </p>
      <p class="cpld-empty-body">
        Social image export is disabled until deterministic CPL data is available.
      </p>
    </div>

    <template v-else>
      <!-- Filters -->
      <section class="cpld-filters" aria-label="Dashboard filters">
        <div class="cpld-filter-group">
          <label class="cpld-filter-label" for="cpld-season-select">Season</label>
          <select id="cpld-season-select" v-model="selectedSeason" class="cpld-select" aria-label="Filter by season">
            <option value="all">All seasons</option>
            <option v-for="s in availableSeasons" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="cpld-filter-group">
          <label class="cpld-filter-label" for="cpld-team-select">Team</label>
          <select id="cpld-team-select" v-model="selectedTeam" class="cpld-select" aria-label="Filter by team">
            <option value="all">All teams</option>
            <option v-for="t in availableTeams" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div class="cpld-filter-group">
          <label class="cpld-filter-label" for="cpld-venue-select">Venue</label>
          <select id="cpld-venue-select" v-model="selectedVenue" class="cpld-select" aria-label="Filter by venue">
            <option value="all">All venues</option>
            <option v-for="v in availableVenues" :key="v" :value="v">{{ v }}</option>
          </select>
        </div>
        <button class="cpld-reset-btn" @click="resetFilters">Reset filters</button>
      </section>

      <section class="cpld-section cpld-export-pack" aria-label="Social image export pack">
        <h4 class="cpld-section-title">🖼 CPL Social Image Export Pack</h4>
        <p class="cpld-export-desc">
          Export deterministic dashboard panels as reviewable images. No AI-generated claims are added.
        </p>

        <div class="cpld-export-grid">
          <div class="cpld-filter-group">
            <label class="cpld-filter-label" for="cpld-export-target">Export target</label>
            <select id="cpld-export-target" v-model="exportTarget" class="cpld-select" aria-label="Select export target">
              <option v-for="target in exportTargets" :key="target.value" :value="target.value">
                {{ target.label }}
              </option>
            </select>
          </div>

          <div class="cpld-filter-group">
            <label class="cpld-filter-label" for="cpld-export-format">Format</label>
            <select id="cpld-export-format" v-model="exportFormat" class="cpld-select" aria-label="Select export format">
              <option v-for="format in exportFormats" :key="format.value" :value="format.value">
                {{ format.label }}
              </option>
            </select>
          </div>

          <div class="cpld-filter-group">
            <label class="cpld-filter-label" for="cpld-export-template">Template</label>
            <select
              id="cpld-export-template"
              v-model="exportTemplateId"
              class="cpld-select"
              aria-label="Select export template"
            >
              <option v-for="templateOption in availableExportTemplates" :key="templateOption.id" :value="templateOption.id">
                {{ templateOption.label }}
              </option>
            </select>
          </div>

          <div class="cpld-export-toggles">
            <label class="cpld-export-check">
              <input v-model="exportIncludePoweredBy" type="checkbox" />
              Powered by Cricksy
            </label>
            <label class="cpld-export-check">
              <input v-model="exportIncludeImportedLabel" type="checkbox" />
              Imported CPL historical data
            </label>
            <label class="cpld-export-check">
              <input v-model="exportIncludeContextLabel" type="checkbox" />
              Include season/match/venue context
            </label>
          </div>
        </div>

        <div class="cpld-export-review" role="note" aria-label="Export review summary">
          <p>
            Review target:
            <strong>{{ activeExportTarget?.label ?? 'Unavailable' }}</strong>
            · Format: <strong>{{ activeExportFormat?.label ?? 'Unavailable' }}</strong>
            · Template: <strong>{{ activeExportTemplate?.label ?? 'Unavailable' }}</strong>
          </p>
          <p v-if="activeExportTemplate" class="cpld-export-meta">
            Family: {{ activeExportTemplateFamilyLabel }} · Variant: {{ activeExportTemplateVariantLabel }}
          </p>
          <p v-if="activeExportTemplate" class="cpld-export-meta">
            {{ activeExportTemplate.description }}
          </p>
          <p class="cpld-export-meta">
            {{ exportReviewLabel }}
          </p>
        </div>

        <div v-if="!activeExportAvailability.available" class="cpld-insufficient cpld-insufficient--warn" role="alert">
          {{ activeExportAvailability.reason }}
        </div>
        <div v-else-if="!templateRequirementAvailability.available" class="cpld-insufficient cpld-insufficient--warn" role="alert">
          {{ templateRequirementAvailability.reason }}
        </div>

        <div class="cpld-export-actions">
          <button
            class="cpld-export-btn"
            :disabled="!activeExportAvailability.available || !templateRequirementAvailability.available || exportBusy"
            aria-label="Generate export preview"
            @click="generateExportPreview"
          >
            {{ exportBusy ? 'Generating preview…' : 'Generate preview' }}
          </button>
          <button
            class="cpld-export-btn cpld-export-btn--secondary"
            :disabled="!exportPreviewUrl || exportBusy"
            aria-label="Download export image"
            @click="downloadExportImage"
          >
            Download PNG
          </button>
        </div>

        <p v-if="exportError" class="cpld-export-error" role="alert">⚠ {{ exportError }}</p>

        <div v-if="exportPreviewUrl" class="cpld-export-preview-wrap">
          <p class="cpld-export-preview-label">Preview (review before download)</p>
          <img class="cpld-export-preview" :src="exportPreviewUrl" alt="Export preview image" />
        </div>
      </section>

      <!-- ── 1. Season Summary Cards ── -->
      <section ref="seasonSummaryRef" class="cpld-section" aria-label="Season summary">
        <h4 class="cpld-section-title">📊 Season Summary</h4>
        <p v-if="selectedSeason !== 'all'" class="cpld-section-scope">
          Showing season: <strong>{{ selectedSeason }}</strong>
          <span v-if="selectedTeam !== 'all'"> · Team: <strong>{{ selectedTeam }}</strong></span>
          <span v-if="selectedVenue !== 'all'"> · Venue: <strong>{{ selectedVenue }}</strong></span>
        </p>

        <div class="cpld-cards">
          <div class="cpld-card">
            <p class="cpld-card-value">{{ filteredMatches.length }}</p>
            <p class="cpld-card-label">Matches available</p>
            <p v-if="filteredMatches.length === 0" class="cpld-card-warn">
              No matches match current filters
            </p>
          </div>
          <div class="cpld-card">
            <p class="cpld-card-value">{{ filteredTeamNames.size }}</p>
            <p class="cpld-card-label">Teams represented</p>
          </div>
          <div class="cpld-card">
            <p class="cpld-card-value">{{ filteredVenueNames.size }}</p>
            <p class="cpld-card-label">Venues represented</p>
          </div>
          <div class="cpld-card">
            <p class="cpld-card-value">{{ filteredTotalRuns.toLocaleString() }}</p>
            <p class="cpld-card-label">Total runs</p>
            <p v-if="filteredMatches.some(m => !m.has_delivery_data)" class="cpld-card-note">
              ⚠ Some matches lack delivery data
            </p>
          </div>
          <div class="cpld-card">
            <p class="cpld-card-value">{{ filteredTotalWickets }}</p>
            <p class="cpld-card-label">Total wickets</p>
          </div>
          <div class="cpld-card" :class="{ 'cpld-card--muted': !topTeamByWins }">
            <p class="cpld-card-value">{{ topTeamByWins ?? '—' }}</p>
            <p class="cpld-card-label">Top team (most wins)</p>
            <p v-if="!topTeamByWins" class="cpld-card-warn">Win data not available in current imports</p>
          </div>
        </div>
      </section>

      <!-- ── 2. Match Story Visuals ── -->
      <section ref="matchStoryRef" class="cpld-section" aria-label="Match story">
        <h4 class="cpld-section-title">📈 Match Story</h4>

        <!-- Match selector -->
        <div class="cpld-filter-group cpld-match-select">
          <label class="cpld-filter-label" for="cpld-match-select">Select match</label>
          <select id="cpld-match-select" v-model="selectedMatchId" class="cpld-select cpld-select--wide" aria-label="Select match for story view">
            <option value="">— select a match —</option>
            <option v-for="m in filteredMatches" :key="m.match_id" :value="m.match_id">
              {{ m.teams }} · {{ m.match_date ?? 'date unknown' }}{{ m.season ? ' · ' + m.season : '' }}
            </option>
          </select>
        </div>

        <div v-if="selectedMatch">
          <!-- Innings comparison -->
          <div class="cpld-match-header">
            <div class="cpld-match-teams">{{ selectedMatch.teams }}</div>
            <div class="cpld-match-meta">
              <span v-if="selectedMatch.venue">📍 {{ selectedMatch.venue }}</span>
              <span v-if="selectedMatch.match_date">📅 {{ selectedMatch.match_date }}</span>
              <span v-if="selectedMatch.match_type">🏏 {{ selectedMatch.match_type }}</span>
            </div>
            <div class="cpld-match-provenance">
              <span class="cpld-badge cpld-badge--imported">Imported</span>
              <span v-if="selectedMatch.source_filename" class="cpld-provenance-file">
                Source: {{ selectedMatch.source_filename }}
              </span>
            </div>
          </div>

          <!-- Innings totals -->
          <div v-if="selectedMatch.innings_totals.length > 0" class="cpld-innings-section">
            <h5 class="cpld-subsection-title">Innings Comparison</h5>
            <div class="cpld-innings-comparison">
              <div
                v-for="inn in selectedMatch.innings_totals"
                :key="inn.inning_no"
                class="cpld-innings-card"
              >
                <div class="cpld-innings-label">
                  Innings {{ inn.inning_no }}
                  <span v-if="inn.team" class="cpld-innings-team">· {{ inn.team }}</span>
                </div>
                <div class="cpld-innings-score">
                  <span class="cpld-innings-runs">{{ inn.runs }}/{{ inn.wickets }}</span>
                  <span class="cpld-innings-overs">({{ inn.overs }} ov)</span>
                </div>
                <!-- Simple run-rate bar -->
                <div class="cpld-rr-bar-wrap" aria-label="Run rate bar">
                  <div
                    class="cpld-rr-bar"
                    :style="{ width: Math.min((inn.runs / Math.max(maxInningsRuns, 1)) * 100, 100) + '%' }"
                    :title="`${inn.runs} runs`"
                  />
                </div>
                <div class="cpld-innings-rr">
                  RR: {{ inn.overs > 0 ? (inn.runs / inn.overs).toFixed(2) : '—' }}
                </div>
              </div>
            </div>
          </div>

          <!-- No innings data warning -->
          <div v-else class="cpld-insufficient">
            ⚠ No innings data available for this match.
            This match may be metadata-only or innings data was not imported.
          </div>

          <!-- Delivery data state -->
          <div v-if="!selectedMatch.has_delivery_data" class="cpld-insufficient cpld-insufficient--warn">
            ⚠ Ball-by-ball delivery data not imported for this match.
            Phase breakdown (powerplay/middle/death) requires delivery data import.
          </div>
          <div v-else class="cpld-delivery-note">
            ✓ Ball-by-ball delivery data available for this match.
          </div>
        </div>

        <!-- No match selected -->
        <div v-else class="cpld-state cpld-state--hint">
          Select a match above to view innings progression and story visuals.
        </div>
      </section>

      <!-- ── 3. Leaderboards ── -->
      <section ref="leaderboardRef" class="cpld-section" aria-label="Leaderboards">
        <h4 class="cpld-section-title">🏆 Leaderboards</h4>

        <div v-if="filteredPlayers.length > 0 || filteredTeamAggregates.length > 0" class="cpld-leaderboards">
          <!-- Top run scorers -->
          <div class="cpld-lb-panel">
            <h5 class="cpld-subsection-title">Top Run Scorers</h5>
            <p class="cpld-lb-note">From matches with delivery data only.</p>
            <div v-if="topRunScorers.length > 0" class="cpld-lb-table-wrap">
              <table class="cpld-lb-table" aria-label="Top run scorers">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Runs</th>
                    <th>Matches</th>
                    <th>SR</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(p, idx) in topRunScorers" :key="p.player_name">
                    <td class="cpld-lb-rank">{{ idx + 1 }}</td>
                    <td>{{ p.player_name }}</td>
                    <td class="cpld-lb-stat">{{ p.runs_scored }}</td>
                    <td class="cpld-lb-muted">{{ p.matches_contributed }}</td>
                    <td class="cpld-lb-muted">{{ p.strike_rate > 0 ? p.strike_rate.toFixed(1) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="cpld-insufficient">
              No batting data available. Delivery data required.
            </div>
          </div>

          <!-- Top wicket takers -->
          <div class="cpld-lb-panel">
            <h5 class="cpld-subsection-title">Top Wicket Takers</h5>
            <p class="cpld-lb-note">From matches with delivery data only.</p>
            <div v-if="topWicketTakers.length > 0" class="cpld-lb-table-wrap">
              <table class="cpld-lb-table" aria-label="Top wicket takers">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Wkts</th>
                    <th>Matches</th>
                    <th>Eco</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(p, idx) in topWicketTakers" :key="p.player_name">
                    <td class="cpld-lb-rank">{{ idx + 1 }}</td>
                    <td>{{ p.player_name }}</td>
                    <td class="cpld-lb-stat">{{ p.wickets }}</td>
                    <td class="cpld-lb-muted">{{ p.matches_contributed }}</td>
                    <td class="cpld-lb-muted">{{ p.economy_rate > 0 ? p.economy_rate.toFixed(2) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="cpld-insufficient">
              No bowling data available. Delivery data required.
            </div>
          </div>

          <!-- Team win/loss summary -->
          <div class="cpld-lb-panel">
            <h5 class="cpld-subsection-title">Team Averages</h5>
            <div v-if="filteredTeamAggregates.length > 0" class="cpld-lb-table-wrap">
              <table class="cpld-lb-table" aria-label="Team averages">
                <thead>
                  <tr>
                    <th>Team</th>
                    <th>Matches</th>
                    <th>Avg Score</th>
                    <th>Total Runs</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="t in filteredTeamAggregates" :key="t.team_name">
                    <td>{{ t.team_name }}</td>
                    <td class="cpld-lb-stat">{{ t.matches_played }}</td>
                    <td class="cpld-lb-muted">{{ t.avg_score > 0 ? t.avg_score.toFixed(1) : '—' }}</td>
                    <td class="cpld-lb-muted">{{ t.total_runs }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="cpld-insufficient">
              No team aggregate data available for current filters.
            </div>
          </div>
        </div>

        <!-- No player data -->
        <div v-else class="cpld-insufficient">
          ⚠ No leaderboard data available.
          Leaderboards are populated from matches with delivery data imported.
          Import delivery data via the Import tab.
        </div>
      </section>

      <!-- ── 4. Venue Intelligence ── -->
      <section ref="venueRef" class="cpld-section" aria-label="Venue intelligence">
        <h4 class="cpld-section-title">📍 Venue Intelligence</h4>

        <div v-if="cplVenues.length > 0" class="cpld-venue-grid">
          <div
            v-for="v in cplVenues"
            :key="v.venue"
            class="cpld-venue-card"
            :class="{ 'cpld-venue-card--selected': selectedVenue === v.venue }"
          >
            <div class="cpld-venue-name">{{ v.venue }}</div>
            <div class="cpld-venue-stats">
              <div class="cpld-venue-stat">
                <span class="cpld-venue-stat-val">{{ v.match_count }}</span>
                <span class="cpld-venue-stat-lbl">matches</span>
              </div>
              <div class="cpld-venue-stat">
                <span class="cpld-venue-stat-val">
                  {{ v.avg_first_innings_score > 0 ? v.avg_first_innings_score.toFixed(0) : '—' }}
                </span>
                <span class="cpld-venue-stat-lbl">avg 1st inn</span>
              </div>
              <div class="cpld-venue-stat">
                <span class="cpld-venue-stat-val">
                  {{ v.avg_total_runs > 0 ? v.avg_total_runs.toFixed(0) : '—' }}
                </span>
                <span class="cpld-venue-stat-lbl">avg total</span>
              </div>
            </div>
            <div v-if="v.avg_first_innings_score === 0" class="cpld-venue-warn">
              ⚠ Avg 1st innings score unavailable (no delivery data)
            </div>
          </div>
        </div>
        <div v-else class="cpld-insufficient">
          No venue data available for imported CPL matches.
        </div>
      </section>

      <!-- ── 5. Podcast Prep Panel ── -->
      <section ref="podcastFactsRef" class="cpld-section cpld-podcast-panel" aria-label="Podcast preparation">
        <h4 class="cpld-section-title">🎙 Podcast Prep Panel</h4>
        <p class="cpld-podcast-desc">
          Deterministic talking-point candidates grounded in imported match data.
          Review each fact carefully — these come from validated imports only.
          <strong>No AI-generated claims are included.</strong>
        </p>

        <div v-if="podcastFacts.length > 0" class="cpld-podcast-facts">
          <div
            v-for="(fact, idx) in podcastFacts"
            :key="idx"
            class="cpld-fact-card"
            :class="`cpld-fact-card--${fact.type}`"
          >
            <div class="cpld-fact-label">{{ fact.label }}</div>
            <div class="cpld-fact-value">{{ fact.value }}</div>
            <div v-if="fact.caveat" class="cpld-fact-caveat">⚠ {{ fact.caveat }}</div>
          </div>
        </div>
        <div v-else class="cpld-insufficient">
          No deterministic facts available with current filters.
          Select a season or match to generate talking-point candidates.
        </div>

        <!-- AI Talking-Point Assistant -->
        <div class="cpld-ai-panel" aria-label="AI Talking-Point Assistant">
          <div class="cpld-ai-panel-header">
            <span class="cpld-ai-panel-title">🤖 AI Talking-Point Assistant</span>
            <span class="cpld-badge cpld-badge--review">Reviewer-gated · Draft only</span>
          </div>
          <p class="cpld-ai-disclaimer">
            AI drafts are generated <strong>only from the deterministic facts shown below</strong>.
            AI will not calculate official scores, invent statistics, or publish without your review.
            All talking points start as <em>needs review</em> — you must approve before use.
          </p>

          <!-- Fact bundle preview -->
          <div class="cpld-ai-bundle" aria-label="Fact bundle preview">
            <p class="cpld-ai-bundle-label">
              Fact bundle ({{ podcastFacts.length }} fact{{ podcastFacts.length === 1 ? '' : 's' }} will be sent to AI)
            </p>
            <div v-if="podcastFacts.length > 0" class="cpld-ai-bundle-list">
              <span
                v-for="(fact, i) in podcastFacts"
                :key="i"
                class="cpld-ai-bundle-tag"
                :title="fact.value"
              >{{ fact.label }}</span>
            </div>
            <p v-else class="cpld-ai-bundle-empty">
              No deterministic facts available — select a season or match to populate the fact bundle before generating.
            </p>
          </div>

          <!-- Insufficient-data block -->
          <div v-if="podcastFacts.length > 0 && podcastFacts.length < 2" class="cpld-ai-insufficient">
            ⚠ At least 2 deterministic facts are required to generate talking points. Add more filter context.
          </div>

          <!-- Generate button -->
          <div class="cpld-ai-generate-row">
            <button
              class="cpld-ai-generate-btn"
              :disabled="podcastFacts.length < 2 || aiGenerating"
              :aria-disabled="podcastFacts.length < 2 || aiGenerating"
              aria-label="Generate AI talking points"
              @click="generateAiTalkingPoints"
            >
              <span v-if="aiGenerating">Generating…</span>
              <span v-else>Generate Talking Points</span>
            </button>
            <button
              v-if="aiResult"
              class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
              aria-label="Clear AI talking points"
              @click="clearAiResult"
            >
              Clear
            </button>
          </div>

          <!-- AI error -->
          <p v-if="aiError" class="cpld-ai-error" role="alert">{{ aiError }}</p>

          <!-- Generated talking points -->
          <div v-if="aiResult" class="cpld-ai-result" aria-label="Generated talking points">
            <div class="cpld-ai-result-meta">
              <span>Generated {{ aiResult.generatedAt }}</span>
              <span class="cpld-badge cpld-badge--needs-review">All points need review</span>
            </div>

            <!-- Limitations -->
            <div v-if="aiResult.limitations.length > 0" class="cpld-ai-limitations" aria-label="AI limitations">
              <p class="cpld-ai-limitations-label">⚠ Limitations</p>
              <ul class="cpld-ai-limitations-list">
                <li v-for="(lim, li) in aiResult.limitations" :key="li">{{ lim }}</li>
              </ul>
            </div>

            <!-- Talking point cards -->
            <div
              v-for="(tp, tpIdx) in aiResult.talkingPoints"
              :key="tp.id"
              class="cpld-tp-card"
              :class="`cpld-tp-card--${tp.status}`"
              :aria-label="`Talking point: ${tp.title}`"
            >
              <!-- Status badge + section label -->
              <div class="cpld-tp-card-top">
                <span class="cpld-tp-section">{{ tp.section }}</span>
                <span
                  class="cpld-badge"
                  :class="{
                    'cpld-badge--needs-review': tp.status === 'needs_review',
                    'cpld-badge--approved': tp.status === 'approved',
                    'cpld-badge--rejected': tp.status === 'rejected',
                  }"
                  :aria-label="`Status: ${tp.status}`"
                >{{ tp.status === 'needs_review' ? 'Needs review' : tp.status === 'approved' ? 'Approved' : 'Rejected' }}</span>
                <span class="cpld-tp-confidence" :title="`Confidence: ${tp.confidence}`">
                  {{ tp.confidence === 'high' ? '🟢' : tp.confidence === 'medium' ? '🟡' : '🔴' }} {{ tp.confidence }}
                </span>
              </div>

              <!-- Title -->
              <p class="cpld-tp-title">{{ tp.title }}</p>

              <!-- Text (show edited version if available) -->
              <div v-if="aiTpEditing[tpIdx]" class="cpld-tp-edit-wrap">
                <textarea
                  class="cpld-tp-edit-area"
                  :value="aiTpEdits[tpIdx] ?? tp.text"
                  :aria-label="`Edit talking point ${tpIdx + 1}`"
                  rows="4"
                  @input="e => { aiTpEdits[tpIdx] = (e.target as HTMLTextAreaElement).value }"
                />
                <div class="cpld-tp-edit-actions">
                  <button class="cpld-tp-btn cpld-tp-btn--save" @click="saveEditTp(tpIdx)">Save edit</button>
                  <button class="cpld-tp-btn cpld-tp-btn--cancel" @click="cancelEditTp(tpIdx)">Cancel</button>
                </div>
              </div>
              <p v-else class="cpld-tp-text">{{ aiTpEdits[tpIdx] ?? tp.text }}</p>

              <!-- Source facts -->
              <div class="cpld-tp-sources">
                <span class="cpld-tp-sources-label">Sources:</span>
                <span
                  v-for="(sid, si) in tp.sourceFactIds"
                  :key="si"
                  class="cpld-tp-source-tag"
                >{{ sid }}</span>
              </div>

              <!-- Review controls -->
              <div class="cpld-tp-actions" v-if="tp.status !== 'rejected'">
                <button
                  v-if="tp.status !== 'approved'"
                  class="cpld-tp-btn cpld-tp-btn--approve"
                  :aria-label="`Approve talking point ${tpIdx + 1}`"
                  @click="approveTp(tpIdx)"
                >✓ Approve</button>
                <button
                  v-if="tp.status === 'approved'"
                  class="cpld-tp-btn cpld-tp-btn--unapprove"
                  :aria-label="`Unapprove talking point ${tpIdx + 1}`"
                  @click="unapproveTp(tpIdx)"
                >↩ Unapprove</button>
                <button
                  class="cpld-tp-btn cpld-tp-btn--edit"
                  :aria-label="`Edit talking point ${tpIdx + 1}`"
                  @click="startEditTp(tpIdx)"
                >✎ Edit</button>
                <button
                  class="cpld-tp-btn cpld-tp-btn--copy"
                  :aria-label="`Copy talking point ${tpIdx + 1}`"
                  :title="tp.status !== 'approved' ? 'Review this point before copying' : 'Copy approved talking point'"
                  @click="copyTp(tpIdx)"
                >
                  {{ tp.status === 'approved' ? '📋 Copy (Reviewed)' : '📋 Copy (Unreviewed)' }}
                </button>
                <button
                  class="cpld-tp-btn cpld-tp-btn--reject"
                  :aria-label="`Reject talking point ${tpIdx + 1}`"
                  @click="rejectTp(tpIdx)"
                >✕ Reject</button>
              </div>
              <div v-else class="cpld-tp-rejected-note">
                Rejected — this talking point has been dismissed.
                <button class="cpld-tp-btn cpld-tp-btn--unapprove" @click="unapproveTp(tpIdx)">↩ Restore</button>
              </div>
            </div>

            <!-- Summary: how many approved -->
            <div class="cpld-ai-review-summary" aria-label="Review summary">
              {{ approvedCount }} of {{ aiResult.talkingPoints.length }} talking point{{ aiResult.talkingPoints.length === 1 ? '' : 's' }} approved.
              <span v-if="approvedCount === 0" class="cpld-ai-review-note">Review and approve before using any content.</span>
              <span v-else-if="approvedCount < aiResult.talkingPoints.length" class="cpld-ai-review-note">Some points still need review.</span>
              <span v-else class="cpld-ai-review-note cpld-ai-review-note--ok">All points reviewed.</span>
            </div>
          </div>
        </div>

        <div class="cpld-script-panel" aria-label="Advanced Podcast Script Builder">
          <div class="cpld-script-panel-header">
            <span class="cpld-script-panel-title">📝 Advanced Podcast Script Builder</span>
            <span class="cpld-badge cpld-badge--review">Deterministic · Analyst editable</span>
          </div>
          <p class="cpld-script-desc">
            Build a podcast prep script from deterministic facts, selected CPL context, reviewed talking points, and export metadata.
            Unreviewed talking points are excluded from final copy/export by default.
          </p>

          <div v-if="!canGeneratePodcastScript" class="cpld-ai-insufficient" role="alert">
            {{ podcastScriptDisabledReason }}
          </div>

          <div v-else class="cpld-script-actions">
            <button
              class="cpld-ai-generate-btn"
              aria-label="Generate podcast script"
              @click="generatePodcastScript"
            >
              Generate script draft
            </button>
            <button
              class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
              aria-label="Copy script as markdown"
              :disabled="!podcastScriptDraft"
              @click="copyPodcastScriptMarkdown"
            >
              Copy Markdown
            </button>
            <button
              class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
              aria-label="Copy script as plain text"
              :disabled="!podcastScriptDraft"
              @click="copyPodcastScriptPlainText"
            >
              Copy Plain Text
            </button>
            <button
              class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
              aria-label="Download script markdown"
              :disabled="!podcastScriptDraft"
              @click="downloadPodcastScriptMarkdown"
            >
              Download .md
            </button>
          </div>

          <div v-if="needsReviewTalkingPoints.length > 0" class="cpld-script-needs-review" aria-label="Talking points needing review">
            <p class="cpld-script-needs-review-label">Needs review (excluded from final script by default):</p>
            <ul class="cpld-script-needs-review-list">
              <li v-for="tp in needsReviewTalkingPoints" :key="tp.id">{{ tp.title }}</li>
            </ul>
          </div>

          <div v-if="podcastScriptDraft" class="cpld-script-editor">
            <label class="cpld-filter-label" for="cpld-script-editor">Podcast script draft (editable before export)</label>
            <textarea
              id="cpld-script-editor"
              v-model="podcastScriptDraft"
              class="cpld-script-textarea"
              rows="22"
              aria-label="Podcast script draft editor"
            />
          </div>

          <div class="cpld-episode-archive" aria-label="Podcast episode archive">
            <div class="cpld-script-panel-header">
              <span class="cpld-script-panel-title">🗂 Podcast Episode Archive</span>
              <span class="cpld-badge cpld-badge--review">Local only · deterministic package</span>
            </div>
            <p class="cpld-script-desc">
              Save and reopen episode prep packages from the current deterministic dashboard, talking-point review state, script draft, and export metadata.
            </p>

            <div class="cpld-archive-form">
              <div class="cpld-filter-group">
                <label class="cpld-filter-label" for="cpld-episode-title">Working title</label>
                <input
                  id="cpld-episode-title"
                  v-model="episodeWorkingTitle"
                  class="cpld-select cpld-archive-input"
                  aria-label="Episode working title input"
                  placeholder="Episode working title"
                  type="text"
                />
              </div>
              <div class="cpld-filter-group">
                <label class="cpld-filter-label" for="cpld-episode-objective">Episode objective</label>
                <textarea
                  id="cpld-episode-objective"
                  v-model="episodeObjective"
                  class="cpld-script-textarea cpld-archive-objective"
                  rows="3"
                  aria-label="Episode objective input"
                  placeholder="What should this episode deliver for analysts/listeners?"
                />
              </div>
              <div class="cpld-filter-group">
                <label class="cpld-filter-label" for="cpld-episode-status">Package status</label>
                <select
                  id="cpld-episode-status"
                  v-model="episodePackageStatus"
                  class="cpld-select"
                  aria-label="Episode package status"
                >
                  <option
                    v-for="statusOption in episodeStatusOptions"
                    :key="statusOption.value"
                    :value="statusOption.value"
                  >
                    {{ statusOption.label }}
                  </option>
                </select>
              </div>
            </div>

            <p v-if="!canCreateEpisodePackage" class="cpld-ai-insufficient" role="alert">
              {{ episodePackageDisabledReason }}
            </p>
            <p v-else-if="packageWillBeIncomplete" class="cpld-archive-note">
              No approved talking points yet — this package will be saved as facts-only/incomplete.
            </p>

            <div class="cpld-script-actions">
              <button
                class="cpld-ai-generate-btn"
                :disabled="!canCreateEpisodePackage"
                aria-label="Save episode package"
                @click="saveEpisodePackage"
              >
                {{ activeEpisodePackageId ? 'Update episode package' : 'Save episode package' }}
              </button>
            </div>

            <p v-if="episodeArchiveError" class="cpld-export-error" role="alert">⚠ {{ episodeArchiveError }}</p>

            <div v-if="sortedEpisodePackages.length === 0" class="cpld-state cpld-state--hint">
              No saved episode packages yet. Generate a script draft and save a package for reuse.
            </div>
            <ul v-else class="cpld-archive-list" aria-label="Episode package list">
              <li
                v-for="pkg in sortedEpisodePackages"
                :key="pkg.id"
                class="cpld-archive-item"
                :aria-label="`Episode package ${pkg.working_title}`"
              >
                <div class="cpld-archive-item-top">
                  <strong>{{ pkg.working_title }}</strong>
                  <span class="cpld-badge cpld-badge--approved">{{ episodeStatusLabel(pkg.status) }}</span>
                </div>
                <p class="cpld-archive-meta">
                  Updated: {{ formatArchiveTimestamp(pkg.updated_at) }} · Created: {{ formatArchiveTimestamp(pkg.created_at) }}
                </p>
                <p class="cpld-archive-meta">
                  Season: {{ pkg.context.filters.season }} · Match: {{ pkg.context.selected_match_label }} · Facts: {{ pkg.deterministic_facts.length }}
                </p>
                <p v-if="pkg.is_incomplete" class="cpld-archive-meta cpld-archive-meta--warn">
                  Incomplete: no approved talking points were saved in this package.
                </p>
                <div class="cpld-script-actions">
                  <button
                    class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
                    :aria-label="`Reopen episode package ${pkg.id}`"
                    @click="reopenEpisodePackage(pkg.id)"
                  >
                    Reopen
                  </button>
                  <button
                    class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
                    :aria-label="`Export package markdown ${pkg.id}`"
                    @click="downloadEpisodePackageMarkdown(pkg)"
                  >
                    Export .md
                  </button>
                  <button
                    class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
                    :aria-label="`Export package json ${pkg.id}`"
                    @click="downloadEpisodePackageJson(pkg)"
                  >
                    Export .json
                  </button>
                  <button
                    class="cpld-ai-generate-btn cpld-ai-generate-btn--secondary"
                    :aria-label="`Delete episode package ${pkg.id}`"
                    @click="deleteEpisodePackage(pkg.id)"
                  >
                    Delete
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { toPng } from 'html-to-image'
import {
  getHistoricalStatsSummary,
  type HistoricalStatsSummaryResponse,
  type HistoricalMatchAggregate,
  type HistoricalPlayerAggregate,
  type HistoricalTeamAggregate,
  type HistoricalVenueAggregate,
} from '@/services/api'
import {
  cplVisualTemplates,
  templateFamilyByTarget,
  templateFormatSpacing,
  templateVariantLabels,
  type CplTemplateFamily,
  type ExportFormat,
  type ExportTarget,
} from '@/components/cplVisualTemplates'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const loading = ref(false)
const error = ref<string | null>(null)
const summary = ref<HistoricalStatsSummaryResponse | null>(null)

const selectedSeason = ref('all')
const selectedTeam = ref('all')
const selectedVenue = ref('all')
const selectedMatchId = ref('')

const seasonSummaryRef = ref<HTMLElement | null>(null)
const matchStoryRef = ref<HTMLElement | null>(null)
const leaderboardRef = ref<HTMLElement | null>(null)
const venueRef = ref<HTMLElement | null>(null)
const podcastFactsRef = ref<HTMLElement | null>(null)

const exportTarget = ref<ExportTarget>('season_summary')
const exportFormat = ref<ExportFormat>('podcast_landscape')
const exportTemplateId = ref('season-clean-broadcast')
const exportIncludePoweredBy = ref(true)
const exportIncludeImportedLabel = ref(true)
const exportIncludeContextLabel = ref(true)
const exportPreviewUrl = ref<string | null>(null)
const exportError = ref<string | null>(null)
const exportBusy = ref(false)

const exportTargets = [
  { value: 'season_summary', label: 'Season summary cards' },
  { value: 'match_story', label: 'Selected match story panel' },
  { value: 'leaderboards', label: 'Leaderboard panel' },
  { value: 'venue_intelligence', label: 'Venue intelligence panel' },
  { value: 'podcast_facts', label: 'Podcast prep facts panel' },
] as const satisfies ReadonlyArray<{ value: ExportTarget; label: string }>

const exportFormats = [
  { value: 'podcast_landscape', label: 'Podcast landscape (1920×1080)', width: 1920, height: 1080 },
  { value: 'social_square', label: 'Social square (1080×1080)', width: 1080, height: 1080 },
  { value: 'story_vertical', label: 'Story/reel vertical (1080×1920)', width: 1080, height: 1920 },
] as const satisfies ReadonlyArray<{ value: ExportFormat; label: string; width: number; height: number }>

// ---------------------------------------------------------------------------
// CPL detection helper
// ---------------------------------------------------------------------------

/** Return true if the competition name indicates Caribbean Premier League. */
function isCplCompetition(name: string | null | undefined): boolean {
  if (!name) return false
  const n = name.trim().toLowerCase()
  return n.includes('caribbean premier league') || /\bcpl\b/.test(n)
}

// ---------------------------------------------------------------------------
// Derived CPL data
// ---------------------------------------------------------------------------

/** All matches belonging to CPL competitions. */
const cplMatches = computed<HistoricalMatchAggregate[]>(() => {
  if (!summary.value) return []
  return summary.value.matches.filter(m => isCplCompetition(m.competition))
})

/** All player aggregates from CPL matches (by match_id intersection). */
const cplMatchIds = computed(() => new Set(cplMatches.value.map(m => m.match_id)))

/** All CPL player aggregates — sourced from matches with delivery data. */
const cplPlayers = computed<HistoricalPlayerAggregate[]>(() => {
  if (!summary.value) return []
  // The summary players list is across all historical imports.
  // We filter to players from CPL matches that have delivery data.
  const cplMatchesWithDeliveries = cplMatches.value
    .filter(m => m.has_delivery_data)
    .map(m => [m.team_a, m.team_b].filter(Boolean))
  if (cplMatchesWithDeliveries.length === 0) return []
  // Since player aggregates are global (not per-match), we return all players
  // when CPL matches with delivery data exist. A future improvement would
  // scope players to CPL specifically.
  return summary.value.players
})

/** CPL team aggregates, keyed by team names found in CPL matches. */
const cplTeamNames = computed(() => {
  const names = new Set<string>()
  cplMatches.value.forEach(m => {
    if (m.team_a) names.add(m.team_a)
    if (m.team_b) names.add(m.team_b)
  })
  return names
})

const cplTeamAggregates = computed<HistoricalTeamAggregate[]>(() => {
  if (!summary.value) return []
  return summary.value.teams.filter(t => cplTeamNames.value.has(t.team_name))
})

const cplVenueNames = computed(() => {
  const names = new Set<string>()
  cplMatches.value.forEach(m => { if (m.venue) names.add(m.venue) })
  return names
})

const cplVenues = computed<HistoricalVenueAggregate[]>(() => {
  if (!summary.value) return []
  return summary.value.venues.filter(v => cplVenueNames.value.has(v.venue))
})

// ---------------------------------------------------------------------------
// Filter options
// ---------------------------------------------------------------------------

const availableSeasons = computed(() => {
  const seasons = new Set<string>()
  cplMatches.value.forEach(m => { if (m.season) seasons.add(m.season) })
  return [...seasons].sort().reverse()
})

const availableTeams = computed(() => [...cplTeamNames.value].sort())
const availableVenues = computed(() => [...cplVenueNames.value].sort())

// ---------------------------------------------------------------------------
// Filtered data
// ---------------------------------------------------------------------------

const filteredMatches = computed(() => {
  return cplMatches.value.filter(m => {
    if (selectedSeason.value !== 'all' && m.season !== selectedSeason.value) return false
    if (selectedTeam.value !== 'all' && m.team_a !== selectedTeam.value && m.team_b !== selectedTeam.value) return false
    if (selectedVenue.value !== 'all' && m.venue !== selectedVenue.value) return false
    return true
  })
})

const filteredTeamNames = computed(() => {
  const names = new Set<string>()
  filteredMatches.value.forEach(m => {
    if (m.team_a) names.add(m.team_a)
    if (m.team_b) names.add(m.team_b)
  })
  return names
})

const filteredVenueNames = computed(() => {
  const names = new Set<string>()
  filteredMatches.value.forEach(m => { if (m.venue) names.add(m.venue) })
  return names
})

const filteredTotalRuns = computed(() =>
  filteredMatches.value.reduce((sum, m) => sum + m.total_runs, 0)
)
const filteredTotalWickets = computed(() =>
  filteredMatches.value.reduce((sum, m) => sum + m.total_wickets, 0)
)

/** Simple heuristic: team appearing in most matches with the most total wins.
 * Since win/loss data is not available in the summary schema, return null. */
const topTeamByWins = computed<string | null>(() => null)

const filteredPlayers = computed(() => {
  // When filters narrow to specific team, only include that team's players.
  // Without per-match player attribution, we show all CPL players when at
  // least one CPL match with delivery data exists in the filtered set.
  const hasDeliveryData = filteredMatches.value.some(m => m.has_delivery_data)
  if (!hasDeliveryData) return []
  return cplPlayers.value
})

const filteredTeamAggregates = computed<HistoricalTeamAggregate[]>(() => {
  if (selectedTeam.value !== 'all') {
    return cplTeamAggregates.value.filter(t => t.team_name === selectedTeam.value)
  }
  // Filter by teams present in filtered matches
  return cplTeamAggregates.value.filter(t => filteredTeamNames.value.has(t.team_name))
})

// ---------------------------------------------------------------------------
// Selected match
// ---------------------------------------------------------------------------

const selectedMatch = computed<HistoricalMatchAggregate | null>(() =>
  filteredMatches.value.find(m => m.match_id === selectedMatchId.value) ?? null
)

const maxInningsRuns = computed(() => {
  if (!selectedMatch.value) return 1
  return Math.max(...selectedMatch.value.innings_totals.map(i => i.runs), 1)
})

// ---------------------------------------------------------------------------
// Leaderboards
// ---------------------------------------------------------------------------

const topRunScorers = computed(() =>
  [...filteredPlayers.value]
    .filter(p => p.runs_scored > 0)
    .sort((a, b) => b.runs_scored - a.runs_scored)
    .slice(0, 10)
)

const topWicketTakers = computed(() =>
  [...filteredPlayers.value]
    .filter(p => p.wickets > 0)
    .sort((a, b) => b.wickets - a.wickets)
    .slice(0, 10)
)

// ---------------------------------------------------------------------------
// Podcast prep facts
// ---------------------------------------------------------------------------

interface PodcastFact {
  label: string
  value: string
  type: 'season' | 'match' | 'venue' | 'player' | 'team'
  caveat?: string
}

const podcastFacts = computed<PodcastFact[]>(() => {
  const facts: PodcastFact[] = []

  // Season-level facts
  if (filteredMatches.value.length > 0) {
    const seasonLabel = selectedSeason.value !== 'all' ? selectedSeason.value : 'all seasons'
    facts.push({
      label: 'Matches imported',
      value: `${filteredMatches.value.length} CPL match${filteredMatches.value.length === 1 ? '' : 'es'} (${seasonLabel})`,
      type: 'season',
    })
    facts.push({
      label: 'Total runs in dataset',
      value: filteredTotalRuns.value.toLocaleString(),
      type: 'season',
      caveat: filteredMatches.value.some(m => !m.has_delivery_data)
        ? 'Some matches lack delivery data; runs from innings totals only'
        : undefined,
    })
    facts.push({
      label: 'Total wickets in dataset',
      value: String(filteredTotalWickets.value),
      type: 'season',
    })
    facts.push({
      label: 'Teams represented',
      value: [...filteredTeamNames.value].join(', ') || '—',
      type: 'team',
    })
    facts.push({
      label: 'Venues represented',
      value: [...filteredVenueNames.value].join(', ') || '—',
      type: 'venue',
    })
  }

  // Top scorer fact
  if (topRunScorers.value.length > 0) {
    const top = topRunScorers.value[0]
    facts.push({
      label: 'Top run scorer',
      value: `${top.player_name} — ${top.runs_scored} runs in ${top.matches_contributed} match${top.matches_contributed === 1 ? '' : 'es'}`,
      type: 'player',
      caveat: 'From matches with delivery data only',
    })
  }

  // Top wicket taker fact
  if (topWicketTakers.value.length > 0) {
    const top = topWicketTakers.value[0]
    facts.push({
      label: 'Top wicket taker',
      value: `${top.player_name} — ${top.wickets} wicket${top.wickets === 1 ? '' : 's'} in ${top.matches_contributed} match${top.matches_contributed === 1 ? '' : 'es'}`,
      type: 'player',
      caveat: 'From matches with delivery data only',
    })
  }

  // Selected match facts
  if (selectedMatch.value) {
    const m = selectedMatch.value
    facts.push({
      label: 'Selected match',
      value: `${m.teams}${m.match_date ? ' · ' + m.match_date : ''}${m.venue ? ' at ' + m.venue : ''}`,
      type: 'match',
    })
    if (m.innings_totals.length >= 2) {
      const inn1 = m.innings_totals[0]
      const inn2 = m.innings_totals[1]
      facts.push({
        label: 'Match scores',
        value: `${inn1.team ?? 'Team 1'}: ${inn1.runs}/${inn1.wickets} vs ${inn2.team ?? 'Team 2'}: ${inn2.runs}/${inn2.wickets}`,
        type: 'match',
      })
    } else if (m.innings_totals.length === 1) {
      const inn1 = m.innings_totals[0]
      facts.push({
        label: '1st innings score',
        value: `${inn1.team ?? 'Team 1'}: ${inn1.runs}/${inn1.wickets} (${inn1.overs} ov)`,
        type: 'match',
        caveat: 'Only one innings imported',
      })
    }
    if (!m.has_delivery_data) {
      facts.push({
        label: 'Delivery data',
        value: 'Not imported',
        type: 'match',
        caveat: 'Ball-by-ball phase breakdown unavailable for this match',
      })
    }
  }

  // Venue facts
  if (cplVenues.value.length > 0 && selectedVenue.value !== 'all') {
    const v = cplVenues.value.find(x => x.venue === selectedVenue.value)
    if (v) {
      facts.push({
        label: 'Venue avg first innings',
        value: v.avg_first_innings_score > 0
          ? `${v.avg_first_innings_score.toFixed(0)} (${v.match_count} match${v.match_count === 1 ? '' : 'es'})`
          : 'Not available',
        type: 'venue',
        caveat: v.avg_first_innings_score === 0 ? 'Delivery data required for avg score' : undefined,
      })
    }
  }

  return facts
})

const activeExportTarget = computed(() =>
  exportTargets.find(t => t.value === exportTarget.value) ?? null
)

const activeExportFormat = computed(() =>
  exportFormats.find(f => f.value === exportFormat.value) ?? null
)

const activeTemplateFamily = computed<CplTemplateFamily>(() => templateFamilyByTarget[exportTarget.value])

const availableExportTemplates = computed(() =>
  cplVisualTemplates.filter(template => template.family === activeTemplateFamily.value)
)

const activeExportTemplate = computed(() => {
  const fromSelection = availableExportTemplates.value.find(template => template.id === exportTemplateId.value)
  return fromSelection ?? availableExportTemplates.value[0] ?? null
})

const activeExportTemplateFamilyLabel = computed(() => {
  if (!activeExportTemplate.value) return 'Unavailable'
  switch (activeExportTemplate.value.family) {
    case 'match_story':
      return 'Match Story Template'
    case 'season_summary':
      return 'Season Summary Template'
    case 'leaderboard':
      return 'Leaderboard Template'
    case 'venue_intelligence':
      return 'Venue Intelligence Template'
    case 'podcast_episode_card':
      return 'Podcast Episode Card Template'
    default:
      return 'Template'
  }
})

const activeExportTemplateVariantLabel = computed(() =>
  activeExportTemplate.value ? templateVariantLabels[activeExportTemplate.value.variant] : 'Unavailable'
)

const activeExportNode = computed<HTMLElement | null>(() => {
  switch (exportTarget.value) {
    case 'season_summary':
      return seasonSummaryRef.value
    case 'match_story':
      return matchStoryRef.value
    case 'leaderboards':
      return leaderboardRef.value
    case 'venue_intelligence':
      return venueRef.value
    case 'podcast_facts':
      return podcastFactsRef.value
    default:
      return null
  }
})

const activeExportAvailability = computed<{ available: boolean; reason: string }>(() => {
  if (cplMatches.value.length === 0) {
    return { available: false, reason: 'Export disabled: no CPL data is available.' }
  }
  if (!activeExportNode.value) {
    return { available: false, reason: 'Export target is not available in this view yet.' }
  }
  if (!activeExportTemplate.value) {
    return { available: false, reason: 'Export disabled: no visual template is available for this target.' }
  }

  switch (exportTarget.value) {
    case 'season_summary':
      if (filteredMatches.value.length === 0) {
        return { available: false, reason: 'Export disabled: no filtered season summary data is available.' }
      }
      return { available: true, reason: '' }
    case 'match_story':
      if (!selectedMatch.value) {
        return { available: false, reason: 'Export disabled: select a match before exporting match story.' }
      }
      if (!selectedMatch.value.has_delivery_data) {
        return {
          available: false,
          reason: 'Export disabled: selected match has no delivery data. Import deliveries before exporting advanced match story visuals.',
        }
      }
      return { available: true, reason: '' }
    case 'leaderboards':
      if (topRunScorers.value.length === 0 && topWicketTakers.value.length === 0) {
        return {
          available: false,
          reason: 'Export disabled: leaderboard data is unavailable (delivery data required).',
        }
      }
      return { available: true, reason: '' }
    case 'venue_intelligence':
      if (cplVenues.value.length === 0) {
        return { available: false, reason: 'Export disabled: venue intelligence data is unavailable.' }
      }
      return { available: true, reason: '' }
    case 'podcast_facts':
      if (podcastFacts.value.length === 0) {
        return { available: false, reason: 'Export disabled: no deterministic podcast prep facts for current filters.' }
      }
      return { available: true, reason: '' }
    default:
      return { available: false, reason: 'Export target not recognized.' }
  }
})

const templateRequirementAvailability = computed<{ available: boolean; reason: string }>(() => {
  const template = activeExportTemplate.value
  if (!template) {
    return { available: false, reason: 'Template unavailable.' }
  }
  for (const requirement of template.requirements) {
    switch (requirement) {
      case 'match_selected':
        if (!selectedMatch.value) {
          return { available: false, reason: 'Template requires a selected match story before export.' }
        }
        break
      case 'match_delivery_data':
        if (!selectedMatch.value?.has_delivery_data) {
          return { available: false, reason: 'Template requires selected match delivery data.' }
        }
        break
      case 'leaderboard_data':
        if (topRunScorers.value.length === 0 && topWicketTakers.value.length === 0) {
          return { available: false, reason: 'Template requires leaderboard data from delivery imports.' }
        }
        break
      case 'venue_data':
        if (cplVenues.value.length === 0) {
          return { available: false, reason: 'Template requires venue intelligence data.' }
        }
        break
      case 'podcast_facts_data':
        if (podcastFacts.value.length === 0) {
          return { available: false, reason: 'Template requires deterministic podcast fact data.' }
        }
        break
      default:
        return { available: false, reason: 'Template requirement is not supported.' }
    }
  }
  return { available: true, reason: '' }
})

const exportReviewLabel = computed(() => {
  const parts: string[] = []
  if (exportIncludePoweredBy.value) parts.push('Powered by Cricksy')
  if (exportIncludeImportedLabel.value) parts.push('Imported CPL historical data')
  if (exportIncludeContextLabel.value) {
    const contextParts = [
      selectedSeason.value !== 'all' ? `Season: ${selectedSeason.value}` : null,
      selectedVenue.value !== 'all' ? `Venue: ${selectedVenue.value}` : null,
      selectedMatch.value?.teams ? `Match: ${selectedMatch.value.teams}` : null,
    ].filter(Boolean)
    if (contextParts.length > 0) {
      parts.push(contextParts.join(' · '))
    }
  }
  parts.push(`Generated: ${new Date().toISOString()}`)
  return parts.join(' · ')
})

watch(exportTarget, () => {
  const nextTemplate = availableExportTemplates.value[0]
  if (nextTemplate) {
    exportTemplateId.value = nextTemplate.id
  }
})

watch(
  [
    exportTarget,
    exportFormat,
    exportTemplateId,
    exportIncludePoweredBy,
    exportIncludeImportedLabel,
    exportIncludeContextLabel,
    selectedSeason,
    selectedVenue,
    selectedMatchId,
    selectedTeam,
  ],
  () => {
    exportPreviewUrl.value = null
    exportError.value = null
  }
)

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function resetFilters() {
  selectedSeason.value = 'all'
  selectedTeam.value = 'all'
  selectedVenue.value = 'all'
  selectedMatchId.value = ''
}

async function load() {
  loading.value = true
  error.value = null
  try {
    summary.value = await getHistoricalStatsSummary()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function buildExportFrame(targetNode: HTMLElement, width: number, height: number): HTMLDivElement {
  const activeTemplate = activeExportTemplate.value
  const spacing = templateFormatSpacing(exportFormat.value)
  const variant = activeTemplate?.variant ?? 'clean_broadcast'
  const wrapper = document.createElement('div')
  wrapper.style.position = 'fixed'
  wrapper.style.left = '-99999px'
  wrapper.style.top = '0'
  wrapper.style.width = `${width}px`
  wrapper.style.height = `${height}px`
  wrapper.style.background = variant === 'bold_social' ? '#0f172a' : '#ffffff'
  wrapper.style.padding = spacing.wrapperPadding
  wrapper.style.display = 'flex'
  wrapper.style.flexDirection = 'column'
  wrapper.style.gap = '14px'
  wrapper.style.boxSizing = 'border-box'
  wrapper.style.fontFamily = 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif'
  wrapper.style.color = variant === 'bold_social' ? '#f8fafc' : '#0f172a'

  const header = document.createElement('div')
  header.style.display = 'flex'
  header.style.justifyContent = 'space-between'
  header.style.alignItems = 'center'
  header.style.gap = '12px'

  const title = document.createElement('div')
  title.style.fontSize = spacing.titleSize
  title.style.fontWeight = variant === 'minimal_stat_card' ? '600' : '700'
  title.style.color = variant === 'bold_social' ? '#f8fafc' : '#0f172a'
  title.textContent = activeExportTarget.value?.label ?? 'CPL export'

  const brand = document.createElement('div')
  brand.style.fontSize = '14px'
  brand.style.fontWeight = '600'
  brand.style.padding = '4px 10px'
  brand.style.borderRadius = '999px'
  brand.style.border = variant === 'bold_social' ? '1px solid #38bdf8' : '1px solid #cbd5e1'
  brand.style.background = variant === 'bold_social' ? 'rgba(14, 165, 233, 0.18)' : '#f8fafc'
  brand.style.color = variant === 'bold_social' ? '#7dd3fc' : '#0f172a'
  brand.textContent = 'Cricksy · CPL Visuals'

  header.append(title, brand)

  const content = document.createElement('div')
  content.style.flex = '1'
  content.style.overflow = 'hidden'
  content.style.border = variant === 'bold_social' ? '1px solid #334155' : '1px solid #e2e8f0'
  content.style.borderRadius = '8px'
  content.style.padding = spacing.contentPadding
  content.style.boxSizing = 'border-box'
  content.style.background = variant === 'bold_social' ? '#0b1220' : '#ffffff'

  const clone = targetNode.cloneNode(true) as HTMLElement
  clone.style.margin = '0'
  clone.style.maxHeight = '100%'
  clone.style.overflow = 'hidden'
  if (variant === 'minimal_stat_card') {
    clone.style.transform = 'scale(0.96)'
    clone.style.transformOrigin = 'top left'
    clone.style.width = '104%'
  }
  content.appendChild(clone)

  if (exportIncludePoweredBy.value && activeTemplate?.watermarkPlacement === 'overlay') {
    const overlayWatermark = document.createElement('div')
    overlayWatermark.style.position = 'absolute'
    overlayWatermark.style.right = spacing.wrapperPadding
    overlayWatermark.style.bottom = spacing.wrapperPadding
    overlayWatermark.style.fontSize = '13px'
    overlayWatermark.style.fontWeight = '600'
    overlayWatermark.style.opacity = '0.7'
    overlayWatermark.style.color = variant === 'bold_social' ? '#bae6fd' : '#334155'
    overlayWatermark.textContent = 'Powered by Cricksy'
    wrapper.appendChild(overlayWatermark)
  }

  const footer = document.createElement('div')
  footer.style.display = 'flex'
  footer.style.justifyContent = 'space-between'
  footer.style.alignItems = 'flex-end'
  footer.style.gap = '8px'
  footer.style.flexWrap = 'wrap'

  const provenance = document.createElement('div')
  provenance.style.fontSize = spacing.footerSize
  provenance.style.lineHeight = '1.4'
  provenance.style.color = variant === 'bold_social' ? '#cbd5e1' : '#334155'
  provenance.textContent = exportReviewLabel.value

  const watermark = document.createElement('div')
  watermark.style.fontSize = spacing.footerSize
  watermark.style.fontWeight = '600'
  watermark.style.color = variant === 'bold_social' ? '#7dd3fc' : '#0f172a'
  watermark.textContent = exportIncludePoweredBy.value ? 'Powered by Cricksy' : ''

  if (!exportIncludePoweredBy.value || activeTemplate?.watermarkPlacement === 'overlay') {
    watermark.style.display = 'none'
  }

  if (activeTemplate?.watermarkPlacement === 'header' && watermark.style.display !== 'none') {
    header.appendChild(watermark)
    footer.append(provenance)
  } else {
    footer.append(provenance, watermark)
  }

  wrapper.append(header, content, footer)
  document.body.appendChild(wrapper)
  return wrapper
}

async function generateExportPreview() {
  if (
    !activeExportAvailability.value.available ||
    !templateRequirementAvailability.value.available ||
    !activeExportNode.value ||
    !activeExportFormat.value
  ) {
    return
  }
  exportBusy.value = true
  exportError.value = null
  exportPreviewUrl.value = null

  let frame: HTMLDivElement | null = null
  try {
    frame = buildExportFrame(
      activeExportNode.value,
      activeExportFormat.value.width,
      activeExportFormat.value.height
    )
    exportPreviewUrl.value = await toPng(frame, {
      cacheBust: true,
      canvasWidth: activeExportFormat.value.width,
      canvasHeight: activeExportFormat.value.height,
      backgroundColor: '#ffffff',
      pixelRatio: 1,
    })
  } catch (e: unknown) {
    exportError.value = e instanceof Error ? e.message : 'Unable to generate export preview.'
  } finally {
    if (frame) {
      frame.remove()
    }
    exportBusy.value = false
  }
}

function downloadExportImage() {
  if (!exportPreviewUrl.value || !activeExportFormat.value || !activeExportTarget.value) return
  const filename = `cpl-${activeExportTarget.value.value}-${activeExportFormat.value.value}.png`
  const link = document.createElement('a')
  link.href = exportPreviewUrl.value
  link.download = filename
  link.click()
}

onMounted(() => {
  loadEpisodeArchive()
  void load()
})

type TalkingPointStatus = 'needs_review' | 'approved' | 'rejected'
type TalkingPointConfidence = 'high' | 'medium' | 'low'

interface TalkingPoint {
  id: string
  section: string
  title: string
  text: string
  sourceFactIds: string[]
  confidence: TalkingPointConfidence
  status: TalkingPointStatus
}

interface AiTalkingPointsResult {
  status: 'needs_review'
  generatedAt: string
  limitations: string[]
  talkingPoints: TalkingPoint[]
}

// ---------------------------------------------------------------------------
// AI Talking-Point Assistant — state
// ---------------------------------------------------------------------------

const aiGenerating = ref(false)
const aiResult = ref<AiTalkingPointsResult | null>(null)
const aiError = ref<string | null>(null)
/** Per-index edited text (set when analyst edits a point). */
const aiTpEdits = reactive<Record<number, string>>({})
/** Per-index editing flag. */
const aiTpEditing = reactive<Record<number, boolean>>({})

const approvedCount = computed<number>(() => {
  if (!aiResult.value) return 0
  return aiResult.value.talkingPoints.filter(tp => tp.status === 'approved').length
})

const approvedTalkingPoints = computed<TalkingPoint[]>(() => {
  if (!aiResult.value) return []
  return aiResult.value.talkingPoints.filter(tp => tp.status === 'approved')
})

const needsReviewTalkingPoints = computed<TalkingPoint[]>(() => {
  if (!aiResult.value) return []
  return aiResult.value.talkingPoints.filter(tp => tp.status === 'needs_review')
})

const canGeneratePodcastScript = computed<boolean>(() =>
  cplMatches.value.length > 0 && podcastFacts.value.length >= 2
)

const podcastScriptDisabledReason = computed<string>(() => {
  if (cplMatches.value.length === 0) {
    return 'Script builder disabled: no CPL data is available.'
  }
  if (podcastFacts.value.length === 0) {
    return 'Script builder disabled: no deterministic facts are available for current filters.'
  }
  if (podcastFacts.value.length < 2) {
    return 'Script builder disabled: at least 2 deterministic facts are required to assemble a script.'
  }
  return ''
})

const podcastScriptDraft = ref('')

type EpisodePackageStatus = 'draft' | 'ready_for_review' | 'approved_for_recording' | 'archived'

interface ArchivedTalkingPoint {
  id: string
  section: string
  title: string
  text: string
  source_fact_ids: string[]
  status: 'approved' | 'needs_review'
}

interface EpisodeArchivePackage {
  id: string
  schema_version: 1
  status: EpisodePackageStatus
  working_title: string
  objective: string
  created_at: string
  updated_at: string
  is_incomplete: boolean
  context: {
    filters: {
      season: string
      team: string
      venue: string
    }
    selected_match_id: string
    selected_match_label: string
    selected_export_target: ExportTarget
    selected_export_format: ExportFormat
    selected_export_template_id: string
    selected_export_template_label: string
    export_review_label: string
  }
  deterministic_facts: PodcastFact[]
  approved_talking_points: ArchivedTalkingPoint[]
  needs_review_talking_points: ArchivedTalkingPoint[]
  script_draft: string
  provenance: {
    source: string
    generated_at_utc: string
    archive_saved_at_utc: string
    import_generated_at_utc: string | null
    limitations: string[]
    note: string
  }
}

const EPISODE_ARCHIVE_STORAGE_KEY = 'cricksy.cplPodcastEpisodeArchive.v1'

const episodeStatusOptions = [
  { value: 'draft', label: 'Draft' },
  { value: 'ready_for_review', label: 'Ready for review' },
  { value: 'approved_for_recording', label: 'Approved for recording' },
  { value: 'archived', label: 'Archived' },
] as const satisfies ReadonlyArray<{ value: EpisodePackageStatus; label: string }>

const episodeStatusLabelMap: Record<EpisodePackageStatus, string> = {
  draft: 'Draft',
  ready_for_review: 'Ready for review',
  approved_for_recording: 'Approved for recording',
  archived: 'Archived',
}

const episodeWorkingTitle = ref('')
const episodeObjective = ref('')
const episodePackageStatus = ref<EpisodePackageStatus>('draft')
const episodeArchive = ref<EpisodeArchivePackage[]>([])
const activeEpisodePackageId = ref<string | null>(null)
const episodeArchiveError = ref<string | null>(null)

const sortedEpisodePackages = computed(() =>
  [...episodeArchive.value].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
)

const canCreateEpisodePackage = computed(() =>
  cplMatches.value.length > 0 && podcastScriptDraft.value.trim().length > 0
)

const episodePackageDisabledReason = computed(() => {
  if (cplMatches.value.length === 0) {
    return 'Episode archive disabled: no CPL data is available.'
  }
  if (podcastScriptDraft.value.trim().length === 0) {
    return 'Episode archive disabled: generate or edit a script draft before saving a package.'
  }
  return ''
})

const packageWillBeIncomplete = computed(() => approvedTalkingPoints.value.length === 0)

function episodeStatusLabel(status: EpisodePackageStatus): string {
  return episodeStatusLabelMap[status]
}

function archiveNowIso(): string {
  return new Date().toISOString()
}

function archivePackageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `episode-${Date.now()}`
}

function archivedTalkingPointText(tp: TalkingPoint): string {
  const idx = aiResult.value?.talkingPoints.findIndex(candidate => candidate.id === tp.id) ?? -1
  return idx >= 0 ? (aiTpEdits[idx] ?? tp.text) : tp.text
}

function buildEpisodeLimitations(): string[] {
  return uniqueNonEmpty([
    ...podcastFacts.value.map(f => f.caveat),
    ...(aiResult.value?.limitations ?? []),
    selectedMatch.value && !selectedMatch.value.has_delivery_data
      ? 'Delivery data is missing for selected match; avoid phase-by-phase or ball-by-ball claims.'
      : null,
    topRunScorers.value.length === 0 && topWicketTakers.value.length === 0
      ? 'Leaderboard data is unavailable; player ranking narratives may be incomplete.'
      : null,
    packageWillBeIncomplete.value
      ? 'No approved talking points are included yet; package is facts-only/incomplete.'
      : null,
  ])
}

function persistEpisodeArchive(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(EPISODE_ARCHIVE_STORAGE_KEY, JSON.stringify(episodeArchive.value))
    episodeArchiveError.value = null
  } catch {
    episodeArchiveError.value = 'Unable to persist episode archive in local storage.'
  }
}

function loadEpisodeArchive(): void {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(EPISODE_ARCHIVE_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return
    episodeArchive.value = parsed.filter(pkg =>
      pkg && typeof pkg === 'object' && pkg.schema_version === 1 && typeof pkg.id === 'string'
    )
    episodeArchiveError.value = null
  } catch {
    episodeArchiveError.value = 'Unable to read episode archive from local storage.'
  }
}

function buildCurrentEpisodePackage(): EpisodeArchivePackage {
  const nowIso = archiveNowIso()
  const existing = activeEpisodePackageId.value
    ? episodeArchive.value.find(pkg => pkg.id === activeEpisodePackageId.value) ?? null
    : null
  const packageId = existing?.id ?? archivePackageId()
  const createdAt = existing?.created_at ?? nowIso
  const selectedMatchLabel = selectedMatch.value?.teams
    ? `${selectedMatch.value.teams}${selectedMatch.value.match_date ? ` (${selectedMatch.value.match_date})` : ''}`
    : 'Not selected'
  const fallbackTitle = selectedMatch.value
    ? `CPL Episode Prep: ${selectedMatch.value.teams}`
    : `CPL Episode Prep${selectedSeason.value !== 'all' ? ` (${selectedSeason.value})` : ''}`
  const workingTitle = episodeWorkingTitle.value.trim() || fallbackTitle
  const objective = episodeObjective.value.trim() || 'Deterministic CPL preparation package.'

  const approved = approvedTalkingPoints.value.map(tp => ({
    id: tp.id,
    section: tp.section,
    title: tp.title,
    text: archivedTalkingPointText(tp),
    source_fact_ids: tp.sourceFactIds,
    status: 'approved' as const,
  }))
  const needsReview = needsReviewTalkingPoints.value.map(tp => ({
    id: tp.id,
    section: tp.section,
    title: tp.title,
    text: archivedTalkingPointText(tp),
    source_fact_ids: tp.sourceFactIds,
    status: 'needs_review' as const,
  }))

  return {
    id: packageId,
    schema_version: 1,
    status: episodePackageStatus.value,
    working_title: workingTitle,
    objective,
    created_at: createdAt,
    updated_at: nowIso,
    is_incomplete: approved.length === 0,
    context: {
      filters: {
        season: selectedSeason.value,
        team: selectedTeam.value,
        venue: selectedVenue.value,
      },
      selected_match_id: selectedMatchId.value,
      selected_match_label: selectedMatchLabel,
      selected_export_target: exportTarget.value,
      selected_export_format: exportFormat.value,
      selected_export_template_id: exportTemplateId.value,
      selected_export_template_label: activeExportTemplate.value?.label ?? 'Unavailable',
      export_review_label: exportReviewLabel.value,
    },
    deterministic_facts: podcastFacts.value.map(f => ({ ...f })),
    approved_talking_points: approved,
    needs_review_talking_points: needsReview,
    script_draft: podcastScriptDraft.value,
    provenance: {
      source: 'validated historical CPL imports displayed in dashboard',
      generated_at_utc: nowIso,
      archive_saved_at_utc: nowIso,
      import_generated_at_utc: summary.value?.generated_at ?? null,
      limitations: buildEpisodeLimitations(),
      note: 'Frontend-only archive package. No auto-publishing and no unsupported AI claims.',
    },
  }
}

function saveEpisodePackage(): void {
  if (!canCreateEpisodePackage.value) return
  const pkg = buildCurrentEpisodePackage()
  episodeWorkingTitle.value = pkg.working_title
  episodeObjective.value = pkg.objective
  activeEpisodePackageId.value = pkg.id
  const withoutExisting = episodeArchive.value.filter(existing => existing.id !== pkg.id)
  episodeArchive.value = [pkg, ...withoutExisting]
  persistEpisodeArchive()
}

function formatArchiveTimestamp(isoValue: string): string {
  const d = new Date(isoValue)
  if (Number.isNaN(d.getTime())) return isoValue
  return d.toLocaleString()
}

function reopenEpisodePackage(packageId: string): void {
  const pkg = episodeArchive.value.find(item => item.id === packageId)
  if (!pkg) return

  selectedSeason.value = pkg.context.filters.season === 'all' || availableSeasons.value.includes(pkg.context.filters.season)
    ? pkg.context.filters.season
    : 'all'
  selectedTeam.value = pkg.context.filters.team === 'all' || availableTeams.value.includes(pkg.context.filters.team)
    ? pkg.context.filters.team
    : 'all'
  selectedVenue.value = pkg.context.filters.venue === 'all' || availableVenues.value.includes(pkg.context.filters.venue)
    ? pkg.context.filters.venue
    : 'all'
  selectedMatchId.value = cplMatches.value.some(match => match.match_id === pkg.context.selected_match_id)
    ? pkg.context.selected_match_id
    : ''

  exportTarget.value = pkg.context.selected_export_target
  exportFormat.value = pkg.context.selected_export_format
  exportTemplateId.value = pkg.context.selected_export_template_id

  episodeWorkingTitle.value = pkg.working_title
  episodeObjective.value = pkg.objective
  episodePackageStatus.value = pkg.status
  podcastScriptDraft.value = pkg.script_draft
  activeEpisodePackageId.value = pkg.id

  aiResult.value = {
    status: 'needs_review',
    generatedAt: formatArchiveTimestamp(pkg.updated_at),
    limitations: [...pkg.provenance.limitations],
    talkingPoints: [
      ...pkg.approved_talking_points.map(tp => ({
        id: tp.id,
        section: tp.section,
        title: tp.title,
        text: tp.text,
        sourceFactIds: [...tp.source_fact_ids],
        confidence: 'medium' as const,
        status: 'approved' as const,
      })),
      ...pkg.needs_review_talking_points.map(tp => ({
        id: tp.id,
        section: tp.section,
        title: tp.title,
        text: tp.text,
        sourceFactIds: [...tp.source_fact_ids],
        confidence: 'medium' as const,
        status: 'needs_review' as const,
      })),
    ],
  }
  Object.keys(aiTpEdits).forEach(k => { delete (aiTpEdits as Record<string, string>)[k] })
  Object.keys(aiTpEditing).forEach(k => { delete (aiTpEditing as Record<string, boolean>)[k] })
}

function deleteEpisodePackage(packageId: string): void {
  episodeArchive.value = episodeArchive.value.filter(pkg => pkg.id !== packageId)
  if (activeEpisodePackageId.value === packageId) {
    activeEpisodePackageId.value = null
  }
  persistEpisodeArchive()
}

function downloadTextFile(filename: string, content: string, mimeType: string): void {
  if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function' || typeof URL.revokeObjectURL !== 'function') {
    return
  }
  const blob = new Blob([content], { type: mimeType })
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  link.click()
  URL.revokeObjectURL(blobUrl)
}

function buildEpisodePackageMarkdown(pkg: EpisodeArchivePackage): string {
  const lines: string[] = [
    '# Podcast episode package',
    `- Working title: ${pkg.working_title}`,
    `- Status: ${episodeStatusLabel(pkg.status)}`,
    `- Created: ${pkg.created_at}`,
    `- Updated: ${pkg.updated_at}`,
    '',
    '## Episode objective',
    pkg.objective,
    '',
    '## Filter and context',
    `- Season: ${pkg.context.filters.season}`,
    `- Team: ${pkg.context.filters.team}`,
    `- Venue: ${pkg.context.filters.venue}`,
    `- Match: ${pkg.context.selected_match_label}`,
    '',
    '## Deterministic facts',
    ...(pkg.deterministic_facts.length > 0
      ? pkg.deterministic_facts.map(f => `- **${f.label}:** ${f.value}${f.caveat ? ` _(caveat: ${f.caveat})_` : ''}`)
      : ['- No deterministic facts saved.']),
    '',
    '## Approved talking points',
    ...(pkg.approved_talking_points.length > 0
      ? pkg.approved_talking_points.map(tp => `- **${tp.title}:** ${tp.text}`)
      : ['- No approved talking points in this package.']),
    '',
    '## Talking points still needing review',
    ...(pkg.needs_review_talking_points.length > 0
      ? pkg.needs_review_talking_points.map(tp => `- **${tp.title}:** ${tp.text}`)
      : ['- None.']),
    '',
    '## Script draft',
    pkg.script_draft,
    '',
    '## Visual/export metadata',
    `- Target: ${pkg.context.selected_export_target}`,
    `- Format: ${pkg.context.selected_export_format}`,
    `- Template: ${pkg.context.selected_export_template_label} (${pkg.context.selected_export_template_id})`,
    `- Review label: ${pkg.context.export_review_label}`,
    '',
    '## Provenance & limitations',
    `- Source: ${pkg.provenance.source}`,
    `- Dashboard aggregate generated at (UTC): ${pkg.provenance.import_generated_at_utc ?? 'Unknown'}`,
    `- Package generated at (UTC): ${pkg.provenance.generated_at_utc}`,
    `- Package saved at (UTC): ${pkg.provenance.archive_saved_at_utc}`,
    `- Note: ${pkg.provenance.note}`,
    ...pkg.provenance.limitations.map(limitation => `- Limitation: ${limitation}`),
  ]
  return lines.join('\n')
}

function downloadEpisodePackageMarkdown(pkg: EpisodeArchivePackage): void {
  const slug = pkg.working_title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || pkg.id
  downloadTextFile(`cpl-episode-package-${slug}.md`, buildEpisodePackageMarkdown(pkg), 'text/markdown;charset=utf-8')
}

function downloadEpisodePackageJson(pkg: EpisodeArchivePackage): void {
  downloadTextFile(
    `cpl-episode-package-${pkg.id}.json`,
    JSON.stringify(pkg, null, 2),
    'application/json;charset=utf-8'
  )
}

// ---------------------------------------------------------------------------
// AI Talking-Point Assistant — generation
// ---------------------------------------------------------------------------

/**
 * Deterministic frontend-only talking-point generator.
 * Generates reviewable drafts from the current podcastFacts bundle.
 * Does not contact any backend — all content is grounded in supplied facts.
 * AI never calculates official scores, invents missing data, or publishes.
 */
function generateAiTalkingPoints(): void {
  if (podcastFacts.value.length < 2) return

  aiGenerating.value = true
  aiError.value = null
  aiResult.value = null
  // Clear any prior edits
  Object.keys(aiTpEdits).forEach(k => { delete (aiTpEdits as Record<string, string>)[k] })
  Object.keys(aiTpEditing).forEach(k => { delete (aiTpEditing as Record<string, boolean>)[k] })

  // Short async tick to reflect generating state in UI
  setTimeout(() => {
    try {
      aiResult.value = _buildTalkingPoints(podcastFacts.value)
    } catch (e: unknown) {
      aiError.value = e instanceof Error ? e.message : 'Unable to generate talking points.'
    } finally {
      aiGenerating.value = false
    }
  }, 0)
}

function clearAiResult(): void {
  aiResult.value = null
  aiError.value = null
  Object.keys(aiTpEdits).forEach(k => { delete (aiTpEdits as Record<string, string>)[k] })
  Object.keys(aiTpEditing).forEach(k => { delete (aiTpEditing as Record<string, boolean>)[k] })
}

function _buildTalkingPoints(facts: PodcastFact[]): AiTalkingPointsResult {
  const limitations: string[] = []
  const tps: TalkingPoint[] = []

  // Categorise facts by type for source referencing
  const seasonFacts = facts.filter(f => f.type === 'season')
  const matchFacts  = facts.filter(f => f.type === 'match')
  const playerFacts = facts.filter(f => f.type === 'player')
  const venueFacts  = facts.filter(f => f.type === 'venue')
  const teamFacts   = facts.filter(f => f.type === 'team')

  // Determine limitations from caveat signals
  const hasNoDeliveryData = facts.some(f => f.label === 'Delivery data' && f.value === 'Not imported')
  const hasDeliveryWarning = facts.some(f => f.caveat?.toLowerCase().includes('delivery data'))
  if (hasNoDeliveryData) {
    limitations.push('Delivery data is missing for the selected match — ball-by-ball and phase claims cannot be made.')
  }
  if (hasDeliveryWarning && !hasNoDeliveryData) {
    limitations.push('Some facts are derived from innings totals only — delivery-level detail is unavailable for some matches.')
  }
  if (playerFacts.length === 0) {
    limitations.push('Leaderboard data is unavailable — top scorer / wicket-taker narratives cannot be stated.')
  }
  if (venueFacts.length === 0) {
    limitations.push('No venue-specific data is selected — venue angle is limited to team/season context.')
  }

  // Helper to build a stable source ID from a fact
  function factId(f: PodcastFact): string {
    return `${f.type}.${f.label.toLowerCase().replace(/\s+/g, '_')}`
  }

  // ── Section 1: Opening hook ──────────────────────────────────────────────
  if (matchFacts.length > 0) {
    const mf = matchFacts[0]
    const scoreFact = matchFacts.find(f => f.label === 'Match scores' || f.label === '1st innings score')
    tps.push({
      id: 'opening-hook',
      section: 'Opening hook',
      title: 'Set the scene',
      text: scoreFact
        ? `This episode looks at ${mf.value}. The match showed: ${scoreFact.value}.`
        : `This episode covers the match: ${mf.value}.`,
      sourceFactIds: [factId(mf), ...(scoreFact ? [factId(scoreFact)] : [])],
      confidence: scoreFact ? 'high' : 'medium',
      status: 'needs_review',
    })
  } else if (seasonFacts.length > 0) {
    const sf = seasonFacts[0]
    tps.push({
      id: 'opening-hook',
      section: 'Opening hook',
      title: 'Set the scene',
      text: `Welcome. Today we look at the CPL data: ${sf.value}.`,
      sourceFactIds: [factId(sf)],
      confidence: 'medium',
      status: 'needs_review',
    })
  }

  // ── Section 2: Key match / season facts ─────────────────────────────────
  if (seasonFacts.length >= 2) {
    const runsFact  = seasonFacts.find(f => f.label === 'Total runs in dataset')
    const wktFact   = seasonFacts.find(f => f.label === 'Total wickets in dataset')
    const mtchFact  = seasonFacts.find(f => f.label === 'Matches imported')
    const sourceFacts = [runsFact, wktFact, mtchFact].filter(Boolean) as PodcastFact[]
    if (sourceFacts.length >= 2) {
      const runsPart   = runsFact  ? `${runsFact.value} total runs` : ''
      const wicketsPart = wktFact  ? `${wktFact.value} wickets` : ''
      const matchPart   = mtchFact ? ` across ${mtchFact.value}` : ''
      tps.push({
        id: 'key-season-facts',
        section: 'Key season facts',
        title: 'Season by the numbers',
        text: `The imported CPL dataset shows${matchPart}: ${[runsPart, wicketsPart].filter(Boolean).join(' and ')}.`,
        sourceFactIds: sourceFacts.map(factId),
        confidence: 'high',
        status: 'needs_review',
      })
    }
  }

  // ── Section 3: Player / team angle ──────────────────────────────────────
  if (playerFacts.length > 0) {
    const runnerFact  = playerFacts.find(f => f.label === 'Top run scorer')
    const wicketFact  = playerFacts.find(f => f.label === 'Top wicket taker')
    const usedFacts   = [runnerFact, wicketFact].filter(Boolean) as PodcastFact[]
    if (usedFacts.length > 0) {
      const runnerText  = runnerFact  ? `Top run scorer: ${runnerFact.value}.` : ''
      const wicketText  = wicketFact  ? `Top wicket taker: ${wicketFact.value}.` : ''
      tps.push({
        id: 'player-angle',
        section: 'Player / team angle',
        title: 'Star performers',
        text: [runnerText, wicketText].filter(Boolean).join(' ') + ' These figures come from matches with delivery data only.',
        sourceFactIds: usedFacts.map(factId),
        confidence: 'medium',
        status: 'needs_review',
      })
    }
  }

  // ── Section 4: Venue angle ───────────────────────────────────────────────
  const venueAvgFact = facts.find(f => f.label === 'Venue avg first innings')
  const venueListFact = facts.find(f => f.label === 'Venues represented')
  if (venueAvgFact) {
    tps.push({
      id: 'venue-angle',
      section: 'Venue angle',
      title: 'The venue factor',
      text: `At the selected venue: ${venueAvgFact.value}.${venueAvgFact.caveat ? ' Note: ' + venueAvgFact.caveat + '.' : ''}`,
      sourceFactIds: [factId(venueAvgFact)],
      confidence: venueAvgFact.caveat ? 'low' : 'medium',
      status: 'needs_review',
    })
  } else if (venueListFact) {
    tps.push({
      id: 'venue-angle',
      section: 'Venue angle',
      title: 'Venues in dataset',
      text: `CPL matches in this dataset were played at: ${venueListFact.value}. Select a specific venue for detailed averages.`,
      sourceFactIds: [factId(venueListFact)],
      confidence: 'medium',
      status: 'needs_review',
    })
  }

  // ── Section 5: Caution / limitation note ────────────────────────────────
  if (limitations.length > 0) {
    tps.push({
      id: 'caution-note',
      section: 'Caution / limitation',
      title: 'What this data cannot tell us',
      text: limitations.join(' ') + ' Always verify with official CPL records before broadcast.',
      sourceFactIds: [],
      confidence: 'low',
      status: 'needs_review',
    })
  }

  // ── Section 6: Questions for the host ───────────────────────────────────
  const questionParts: string[] = []
  if (playerFacts.length > 0) {
    questionParts.push('Which player performance surprised you most in this dataset?')
  }
  if (matchFacts.length > 0) {
    questionParts.push('What was the tactical turning point in the selected match?')
  }
  if (venueFacts.length > 0 || facts.find(f => f.type === 'venue')) {
    questionParts.push('How does this venue compare to others in the CPL circuit?')
  }
  if (seasonFacts.length > 0) {
    questionParts.push("What does this season's run-rate and wickets data suggest about batting depth?")
  }
  if (questionParts.length > 0) {
    const allFactIds = facts.slice(0, 4).map(factId)
    tps.push({
      id: 'host-questions',
      section: 'Questions for the host',
      title: 'Suggested discussion questions',
      text: questionParts.join(' | '),
      sourceFactIds: allFactIds,
      confidence: 'medium',
      status: 'needs_review',
    })
  }

  return {
    status: 'needs_review',
    generatedAt: new Date().toLocaleTimeString(),
    limitations,
    talkingPoints: tps,
  }
}

// ---------------------------------------------------------------------------
// AI Talking-Point Assistant — review actions
// ---------------------------------------------------------------------------

function approveTp(idx: number): void {
  if (aiResult.value) {
    aiResult.value.talkingPoints[idx].status = 'approved'
  }
}

function unapproveTp(idx: number): void {
  if (aiResult.value) {
    aiResult.value.talkingPoints[idx].status = 'needs_review'
  }
}

function rejectTp(idx: number): void {
  if (aiResult.value) {
    aiResult.value.talkingPoints[idx].status = 'rejected'
  }
}

function startEditTp(idx: number): void {
  aiTpEditing[idx] = true
  if (!aiTpEdits[idx] && aiResult.value) {
    aiTpEdits[idx] = aiResult.value.talkingPoints[idx].text
  }
}

function saveEditTp(idx: number): void {
  aiTpEditing[idx] = false
}

function cancelEditTp(idx: number): void {
  aiTpEditing[idx] = false
}

function copyTp(idx: number): void {
  if (!aiResult.value) return
  const tp = aiResult.value.talkingPoints[idx]
  const text = aiTpEdits[idx] ?? tp.text
  const reviewedLabel = tp.status === 'approved' ? '[REVIEWED]' : '[UNREVIEWED — not final]'
  const fullText = `${reviewedLabel} ${tp.title}: ${text}`
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    void navigator.clipboard.writeText(fullText)
  }
}

function uniqueNonEmpty(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.map(v => (v ?? '').trim()).filter(Boolean))]
}

function buildPodcastScriptMarkdown(): string {
  const nowIso = new Date().toISOString()
  const selectedMatchLabel = selectedMatch.value?.teams
    ? `${selectedMatch.value.teams}${selectedMatch.value.match_date ? ` (${selectedMatch.value.match_date})` : ''}`
    : 'Not selected'
  const contextBits = uniqueNonEmpty([
    selectedSeason.value !== 'all' ? `Season: ${selectedSeason.value}` : 'Season: all seasons',
    selectedTeam.value !== 'all' ? `Team focus: ${selectedTeam.value}` : null,
    selectedVenue.value !== 'all' ? `Venue focus: ${selectedVenue.value}` : null,
    `Match: ${selectedMatchLabel}`,
  ])

  const approved = approvedTalkingPoints.value
  const incompleteFactsOnly = approved.length === 0
  const keyFacts = podcastFacts.value

  const approvedQuestions = approved
    .filter(tp => tp.section.toLowerCase().includes('question'))
    .flatMap(tp => tp.text.split('|').map(part => part.trim()).filter(Boolean))

  const caveatLines = uniqueNonEmpty([
    ...keyFacts.map(f => f.caveat),
    ...(aiResult.value?.limitations ?? []),
    selectedMatch.value && !selectedMatch.value.has_delivery_data
      ? 'Delivery data is missing for selected match; avoid phase-by-phase or ball-by-ball claims.'
      : null,
    keyFacts.some(f => f.label === 'Top run scorer' || f.label === 'Top wicket taker')
      ? null
      : 'Leaderboard data is unavailable; avoid player-rank narratives.',
    incompleteFactsOnly
      ? 'No approved talking points yet. This is a facts-only outline and is incomplete for publication.'
      : null,
  ])

  const visualCueLines = uniqueNonEmpty([
    activeExportTarget.value ? `Export target: ${activeExportTarget.value.label}` : null,
    activeExportFormat.value ? `Format: ${activeExportFormat.value.label}` : null,
    activeExportTemplate.value ? `Template: ${activeExportTemplate.value.label}` : null,
    exportPreviewUrl.value ? 'Export preview is available and can be reviewed before publishing assets.' : 'No export preview generated yet.',
  ])

  const followUpIdeas = uniqueNonEmpty([
    selectedSeason.value !== 'all' ? `Create a season recap segment for ${selectedSeason.value}.` : 'Create a multi-season CPL comparison segment.',
    selectedVenue.value !== 'all' ? `Prepare a venue-focused clip for ${selectedVenue.value}.` : 'Prepare a venue-comparison clip for social channels.',
    selectedMatch.value ? 'Publish a match-specific teaser image from the selected match story panel.' : 'Select a specific match to prepare a focused teaser image.',
  ])

  const lines: string[] = [
    '# Episode working title',
    selectedMatch.value
      ? `CPL Match Breakdown: ${selectedMatch.value.teams}`
      : `CPL Data Briefing${selectedSeason.value !== 'all' ? ` (${selectedSeason.value})` : ''}`,
    '',
    '## Episode objective',
    incompleteFactsOnly
      ? 'Prepare a deterministic facts-first briefing while approved talking points are still pending review.'
      : 'Deliver a deterministic CPL analysis using approved talking points and validated dashboard facts.',
    '',
    '## Opening hook',
  ]

  if (approved.length > 0) {
    lines.push(approved[0].text)
  } else {
    const selectedMatchFact = keyFacts.find(f => f.label === 'Selected match')
    lines.push(selectedMatchFact ? selectedMatchFact.value : `Dataset scope: ${keyFacts[0]?.value ?? 'No fact available'}.`)
  }

  lines.push(
    '',
    '## Context setup',
    ...contextBits.map(item => `- ${item}`),
    '',
    '## Key facts to mention',
    ...keyFacts.map(f => `- **${f.label}:** ${f.value}${f.caveat ? ` _(caveat: ${f.caveat})_` : ''}`),
    '',
    '## Visual cue list',
    ...visualCueLines.map(item => `- ${item}`),
    '',
    '## Approved talking points'
  )

  if (approved.length > 0) {
    lines.push(
      ...approved.map(tp => {
        const idx = aiResult.value?.talkingPoints.findIndex(candidate => candidate.id === tp.id) ?? -1
        const editedText = idx >= 0 ? aiTpEdits[idx] : undefined
        return `- **${tp.title}:** ${editedText ?? tp.text}`
      })
    )
  } else {
    lines.push('- _No approved talking points yet. Facts-only outline in progress._')
  }

  lines.push(
    '',
    '## Host/analyst questions',
    ...(approvedQuestions.length > 0
      ? approvedQuestions.map(q => `- ${q}`)
      : ['- Which deterministic fact should be reviewed next for approval?']),
    '',
    '## Limitations / data caveats',
    ...(caveatLines.length > 0
      ? caveatLines.map(l => `- ${l}`)
      : ['- No additional caveats flagged from current deterministic dashboard context.']),
    '',
    '## Closing summary',
    incompleteFactsOnly
      ? 'This draft is incomplete and uses deterministic facts only until talking points are approved.'
      : `Approved talking points ready: ${approved.length}. Keep all claims grounded in validated import data.`,
    '',
    '## Follow-up content ideas',
    ...followUpIdeas.map(item => `- ${item}`),
    '',
    '## Provenance & limitations',
    '- Source: validated historical CPL imports displayed in the dashboard',
    `- Fact bundle count: ${keyFacts.length}`,
    `- Approved talking points included: ${approved.length}`,
    `- Export context: ${exportReviewLabel.value}`,
    `- Generated at (UTC): ${nowIso}`,
    '- No auto-publishing, no social posting automation, no unsupported AI claims',
  )

  return lines.join('\n')
}

function generatePodcastScript(): void {
  if (!canGeneratePodcastScript.value) return
  podcastScriptDraft.value = buildPodcastScriptMarkdown()
}

function toPlainText(markdown: string): string {
  return markdown
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/_(.*?)_/g, '$1')
    .replace(/^- /gm, '• ')
}

function copyText(text: string): void {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    void navigator.clipboard.writeText(text)
  }
}

function copyPodcastScriptMarkdown(): void {
  if (!podcastScriptDraft.value) return
  copyText(podcastScriptDraft.value)
}

function copyPodcastScriptPlainText(): void {
  if (!podcastScriptDraft.value) return
  copyText(toPlainText(podcastScriptDraft.value))
}

function downloadPodcastScriptMarkdown(): void {
  if (!podcastScriptDraft.value) return
  if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function' || typeof URL.revokeObjectURL !== 'function') {
    return
  }
  const blob = new Blob([podcastScriptDraft.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'cpl-podcast-script.md'
  link.click()
  URL.revokeObjectURL(url)
}

</script>

<style scoped>
.cpld {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.cpld-header {
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  padding-bottom: 0.75rem;
}

.cpld-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  color: var(--color-text, #1e293b);
}

.cpld-subtitle {
  font-size: 0.8rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

.cpld-provenance-bar {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: #15803d;
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}

.cpld-provenance-icon {
  flex-shrink: 0;
}

.cpld-warn-inline {
  color: #b45309;
  margin-left: 0.25rem;
}

/* States */
.cpld-state {
  padding: 1.5rem;
  text-align: center;
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-state--loading {
  background: #f8fafc;
}

.cpld-state--error {
  background: #fef2f2;
  color: #b91c1c;
}

.cpld-state--empty {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
}

.cpld-state--hint {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  padding: 1rem;
  text-align: left;
}

.cpld-empty-heading {
  font-weight: 600;
  margin: 0 0 0.5rem;
  font-size: 1rem;
}

.cpld-empty-body {
  margin: 0;
  font-size: 0.85rem;
}

.cpld-retry-btn {
  margin-top: 0.75rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

/* Filters */
.cpld-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-end;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

.cpld-filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cpld-filter-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #64748b);
}

.cpld-select {
  padding: 0.35rem 0.6rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.825rem;
  background: #fff;
  min-width: 140px;
}

.cpld-select--wide {
  min-width: 280px;
}

.cpld-reset-btn {
  padding: 0.35rem 0.75rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--color-text-muted, #64748b);
  align-self: flex-end;
}

.cpld-export-pack {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem 1rem;
}

.cpld-export-desc {
  margin: 0;
  font-size: 0.78rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-export-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  align-items: flex-start;
}

.cpld-export-toggles {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.cpld-export-check {
  font-size: 0.74rem;
  color: var(--color-text-muted, #64748b);
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.cpld-export-review {
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  background: #ffffff;
}

.cpld-export-review p {
  margin: 0;
  font-size: 0.76rem;
  color: var(--color-text, #1e293b);
}

.cpld-export-meta {
  margin-top: 0.2rem !important;
  color: var(--color-text-muted, #64748b) !important;
}

.cpld-export-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.cpld-export-btn {
  padding: 0.4rem 0.8rem;
  border: 1px solid #0f766e;
  background: #0f766e;
  color: #ffffff;
  border-radius: 4px;
  font-size: 0.78rem;
  cursor: pointer;
}

.cpld-export-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.cpld-export-btn--secondary {
  border-color: #cbd5e1;
  background: #ffffff;
  color: #334155;
}

.cpld-export-error {
  margin: 0;
  font-size: 0.76rem;
  color: #b91c1c;
}

.cpld-export-preview-wrap {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.65rem;
}

.cpld-export-preview-label {
  margin: 0 0 0.35rem;
  font-size: 0.74rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-export-preview {
  width: 100%;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

/* Section */
.cpld-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cpld-section-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text, #1e293b);
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.4rem;
}

.cpld-section-scope {
  font-size: 0.78rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

.cpld-subsection-title {
  font-size: 0.85rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
  color: var(--color-text, #1e293b);
}

/* Summary Cards */
.cpld-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

.cpld-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.cpld-card--muted {
  background: #f8fafc;
}

.cpld-card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text, #1e293b);
  margin: 0;
  line-height: 1.1;
}

.cpld-card-label {
  font-size: 0.7rem;
  color: var(--color-text-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0;
}

.cpld-card-warn {
  font-size: 0.68rem;
  color: #b45309;
  margin: 0;
}

.cpld-card-note {
  font-size: 0.68rem;
  color: #b45309;
  margin: 0;
}

/* Match story */
.cpld-match-select {
  margin-bottom: 0.25rem;
}

.cpld-match-header {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
}

.cpld-match-teams {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}

.cpld-match-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-match-provenance {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.cpld-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.cpld-badge--imported {
  background: #e0f2fe;
  color: #0369a1;
}

.cpld-provenance-file {
  font-size: 0.72rem;
  color: var(--color-text-muted, #64748b);
}

/* Innings section */
.cpld-innings-section {
  margin-bottom: 0.75rem;
}

.cpld-innings-comparison {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.cpld-innings-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

.cpld-innings-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  margin-bottom: 0.35rem;
}

.cpld-innings-team {
  font-weight: 400;
}

.cpld-innings-score {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  margin-bottom: 0.35rem;
}

.cpld-innings-runs {
  font-size: 1.4rem;
  font-weight: 700;
}

.cpld-innings-overs {
  font-size: 0.78rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-rr-bar-wrap {
  background: #f1f5f9;
  border-radius: 2px;
  height: 6px;
  margin-bottom: 0.3rem;
  overflow: hidden;
}

.cpld-rr-bar {
  height: 100%;
  background: #3b82f6;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.cpld-innings-rr {
  font-size: 0.72rem;
  color: var(--color-text-muted, #64748b);
}

.cpld-insufficient {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  font-size: 0.8rem;
  color: #92400e;
}

.cpld-insufficient--warn {
  background: #fff7ed;
  border-color: #fed7aa;
}

.cpld-delivery-note {
  font-size: 0.78rem;
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  padding: 0.4rem 0.75rem;
}

/* Leaderboards */
.cpld-leaderboards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.cpld-lb-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cpld-lb-note {
  font-size: 0.7rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

.cpld-lb-table-wrap {
  overflow-x: auto;
}

.cpld-lb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.cpld-lb-table th {
  text-align: left;
  padding: 0.3rem 0.5rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted, #64748b);
}

.cpld-lb-table td {
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.cpld-lb-rank {
  color: var(--color-text-muted, #64748b);
  font-size: 0.72rem;
  width: 1.5rem;
}

.cpld-lb-stat {
  font-weight: 700;
}

.cpld-lb-muted {
  color: var(--color-text-muted, #64748b);
}

/* Venue */
.cpld-venue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.cpld-venue-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem 1rem;
}

.cpld-venue-card--selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.cpld-venue-name {
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text, #1e293b);
}

.cpld-venue-stats {
  display: flex;
  gap: 0.75rem;
}

.cpld-venue-stat {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.cpld-venue-stat-val {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.1;
}

.cpld-venue-stat-lbl {
  font-size: 0.65rem;
  color: var(--color-text-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cpld-venue-warn {
  font-size: 0.68rem;
  color: #b45309;
  margin-top: 0.5rem;
}

/* Podcast panel */
.cpld-podcast-panel {
  background: #fafaf9;
  border: 1px solid #e7e5e4;
  border-radius: 8px;
  padding: 1rem;
}

.cpld-podcast-desc {
  font-size: 0.78rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

.cpld-podcast-facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.6rem;
}

.cpld-fact-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
}

.cpld-fact-card--season { border-left: 3px solid #3b82f6; }
.cpld-fact-card--match  { border-left: 3px solid #8b5cf6; }
.cpld-fact-card--player { border-left: 3px solid #10b981; }
.cpld-fact-card--team   { border-left: 3px solid #f59e0b; }
.cpld-fact-card--venue  { border-left: 3px solid #ef4444; }

.cpld-fact-label {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted, #64748b);
  margin-bottom: 0.25rem;
}

.cpld-fact-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text, #1e293b);
}

.cpld-fact-caveat {
  font-size: 0.68rem;
  color: #b45309;
  margin-top: 0.25rem;
}

/* AI placeholder (kept for backward compat, unused) */
.cpld-ai-placeholder {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
}

.cpld-ai-placeholder-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  margin: 0 0 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cpld-ai-placeholder-body {
  font-size: 0.75rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

/* AI Talking-Point Panel */
.cpld-ai-panel {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cpld-ai-panel-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.cpld-ai-panel-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #0c4a6e;
}

.cpld-ai-disclaimer {
  font-size: 0.75rem;
  color: #075985;
  margin: 0;
  background: #e0f2fe;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
}

.cpld-badge--review {
  background: #fef3c7;
  color: #92400e;
}

.cpld-badge--needs-review {
  background: #fff7ed;
  color: #9a3412;
}

.cpld-badge--approved {
  background: #dcfce7;
  color: #166534;
}

.cpld-badge--rejected {
  background: #fee2e2;
  color: #991b1b;
}

/* Fact bundle */
.cpld-ai-bundle {
  background: #ffffff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
}

.cpld-ai-bundle-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #0369a1;
  margin: 0 0 0.4rem;
}

.cpld-ai-bundle-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.cpld-ai-bundle-tag {
  display: inline-block;
  background: #e0f2fe;
  color: #0369a1;
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 500;
}

.cpld-ai-bundle-empty {
  font-size: 0.75rem;
  color: var(--color-text-muted, #64748b);
  margin: 0;
}

/* Insufficient warning */
.cpld-ai-insufficient {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: #92400e;
}

/* Generate row */
.cpld-ai-generate-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.cpld-ai-generate-btn {
  padding: 0.4rem 1rem;
  background: #0369a1;
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.cpld-ai-generate-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cpld-ai-generate-btn--secondary {
  background: #ffffff;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.cpld-ai-error {
  font-size: 0.75rem;
  color: #b91c1c;
  margin: 0;
}

/* AI result */
.cpld-ai-result {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cpld-ai-result-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  font-size: 0.72rem;
  color: var(--color-text-muted, #64748b);
  flex-wrap: wrap;
}

/* Limitations */
.cpld-ai-limitations {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
}

.cpld-ai-limitations-label {
  font-size: 0.75rem;
  font-weight: 700;
  margin: 0 0 0.3rem;
  color: #92400e;
}

.cpld-ai-limitations-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.75rem;
  color: #92400e;
}

/* Talking point cards */
.cpld-tp-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.cpld-tp-card--approved {
  border-color: #86efac;
  background: #f0fdf4;
}

.cpld-tp-card--rejected {
  border-color: #fca5a5;
  background: #fff5f5;
  opacity: 0.75;
}

.cpld-tp-card-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.cpld-tp-section {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #64748b);
}

.cpld-tp-confidence {
  font-size: 0.7rem;
  color: var(--color-text-muted, #64748b);
  margin-left: auto;
}

.cpld-tp-title {
  font-size: 0.88rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text, #1e293b);
}

.cpld-tp-text {
  font-size: 0.82rem;
  color: var(--color-text, #1e293b);
  margin: 0;
  line-height: 1.5;
}

.cpld-tp-edit-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.cpld-tp-edit-area {
  width: 100%;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  font-size: 0.82rem;
  line-height: 1.5;
  resize: vertical;
  box-sizing: border-box;
}

.cpld-tp-edit-actions {
  display: flex;
  gap: 0.35rem;
}

/* Source fact tags */
.cpld-tp-sources {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.cpld-tp-sources-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cpld-tp-source-tag {
  display: inline-block;
  background: #f1f5f9;
  color: #475569;
  border-radius: 3px;
  padding: 0.1rem 0.4rem;
  font-size: 0.68rem;
  font-family: monospace;
}

/* Review action buttons */
.cpld-tp-actions {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}

.cpld-tp-btn {
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.cpld-tp-btn--approve {
  background: #dcfce7;
  color: #166534;
  border-color: #86efac;
}

.cpld-tp-btn--unapprove {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}

.cpld-tp-btn--edit {
  background: #e0f2fe;
  color: #0369a1;
  border-color: #bae6fd;
}

.cpld-tp-btn--save {
  background: #dcfce7;
  color: #166534;
  border-color: #86efac;
}

.cpld-tp-btn--cancel {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}

.cpld-tp-btn--copy {
  background: #f8fafc;
  color: #334155;
  border-color: #e2e8f0;
}

.cpld-tp-btn--reject {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fca5a5;
}

.cpld-tp-rejected-note {
  font-size: 0.72rem;
  color: #991b1b;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

/* Review summary */
.cpld-ai-review-summary {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-muted, #64748b);
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.cpld-ai-review-note {
  font-weight: 500;
  color: #b45309;
}

.cpld-ai-review-note--ok {
  color: #166534;
}

.cpld-script-panel {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cpld-script-panel-header {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  align-items: center;
}

.cpld-script-panel-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1e293b;
}

.cpld-script-desc {
  margin: 0;
  font-size: 0.75rem;
  color: #475569;
}

.cpld-script-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.cpld-script-editor {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.cpld-script-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0.65rem;
  font-size: 0.8rem;
  line-height: 1.45;
  resize: vertical;
  background: #ffffff;
  color: #0f172a;
}

.cpld-script-needs-review {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
}

.cpld-script-needs-review-label {
  margin: 0 0 0.3rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #9a3412;
}

.cpld-script-needs-review-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.74rem;
  color: #9a3412;
}

.cpld-episode-archive {
  border-top: 1px solid #cbd5e1;
  padding-top: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cpld-archive-form {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.cpld-archive-input {
  min-width: 100%;
}

.cpld-archive-objective {
  min-height: 82px;
}

.cpld-archive-note {
  margin: 0;
  font-size: 0.75rem;
  color: #b45309;
}

.cpld-archive-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.cpld-archive-item {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  padding: 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.cpld-archive-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.cpld-archive-meta {
  margin: 0;
  font-size: 0.73rem;
  color: #475569;
}

.cpld-archive-meta--warn {
  color: #9a3412;
}
</style>
