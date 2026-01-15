<template>
  <div class="form-tracker-widget">
    <div class="form-tracker-header">
      <h3 class="form-tracker-title">📈 Recent Form (Last 10 Matches)</h3>
      <div class="form-tracker-summary">
        <div class="form-badge" :class="`form-badge--${formData.recentForm}`">
          {{ getFormLabel(formData.recentForm) }}
        </div>
        <div class="trend-indicator" :title="`Form: ${getTrendLabel(formData.overallTrend)}`">
          <span class="trend-arrow">{{ trendEmoji[formData.overallTrend] }}</span>
          <span class="trend-label">{{ getTrendLabel(formData.overallTrend) }}</span>
        </div>
      </div>
    </div>

    <div class="form-chart">
      <div
        v-for="match in formData.matches"
        :key="match.matchIndex"
        class="form-bar-container"
        :title="`Match ${match.matchIndex}: SR ${match.strikeRate.toFixed(1)}`"
      >
        <div
          class="form-bar"
          :class="getFormClass(match.performance)"
          :style="{
            height: `${(match.strikeRate / 200) * 100}%`,
            backgroundColor: colorMap[match.performance],
          }"
        />
        <div class="form-label">M{{ match.matchIndex }}</div>
      </div>
    </div>

    <div class="form-legend">
      <div class="legend-item">
        <div class="legend-color good" />
        <span>Good Form (SR ≥ 130)</span>
      </div>
      <div class="legend-item">
        <div class="legend-color average" />
        <span>Average (SR 90-129)</span>
      </div>
      <div class="legend-item">
        <div class="legend-color poor" />
        <span>Poor Form (SR < 90)</span>
      </div>
    </div>

    <div class="form-stats">
      <div class="stat-row">
        <span class="stat-label">Average Performance:</span>
        <span class="stat-value" :class="`form-${formData.averagePerformance}`">
          {{ getFormLabel(formData.averagePerformance) }}
        </span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Current Trend:</span>
        <span class="stat-value">
          {{ trendEmoji[formData.overallTrend] }} {{ getTrendLabel(formData.overallTrend) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'

import { usePlayerFormTracker } from '@/composables/usePlayerFormTracker'
import type { PlayerProfile } from '@/types/player'

const props = defineProps<{
  profile: PlayerProfile | null
}>()

const { formData, colorMap, trendEmoji, getFormClass, getFormLabel, getTrendLabel } =
  usePlayerFormTracker({ value: props.profile })
</script>

<style scoped>
.form-tracker-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

/* Header */
.form-tracker-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
}

.form-tracker-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.form-tracker-summary {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

/* Form Badge */
.form-badge {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 600;
  white-space: nowrap;
}

.form-badge--good {
  background: rgb(220, 252, 231);
  color: rgb(22, 101, 52);
  border: 1px solid rgb(134, 239, 172);
}

.form-badge--average {
  background: rgb(254, 252, 232);
  color: rgb(113, 63, 18);
  border: 1px solid rgb(253, 224, 71);
}

.form-badge--poor {
  background: rgb(254, 226, 226);
  color: rgb(127, 29, 29);
  border: 1px solid rgb(252, 165, 165);
}

/* Trend Indicator */
.trend-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.trend-arrow {
  font-size: var(--text-lg);
  font-weight: bold;
}

.trend-label {
  font-weight: 500;
}

/* Form Chart */
.form-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: var(--space-2);
  height: 150px;
  padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.form-bar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  gap: var(--space-2);
  min-width: 0;
}

.form-bar {
  width: 100%;
  min-height: 4px;
  border-radius: var(--radius-sm);
  transition: opacity 0.2s ease, transform 0.2s ease;
  cursor: pointer;
}

.form-bar:hover {
  opacity: 0.8;
  transform: scaleY(1.1);
}

.form-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
  text-align: center;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Legend */
.form-legend {
  display: flex;
  justify-content: center;
  gap: var(--space-6);
  flex-wrap: wrap;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 2px;
}

.legend-color.good {
  background: rgb(34, 197, 94);
}

.legend-color.average {
  background: rgb(234, 179, 8);
}

.legend-color.poor {
  background: rgb(239, 68, 68);
}

/* Stats */
.form-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
}

.stat-label {
  color: var(--color-text-muted);
  font-weight: 500;
}

.stat-value {
  font-weight: 600;
}

.stat-value.form-good {
  color: rgb(22, 101, 52);
}

.stat-value.form-average {
  color: rgb(113, 63, 18);
}

.stat-value.form-poor {
  color: rgb(127, 29, 29);
}

/* Responsive */
@media (max-width: 640px) {
  .form-tracker-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-tracker-summary {
    width: 100%;
    justify-content: space-between;
  }

  .form-chart {
    gap: var(--space-1);
    padding: var(--space-3) 0;
  }

  .form-legend {
    flex-direction: column;
    gap: var(--space-3);
  }

  .legend-item {
    width: 100%;
  }
}
</style>
