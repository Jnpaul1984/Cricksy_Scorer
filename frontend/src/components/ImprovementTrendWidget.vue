<template>
  <div class="improvement-widget">
    <div class="widget-header">
      <h3 class="widget-title">📈 Player Improvement Tracker</h3>
      <div class="header-controls">
        <select v-model="selectedMetric" class="metric-select">
          <option value="all">All Metrics</option>
          <option value="batting_average">Batting Average</option>
          <option value="strike_rate">Strike Rate</option>
          <option value="consistency">Consistency</option>
          <option value="dismissal_rate">Dismissal Rate</option>
        </select>
        <span v-if="summaryData" :class="['trend-badge', summaryData.overall_trend]">
          {{ summaryData.overall_trend }}
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Analyzing player improvement...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
    </div>

    <!-- Monthly Stats View -->
    <div v-else-if="summaryData" class="improvement-content">
      <!-- Overall Summary -->
      <div class="summary-section">
        <div class="summary-card">
          <div class="summary-stat">
            <span class="stat-label">Improvement Score</span>
            <span class="stat-value">{{ summaryData.improvement_score }}%</span>
          </div>
          <div class="summary-stat">
            <span class="stat-label">Months Analyzed</span>
            <span class="stat-value">{{ summaryData.months_analyzed }}</span>
          </div>
          <div class="summary-stat">
            <span class="stat-label">Current Role</span>
            <span class="stat-value">{{ formatRole(summaryData.latest_stats.role) }}</span>
          </div>
        </div>

        <!-- Key Metrics -->
        <div class="latest-metrics">
          <div class="metric-item">
            <span class="metric-name">Batting Average</span>
            <span class="metric-value">{{ summaryData.latest_stats.batting_average }}</span>
            <span v-if="summaryData.latest_improvements.batting_average" class="metric-change" :class="summaryData.latest_improvements.batting_average.trend">
              {{ showTrendIcon(summaryData.latest_improvements.batting_average.trend) }}
              {{ summaryData.latest_improvements.batting_average.percentage_change }}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-name">Strike Rate</span>
            <span class="metric-value">{{ summaryData.latest_stats.strike_rate }}</span>
            <span v-if="summaryData.latest_improvements.strike_rate" class="metric-change" :class="summaryData.latest_improvements.strike_rate.trend">
              {{ showTrendIcon(summaryData.latest_improvements.strike_rate.trend) }}
              {{ summaryData.latest_improvements.strike_rate.percentage_change }}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-name">Consistency</span>
            <span class="metric-value">{{ summaryData.latest_stats.consistency_score }}</span>
            <span v-if="summaryData.latest_improvements.consistency" class="metric-change" :class="summaryData.latest_improvements.consistency.trend">
              {{ showTrendIcon(summaryData.latest_improvements.consistency.trend) }}
              {{ summaryData.latest_improvements.consistency.percentage_change }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Highlights -->
      <div v-if="summaryData.highlights && summaryData.highlights.length" class="highlights-section">
        <h4 class="section-title">Key Insights</h4>
        <div class="highlights-list">
          <div v-for="(highlight, idx) in summaryData.highlights" :key="idx" class="highlight-item">
            {{ highlight }}
          </div>
        </div>
      </div>

      <!-- Historical Trends -->
      <div v-if="summaryData.historical_improvements && summaryData.historical_improvements.length" class="trends-section">
        <h4 class="section-title">Month-to-Month Trends</h4>
        <div class="trends-timeline">
          <div v-for="(period, idx) in summaryData.historical_improvements" :key="idx" class="trend-card">
            <div class="trend-header">
              <span class="period-label">{{ formatPeriod(period.from_month) }} → {{ formatPeriod(period.to_month) }}</span>
            </div>
            <div class="trend-metrics">
              <div v-for="(metric, metricName) in filteredMetrics(period.metrics)" :key="metricName" class="trend-metric">
                <span class="metric-name">{{ metric.metric_name }}</span>
                <div class="metric-bar">
                  <div :class="['metric-trend', metric.trend]" :style="{ width: getMetricWidth(metric.percentage_change) }">
                    {{ metric.percentage_change }}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Performance Details -->
      <div class="details-section">
        <h4 class="section-title">Performance Details</h4>
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Matches Played</span>
            <span class="detail-value">{{ summaryData.latest_stats.matches_played }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Innings Played</span>
            <span class="detail-value">{{ summaryData.latest_stats.innings_played }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Latest Month</span>
            <span class="detail-value">{{ formatMonth(summaryData.latest_month) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>No improvement data available. Check back after the player participates in matches.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import { usePlayerImprovement } from '../composables/usePlayerImprovement'

interface Props {
  playerId: string
  monthsToAnalyze?: number
}

const props = withDefaults(defineProps<Props>(), {
  monthsToAnalyze: 6,
})

const selectedMetric = ref('all')
const { summaryData, loading, error, fetchImprovementSummary } = usePlayerImprovement()

onMounted(() => {
  fetchImprovementSummary(props.playerId, props.monthsToAnalyze)
})

const formatRole = (role: string): string => {
  const roleMap: Record<string, string> = {
    opener: 'Opener',
    top_order: 'Top Order',
    middle_order: 'Middle Order',
    finisher: 'Finisher',
    bowler: 'Bowler',
    all_rounder: 'All-rounder',
  }
  return roleMap[role] || role
}

const showTrendIcon = (trend: string): string => {
  if (trend === 'improving') return '📈'
  if (trend === 'declining') return '📉'
  return '➡️'
}

const formatPeriod = (month: string): string => {
  const date = new Date(month + '-01')
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

const formatMonth = (month: string): string => {
  const date = new Date(month + '-01')
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

const filteredMetrics = (metrics: Record<string, any>) => {
  if (selectedMetric.value === 'all') {
    return metrics
  }
  return selectedMetric.value in metrics ? { [selectedMetric.value]: metrics[selectedMetric.value] } : {}
}

const getMetricWidth = (percentage: number): string => {
  const base = 50 // Base width for 0%
  const scale = Math.min(Math.abs(percentage), 50) // Cap at 50 units
  const width = base + (percentage > 0 ? scale : -scale)
  return `${Math.max(0, width)}%`
}
</script>

<style scoped>
.improvement-widget {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #333;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
  padding-bottom: 12px;
}

.widget-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.metric-select {
  padding: 8px 12px;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 14px;
}

.trend-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.trend-badge.improving {
  background: #d4edda;
  color: #155724;
}

.trend-badge.declining {
  background: #f8d7da;
  color: #721c24;
}

.trend-badge.accelerating {
  background: #cfe2ff;
  color: #084298;
}

.trend-badge.stable {
  background: #fff3cd;
  color: #856404;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.spinner {
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-top: 3px solid #333;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.error-message {
  color: #d32f2f;
  margin: 0;
}

.improvement-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.summary-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.summary-card {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a3a52;
}

.latest-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: #f8fafb;
  border-left: 4px solid #007bff;
  border-radius: 6px;
}

.metric-name {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a3a52;
}

.metric-change {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
}

.metric-change.improving {
  background: #d4edda;
  color: #155724;
}

.metric-change.declining {
  background: #f8d7da;
  color: #721c24;
}

.metric-change.stable {
  background: #fff3cd;
  color: #856404;
}

.highlights-section,
.trends-section,
.details-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.section-title {
  margin: 0 0 16px;
  font-size: 14px;
  font-weight: 700;
  color: #1a3a52;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #007bff;
  padding-bottom: 8px;
}

.highlights-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.highlight-item {
  padding: 12px;
  background: #f0f8ff;
  border-left: 4px solid #007bff;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: #333;
}

.trends-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.trend-card {
  background: #f8fafb;
  border: 1px solid #e0e6ed;
  border-radius: 8px;
  padding: 16px;
}

.trend-header {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.period-label {
  color: #1a3a52;
}

.trend-metrics {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trend-metric {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.trend-metric .metric-name {
  min-width: 120px;
  color: #666;
}

.metric-bar {
  flex: 1;
  height: 24px;
  background: #e0e6ed;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.metric-trend {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 11px;
  transition: width 0.3s ease;
}

.metric-trend.improving {
  background: linear-gradient(90deg, #28a745, #20c997);
}

.metric-trend.declining {
  background: linear-gradient(90deg, #dc3545, #e74c3c);
}

.metric-trend.stable {
  background: linear-gradient(90deg, #ffc107, #ff9800);
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: #f0f4f8;
  border-radius: 8px;
  text-align: center;
}

.detail-label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.detail-value {
  font-size: 18px;
  font-weight: 700;
  color: #1a3a52;
}

@media (max-width: 768px) {
  .widget-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .summary-card {
    grid-template-columns: 1fr;
  }

  .latest-metrics {
    grid-template-columns: 1fr;
  }

  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
