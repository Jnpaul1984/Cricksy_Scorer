<template>
  <div class="dismissal-patterns-panel">
    <div class="panel-header">
      <h2>🎯 Dismissal Patterns Analysis</h2>
      <p v-if="playerName" class="player-name">for {{ playerName }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="state-message">
      <p>Analyzing dismissal patterns...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-message error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="refresh">Retry</button>
    </div>

    <!-- No Data State -->
    <div v-else-if="!vulnerabilityScore || vulnerabilityScore === 0" class="state-message">
      <p>No dismissal patterns recorded.</p>
      <p class="text-sm">Player has not been dismissed yet or data is unavailable.</p>
    </div>

    <!-- Analysis Display -->
    <div v-else class="analysis-container">
      <!-- Vulnerability Score Card -->
      <div class="score-card">
        <div class="score-display">
          <div class="score-value" :class="`risk-${riskLevel}`">
            {{ vulnerabilityScore.toFixed(0) }}
          </div>
          <div class="score-label">Vulnerability Score</div>
        </div>
        <div class="score-details">
          <div class="detail-row">
            <span class="label">Risk Level:</span>
            <span class="value" :class="`risk-badge-${riskLevel}`">
              {{ riskLevel.toUpperCase() }}
            </span>
          </div>
          <div class="detail-row">
            <span class="label">Total Dismissals:</span>
            <span class="value">{{ totalDismissals }}</span>
          </div>
          <div v-if="primaryVulnerability" class="detail-row">
            <span class="label">Main Weakness:</span>
            <span class="value">{{ primaryVulnerability }}</span>
          </div>
        </div>
      </div>

      <!-- Top Patterns Grid -->
      <div v-if="topPatterns.length > 0" class="patterns-section">
        <h3>🔴 Top Dismissal Patterns</h3>
        <div class="patterns-grid">
          <div
            v-for="(pattern, idx) in topPatterns"
            :key="idx"
            :class="['pattern-card', `severity-${pattern.severity}`]"
          >
            <div class="pattern-header">
              <h4 class="pattern-name">{{ pattern.pattern_name }}</h4>
              <span class="severity-badge" :class="`badge-${pattern.severity}`">
                {{ pattern.severity.toUpperCase() }}
              </span>
            </div>

            <div class="pattern-stats">
              <div class="stat">
                <span class="stat-label">Occurrences:</span>
                <span class="stat-value">{{ pattern.dismissal_count }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">Percentage:</span>
                <span class="stat-value">{{ pattern.dismissal_percentage }}%</span>
              </div>
              <div class="stat">
                <span class="stat-label">Confidence:</span>
                <div class="confidence-bar">
                  <div class="confidence-fill" :style="{ width: ((pattern.confidence || 0.5) * 100) + '%' }"></div>
                  {{ ((pattern.confidence || 0.5) * 100).toFixed(0) }}%
                </div>
              </div>
            </div>

            <div class="pattern-context">
              <p>{{ pattern.context }}</p>
            </div>

            <div class="pattern-recommendation">
              <strong>💡 Recommendation:</strong>
              <p>{{ pattern.recommendation }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Critical Situations -->
      <div v-if="criticalSituations.length > 0" class="situations-section">
        <h3>⚠️ Critical Dismissal Situations</h3>
        <div class="situations-list">
          <div
            v-for="(situation, idx) in criticalSituations"
            :key="idx"
            :class="['situation-card', `risk-${situation.risk_level}`]"
          >
            <div class="situation-header">
              <h4>{{ situation.situation_type }}</h4>
              <span class="risk-badge" :class="`risk-badge-${situation.risk_level}`">
                {{ situation.risk_level.toUpperCase() }}
              </span>
            </div>
            <div class="situation-description">
              {{ situation.scenario_description }}
            </div>
            <div class="situation-stat">
              <span class="label">Dismissals in this situation:</span>
              <span class="value">{{ situation.dismissal_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Secondary Vulnerabilities -->
      <div v-if="secondaryVulnerabilities.length > 0" class="vulnerabilities-section">
        <h3>🛡️ Secondary Vulnerabilities</h3>
        <div class="vulnerabilities-list">
          <div v-for="(vuln, idx) in secondaryVulnerabilities" :key="idx" class="vulnerability-item">
            <span class="vulnerability-tag">{{ vuln }}</span>
          </div>
        </div>
      </div>

      <!-- Improvement Areas -->
      <div v-if="improvementAreas.length > 0" class="improvement-section">
        <h3>📈 Focus Areas for Improvement</h3>
        <ol class="improvement-list">
          <li v-for="(area, idx) in improvementAreas" :key="idx" class="improvement-item">
            {{ area }}
          </li>
        </ol>
      </div>

      <!-- Dismissals by Type Chart -->
      <div v-if="dismissalsByType && Object.keys(dismissalsByType).length > 0" class="breakdown-section">
        <h3>📊 Dismissals Breakdown</h3>
        <div class="breakdown-grid">
          <div class="breakdown-item">
            <h4>By Dismissal Type</h4>
            <div class="breakdown-list">
              <div
                v-for="(count, type) in dismissalsByType"
                :key="type"
                class="breakdown-entry"
              >
                <span class="type">{{ type }}:</span>
                <span class="count">{{ count }}</span>
              </div>
            </div>
          </div>

          <div v-if="dismissalsByPhase" class="breakdown-item">
            <h4>By Match Phase</h4>
            <div class="breakdown-list">
              <div
                v-for="(count, phase) in dismissalsByPhase"
                :key="phase"
                class="breakdown-entry"
              >
                <span class="type">{{ phase }}:</span>
                <span class="count">{{ count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto-refresh Footer -->
    <div class="footer-info">
      <p class="refresh-info">
        Last updated: {{ lastUpdated }}
        <button class="refresh-btn" @click="refresh">🔄 Refresh Now</button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

import { useDismissalPatterns } from '../composables/useDismissalPatterns'

interface DismissalPattern {
  pattern_name: string
  pattern_type: string
  dismissal_count: number
  dismissal_percentage: number
  severity: string
  context: string
  recommendation: string
  confidence?: number
}

interface CriticalSituation {
  situation_type: string
  dismissal_count: number
  risk_level: string
  scenario_description: string
}

const props = withDefaults(
  defineProps<{
    playerId?: string
    gameId?: string
    teamSide?: 'a' | 'b'
    autoRefresh?: boolean
    refreshIntervalSeconds?: number
  }>(),
  {
    autoRefresh: true,
    refreshIntervalSeconds: 15,
  }
)

const emit = defineEmits<{
  analysisLoaded: [analysis: any]
  error: [error: string]
}>()

const { fetchPlayerAnalysis, fetchTeamAnalysis, loading } = useDismissalPatterns()

const playerName = ref<string>('')
const error = ref<string>('')
const vulnerabilityScore = ref<number>(0)
const riskLevel = ref<string>('low')
const totalDismissals = ref<number>(0)
const primaryVulnerability = ref<string>('')
const secondaryVulnerabilities = ref<string[]>([])
const topPatterns = ref<DismissalPattern[]>([])
const criticalSituations = ref<CriticalSituation[]>([])
const improvementAreas = ref<string[]>([])
const dismissalsByType = ref<Record<string, number>>({})
const dismissalsByPhase = ref<Record<string, number>>({})
const lastUpdated = ref<string>('')
let refreshInterval: number | null = null

async function loadAnalysis() {
  error.value = ''
  lastUpdated.value = new Date().toLocaleTimeString()

  try {
    let data

    if (props.playerId) {
      data = await fetchPlayerAnalysis(props.playerId)
    } else if (props.gameId && props.teamSide) {
      data = await fetchTeamAnalysis(props.gameId, props.teamSide)
    } else {
      error.value = 'No player or game ID provided'
      return
    }

    if (data) {
      const analysis = (data as any).analysis
      if (analysis) {
        vulnerabilityScore.value = analysis.overall_vulnerability_score || 0
        totalDismissals.value = analysis.total_dismissals || 0
        primaryVulnerability.value = analysis.primary_vulnerability || ''
        secondaryVulnerabilities.value = analysis.secondary_vulnerabilities || []
        topPatterns.value = analysis.top_patterns || []
        criticalSituations.value = analysis.critical_situations || []
        improvementAreas.value = analysis.improvement_areas || []
        dismissalsByType.value = analysis.dismissals_by_type || {}
        dismissalsByPhase.value = analysis.dismissals_by_phase || {}

        // Set risk level
        if (vulnerabilityScore.value >= 70) {
          riskLevel.value = 'critical'
        } else if (vulnerabilityScore.value >= 50) {
          riskLevel.value = 'high'
        } else if (vulnerabilityScore.value >= 30) {
          riskLevel.value = 'medium'
        } else {
          riskLevel.value = 'low'
        }

        if ((data as any).player_name) {
          playerName.value = (data as any).player_name
        }

        emit('analysisLoaded', data)
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load analysis'
    emit('error', error.value)
  }
}

function refresh() {
  loadAnalysis()
}

function startAutoRefresh() {
  if (props.autoRefresh && refreshInterval === null) {
    refreshInterval = window.setInterval(() => {
      loadAnalysis()
    }, props.refreshIntervalSeconds * 1000)
  }
}

function stopAutoRefresh() {
  if (refreshInterval !== null) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

onMounted(() => {
  loadAnalysis()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.dismissal-patterns-panel {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.panel-header {
  margin-bottom: 24px;
  text-align: center;
}

.panel-header h2 {
  font-size: 28px;
  color: #1a202c;
  margin: 0 0 8px 0;
  font-weight: 700;
}

.player-name {
  color: #666;
  font-size: 14px;
  margin: 0;
}

/* State Messages */
.state-message {
  text-align: center;
  padding: 40px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  color: #666;
  font-size: 16px;
}

.state-message.error {
  color: #e53e3e;
  background: rgba(255, 229, 229, 0.5);
}

.text-sm {
  font-size: 13px;
  color: #999;
  margin-top: 8px;
}

.retry-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #4299e1;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: #3182ce;
}

/* Analysis Container */
.analysis-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Score Card */
.score-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  gap: 24px;
  align-items: center;
}

.score-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 120px;
}

.score-value {
  font-size: 56px;
  font-weight: 700;
  border-radius: 50%;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.score-value.risk-critical {
  background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
}

.score-value.risk-high {
  background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
}

.score-value.risk-medium {
  background: linear-gradient(135deg, #ecc94b 0%, #d69e2e 100%);
}

.score-value.risk-low {
  background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
}

.score-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 8px;
  font-weight: 600;
}

.score-details {
  flex: 1;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row .label {
  color: #999;
  font-weight: 600;
}

.detail-row .value {
  color: #1a202c;
  font-weight: 600;
}

.risk-badge-critical {
  color: #e53e3e;
  background: rgba(229, 62, 62, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.risk-badge-high {
  color: #ed8936;
  background: rgba(237, 137, 54, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.risk-badge-medium {
  color: #ecc94b;
  background: rgba(236, 201, 75, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.risk-badge-low {
  color: #48bb78;
  background: rgba(72, 187, 120, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

/* Patterns Section */
.patterns-section {
  margin-top: 24px;
}

.patterns-section h3 {
  font-size: 18px;
  color: #1a202c;
  margin: 0 0 16px 0;
  font-weight: 700;
}

.patterns-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.pattern-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-top: 4px solid;
}

.pattern-card.severity-high {
  border-top-color: #e53e3e;
}

.pattern-card.severity-medium {
  border-top-color: #ed8936;
}

.pattern-card.severity-low {
  border-top-color: #48bb78;
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.pattern-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
}

.severity-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.badge-high {
  background: rgba(229, 62, 62, 0.1);
  color: #e53e3e;
}

.badge-medium {
  background: rgba(237, 137, 54, 0.1);
  color: #ed8936;
}

.badge-low {
  background: rgba(72, 187, 120, 0.1);
  color: #48bb78;
}

.pattern-stats {
  background: #f9fafb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}

.stat-label {
  color: #999;
  font-weight: 600;
}

.stat-value {
  color: #1a202c;
  font-weight: 700;
}

.confidence-bar {
  display: inline-flex;
  align-items: center;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  height: 18px;
  width: 60px;
  padding: 2px;
  font-size: 10px;
  color: #666;
}

.confidence-fill {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 100%;
}

.pattern-context {
  font-size: 13px;
  color: #666;
  margin-bottom: 12px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
}

.pattern-recommendation {
  font-size: 12px;
  color: #666;
  background: rgba(102, 126, 234, 0.05);
  border-left: 3px solid #667eea;
  padding: 8px;
  border-radius: 4px;
}

.pattern-recommendation strong {
  color: #1a202c;
  display: block;
  margin-bottom: 4px;
}

.pattern-recommendation p {
  margin: 0;
}

/* Situations Section */
.situations-section {
  margin-top: 24px;
}

.situations-section h3 {
  font-size: 18px;
  color: #1a202c;
  margin: 0 0 16px 0;
  font-weight: 700;
}

.situations-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.situation-card {
  background: white;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-left: 4px solid;
}

.risk-high {
  border-left-color: #e53e3e;
}

.risk-medium {
  border-left-color: #ed8936;
}

.risk-low {
  border-left-color: #48bb78;
}

.situation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.situation-header h4 {
  font-size: 14px;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
}

.risk-badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}

.situation-description {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.situation-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.situation-stat .label {
  font-weight: 600;
}

.situation-stat .value {
  color: #1a202c;
  font-weight: 700;
}

/* Vulnerabilities Section */
.vulnerabilities-section {
  margin-top: 24px;
}

.vulnerabilities-section h3 {
  font-size: 18px;
  color: #1a202c;
  margin: 0 0 12px 0;
  font-weight: 700;
}

.vulnerabilities-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.vulnerability-item {
  background: white;
  border-radius: 6px;
  padding: 8px 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.vulnerability-tag {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

/* Improvement Section */
.improvement-section {
  margin-top: 24px;
  background: rgba(72, 187, 120, 0.05);
  border-radius: 8px;
  padding: 16px;
  border-left: 4px solid #48bb78;
}

.improvement-section h3 {
  font-size: 18px;
  color: #1a202c;
  margin: 0 0 12px 0;
  font-weight: 700;
}

.improvement-list {
  list-style-position: inside;
  margin: 0;
  padding: 0;
}

.improvement-item {
  font-size: 14px;
  color: #666;
  padding: 6px 0;
  font-weight: 500;
}

/* Breakdown Section */
.breakdown-section {
  margin-top: 24px;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.breakdown-section h3 {
  font-size: 18px;
  color: #1a202c;
  margin: 0 0 16px 0;
  font-weight: 700;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.breakdown-item h4 {
  font-size: 14px;
  color: #666;
  margin: 0 0 12px 0;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.breakdown-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.breakdown-entry {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 6px 0;
}

.breakdown-entry .type {
  color: #666;
  font-weight: 500;
}

.breakdown-entry .count {
  color: #1a202c;
  font-weight: 700;
  background: #f9fafb;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Footer Info */
.footer-info {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 16px;
}

.refresh-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0;
}

.refresh-btn {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: white;
  border-color: #a0aec0;
}

/* Responsive */
@media (max-width: 768px) {
  .dismissal-patterns-panel {
    padding: 16px;
  }

  .panel-header h2 {
    font-size: 22px;
  }

  .score-card {
    flex-direction: column;
    text-align: center;
  }

  .patterns-grid,
  .situations-list {
    grid-template-columns: 1fr;
  }

  .breakdown-grid {
    grid-template-columns: 1fr;
  }
}
</style>
