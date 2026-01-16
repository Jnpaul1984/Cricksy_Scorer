<template>
  <div class="phase-analysis">
    <div class="phase-header">
      <h2 class="phase-title">🎯 Phase Analysis</h2>
      <p class="phase-subtitle">Performance breakdown by match phases</p>
    </div>

    <!-- FIX A1: Show unavailable state instead of mock data -->
    <div class="phase-unavailable">
      <div class="unavailable-icon">📊</div>
      <h3 class="unavailable-title">Phase Analysis Unavailable</h3>
      <p class="unavailable-message">
        This feature requires backend endpoint: 
        <code>{{ requiredEndpoint }}</code>
      </p>
      <p class="unavailable-detail">
        Phase analysis will show powerplay, middle, and death overs performance 
        once the backend analytics service is connected.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
// FIX A1: Remove ALL mock phase data, show unavailable state
// Backend endpoint required: GET /games/{gameId}/phase-analysis

const requiredEndpoint = 'GET /games/{gameId}/phase-analysis'
</script>

<style scoped>
.phase-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Unavailable State */
.phase-unavailable {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  text-align: center;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 2px dashed var(--color-border);
}

.unavailable-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.unavailable-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.unavailable-message {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

.unavailable-message code {
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: var(--text-sm);
  color: var(--color-primary);
}

.unavailable-detail {
  margin: var(--space-4) 0 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 500px;
}

/* Header */
.phase-header {
  margin-bottom: var(--space-2);
}

.phase-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.phase-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Phase Tabs */
.phase-tabs {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.phase-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.phase-tab:hover {
  color: var(--color-text);
}

.phase-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.phase-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Metrics */
.phase-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.metric-card {
  text-align: center;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

.metric-value.sr-high {
  color: #22c55e;
}

.metric-value.sr-normal {
  color: var(--color-text);
}

.metric-value.sr-low {
  color: #ef4444;
}

.metric-value.danger {
  color: #ef4444;
}

/* Details */
.phase-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}

.details-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.details-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

/* Trend Chart */
.trend-chart {
  width: 100%;
}

.trend-svg {
  width: 100%;
  height: auto;
}

.grid-line {
  stroke: var(--color-border);
  stroke-width: 1;
  stroke-dasharray: 4 4;
}

.axis {
  stroke: var(--color-text-muted);
  stroke-width: 2;
}

.trend-line {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trend-point {
  fill: var(--color-primary);
  stroke: white;
  stroke-width: 2;
}

/* Batting Order */
.batting-order {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.order-row {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.order-position {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary);
  color: white;
  font-weight: 700;
  font-size: var(--text-sm);
}

.order-player {
  min-width: 0;
}

.player-name {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.player-role {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.order-stats {
  display: flex;
  gap: var(--space-2);
}

.stat {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-primary);
  white-space: nowrap;
}

/* Key Moments */
.key-moments {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.moment-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.moment-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.moment-content {
  min-width: 0;
}

.moment-title {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.moment-time {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Phase Comparison */
.phase-comparison {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.comparison-title {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.comparison-chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.comparison-bar {
  display: grid;
  grid-template-columns: 100px 1fr 60px;
  gap: var(--space-3);
  align-items: center;
}

.bar-label {
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.bar-container {
  height: 32px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.bar-fill.phase-powerplay {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.bar-fill.phase-middle {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.bar-fill.phase-death {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.bar-value {
  text-align: right;
  font-weight: 600;
  color: var(--color-primary);
  font-size: var(--text-sm);
}

/* Stats Table */
.phase-stats-table {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.table-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.table-scroll {
  overflow-x: auto;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
}

.stats-table thead {
  background: var(--color-bg);
  border-bottom: 2px solid var(--color-border);
}

.stats-table th {
  padding: var(--space-3);
  text-align: left;
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stats-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.stats-table td.label {
  font-weight: 600;
  background: var(--color-bg);
  color: var(--color-text-muted);
}

.stats-table tbody tr:hover {
  background: var(--color-bg);
}

/* Insights */
.phase-insights {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-bg-secondary));
}

.insights-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}

.insight-card {
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.insight-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.insight-text {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 768px) {
  .phase-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .phase-details {
    grid-template-columns: 1fr;
  }

  .order-row {
    grid-template-columns: 40px 1fr;
  }

  .order-stats {
    grid-column: 1 / -1;
    flex-direction: column;
  }

  .comparison-bar {
    grid-template-columns: 80px 1fr 50px;
  }
}
</style>
