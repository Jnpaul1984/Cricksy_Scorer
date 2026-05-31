<template>
  <div class="tip">
    <!-- Header -->
    <div class="tip-header">
      <h3 class="tip-title">🏆 Tournament Intelligence</h3>
      <p class="tip-subtitle">
        Phase 10S.1 — derived tournament summaries, standings, and champion context from
        validated historical match data. All values are labeled with their derivation source.
        No official standings or championship claims are fabricated.
      </p>
    </div>

    <!-- Provenance bar -->
    <div class="tip-provenance-bar" role="note">
      <span class="tip-provenance-icon">🔒</span>
      <span>Source: validated historical imports only. Derived standings are estimated — not official.</span>
    </div>

    <!-- Tournament selector -->
    <div class="tip-selector-row">
      <div class="tip-filter-group">
        <label class="tip-filter-label" for="ti-competition">Competition</label>
        <select id="ti-competition" v-model="selectedCompetitionCode" class="tip-select" @change="onGroupChange">
          <option value="">— select competition —</option>
          <option
            v-for="group in uniqueCompetitions"
            :key="group.competition_code"
            :value="group.competition_code"
          >
            {{ group.competition_name || group.competition_code }}
          </option>
        </select>
      </div>

      <div class="tip-filter-group">
        <label class="tip-filter-label" for="ti-season">Season</label>
        <select id="ti-season" v-model="selectedSeason" class="tip-select" @change="onGroupChange">
          <option value="">— all seasons —</option>
          <option
            v-for="season in availableSeasons"
            :key="season"
            :value="season"
          >
            {{ season }}
          </option>
        </select>
      </div>

      <div class="tip-filter-group">
        <label class="tip-filter-label" for="ti-gender">Gender</label>
        <select id="ti-gender" v-model="selectedGender" class="tip-select" @change="onGroupChange">
          <option value="">all</option>
          <option value="men">Men</option>
          <option value="women">Women</option>
          <option value="mixed">Mixed</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      <button class="tip-load-btn" :disabled="!selectedCompetitionCode || summaryLoading" @click="loadSummary">
        {{ summaryLoading ? 'Loading…' : 'Load Tournament' }}
      </button>
    </div>

    <!-- Groups loading state -->
    <div v-if="groupsLoading" class="tip-state tip-state--loading" role="status" aria-live="polite">
      <p>Loading tournament groups…</p>
    </div>

    <!-- Groups error -->
    <div v-else-if="groupsError" class="tip-state tip-state--error" role="alert">
      <p>⚠️ Unable to load tournament groups: {{ groupsError }}</p>
      <button class="tip-retry-btn" @click="loadGroups">Retry</button>
    </div>

    <!-- No groups -->
    <div v-else-if="groups && groups.groups.length === 0" class="tip-state tip-state--empty">
      <p class="tip-empty-heading">No tournament groups found</p>
      <p class="tip-empty-body">
        Import historical match data through the <strong>Import Data</strong> tab to build
        tournament intelligence.
      </p>
    </div>

    <!-- Groups overview (before tournament selected) -->
    <div v-else-if="groups && !summary" class="tip-groups-overview">
      <p class="tip-groups-count">
        {{ groups.total_groups }} tournament group{{ groups.total_groups === 1 ? '' : 's' }} found
        across {{ groups.total_matches }} match{{ groups.total_matches === 1 ? '' : 'es' }}.
        Select a competition and season above to explore.
      </p>
      <div class="tip-group-cards">
        <div
          v-for="g in groups.groups"
          :key="groupCardKey(g)"
          class="tip-group-card"
          :class="{ 'tip-group-card--has-champion': g.champion_detected }"
          role="button"
          tabindex="0"
          @click="selectGroup(g)"
          @keydown.enter="selectGroup(g)"
        >
          <div class="tip-group-card-title">
            {{ g.group_key.competition_name || g.group_key.competition_code }}
          </div>
          <div class="tip-group-card-meta">
            <span v-if="g.group_key.season">{{ g.group_key.season }}</span>
            <span class="tip-tag tip-tag--format">{{ g.group_key.format_family }}</span>
            <span class="tip-tag tip-tag--gender">{{ g.group_key.gender_category }}</span>
          </div>
          <div class="tip-group-card-stats">
            <span>{{ g.match_count }} match{{ g.match_count === 1 ? '' : 'es' }}</span>
            <span>{{ g.teams_count }} team{{ g.teams_count === 1 ? '' : 's' }}</span>
          </div>
          <div v-if="g.champion_detected && g.champion_team" class="tip-group-card-champion">
            🏆 {{ g.champion_team }}
          </div>
          <div v-if="!g.has_result_data" class="tip-group-card-warn">
            ⚠ Limited result data
          </div>
        </div>
      </div>
    </div>

    <!-- Summary loading -->
    <div v-if="summaryLoading" class="tip-state tip-state--loading" role="status" aria-live="polite">
      <p>Loading tournament summary…</p>
    </div>

    <!-- Summary error -->
    <div v-else-if="summaryError" class="tip-state tip-state--error" role="alert">
      <p>⚠️ {{ summaryError }}</p>
      <button class="tip-retry-btn" @click="loadSummary">Retry</button>
    </div>

    <!-- Full tournament summary -->
    <div v-else-if="summary" class="tip-summary">

      <!-- Back to groups -->
      <button class="tip-back-btn" @click="clearSummary">← Back to groups</button>

      <!-- Tournament header -->
      <div class="tip-summary-header">
        <h4 class="tip-summary-title">
          {{ summary.group_key.competition_name || summary.group_key.competition_code }}
          <span v-if="summary.group_key.season" class="tip-summary-season">{{ summary.group_key.season }}</span>
        </h4>
        <div class="tip-summary-meta">
          <span class="tip-tag tip-tag--format">{{ summary.group_key.format_family }}</span>
          <span class="tip-tag tip-tag--gender">{{ summary.group_key.gender_category }}</span>
          <span class="tip-tag tip-tag--source">{{ summary.group_key.source_type }}</span>
        </div>
      </div>

      <!-- Data completeness warning -->
      <div class="tip-completeness-bar" role="note" aria-label="Data completeness">
        <strong>Data completeness:</strong>
        {{ summary.data_completeness.matches_with_result }} of {{ summary.data_completeness.total_matches }} matches have result data.
        <span v-if="summary.data_completeness.delivery_complete_matches > 0">
          {{ summary.data_completeness.delivery_complete_matches }} delivery-complete.
        </span>
        <span
          v-if="summary.data_completeness.matches_missing_result > 0"
          class="tip-warn-inline"
        >
          ⚠ {{ summary.data_completeness.matches_missing_result }} missing result.
        </span>
        <span class="tip-confidence-badge" :class="`tip-confidence-badge--${summary.data_completeness.confidence_level}`">
          {{ summary.data_completeness.confidence_level }} confidence
        </span>
      </div>

      <!-- Summary cards -->
      <div class="tip-stat-grid">
        <div class="tip-stat-card">
          <span class="tip-stat-label">Matches</span>
          <span class="tip-stat-val">{{ summary.match_count }}</span>
        </div>
        <div class="tip-stat-card">
          <span class="tip-stat-label">Teams</span>
          <span class="tip-stat-val">{{ summary.teams.length }}</span>
        </div>
        <div class="tip-stat-card">
          <span class="tip-stat-label">Venues</span>
          <span class="tip-stat-val">{{ summary.venues.length }}</span>
        </div>
        <div class="tip-stat-card">
          <span class="tip-stat-label">Total runs</span>
          <span class="tip-stat-val">{{ summary.total_runs.toLocaleString() }}</span>
        </div>
        <div class="tip-stat-card">
          <span class="tip-stat-label">Total wickets</span>
          <span
            class="tip-stat-val"
            :class="{ 'tip-stat-val--unavailable': summary.total_wickets <= 0 }"
            :title="summary.total_wickets <= 0 ? wicketsUnavailableHelperText : undefined"
          >
            {{ summary.total_wickets > 0 ? summary.total_wickets : 'Unavailable' }}
          </span>
        </div>
        <div v-if="summary.highest_team_total" class="tip-stat-card">
          <span class="tip-stat-label">Highest total</span>
          <span class="tip-stat-val">{{ summary.highest_team_total }}</span>
          <span v-if="summary.highest_team_total_by" class="tip-stat-sub">{{ summary.highest_team_total_by }}</span>
        </div>
      </div>

      <!-- Champion / finalist card -->
      <div
        v-if="summary.knockout_context?.champion_team_canonical || summary.knockout_context?.champion_team"
        class="tip-champion-card"
        role="region"
        aria-label="Champion context"
      >
        <div class="tip-champion-icon">🏆</div>
        <div class="tip-champion-body">
          <div class="tip-champion-name">
            {{ summary.knockout_context.champion_team_canonical || summary.knockout_context.champion_team }}
          </div>
          <div class="tip-champion-sub">Champions</div>
          <div v-if="summary.knockout_context.runner_up_team" class="tip-champion-runnerup">
            Runner-up: {{ summary.knockout_context.runner_up_team_canonical || summary.knockout_context.runner_up_team }}
          </div>
          <div v-if="summary.knockout_context.final_result" class="tip-champion-result">
            {{ formatTournamentResult(summary.knockout_context.final_result) }}
          </div>
          <div class="tip-champion-source">
            Source: {{ summary.knockout_context.outcome_source }} —
            <span :class="`tip-confidence-badge tip-confidence-badge--${summary.knockout_context.confidence}`">
              {{ summary.knockout_context.confidence }} confidence
            </span>
          </div>
        </div>
      </div>

      <!-- Key highlights row -->
      <div class="tip-highlights-row">
        <div v-if="summary.biggest_win_by_runs" class="tip-highlight-card">
          <span class="tip-highlight-label">Biggest win (runs)</span>
          <span class="tip-highlight-val">{{ formatHighlightResult(summary.biggest_win_by_runs) }}</span>
          <span class="tip-highlight-match">{{ summary.biggest_win_by_runs.match_title }}</span>
        </div>
        <div v-if="summary.biggest_win_by_wickets" class="tip-highlight-card">
          <span class="tip-highlight-label">Biggest win (wickets)</span>
          <span class="tip-highlight-val">{{ formatHighlightResult(summary.biggest_win_by_wickets) }}</span>
          <span class="tip-highlight-match">{{ summary.biggest_win_by_wickets.match_title }}</span>
        </div>
        <div v-if="summary.closest_match" class="tip-highlight-card">
          <span class="tip-highlight-label">Closest match</span>
          <span class="tip-highlight-val">{{ formatHighlightResult(summary.closest_match) }}</span>
          <span class="tip-highlight-match">{{ summary.closest_match.match_title }}</span>
        </div>
      </div>

      <!-- Top performers -->
      <div v-if="summary.top_run_scorer || summary.top_wicket_taker" class="tip-leaders-row">
        <div v-if="summary.top_run_scorer" class="tip-leader-card">
          <span class="tip-leader-label">Top run scorer</span>
          <span class="tip-leader-name">{{ summary.top_run_scorer.player_name }}</span>
          <span class="tip-leader-val">{{ summary.top_run_scorer.value }} runs</span>
          <span class="tip-leader-source">{{ summary.top_run_scorer.source }}</span>
        </div>
        <div v-if="summary.top_wicket_taker" class="tip-leader-card">
          <span class="tip-leader-label">Top wicket taker</span>
          <span class="tip-leader-name">{{ summary.top_wicket_taker.player_name }}</span>
          <span class="tip-leader-val">{{ summary.top_wicket_taker.value }} wickets</span>
          <span class="tip-leader-source">{{ summary.top_wicket_taker.source }}</span>
        </div>
      </div>

      <!-- Derived standings -->
      <div v-if="summary.derived_standings.length > 0" class="tip-standings-section" role="region" aria-label="Derived standings">
        <div class="tip-standings-header">
          <h5 class="tip-standings-title">Derived Standings</h5>
          <span class="tip-derived-label" title="Not official standings — estimated from imported match results">
            ⚠ {{ summary.standings_label }}
          </span>
        </div>
        <div class="tip-standings-table-wrapper">
          <table class="tip-standings-table">
            <thead>
              <tr>
                <th class="tip-th-team">Team</th>
                <th class="tip-th-num">P</th>
                <th class="tip-th-num">W</th>
                <th class="tip-th-num">L</th>
                <th class="tip-th-num">T</th>
                <th class="tip-th-num">NR</th>
                <th class="tip-th-num">Pts</th>
                <th class="tip-th-num">NRR</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in summary.derived_standings"
                :key="row.team_name"
                class="tip-standings-row"
                :class="{ 'tip-standings-row--first': idx === 0 }"
              >
                <td class="tip-td-team">
                  {{ row.canonical_team_name || row.team_name }}
                  <button
                    class="tip-journey-link"
                    :title="`View ${row.team_name} journey`"
                    @click="loadTeamJourney(row.team_name)"
                  >
                    Journey →
                  </button>
                </td>
                <td class="tip-td-num">{{ row.played }}</td>
                <td class="tip-td-num">{{ row.wins }}</td>
                <td class="tip-td-num">{{ row.losses }}</td>
                <td class="tip-td-num">{{ row.ties }}</td>
                <td class="tip-td-num">{{ row.no_results }}</td>
                <td class="tip-td-num">{{ row.points }}</td>
                <td class="tip-td-num">
                  <span v-if="row.nrr_available">{{ row.net_run_rate?.toFixed(3) }}</span>
                  <span v-else class="tip-na">N/A</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="tip-standings-note">
          Points: 2 = win, 1 = tie/no-result, 0 = loss. Derived from imported match results only.
          NRR computed only when overs data is available.
        </p>
      </div>

      <!-- Podcast facts -->
      <div v-if="summary.podcast_facts" class="tip-podcast-section" role="region" aria-label="Podcast talking points">
        <h5 class="tip-podcast-title">🎙 Podcast Talking Points</h5>
        <div class="tip-podcast-label-bar">
          Source: {{ summary.podcast_facts.source_label }}
          <span :class="`tip-confidence-badge tip-confidence-badge--${summary.podcast_facts.confidence}`">
            {{ summary.podcast_facts.confidence }} confidence
          </span>
        </div>
        <ul class="tip-podcast-facts">
          <li v-if="summary.podcast_facts.champion">
            🏆 <strong>Champion:</strong> {{ summary.podcast_facts.champion }}
          </li>
          <li v-if="summary.podcast_facts.finalist">
            🥈 <strong>Finalist:</strong> {{ summary.podcast_facts.finalist }}
          </li>
          <li v-if="summary.knockout_context?.final_result">
            🎯 <strong>Final result:</strong> {{ formatTournamentResult(summary.knockout_context.final_result) }}
          </li>
          <li v-if="summary.podcast_facts.strongest_team_by_wins">
            📊 <strong>Strongest team (wins):</strong> {{ summary.podcast_facts.strongest_team_by_wins }}
          </li>
          <li v-if="summary.podcast_facts.top_scoring_venue">
            🏟 <strong>Top scoring venue:</strong> {{ summary.podcast_facts.top_scoring_venue }}
          </li>
          <li v-if="summary.podcast_facts.highest_scoring_match_title">
            ⚡ <strong>Highest-scoring match:</strong>
            {{ summary.podcast_facts.highest_scoring_match_title }}
            <span v-if="summary.podcast_facts.highest_match_total_runs">
              ({{ summary.podcast_facts.highest_match_total_runs }} total runs)
            </span>
          </li>
          <li v-if="summary.podcast_facts.key_journey_note">
            📝 {{ formatTournamentResult(summary.podcast_facts.key_journey_note) }}
          </li>
        </ul>
      </div>

      <!-- Team journey -->
      <div v-if="journeyTeamName" class="tip-journey-section" role="region" :aria-label="`${journeyTeamName} journey`">
        <div class="tip-journey-header">
          <h5 class="tip-journey-title">{{ journeyTeamName }} — Tournament Journey</h5>
          <button class="tip-journey-close" @click="clearJourney">× Close</button>
        </div>

        <div v-if="journeyLoading" class="tip-state tip-state--loading" role="status">
          <p>Loading journey…</p>
        </div>
        <div v-else-if="journeyError" class="tip-state tip-state--error" role="alert">
          <p>⚠️ {{ journeyError }}</p>
        </div>
        <div v-else-if="journey">
          <!-- Journey summary -->
          <div class="tip-journey-summary-row">
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">W</span>
              <span class="tip-journey-stat-val tip-journey-stat-val--win">{{ journey.summary.wins }}</span>
            </div>
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">L</span>
              <span class="tip-journey-stat-val tip-journey-stat-val--loss">{{ journey.summary.losses }}</span>
            </div>
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">T</span>
              <span class="tip-journey-stat-val">{{ journey.summary.ties }}</span>
            </div>
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">NR</span>
              <span class="tip-journey-stat-val">{{ journey.summary.no_results }}</span>
            </div>
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">Runs for</span>
              <span class="tip-journey-stat-val">{{ journey.summary.total_runs_for }}</span>
            </div>
            <div class="tip-journey-stat">
              <span class="tip-journey-stat-label">Runs against</span>
              <span class="tip-journey-stat-val">{{ journey.summary.total_runs_against }}</span>
            </div>
          </div>

          <!-- Match list -->
          <table class="tip-journey-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Opponent</th>
                <th>Result</th>
                <th>Outcome</th>
                <th>Stage</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="m in journey.matches"
                :key="m.match_id"
                class="tip-journey-row"
                :class="{
                  'tip-journey-row--win': m.outcome === 'win',
                  'tip-journey-row--loss': m.outcome === 'loss',
                }"
              >
                <td>{{ m.match_date || '—' }}</td>
                <td>{{ m.opponent }}</td>
                <td class="tip-journey-result">{{ formatTournamentResult(m.result) || '—' }}</td>
                <td>
                  <span class="tip-outcome-badge" :class="`tip-outcome-badge--${m.outcome}`">
                    {{ m.outcome }}
                  </span>
                </td>
                <td>{{ m.stage_label || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p class="tip-journey-note">{{ journey.note }}</p>
        </div>
      </div>

      <!-- ── Tournament Podcast Rundown ────────────────────────────── -->
      <div class="tip-podcast-rundown-section" role="region" aria-label="Tournament Podcast Rundown">
        <div class="tip-podcast-rundown-header">
          <h5 class="tip-podcast-rundown-title">🎙 Tournament Podcast Rundown</h5>
          <div class="tip-podcast-rundown-actions">
            <button
              class="tip-btn tip-btn--primary"
              :disabled="!selectedCompetitionCode || podcastRundownLoading"
              @click="generatePodcastRundown"
              data-testid="generate-rundown-btn"
            >
              {{ podcastRundownLoading ? 'Generating…' : 'Generate Rundown' }}
            </button>
            <template v-if="podcastRundown">
              <button
                class="tip-btn tip-btn--copy"
                @click="copyPodcastMarkdown"
                data-testid="copy-md-btn"
              >
                {{ podcastRundownCopied === 'md' ? '✓ Copied' : 'Copy Markdown' }}
              </button>
              <button
                class="tip-btn tip-btn--copy"
                @click="copyPodcastPlainText"
                data-testid="copy-text-btn"
              >
                {{ podcastRundownCopied === 'text' ? '✓ Copied' : 'Copy Plain Text' }}
              </button>
              <button
                class="tip-btn tip-btn--close"
                @click="clearPodcastRundown"
                data-testid="clear-rundown-btn"
              >
                × Clear
              </button>
            </template>
          </div>
        </div>

        <div v-if="podcastRundownLoading" class="tip-state tip-state--loading" role="status">
          <p>Generating podcast rundown…</p>
        </div>
        <div v-else-if="podcastRundownError" class="tip-state tip-state--error" role="alert">
          <p>⚠️ {{ podcastRundownError }}</p>
        </div>
        <div v-else-if="podcastRundown" class="tip-rundown-body">

          <!-- Trust / confidence bar -->
          <div class="tip-provenance-bar" data-testid="rundown-trust-note">
            {{ podcastRundown.source_label }}
            <span :class="`tip-confidence-badge tip-confidence-badge--${podcastRundown.overall_confidence}`">
              {{ podcastRundown.overall_confidence }} confidence
            </span>
          </div>

          <!-- Opening hook (season review narrative) -->
          <div class="tip-rundown-hook" data-testid="season-review-narrative">
            <p>{{ podcastRundown.season_review.narrative }}</p>
            <span :class="`tip-confidence-badge tip-confidence-badge--${podcastRundown.season_review.confidence}`">
              {{ podcastRundown.season_review.confidence }}
            </span>
          </div>

          <!-- Champion journey card -->
          <div
            v-if="podcastRundown.champion_journey"
            class="tip-rundown-card tip-rundown-card--champion"
            data-testid="champion-journey-card"
          >
            <h6 class="tip-rundown-card-title">🏆 Champion Journey</h6>
            <dl class="tip-rundown-dl">
              <template v-if="podcastRundown.champion_journey.champion_team">
                <dt>Champion (detected)</dt>
                <dd>{{ podcastRundown.champion_journey.champion_team }}</dd>
              </template>
              <template v-if="podcastRundown.champion_journey.final_opponent">
                <dt>Final opponent</dt>
                <dd>{{ podcastRundown.champion_journey.final_opponent }}</dd>
              </template>
              <template v-if="podcastRundown.champion_journey.final_result">
                <dt>Final result</dt>
                <dd>{{ formatTournamentResult(podcastRundown.champion_journey.final_result) }}</dd>
              </template>
              <template v-if="podcastRundown.champion_journey.derived_group_standing">
                <dt>Derived standing</dt>
                <dd>{{ podcastRundown.champion_journey.derived_group_standing }}</dd>
              </template>
              <template v-if="podcastRundown.champion_journey.key_note">
                <dt>Note</dt>
                <dd>{{ podcastRundown.champion_journey.key_note }}</dd>
              </template>
            </dl>
            <p class="tip-rundown-source">
              {{ podcastRundown.champion_journey.source_label }}
              <span :class="`tip-confidence-badge tip-confidence-badge--${podcastRundown.champion_journey.confidence}`">
                {{ podcastRundown.champion_journey.confidence }}
              </span>
            </p>
          </div>
          <div v-else class="tip-rundown-card tip-rundown-card--fallback" data-testid="champion-journey-fallback">
            <p>Champion journey unavailable — insufficient data detected.</p>
          </div>

          <!-- Road to the final card -->
          <div
            v-if="podcastRundown.road_to_final"
            class="tip-rundown-card"
            data-testid="road-to-final-card"
          >
            <h6 class="tip-rundown-card-title">🛣 Road to the Final</h6>
            <p v-if="podcastRundown.road_to_final.narrative">{{ podcastRundown.road_to_final.narrative }}</p>
            <dl class="tip-rundown-dl">
              <template v-if="podcastRundown.road_to_final.finalist_a">
                <dt>Finalist A</dt>
                <dd>{{ podcastRundown.road_to_final.finalist_a }}</dd>
              </template>
              <template v-if="podcastRundown.road_to_final.finalist_b">
                <dt>Finalist B</dt>
                <dd>{{ podcastRundown.road_to_final.finalist_b }}</dd>
              </template>
            </dl>
            <p class="tip-rundown-source">{{ podcastRundown.road_to_final.source_label }}</p>
          </div>

          <!-- Additional rundown sections -->
          <div
            v-for="section in podcastRundown.sections"
            :key="section.section_key"
            class="tip-rundown-card"
            :data-testid="`rundown-section-${section.section_key}`"
          >
            <h6 class="tip-rundown-card-title">{{ section.title }}</h6>
            <p v-if="section.body" class="tip-rundown-section-body">{{ formatRundownSectionBody(section) }}</p>
            <span :class="`tip-confidence-badge tip-confidence-badge--${section.confidence}`">
              {{ section.confidence }}
            </span>
          </div>

          <!-- Data trust note footer -->
          <p class="tip-rundown-note" data-testid="rundown-note">{{ podcastRundown.note }}</p>
        </div>
        <div v-else-if="!selectedCompetitionCode" class="tip-rundown-empty">
          <p>Select a competition above, then click <strong>Generate Rundown</strong> to create a presenter-ready podcast rundown.</p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getTournamentGroups,
  getTournamentSummary,
  getTeamJourney,
  getTournamentPodcastRundown,
  type TournamentMatchHighlight,
  type TournamentGroupsResponse,
  type TournamentGroupSummary,
  type TournamentSummaryResponse,
  type TeamJourneyResponse,
  type TournamentPodcastRundown,
} from '@/services/api'
import { normalizeResultDisplayText } from '@/utils/resultDisplay'

// --- State ---

const groups = ref<TournamentGroupsResponse | null>(null)
const groupsLoading = ref(false)
const groupsError = ref<string | null>(null)

const summary = ref<TournamentSummaryResponse | null>(null)
const summaryLoading = ref(false)
const summaryError = ref<string | null>(null)

const journey = ref<TeamJourneyResponse | null>(null)
const journeyLoading = ref(false)
const journeyError = ref<string | null>(null)
const journeyTeamName = ref<string | null>(null)

const podcastRundown = ref<TournamentPodcastRundown | null>(null)
const podcastRundownLoading = ref(false)
const podcastRundownError = ref<string | null>(null)
const podcastRundownCopied = ref<'md' | 'text' | null>(null)

const selectedCompetitionCode = ref('')
const selectedSeason = ref('')
const selectedGender = ref('')
const wicketsUnavailableHelperText =
  'Wicket totals require reliable dismissal/wicket data from imported records.'

// --- Computed ---

const uniqueCompetitions = computed((): { competition_code: string; competition_name: string | null }[] => {
  if (!groups.value) return []
  const seen = new Map<string, string | null>()
  for (const g of groups.value.groups) {
    if (!seen.has(g.group_key.competition_code)) {
      seen.set(g.group_key.competition_code, g.group_key.competition_name)
    }
  }
  return Array.from(seen.entries()).map(([code, name]) => ({ competition_code: code, competition_name: name }))
})

const availableSeasons = computed((): string[] => {
  if (!groups.value || !selectedCompetitionCode.value) return []
  const seasons = new Set<string>()
  for (const g of groups.value.groups) {
    if (g.group_key.competition_code === selectedCompetitionCode.value && g.group_key.season) {
      seasons.add(g.group_key.season)
    }
  }
  return Array.from(seasons).sort().reverse()
})

// --- Lifecycle ---

onMounted(() => {
  loadGroups()
})

// --- Methods ---

async function loadGroups() {
  groupsLoading.value = true
  groupsError.value = null
  try {
    groups.value = await getTournamentGroups()
  } catch (err: unknown) {
    groupsError.value = err instanceof Error ? err.message : 'Failed to load tournament groups'
  } finally {
    groupsLoading.value = false
  }
}

function onGroupChange() {
  summary.value = null
  summaryError.value = null
  podcastRundown.value = null
  podcastRundownError.value = null
  clearJourney()
}

function clearSummary() {
  summary.value = null
  summaryError.value = null
  podcastRundown.value = null
  podcastRundownError.value = null
  clearJourney()
}

function clearJourney() {
  journey.value = null
  journeyError.value = null
  journeyTeamName.value = null
}

async function loadSummary() {
  if (!selectedCompetitionCode.value) return
  summaryLoading.value = true
  summaryError.value = null
  summary.value = null
  podcastRundown.value = null
  podcastRundownError.value = null
  clearJourney()
  try {
    summary.value = await getTournamentSummary(
      selectedCompetitionCode.value,
      selectedSeason.value || null,
      selectedGender.value || undefined,
    )
  } catch (err: unknown) {
    summaryError.value =
      err instanceof Error ? err.message : 'Failed to load tournament summary'
  } finally {
    summaryLoading.value = false
  }
}

function selectGroup(g: TournamentGroupSummary) {
  selectedCompetitionCode.value = g.group_key.competition_code
  selectedSeason.value = g.group_key.season ?? ''
  selectedGender.value = g.group_key.gender_category === 'unknown' ? '' : g.group_key.gender_category
  loadSummary()
}

async function loadTeamJourney(teamName: string) {
  if (!summary.value) return
  journeyTeamName.value = teamName
  journeyLoading.value = true
  journeyError.value = null
  journey.value = null
  try {
    journey.value = await getTeamJourney(
      summary.value.group_key.competition_code,
      teamName,
      summary.value.group_key.season,
      summary.value.group_key.gender_category === 'unknown'
        ? undefined
        : summary.value.group_key.gender_category,
    )
  } catch (err: unknown) {
    journeyError.value =
      err instanceof Error ? err.message : `Failed to load journey for ${teamName}`
  } finally {
    journeyLoading.value = false
  }
}

async function generatePodcastRundown() {
  if (!selectedCompetitionCode.value) return
  podcastRundownLoading.value = true
  podcastRundownError.value = null
  podcastRundown.value = null
  try {
    podcastRundown.value = await getTournamentPodcastRundown(
      selectedCompetitionCode.value,
      selectedSeason.value || null,
      selectedGender.value || undefined,
    )
  } catch (err: unknown) {
    podcastRundownError.value =
      err instanceof Error ? err.message : 'Failed to generate podcast rundown'
  } finally {
    podcastRundownLoading.value = false
  }
}

function clearPodcastRundown() {
  podcastRundown.value = null
  podcastRundownError.value = null
  podcastRundownCopied.value = null
}

function buildPodcastMarkdown(rundown: TournamentPodcastRundown): string {
  const comp = rundown.group_key.competition_name || rundown.group_key.competition_code
  const season = rundown.group_key.season || ''
  const lines: string[] = [
    `# ${comp} ${season} — Tournament Podcast Rundown`,
    '',
    `> ${rundown.source_label}`,
    '',
    `**Overall confidence:** ${rundown.overall_confidence}`,
    '',
    '## Season Review',
    '',
    rundown.season_review.narrative,
    '',
  ]
  if (rundown.champion_journey) {
    const cj = rundown.champion_journey
    lines.push('## Champion Journey', '')
    if (cj.champion_team) lines.push(`**Champion (detected):** ${cj.champion_team}`)
    if (cj.final_opponent) lines.push(`**Final opponent:** ${cj.final_opponent}`)
    if (cj.final_result) lines.push(`**Final result:** ${normalizeResultDisplayText(cj.final_result) || cj.final_result}`)
    if (cj.derived_group_standing) lines.push(`**Derived standing:** ${cj.derived_group_standing}`)
    if (cj.key_note) lines.push(`**Note:** ${cj.key_note}`)
    lines.push(`*${cj.source_label}*`, '')
  }
  if (rundown.road_to_final) {
    const rf = rundown.road_to_final
    lines.push('## Road to the Final', '')
    if (rf.narrative) lines.push(rf.narrative)
    lines.push(`*${rf.source_label}*`, '')
  }
  for (const section of rundown.sections) {
    if (section.section_key === 'opening_hook') continue
    lines.push(`## ${section.title}`, '')
    const sectionBody = formatRundownSectionBody(section)
    if (sectionBody) lines.push(sectionBody)
    lines.push('')
  }
  lines.push('---', `*${rundown.note}*`)
  return lines.join('\n')
}

function buildPodcastPlainText(rundown: TournamentPodcastRundown): string {
  const comp = rundown.group_key.competition_name || rundown.group_key.competition_code
  const season = rundown.group_key.season || ''
  const lines: string[] = [
    `${comp} ${season} — TOURNAMENT PODCAST RUNDOWN`,
    '='.repeat(50),
    '',
    rundown.source_label,
    `Confidence: ${rundown.overall_confidence}`,
    '',
    'SEASON REVIEW',
    '-'.repeat(30),
    rundown.season_review.narrative,
    '',
  ]
  if (rundown.champion_journey) {
    const cj = rundown.champion_journey
    lines.push('CHAMPION JOURNEY', '-'.repeat(30))
    if (cj.champion_team) lines.push(`Champion (detected): ${cj.champion_team}`)
    if (cj.final_opponent) lines.push(`Final opponent: ${cj.final_opponent}`)
    if (cj.final_result) lines.push(`Final result: ${normalizeResultDisplayText(cj.final_result) || cj.final_result}`)
    if (cj.derived_group_standing) lines.push(`Derived standing: ${cj.derived_group_standing}`)
    if (cj.key_note) lines.push(`Note: ${cj.key_note}`)
    lines.push(cj.source_label, '')
  }
  if (rundown.road_to_final) {
    const rf = rundown.road_to_final
    lines.push('ROAD TO THE FINAL', '-'.repeat(30))
    if (rf.narrative) lines.push(rf.narrative)
    lines.push(rf.source_label, '')
  }
  for (const section of rundown.sections) {
    if (section.section_key === 'opening_hook') continue
    lines.push(section.title.toUpperCase(), '-'.repeat(30))
    const sectionBody = formatRundownSectionBody(section)
    if (sectionBody) lines.push(sectionBody)
    lines.push('')
  }
  lines.push('='.repeat(50), rundown.note)
  return lines.join('\n')
}

async function copyPodcastMarkdown() {
  if (!podcastRundown.value) return
  const text = buildPodcastMarkdown(podcastRundown.value)
  await navigator.clipboard.writeText(text)
  podcastRundownCopied.value = 'md'
  setTimeout(() => { podcastRundownCopied.value = null }, 2500)
}

async function copyPodcastPlainText() {
  if (!podcastRundown.value) return
  const text = buildPodcastPlainText(podcastRundown.value)
  await navigator.clipboard.writeText(text)
  podcastRundownCopied.value = 'text'
  setTimeout(() => { podcastRundownCopied.value = null }, 2500)
}

function groupCardKey(g: TournamentGroupSummary): string {
  const k = g.group_key
  return `${k.competition_code}__${k.season ?? 'all'}__${k.gender_category}__${k.format_family}`
}

function formatTournamentResult(result: string | null | undefined): string {
  return normalizeResultDisplayText(result) || result || ''
}

function stripLeadingLabel(text: string, label: string): string {
  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(`^\\s*(?:${escapedLabel}\\s*)+`, 'i'), '').trimStart()
}

function normalizeClosestFinishText(text: string): string {
  const normalized = normalizeResultDisplayText(text) || text
  return `Closest finish: ${stripLeadingLabel(normalized, 'Closest finish:')}`
}

function formatRundownSectionBody(section: { section_key: string; body?: string | null }): string {
  const body = section.body || ''
  if (!body) return ''
  if (section.section_key !== 'key_matches') return body

  return body
    .split('\n')
    .map((line) => {
      const trimmed = line.trimStart()
      if (/^closest finish:/i.test(trimmed)) return normalizeClosestFinishText(trimmed)
      return normalizeResultDisplayText(line) || line
    })
    .join('\n')
}

function formatHighlightResult(highlight: TournamentMatchHighlight | null | undefined): string {
  if (!highlight) return ''
  const raw = formatTournamentResult(highlight.detail) || formatTournamentResult(highlight.result)
  if (highlight.highlight_type === 'closest_match' && raw) {
    return stripLeadingLabel(raw, 'Closest finish:')
  }
  return raw
}
</script>

<style scoped>
.tip {
  font-size: 0.875rem;
  color: var(--color-text, #e2e8f0);
}

.tip-header {
  margin-bottom: 1rem;
}
.tip-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
}
.tip-subtitle {
  margin: 0;
  color: var(--color-text-muted, #6b7280);
  font-size: 0.8rem;
}

.tip-provenance-bar {
  background: rgba(15, 23, 42, 0.72);
  border-left: 3px solid rgba(59, 130, 246, 0.9);
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.78rem;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.tip-provenance-icon { font-size: 0.85rem; }

.tip-selector-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-end;
  margin-bottom: 1.25rem;
}
.tip-filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.tip-filter-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted, #6b7280);
}
.tip-select {
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  background: var(--color-surface, #fff);
  font-size: 0.82rem;
  min-width: 160px;
}
.tip-load-btn {
  padding: 0.4rem 1rem;
  background: var(--color-brand, #1d6aff);
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  height: 2rem;
  align-self: flex-end;
}
.tip-load-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tip-state {
  padding: 1.5rem;
  text-align: center;
  border-radius: 8px;
  margin: 1rem 0;
}
.tip-state--loading { background: var(--color-surface-alt, #f0f4f8); }
.tip-state--error { background: #fff2f2; color: #c0392b; }
.tip-state--empty { background: var(--color-surface-alt, #f0f4f8); color: var(--color-text-muted, #6b7280); }

.tip-retry-btn {
  margin-top: 0.5rem;
  padding: 0.3rem 0.8rem;
  border: 1px solid currentColor;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.8rem;
}

.tip-empty-heading { font-weight: 700; margin-bottom: 0.25rem; }
.tip-empty-body { font-size: 0.8rem; }

.tip-groups-count {
  color: var(--color-text-muted, #6b7280);
  font-size: 0.8rem;
  margin-bottom: 0.75rem;
}

.tip-group-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.tip-group-card {
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 8px;
  padding: 0.75rem;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  background: var(--color-surface, #fff);
}
.tip-group-card:hover,
.tip-group-card:focus {
  border-color: var(--color-brand, #1d6aff);
  box-shadow: 0 2px 8px rgba(29, 106, 255, 0.12);
  outline: none;
}
.tip-group-card--has-champion {
  border-color: var(--color-brand, #1d6aff);
}

.tip-group-card-title {
  font-weight: 700;
  font-size: 0.88rem;
  margin-bottom: 0.3rem;
}
.tip-group-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.3rem;
}
.tip-group-card-stats {
  font-size: 0.77rem;
  color: var(--color-text-muted, #6b7280);
  display: flex;
  gap: 0.5rem;
}
.tip-group-card-champion {
  font-size: 0.77rem;
  color: var(--color-brand, #1d6aff);
  font-weight: 600;
  margin-top: 0.3rem;
}
.tip-group-card-warn {
  font-size: 0.75rem;
  color: #e67e22;
  margin-top: 0.3rem;
}

.tip-tag {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 10px;
  font-weight: 600;
}
.tip-tag--format { background: rgba(56, 189, 248, 0.18); color: #bae6fd; }
.tip-tag--gender { background: rgba(250, 204, 21, 0.2); color: #fde68a; }
.tip-tag--source { background: rgba(74, 222, 128, 0.16); color: #bbf7d0; }

/* Summary layout */
.tip-back-btn {
  background: none;
  border: none;
  color: var(--color-brand, #1d6aff);
  cursor: pointer;
  font-size: 0.82rem;
  padding: 0.25rem 0;
  margin-bottom: 0.75rem;
}

.tip-summary-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}
.tip-summary-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}
.tip-summary-season {
  color: var(--color-text-muted, #6b7280);
  font-weight: 400;
  margin-left: 0.3rem;
}
.tip-summary-meta {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
  align-items: center;
}

.tip-completeness-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(251, 191, 36, 0.45);
  border-left: 3px solid rgba(251, 191, 36, 0.8);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-size: 0.78rem;
  margin-bottom: 1rem;
  color: #f8fafc;
}
.tip-completeness-bar strong {
  color: #fef3c7;
}
.tip-warn-inline { color: #fbbf24; font-weight: 600; }

.tip-confidence-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border: 1px solid transparent;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 700;
}
.tip-confidence-badge--high { background: rgba(22, 163, 74, 0.2); border-color: rgba(74, 222, 128, 0.45); color: #bbf7d0; }
.tip-confidence-badge--medium { background: rgba(251, 191, 36, 0.2); border-color: rgba(251, 191, 36, 0.45); color: #fde68a; }
.tip-confidence-badge--low { background: rgba(220, 38, 38, 0.2); border-color: rgba(248, 113, 113, 0.45); color: #fecaca; }
.tip-confidence-badge--unknown { background: rgba(148, 163, 184, 0.2); border-color: rgba(148, 163, 184, 0.45); color: #cbd5e1; }

.tip-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.tip-stat-card {
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.tip-stat-label {
  font-size: 0.72rem;
  color: #cbd5e1;
  font-weight: 600;
}
.tip-stat-val {
  font-size: 1.15rem;
  font-weight: 700;
  color: #f8fafc;
}
.tip-stat-val--unavailable {
  font-size: 1rem;
  white-space: nowrap;
  word-break: keep-all;
}
.tip-stat-sub {
  font-size: 0.7rem;
  color: #93c5fd;
}

.tip-champion-card {
  background: linear-gradient(135deg, rgba(120, 53, 15, 0.4), rgba(30, 41, 59, 0.92));
  border: 1px solid rgba(245, 158, 11, 0.65);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.tip-champion-icon { font-size: 1.5rem; }
.tip-champion-body { display: flex; flex-direction: column; gap: 0.2rem; }
.tip-champion-name { font-size: 1rem; font-weight: 700; color: #fef3c7; }
.tip-champion-sub { font-size: 0.75rem; color: #fde68a; font-weight: 600; }
.tip-champion-runnerup { font-size: 0.8rem; color: #f8fafc; }
.tip-champion-result { font-size: 0.78rem; color: #e2e8f0; }
.tip-champion-source { font-size: 0.72rem; color: #cbd5e1; }

.tip-highlights-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.tip-highlight-card {
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.tip-highlight-label { font-size: 0.72rem; color: #cbd5e1; font-weight: 600; }
.tip-highlight-val { font-size: 0.85rem; font-weight: 600; color: #f8fafc; }
.tip-highlight-match { font-size: 0.72rem; color: #94a3b8; }

.tip-leaders-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.tip-leader-card {
  background: var(--color-surface-alt, #f0f4f8);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 180px;
}
.tip-leader-label { font-size: 0.72rem; color: var(--color-text-muted, #6b7280); font-weight: 600; }
.tip-leader-name { font-size: 0.9rem; font-weight: 700; }
.tip-leader-val { font-size: 0.82rem; }
.tip-leader-source { font-size: 0.7rem; color: var(--color-text-muted, #6b7280); }

/* Derived standings */
.tip-standings-section {
  margin-bottom: 1.25rem;
}
.tip-standings-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}
.tip-standings-title { font-size: 0.88rem; font-weight: 700; margin: 0; }
.tip-derived-label {
  font-size: 0.72rem;
  background: rgba(251, 191, 36, 0.2);
  color: #fde68a;
  border: 1px solid rgba(251, 191, 36, 0.45);
  border-radius: 10px;
  padding: 0.1rem 0.5rem;
}

.tip-standings-table-wrapper {
  overflow-x: auto;
  border: 1px solid rgba(148, 163, 184, 0.32);
  background: rgba(15, 23, 42, 0.72);
  border-radius: 8px;
}
.tip-standings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}
.tip-standings-table th,
.tip-standings-table td {
  padding: 0.35rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(148, 163, 184, 0.28);
  color: #e2e8f0;
}
.tip-standings-table th { background: rgba(15, 23, 42, 0.85); color: #f8fafc; }
.tip-th-team { min-width: 160px; }
.tip-th-num, .tip-td-num { text-align: center; font-variant-numeric: tabular-nums; }
.tip-standings-row:hover { background: rgba(30, 41, 59, 0.72); }
.tip-standings-row--first .tip-td-team { font-weight: 700; }
.tip-td-team {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.tip-journey-link {
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(96, 165, 250, 0.7);
  color: #bfdbfe;
  font-size: 0.68rem;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.tip-journey-link:hover { background: rgba(37, 99, 235, 0.28); }
.tip-na { color: #94a3b8; font-size: 0.75rem; }
.tip-standings-note {
  font-size: 0.72rem;
  color: #cbd5e1;
  margin: 0.25rem 0 0;
}

/* Podcast */
.tip-podcast-section {
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
}
.tip-podcast-title { font-size: 0.88rem; font-weight: 700; margin: 0 0 0.35rem; color: #f8fafc; }
.tip-podcast-label-bar { font-size: 0.72rem; color: #cbd5e1; margin-bottom: 0.5rem; }
.tip-podcast-facts {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.82rem;
  color: #e2e8f0;
}
.tip-podcast-facts li { border-bottom: 1px solid rgba(148, 163, 184, 0.2); padding-bottom: 0.2rem; }
.tip-podcast-facts li:last-child { border-bottom: none; padding-bottom: 0; }

/* Team journey */
.tip-journey-section {
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-top: 1rem;
}
.tip-journey-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.tip-journey-title { font-size: 0.88rem; font-weight: 700; margin: 0; }
.tip-journey-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: var(--color-text-muted, #6b7280);
}

.tip-journey-summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.tip-journey-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--color-surface-alt, #f0f4f8);
  border-radius: 6px;
  padding: 0.4rem 0.6rem;
  min-width: 60px;
}
.tip-journey-stat-label { font-size: 0.68rem; color: var(--color-text-muted, #6b7280); font-weight: 600; }
.tip-journey-stat-val { font-size: 1rem; font-weight: 700; }
.tip-journey-stat-val--win { color: #065f46; }
.tip-journey-stat-val--loss { color: #991b1b; }

.tip-journey-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
  margin-bottom: 0.5rem;
}
.tip-journey-table th,
.tip-journey-table td {
  padding: 0.3rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}
.tip-journey-row--win { background: rgba(16, 185, 129, 0.05); }
.tip-journey-row--loss { background: rgba(239, 68, 68, 0.05); }
.tip-journey-result { max-width: 220px; word-break: break-word; }

.tip-outcome-badge {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.tip-outcome-badge--win { background: #d1fae5; color: #065f46; }
.tip-outcome-badge--loss { background: #fee2e2; color: #991b1b; }
.tip-outcome-badge--tie { background: #fef3c7; color: #92400e; }
.tip-outcome-badge--no_result { background: #f1f5f9; color: #6b7280; }
.tip-outcome-badge--unknown { background: #f1f5f9; color: #9ca3af; }

.tip-journey-note { font-size: 0.72rem; color: var(--color-text-muted, #6b7280); }

/* ── Podcast Rundown ──────────────────────────────── */
.tip-podcast-rundown-section {
  margin-top: 2rem;
  padding: 1rem 1.25rem;
  background: rgba(15, 23, 42, 0.55);
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.tip-podcast-rundown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.tip-podcast-rundown-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}

.tip-podcast-rundown-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.tip-btn {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.3rem 0.75rem;
  border-radius: 5px;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}
.tip-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.tip-btn--primary {
  background: rgba(59, 130, 246, 0.85);
  color: #f8fafc;
}
.tip-btn--primary:not(:disabled):hover {
  background: rgba(59, 130, 246, 1);
}
.tip-btn--copy {
  background: rgba(51, 65, 85, 0.8);
  color: #e2e8f0;
}
.tip-btn--copy:hover {
  background: rgba(71, 85, 105, 0.9);
}
.tip-btn--close {
  background: transparent;
  color: var(--color-text-muted, #6b7280);
  border: 1px solid rgba(100, 116, 139, 0.4);
}
.tip-btn--close:hover { color: #e2e8f0; }

.tip-rundown-body { margin-top: 0.5rem; }

.tip-rundown-hook {
  background: rgba(51, 65, 85, 0.45);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  font-style: italic;
  font-size: 0.875rem;
  color: var(--color-text, #e2e8f0);
}

.tip-rundown-card {
  background: rgba(30, 41, 59, 0.55);
  border: 1px solid rgba(100, 116, 139, 0.18);
  border-radius: 6px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.65rem;
}
.tip-rundown-card--champion {
  border-left: 3px solid #f59e0b;
}
.tip-rundown-card--fallback {
  opacity: 0.65;
  font-style: italic;
  font-size: 0.8rem;
}

.tip-rundown-card-title {
  font-size: 0.88rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
}

.tip-rundown-dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.2rem 0.75rem;
  font-size: 0.8rem;
  margin: 0 0 0.5rem;
}
.tip-rundown-dl dt {
  color: var(--color-text-muted, #9ca3af);
  font-weight: 600;
}
.tip-rundown-dl dd { margin: 0; color: var(--color-text, #e2e8f0); }

.tip-rundown-section-body {
  font-size: 0.83rem;
  color: var(--color-text, #cbd5e1);
  white-space: pre-line;
  margin: 0.25rem 0;
}

.tip-rundown-source {
  font-size: 0.71rem;
  color: var(--color-text-muted, #6b7280);
  margin: 0.4rem 0 0;
}

.tip-rundown-note {
  font-size: 0.72rem;
  color: var(--color-text-muted, #6b7280);
  margin-top: 0.5rem;
  border-top: 1px solid rgba(100, 116, 139, 0.15);
  padding-top: 0.4rem;
}

.tip-rundown-empty {
  font-size: 0.83rem;
  color: var(--color-text-muted, #6b7280);
  font-style: italic;
}
</style>
