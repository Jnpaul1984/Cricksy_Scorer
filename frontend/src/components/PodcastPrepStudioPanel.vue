<template>
  <div class="pps">
    <!-- Header -->
    <div class="pps-header">
      <h3 class="pps-title">🎙️ Podcast Prep Studio</h3>
      <p class="pps-subtitle">
        Phase 10T — Generate deterministic research packs and presenter-ready rundowns from
        validated match, tournament, archive, or roster data. All facts are derived — no
        unsupported claims are added.
      </p>
    </div>

    <!-- Provenance bar -->
    <div class="pps-provenance-bar" role="note">
      <span class="pps-provenance-icon">🔒</span>
      <span>All output is derived from imported data only. Trust notes are included in every report.</span>
    </div>

    <!-- Topic type selector -->
    <div class="pps-topic-row">
      <div
        v-for="t in topicTypes"
        :key="t.value"
        :class="['pps-topic-btn', { 'pps-topic-btn--active': topicType === t.value }]"
        @click="selectTopic(t.value)"
      >
        {{ t.icon }} {{ t.label }}
      </div>
    </div>

    <!-- ── Match topic form ── -->
    <div v-if="topicType === 'match'" class="pps-form-section">
      <label class="pps-label" for="pps-match-id">Match ID</label>
      <input
        id="pps-match-id"
        v-model="matchId"
        class="pps-input"
        placeholder="Paste a match ID from the Match Registry"
      />
    </div>

    <!-- ── Tournament topic form ── -->
    <div v-if="topicType === 'tournament'" class="pps-form-section">
      <div class="pps-form-row">
        <div class="pps-form-col">
          <label class="pps-label" for="pps-comp-code">Competition Code</label>
          <input
            id="pps-comp-code"
            v-model="competitionCode"
            class="pps-input"
            placeholder="e.g. CPL_MEN"
          />
        </div>
        <div class="pps-form-col">
          <label class="pps-label" for="pps-season">Season</label>
          <input
            id="pps-season"
            v-model="season"
            class="pps-input"
            placeholder="e.g. 2024"
          />
        </div>
        <div class="pps-form-col">
          <label class="pps-label" for="pps-gender">Gender</label>
          <select id="pps-gender" v-model="gender" class="pps-select">
            <option value="">— any —</option>
            <option value="men">Men</option>
            <option value="women">Women</option>
          </select>
        </div>
      </div>
    </div>

    <!-- ── Archive topic form ── -->
    <div v-if="topicType === 'archive'" class="pps-form-section">
      <div class="pps-form-row">
        <div class="pps-form-col">
          <label class="pps-label" for="pps-arch-comp">Competition Code</label>
          <input
            id="pps-arch-comp"
            v-model="competitionCode"
            class="pps-input"
            placeholder="e.g. CPL_MEN"
          />
        </div>
        <div class="pps-form-col">
          <label class="pps-label" for="pps-era">Era Label (optional)</label>
          <input
            id="pps-era"
            v-model="eraLabel"
            class="pps-input"
            placeholder="e.g. 2013–2016"
          />
        </div>
      </div>
    </div>

    <!-- ── Roster topic form ── -->
    <div v-if="topicType === 'roster'" class="pps-form-section">
      <div class="pps-form-row">
        <div class="pps-form-col">
          <label class="pps-label" for="pps-ros-comp">Competition Code</label>
          <input
            id="pps-ros-comp"
            v-model="competitionCode"
            class="pps-input"
            placeholder="e.g. CPL_MEN"
          />
        </div>
        <div class="pps-form-col">
          <label class="pps-label" for="pps-ros-season">Season</label>
          <input
            id="pps-ros-season"
            v-model="season"
            class="pps-input"
            placeholder="e.g. 2025"
          />
        </div>
        <div class="pps-form-col">
          <label class="pps-label" for="pps-ros-team">Team (optional)</label>
          <input
            id="pps-ros-team"
            v-model="teamName"
            class="pps-input"
            placeholder="Team name filter"
          />
        </div>
      </div>
    </div>

    <!-- Generate button -->
    <div class="pps-actions-top">
      <button
        class="pps-generate-btn"
        :disabled="generating || !canGenerate"
        @click="generatePack"
      >
        {{ generating ? '⏳ Generating…' : '⚡ Generate Research Pack' }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="pps-error" role="alert">
      <strong>Error:</strong> {{ error }}
    </div>

    <!-- Research Pack output -->
    <div v-if="pack" class="pps-pack">
      <!-- Pack header -->
      <div class="pps-pack-header">
        <h4 class="pps-pack-title">{{ pack.title }}</h4>
        <p v-if="pack.subtitle" class="pps-pack-subtitle">{{ pack.subtitle }}</p>
        <span :class="['pps-confidence-badge', `pps-confidence-badge--${pack.overall_confidence}`]">
          Confidence: {{ pack.overall_confidence }}
        </span>
      </div>

      <!-- Trust note -->
      <div class="pps-trust-note" role="note">
        🔍 <strong>Trust note:</strong> {{ pack.trust_note }}
      </div>

      <!-- Sections -->
      <div class="pps-sections">
        <div
          v-for="(section, idx) in pack.sections"
          :key="idx"
          class="pps-section"
        >
          <div class="pps-section-label">{{ section.label }}</div>
          <div class="pps-section-content">{{ section.content }}</div>
          <div v-if="section.source_note" class="pps-section-source">{{ section.source_note }}</div>
        </div>
      </div>

      <!-- Copy/Export actions -->
      <div class="pps-export-row">
        <button class="pps-copy-btn" @click="copyMarkdown">
          {{ copyMdStatus === 'copied' ? '✅ Copied!' : copyMdStatus === 'error' ? '❌ Failed' : '📋 Copy Markdown' }}
        </button>
        <button class="pps-copy-btn" @click="copyPlainText">
          {{ copyTxtStatus === 'copied' ? '✅ Copied!' : copyTxtStatus === 'error' ? '❌ Failed' : '📄 Copy Plain Text' }}
        </button>
        <button class="pps-save-btn" :disabled="saving" @click="showSaveForm = !showSaveForm">
          💾 Save Report
        </button>
      </div>

      <!-- Save form -->
      <div v-if="showSaveForm" class="pps-save-form">
        <div class="pps-form-row">
          <div class="pps-form-col pps-form-col--wide">
            <label class="pps-label" for="pps-report-title">Report Title</label>
            <input
              id="pps-report-title"
              v-model="saveTitle"
              class="pps-input"
              placeholder="e.g. CPL 2025 — Trinbago Knight Riders preview"
            />
          </div>
          <div class="pps-form-col">
            <label class="pps-label" for="pps-report-status">Status</label>
            <select id="pps-report-status" v-model="saveStatus" class="pps-select">
              <option value="draft">Draft</option>
              <option value="reviewed">Reviewed</option>
              <option value="approved">Approved</option>
            </select>
          </div>
        </div>
        <div class="pps-save-actions">
          <button class="pps-generate-btn" :disabled="saving || !saveTitle.trim()" @click="saveReport">
            {{ saving ? '⏳ Saving…' : '💾 Confirm Save' }}
          </button>
          <button class="pps-cancel-btn" @click="showSaveForm = false">Cancel</button>
        </div>
        <div v-if="saveError" class="pps-error" role="alert">{{ saveError }}</div>
        <div v-if="saveSuccess" class="pps-success" role="status">✅ Report saved.</div>
      </div>
    </div>

    <!-- Saved Reports section -->
    <div class="pps-saved-section">
      <div class="pps-saved-header">
        <h4 class="pps-saved-title">📁 Saved Reports</h4>
        <div class="pps-saved-filters">
          <select v-model="filterStatus" class="pps-select pps-select--sm" @change="loadReports">
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="reviewed">Reviewed</option>
            <option value="approved">Approved</option>
            <option value="archived">Archived</option>
          </select>
          <select v-model="filterTopicType" class="pps-select pps-select--sm" @change="loadReports">
            <option value="">All topics</option>
            <option value="match">Match</option>
            <option value="tournament">Tournament</option>
            <option value="roster">Roster</option>
            <option value="archive">Archive</option>
            <option value="custom">Custom</option>
          </select>
          <button class="pps-refresh-btn" :disabled="reportsLoading" @click="loadReports">
            {{ reportsLoading ? '⏳' : '🔄' }} Refresh
          </button>
        </div>
      </div>

      <div v-if="reportsLoading" class="pps-loading">Loading saved reports…</div>
      <div v-else-if="reportsError" class="pps-error">{{ reportsError }}</div>
      <div v-else-if="savedReports.length === 0" class="pps-empty">
        No saved reports found. Generate a pack above and save it.
      </div>
      <div v-else class="pps-saved-list">
        <div
          v-for="report in savedReports"
          :key="report.id"
          class="pps-saved-card"
        >
          <div class="pps-saved-card-header">
            <span class="pps-saved-card-title">{{ report.title }}</span>
            <span :class="['pps-status-badge', `pps-status-badge--${report.status}`]">
              {{ report.status }}
            </span>
            <span class="pps-type-badge">{{ report.topic_type }}</span>
          </div>
          <div class="pps-saved-card-meta">
            <span v-if="report.source_competition_code">{{ report.source_competition_code }}</span>
            <span v-if="report.source_season"> · {{ report.source_season }}</span>
            <span v-if="report.source_team_name"> · {{ report.source_team_name }}</span>
            <span class="pps-saved-card-date"> · {{ formatDate(report.updated_at) }}</span>
          </div>
          <div v-if="report.trust_summary" class="pps-saved-card-trust">
            🔍 {{ report.trust_summary }}
          </div>
          <div class="pps-saved-card-actions">
            <button class="pps-copy-btn pps-copy-btn--sm" @click="copyReportMarkdown(report)">
              📋 Copy MD
            </button>
            <button class="pps-copy-btn pps-copy-btn--sm" @click="copyReportPlainText(report)">
              📄 Copy TXT
            </button>
            <select
              :value="report.status"
              class="pps-select pps-select--sm"
              @change="(e) => changeReportStatus(report.id, (e.target as HTMLSelectElement).value)"
            >
              <option value="draft">Draft</option>
              <option value="reviewed">Reviewed</option>
              <option value="approved">Approved</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
        <div v-if="reportsTotal > savedReports.length" class="pps-load-more">
          <button class="pps-cancel-btn" @click="loadMoreReports">Load more…</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  generateMatchPodcastPack,
  generateTournamentPodcastPack,
  generateArchivePodcastPack,
  generateRosterPodcastPack,
  listPodcastPrepReports,
  createPodcastPrepReport,
  updatePodcastPrepReport,
} from '@/services/api'
import type {
  PodcastResearchPack,
  PodcastPrepReportResponse,
  PodcastTopicType,
} from '@/services/api'

// ---------------------------------------------------------------------------
// Topic type config
// ---------------------------------------------------------------------------

const topicTypes: { value: PodcastTopicType; label: string; icon: string }[] = [
  { value: 'match', label: 'Match', icon: '🏏' },
  { value: 'tournament', label: 'Tournament', icon: '🏆' },
  { value: 'archive', label: 'Archive', icon: '📚' },
  { value: 'roster', label: 'Roster / CPL', icon: '👥' },
]

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const topicType = ref<PodcastTopicType>('match')
const matchId = ref('')
const competitionCode = ref('CPL_MEN')
const season = ref('')
const gender = ref('')
const teamName = ref('')
const eraLabel = ref('')

const pack = ref<PodcastResearchPack | null>(null)
const generating = ref(false)
const error = ref('')

const copyMdStatus = ref<'idle' | 'copied' | 'error'>('idle')
const copyTxtStatus = ref<'idle' | 'copied' | 'error'>('idle')

const showSaveForm = ref(false)
const saveTitle = ref('')
const saveStatus = ref<'draft' | 'reviewed' | 'approved'>('draft')
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const savedReports = ref<PodcastPrepReportResponse[]>([])
const reportsTotal = ref(0)
const reportsLoading = ref(false)
const reportsError = ref('')
const filterStatus = ref('')
const filterTopicType = ref('')
const reportsOffset = ref(0)
const REPORTS_PAGE_SIZE = 20

// Markdown + plain text derived from pack (stored for save/copy)
const renderedMarkdown = computed(() => pack.value ? buildMarkdown(pack.value) : '')
const renderedPlainText = computed(() => pack.value ? buildPlainText(pack.value) : '')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const canGenerate = computed(() => {
  if (topicType.value === 'match') return matchId.value.trim().length > 0
  if (topicType.value === 'tournament') return competitionCode.value.trim().length > 0
  if (topicType.value === 'archive') return competitionCode.value.trim().length > 0
  if (topicType.value === 'roster') return competitionCode.value.trim().length > 0 && season.value.trim().length > 0
  return false
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function selectTopic(t: PodcastTopicType) {
  topicType.value = t
  pack.value = null
  error.value = ''
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function buildMarkdown(p: PodcastResearchPack): string {
  const lines: string[] = []
  lines.push(`# ${p.title}`)
  if (p.subtitle) lines.push(`> ${p.subtitle}`)
  lines.push('')
  lines.push(`**Trust note:** ${p.trust_note}`)
  lines.push(`**Confidence:** ${p.overall_confidence}`)
  lines.push('')
  for (const s of p.sections) {
    lines.push(`## ${s.label}`)
    lines.push(s.content)
    if (s.source_note) lines.push(`*Source: ${s.source_note}*`)
    lines.push('')
  }
  return lines.join('\n')
}

function buildPlainText(p: PodcastResearchPack): string {
  const lines: string[] = []
  lines.push(p.title.toUpperCase())
  if (p.subtitle) lines.push(p.subtitle)
  lines.push('')
  lines.push(`Trust note: ${p.trust_note}`)
  lines.push(`Confidence: ${p.overall_confidence}`)
  lines.push('')
  for (const s of p.sections) {
    lines.push(`--- ${s.label.toUpperCase()} ---`)
    lines.push(s.content)
    if (s.source_note) lines.push(`(${s.source_note})`)
    lines.push('')
  }
  return lines.join('\n')
}

async function copyText(text: string, statusRef: typeof copyMdStatus) {
  try {
    await navigator.clipboard.writeText(text)
    statusRef.value = 'copied'
    setTimeout(() => { statusRef.value = 'idle' }, 2000)
  } catch {
    statusRef.value = 'error'
    setTimeout(() => { statusRef.value = 'idle' }, 2000)
  }
}

// ---------------------------------------------------------------------------
// Generate
// ---------------------------------------------------------------------------

async function generatePack() {
  error.value = ''
  pack.value = null
  generating.value = true
  try {
    if (topicType.value === 'match') {
      pack.value = await generateMatchPodcastPack({ match_id: matchId.value.trim() })
    } else if (topicType.value === 'tournament') {
      pack.value = await generateTournamentPodcastPack({
        competition_code: competitionCode.value.trim(),
        season: season.value.trim() || null,
        gender: gender.value || null,
      })
    } else if (topicType.value === 'archive') {
      pack.value = await generateArchivePodcastPack({
        competition_code: competitionCode.value.trim(),
        era_label: eraLabel.value.trim() || null,
      })
    } else if (topicType.value === 'roster') {
      pack.value = await generateRosterPodcastPack({
        competition_code: competitionCode.value.trim(),
        season: season.value.trim(),
        team_name: teamName.value.trim() || null,
      })
    }
    if (pack.value) {
      saveTitle.value = pack.value.title
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to generate research pack.'
  } finally {
    generating.value = false
  }
}

// ---------------------------------------------------------------------------
// Copy/Export
// ---------------------------------------------------------------------------

async function copyMarkdown() {
  await copyText(renderedMarkdown.value, copyMdStatus)
}

async function copyPlainText() {
  await copyText(renderedPlainText.value, copyTxtStatus)
}

async function copyReportMarkdown(report: PodcastPrepReportResponse) {
  await navigator.clipboard.writeText(report.generated_markdown ?? '').catch(() => {})
}

async function copyReportPlainText(report: PodcastPrepReportResponse) {
  await navigator.clipboard.writeText(report.generated_plain_text ?? '').catch(() => {})
}

// ---------------------------------------------------------------------------
// Save
// ---------------------------------------------------------------------------

async function saveReport() {
  if (!pack.value || !saveTitle.value.trim()) return
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    await createPodcastPrepReport({
      title: saveTitle.value.trim(),
      topic_type: topicType.value,
      source_competition_code: competitionCode.value.trim() || null,
      source_season: season.value.trim() || null,
      source_team_name: teamName.value.trim() || null,
      source_match_id: matchId.value.trim() || null,
      generated_markdown: renderedMarkdown.value,
      generated_plain_text: renderedPlainText.value,
      trust_summary: pack.value.trust_note,
      status: saveStatus.value,
    })
    saveSuccess.value = true
    showSaveForm.value = false
    await loadReports()
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'Failed to save report.'
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Saved reports
// ---------------------------------------------------------------------------

async function loadReports() {
  reportsLoading.value = true
  reportsError.value = ''
  reportsOffset.value = 0
  try {
    const resp = await listPodcastPrepReports({
      status: filterStatus.value || undefined,
      topic_type: filterTopicType.value || undefined,
      limit: REPORTS_PAGE_SIZE,
      offset: 0,
    })
    savedReports.value = resp.reports
    reportsTotal.value = resp.total
  } catch (e: unknown) {
    reportsError.value = e instanceof Error ? e.message : 'Failed to load saved reports.'
  } finally {
    reportsLoading.value = false
  }
}

async function loadMoreReports() {
  reportsOffset.value += REPORTS_PAGE_SIZE
  try {
    const resp = await listPodcastPrepReports({
      status: filterStatus.value || undefined,
      topic_type: filterTopicType.value || undefined,
      limit: REPORTS_PAGE_SIZE,
      offset: reportsOffset.value,
    })
    savedReports.value.push(...resp.reports)
    reportsTotal.value = resp.total
  } catch {
    // ignore pagination errors
  }
}

async function changeReportStatus(id: string, newStatus: string) {
  try {
    const updated = await updatePodcastPrepReport(id, { status: newStatus as 'draft' | 'reviewed' | 'approved' | 'archived' })
    const idx = savedReports.value.findIndex(r => r.id === id)
    if (idx >= 0) savedReports.value[idx] = updated
  } catch {
    // ignore status update errors
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.pps {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.pps-header {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.pps-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.pps-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-muted, #6b7280);
  margin: 0;
}

.pps-provenance-bar {
  background: color-mix(in srgb, var(--color-primary, #1d4ed8) 8%, transparent);
  border-left: 3px solid var(--color-primary, #1d4ed8);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.pps-topic-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pps-topic-btn {
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  background: var(--color-surface, #fff);
  transition: all 0.15s;
  user-select: none;
}

.pps-topic-btn:hover {
  background: color-mix(in srgb, var(--color-primary, #1d4ed8) 8%, transparent);
}

.pps-topic-btn--active {
  background: var(--color-primary, #1d4ed8);
  color: #fff;
  border-color: var(--color-primary, #1d4ed8);
}

.pps-form-section {
  background: var(--color-surface-alt, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  padding: 0.85rem 1rem;
}

.pps-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.pps-form-col {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  flex: 1;
  min-width: 140px;
}

.pps-form-col--wide {
  flex: 3;
}

.pps-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.pps-input,
.pps-select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  font-size: 0.875rem;
  background: var(--color-surface, #fff);
  color: var(--color-text, #111827);
}

.pps-select--sm {
  font-size: 0.78rem;
  padding: 0.3rem 0.5rem;
}

.pps-actions-top {
  display: flex;
  gap: 0.75rem;
}

.pps-generate-btn {
  padding: 0.55rem 1.2rem;
  background: var(--color-primary, #1d4ed8);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: opacity 0.15s;
}

.pps-generate-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pps-error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  padding: 0.6rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.pps-success {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.pps-pack {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}

.pps-pack-header {
  padding: 0.85rem 1rem;
  background: color-mix(in srgb, var(--color-primary, #1d4ed8) 5%, transparent);
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: flex-start;
}

.pps-pack-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  flex: 1;
}

.pps-pack-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-muted, #6b7280);
  margin: 0;
  width: 100%;
}

.pps-confidence-badge {
  padding: 0.2rem 0.55rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.pps-confidence-badge--high { background: #dcfce7; color: #166534; }
.pps-confidence-badge--medium { background: #fef9c3; color: #854d0e; }
.pps-confidence-badge--low { background: #fee2e2; color: #991b1b; }
.pps-confidence-badge--unknown { background: #f3f4f6; color: #6b7280; }

.pps-trust-note {
  padding: 0.55rem 1rem;
  background: #fefce8;
  border-bottom: 1px solid #fef08a;
  font-size: 0.82rem;
  color: #713f12;
}

.pps-sections {
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.pps-section {
  padding: 0.6rem 0.8rem;
  border-left: 3px solid var(--color-primary, #1d4ed8);
  background: var(--color-surface-alt, #f9fafb);
  border-radius: 0 5px 5px 0;
}

.pps-section-label {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-primary, #1d4ed8);
  margin-bottom: 0.25rem;
}

.pps-section-content {
  font-size: 0.875rem;
  white-space: pre-wrap;
  line-height: 1.5;
}

.pps-section-source {
  font-size: 0.75rem;
  color: var(--color-text-muted, #9ca3af);
  margin-top: 0.25rem;
  font-style: italic;
}

.pps-export-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border, #e5e7eb);
}

.pps-copy-btn {
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.82rem;
  background: var(--color-surface, #fff);
  transition: background 0.15s;
}

.pps-copy-btn:hover { background: var(--color-surface-alt, #f3f4f6); }

.pps-copy-btn--sm {
  font-size: 0.75rem;
  padding: 0.3rem 0.6rem;
}

.pps-save-btn {
  padding: 0.4rem 0.85rem;
  background: #059669;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
}

.pps-save-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.pps-cancel-btn {
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.82rem;
  background: var(--color-surface, #fff);
}

.pps-save-form {
  padding: 0.85rem 1rem;
  background: var(--color-surface-alt, #f9fafb);
  border-top: 1px solid var(--color-border, #e5e7eb);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.pps-save-actions {
  display: flex;
  gap: 0.5rem;
}

/* Saved reports */
.pps-saved-section {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}

.pps-saved-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--color-surface-alt, #f9fafb);
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  gap: 0.5rem;
}

.pps-saved-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}

.pps-saved-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.pps-refresh-btn {
  padding: 0.3rem 0.65rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.78rem;
  background: var(--color-surface, #fff);
}

.pps-loading,
.pps-empty {
  padding: 1.25rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-muted, #9ca3af);
}

.pps-saved-list {
  display: flex;
  flex-direction: column;
}

.pps-saved-card {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border, #f3f4f6);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.pps-saved-card:last-child { border-bottom: none; }

.pps-saved-card-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}

.pps-saved-card-title {
  font-size: 0.9rem;
  font-weight: 600;
  flex: 1;
}

.pps-status-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: capitalize;
}

.pps-status-badge--draft { background: #f3f4f6; color: #6b7280; }
.pps-status-badge--reviewed { background: #dbeafe; color: #1d4ed8; }
.pps-status-badge--approved { background: #dcfce7; color: #166534; }
.pps-status-badge--archived { background: #fef3c7; color: #92400e; }

.pps-type-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
  font-size: 0.72rem;
  background: #f3f4f6;
  color: #374151;
  text-transform: capitalize;
}

.pps-saved-card-meta {
  font-size: 0.78rem;
  color: var(--color-text-muted, #9ca3af);
}

.pps-saved-card-date {
  font-style: italic;
}

.pps-saved-card-trust {
  font-size: 0.78rem;
  color: #92400e;
  background: #fefce8;
  padding: 0.3rem 0.55rem;
  border-radius: 4px;
}

.pps-saved-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}

.pps-load-more {
  padding: 0.75rem 1rem;
  text-align: center;
}
</style>
