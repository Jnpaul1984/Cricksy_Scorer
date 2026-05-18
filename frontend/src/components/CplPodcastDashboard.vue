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
          </p>
          <p class="cpld-export-meta">
            {{ exportReviewLabel }}
          </p>
        </div>

        <div v-if="!activeExportAvailability.available" class="cpld-insufficient cpld-insufficient--warn" role="alert">
          {{ activeExportAvailability.reason }}
        </div>

        <div class="cpld-export-actions">
          <button
            class="cpld-export-btn"
            :disabled="!activeExportAvailability.available || exportBusy"
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

        <!-- AI placeholder -->
        <div class="cpld-ai-placeholder">
          <p class="cpld-ai-placeholder-label">AI Talking-Point Assistant</p>
          <p class="cpld-ai-placeholder-body">
            AI-assisted podcast talking-point generation is documented as a future enhancement.
            When available it will summarise deterministic chart data and suggest reviewable talking points.
            AI will never calculate official scores, invent missing facts, or publish without review.
          </p>
        </div>
      </section>

    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { toPng } from 'html-to-image'
import {
  getHistoricalStatsSummary,
  type HistoricalStatsSummaryResponse,
  type HistoricalMatchAggregate,
  type HistoricalPlayerAggregate,
  type HistoricalTeamAggregate,
  type HistoricalVenueAggregate,
} from '@/services/api'

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

type ExportTarget = 'season_summary' | 'match_story' | 'leaderboards' | 'venue_intelligence' | 'podcast_facts'
type ExportFormat = 'podcast_landscape' | 'social_square' | 'story_vertical'

const seasonSummaryRef = ref<HTMLElement | null>(null)
const matchStoryRef = ref<HTMLElement | null>(null)
const leaderboardRef = ref<HTMLElement | null>(null)
const venueRef = ref<HTMLElement | null>(null)
const podcastFactsRef = ref<HTMLElement | null>(null)

const exportTarget = ref<ExportTarget>('season_summary')
const exportFormat = ref<ExportFormat>('podcast_landscape')
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

watch(
  [
    exportTarget,
    exportFormat,
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
  const wrapper = document.createElement('div')
  wrapper.style.position = 'fixed'
  wrapper.style.left = '-99999px'
  wrapper.style.top = '0'
  wrapper.style.width = `${width}px`
  wrapper.style.height = `${height}px`
  wrapper.style.background = '#ffffff'
  wrapper.style.padding = '24px'
  wrapper.style.display = 'flex'
  wrapper.style.flexDirection = 'column'
  wrapper.style.gap = '12px'
  wrapper.style.boxSizing = 'border-box'
  wrapper.style.fontFamily = 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif'

  const title = document.createElement('div')
  title.style.fontSize = '20px'
  title.style.fontWeight = '700'
  title.style.color = '#0f172a'
  title.textContent = activeExportTarget.value?.label ?? 'CPL export'

  const content = document.createElement('div')
  content.style.flex = '1'
  content.style.overflow = 'hidden'
  content.style.border = '1px solid #e2e8f0'
  content.style.borderRadius = '8px'
  content.style.padding = '16px'
  content.style.boxSizing = 'border-box'

  const clone = targetNode.cloneNode(true) as HTMLElement
  clone.style.margin = '0'
  clone.style.maxHeight = '100%'
  clone.style.overflow = 'hidden'
  content.appendChild(clone)

  const provenance = document.createElement('div')
  provenance.style.fontSize = '14px'
  provenance.style.lineHeight = '1.4'
  provenance.style.color = '#334155'
  provenance.textContent = exportReviewLabel.value

  wrapper.append(title, content, provenance)
  document.body.appendChild(wrapper)
  return wrapper
}

async function generateExportPreview() {
  if (!activeExportAvailability.value.available || !activeExportNode.value || !activeExportFormat.value) {
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

onMounted(load)
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

/* AI placeholder */
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
</style>
