<template>
  <div class="hae">
    <div class="hae-header">
      <h3 class="hae-title">📚 Historical Archive Explorer</h3>
      <p class="hae-subtitle">
        Compare imported competitions and seasons across the historical archive with careful derived-data
        language for champions, finals, venue trends, and era stories.
      </p>
    </div>

    <div class="hae-note" role="note">
      Derived from imported match data only. Archive comparisons are not official, incomplete seasons may
      affect comparisons, and wicket trends use delivery-derived dismissal records only where available.
    </div>

    <div class="hae-filters">
      <label class="hae-filter">
        <span>Competition</span>
        <select v-model="filters.competitionCode">
          <option value="">All competitions</option>
          <option v-for="option in competitionOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="hae-filter">
        <span>Format</span>
        <select v-model="filters.formatFamily">
          <option value="">All formats</option>
          <option value="T20">T20</option>
          <option value="ODI">ODI</option>
          <option value="TEST">Test</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>

      <label class="hae-filter">
        <span>Gender</span>
        <select v-model="filters.genderCategory">
          <option value="">All</option>
          <option value="men">Men</option>
          <option value="women">Women</option>
          <option value="mixed">Mixed</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>

      <label class="hae-filter">
        <span>Season start</span>
        <input v-model="filters.seasonStart" type="number" min="0" placeholder="e.g. 2020" />
      </label>

      <label class="hae-filter">
        <span>Season end</span>
        <input v-model="filters.seasonEnd" type="number" min="0" placeholder="e.g. 2025" />
      </label>

      <label class="hae-filter">
        <span>Minimum matches</span>
        <input v-model="filters.minimumMatches" type="number" min="1" />
      </label>

      <label class="hae-checkbox">
        <input v-model="filters.includeIncomplete" type="checkbox" />
        <span>Include incomplete seasons</span>
      </label>

      <div class="hae-actions">
        <button class="hae-btn hae-btn--primary" @click="loadArchive">Apply filters</button>
      </div>
    </div>

    <div v-if="loading" class="hae-state hae-state--loading" role="status" aria-live="polite">
      Loading archive comparisons…
    </div>

    <div v-else-if="error" class="hae-state hae-state--error" role="alert">
      {{ error }}
    </div>

    <div v-else-if="!archive || archive.comparison_rows.length === 0" class="hae-state hae-state--empty">
      No archive groups matched the current filters.
    </div>

    <template v-else>
      <div class="hae-overview">
        <div class="hae-overview-card">
          <span class="hae-overview-label">Filtered groups</span>
          <strong>{{ archive.total_groups }}</strong>
        </div>
        <div class="hae-overview-card">
          <span class="hae-overview-label">Imported matches</span>
          <strong>{{ archive.total_matches }}</strong>
        </div>
        <div class="hae-overview-card">
          <span class="hae-overview-label">Selected competition</span>
          <strong>{{ selectedCompetitionLabel }}</strong>
        </div>
      </div>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Competition / season comparison</h4>
          <p>All champion, final, and standings context shown here is derived and not official.</p>
        </div>
        <div class="hae-table-wrap">
          <table class="hae-table" data-testid="archive-comparison-table">
            <thead>
              <tr>
                <th>Competition</th>
                <th>Season</th>
                <th>Format</th>
                <th>Gender</th>
                <th>Imported matches</th>
                <th>Teams</th>
                <th>Venues</th>
                <th>Champion</th>
                <th>Runner-up</th>
                <th>Total runs</th>
                <th>Total wickets</th>
                <th>Avg runs / match</th>
                <th>Avg runs / wicket</th>
                <th>Data trust</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in archive.comparison_rows" :key="comparisonKey(row)">
                <td>{{ row.group_key.competition_name || row.group_key.competition_code }}</td>
                <td>{{ row.group_key.season || 'Unknown' }}</td>
                <td>{{ row.group_key.format_family }}</td>
                <td>{{ row.group_key.gender_category }}</td>
                <td>{{ row.imported_matches }}</td>
                <td>{{ row.teams_count }}</td>
                <td>{{ row.venues_count }}</td>
                <td>{{ row.champion_detected || 'Unavailable' }}</td>
                <td>{{ row.runner_up_detected || 'Unavailable' }}</td>
                <td>{{ row.total_runs.toLocaleString() }}</td>
                <td>{{ row.total_wickets ?? 'Unavailable' }}</td>
                <td>{{ formatMetric(row.average_runs_per_match) }}</td>
                <td>{{ formatMetric(row.average_runs_per_wicket) }}</td>
                <td>
                  <div>{{ row.data_completeness_label }}</div>
                  <div class="hae-table-note">{{ row.confidence }} confidence</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Era comparison cards</h4>
          <p>Cards fall back safely when archive coverage is too thin.</p>
        </div>
        <div class="hae-card-grid">
          <article v-for="card in archive.era_comparison_cards" :key="card.card_key" class="hae-card">
            <span class="hae-card-label">{{ card.title }}</span>
            <strong class="hae-card-value">{{ card.value }}</strong>
            <p class="hae-card-subtitle">{{ card.subtitle || card.note }}</p>
          </article>
        </div>
      </section>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Champion history</h4>
          <p>{{ archive.champion_history_note }}</p>
        </div>

        <div v-if="archive.champion_history.length === 0" class="hae-inline-empty">
          Select a competition to view a year-by-year champion timeline.
        </div>

        <div v-else class="hae-table-wrap">
          <table class="hae-table" data-testid="champion-history-table">
            <thead>
              <tr>
                <th>Season</th>
                <th>Champion detected</th>
                <th>Runner-up detected</th>
                <th>Final result</th>
                <th>Confidence / source</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in archive.champion_history" :key="entry.season || `season-${entry.season_year}`">
                <td>{{ entry.season || entry.season_year || 'Unknown' }}</td>
                <td>{{ entry.champion_detected || 'Unavailable' }}</td>
                <td>{{ entry.runner_up_detected || 'Unavailable' }}</td>
                <td>{{ normalizeResultDisplayText(entry.final_result) || 'Unavailable' }}</td>
                <td>{{ entry.confidence }} · {{ entry.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Dynasty / repeat-success indicators</h4>
          <p>Detected titles, derived finals, and estimated standings only.</p>
        </div>
        <div class="hae-card-grid">
          <article v-for="indicator in archive.dynasty_indicators" :key="indicator.metric_key" class="hae-card">
            <span class="hae-card-label">{{ indicator.title }}</span>
            <strong class="hae-card-value">
              {{ indicator.team_name ? `${indicator.team_name} — ${indicator.value}` : indicator.value }}
            </strong>
            <p class="hae-card-subtitle">{{ indicator.subtitle || indicator.note }}</p>
          </article>
        </div>
      </section>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Venue trends</h4>
          <p>Average venue metrics are withheld for one-match samples.</p>
        </div>
        <div class="hae-table-wrap">
          <table class="hae-table" data-testid="venue-trends-table">
            <thead>
              <tr>
                <th>Venue</th>
                <th>Matches</th>
                <th>Total runs</th>
                <th>Avg runs / match</th>
                <th>Total wickets</th>
                <th>Wickets / match</th>
                <th>Sample note</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="venue in archive.venue_trends" :key="venue.venue">
                <td>{{ venue.venue }}</td>
                <td>{{ venue.matches }}</td>
                <td>{{ venue.total_runs.toLocaleString() }}</td>
                <td>{{ formatMetric(venue.average_runs_per_match) }}</td>
                <td>{{ venue.total_wickets ?? 'Unavailable' }}</td>
                <td>{{ formatMetric(venue.wickets_per_match) }}</td>
                <td>{{ venue.sample_note }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="hae-section">
        <div class="hae-section-header">
          <h4>Archive podcast / research summary</h4>
          <p>Deterministic archive copy with the required trust note.</p>
        </div>

        <div class="hae-copy-actions">
          <button
            class="hae-btn"
            data-testid="archive-copy-md-btn"
            :disabled="!archive.research_summary.markdown"
            @click="copyText('md')"
          >
            {{ copiedKind === 'md' ? '✓ Copied' : 'Copy Markdown' }}
          </button>
          <button
            class="hae-btn"
            data-testid="archive-copy-text-btn"
            :disabled="!archive.research_summary.plain_text"
            @click="copyText('text')"
          >
            {{ copiedKind === 'text' ? '✓ Copied' : 'Copy Plain Text' }}
          </button>
        </div>

        <div class="hae-summary">
          <article
            v-for="section in archive.research_summary.sections"
            :key="section.section_key"
            class="hae-summary-section"
          >
            <h5>{{ section.title }}</h5>
            <p>{{ section.body || 'Unavailable for the current archive filters.' }}</p>
          </article>
        </div>
      </section>

      <div class="hae-footer-note" data-testid="archive-trust-note">
        {{ archive.trust_note }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  getHistoricalArchiveExplorer,
  getTournamentGroups,
  type HistoricalArchiveExplorerResponse,
  type HistoricalArchiveExplorerFilters,
  type TournamentGroupSummary,
} from '@/services/api'
import { normalizeResultDisplayText } from '@/utils/resultDisplay'

type CopyKind = 'md' | 'text' | null

const loading = ref(false)
const error = ref('')
const archive = ref<HistoricalArchiveExplorerResponse | null>(null)
const groups = ref<TournamentGroupSummary[]>([])
const copiedKind = ref<CopyKind>(null)

const filters = reactive({
  competitionCode: '',
  seasonStart: '',
  seasonEnd: '',
  formatFamily: '',
  genderCategory: '',
  minimumMatches: '1',
  includeIncomplete: true,
})

const competitionOptions = computed(() => {
  const source = groups.value.length
    ? groups.value.map((group) => group.group_key)
    : (archive.value?.comparison_rows ?? []).map((row) => row.group_key)
  const seen = new Map<string, string>()
  source.forEach((group) => {
    if (!seen.has(group.competition_code)) {
      seen.set(group.competition_code, group.competition_name || group.competition_code)
    }
  })
  return Array.from(seen.entries()).map(([value, label]) => ({ value, label }))
})

const selectedCompetitionLabel = computed(() => {
  if (!filters.competitionCode) return 'All competitions'
  return competitionOptions.value.find((option) => option.value === filters.competitionCode)?.label || filters.competitionCode
})

function comparisonKey(row: HistoricalArchiveExplorerResponse['comparison_rows'][number]) {
  return `${row.group_key.competition_code}-${row.group_key.season || 'unknown'}-${row.group_key.gender_category}-${row.group_key.format_family}`
}

function formatMetric(value: number | null) {
  return value == null ? 'Unavailable' : value.toFixed(2)
}

function buildArchiveFilters(): HistoricalArchiveExplorerFilters {
  return {
    competitionCode: filters.competitionCode || undefined,
    seasonStart: filters.seasonStart ? Number.parseInt(filters.seasonStart, 10) : undefined,
    seasonEnd: filters.seasonEnd ? Number.parseInt(filters.seasonEnd, 10) : undefined,
    formatFamily: filters.formatFamily || undefined,
    genderCategory: filters.genderCategory || undefined,
    minimumMatches: Number.parseInt(filters.minimumMatches || '1', 10) || 1,
    includeIncomplete: filters.includeIncomplete,
  }
}

async function loadGroups() {
  try {
    const response = await getTournamentGroups()
    groups.value = response.groups
  } catch {
    groups.value = []
  }
}

async function loadArchive() {
  loading.value = true
  error.value = ''
  try {
    archive.value = await getHistoricalArchiveExplorer(buildArchiveFilters())
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load archive explorer.'
  } finally {
    loading.value = false
  }
}

async function copyText(kind: Exclude<CopyKind, null>) {
  if (!archive.value) return
  const text = kind === 'md' ? archive.value.research_summary.markdown : archive.value.research_summary.plain_text
  if (!text) return
  await navigator.clipboard.writeText(text)
  copiedKind.value = kind
  window.setTimeout(() => {
    copiedKind.value = null
  }, 2500)
}

onMounted(async () => {
  await Promise.all([loadGroups(), loadArchive()])
})
</script>

<style scoped>
.hae {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  color: var(--color-text, #e2e8f0);
}

.hae-header,
.hae-section,
.hae-overview-card,
.hae-card,
.hae-summary-section {
  border: 1px solid var(--color-border, rgba(148, 163, 184, 0.28));
  border-radius: 16px;
  background: var(--color-surface, rgba(15, 23, 42, 0.84));
}

.hae-header,
.hae-section {
  padding: 1rem;
}

.hae-title,
.hae-section-header h4,
.hae-summary-section h5 {
  margin: 0;
}

.hae-subtitle,
.hae-section-header p,
.hae-card-subtitle,
.hae-table-note,
.hae-footer-note,
.hae-inline-empty,
.hae-summary-section p,
.hae-note {
  color: var(--color-text-muted, #94a3b8);
}

.hae-note,
.hae-state {
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: var(--color-surface-alt, rgba(30, 41, 59, 0.82));
}

.hae-state--error {
  border: 1px solid rgba(248, 113, 113, 0.55);
}

.hae-filters,
.hae-overview,
.hae-card-grid,
.hae-copy-actions {
  display: grid;
  gap: 0.75rem;
}

.hae-filters {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  align-items: end;
}

.hae-filter,
.hae-checkbox {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
}

.hae-checkbox {
  flex-direction: row;
  align-items: center;
  padding-top: 1.35rem;
}

.hae-filter select,
.hae-filter input,
.hae-btn {
  border: 1px solid var(--color-border, rgba(148, 163, 184, 0.28));
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.95);
  color: inherit;
  padding: 0.65rem 0.75rem;
}

.hae-actions {
  display: flex;
}

.hae-btn {
  cursor: pointer;
}

.hae-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.hae-btn--primary {
  background: var(--color-brand, #1d6aff);
  border-color: transparent;
}

.hae-overview,
.hae-card-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.hae-overview-card,
.hae-card,
.hae-summary-section {
  padding: 0.9rem 1rem;
}

.hae-overview-label,
.hae-card-label {
  display: block;
  font-size: 0.78rem;
  color: var(--color-text-muted, #94a3b8);
  margin-bottom: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hae-card-value {
  display: block;
  margin-bottom: 0.35rem;
}

.hae-table-wrap {
  overflow-x: auto;
}

.hae-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.hae-table th,
.hae-table td {
  padding: 0.75rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  vertical-align: top;
}

.hae-table th {
  text-align: left;
  color: var(--color-text-muted, #94a3b8);
}

.hae-summary {
  display: grid;
  gap: 0.75rem;
}

.hae-summary-section p {
  white-space: pre-line;
}

@media (max-width: 720px) {
  .hae {
    gap: 0.85rem;
  }

  .hae-section,
  .hae-header {
    padding: 0.85rem;
  }
}
</style>
