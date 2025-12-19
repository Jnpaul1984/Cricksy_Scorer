<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface InningsGradeData {
  grade: 'A+' | 'A' | 'B' | 'C' | 'D'
  score_percentage: number
  par_score: number
  total_runs: number
  run_rate: number
  wickets_lost: number
  wicket_efficiency: number
  boundary_count: number
  boundary_percentage: number
  dot_ball_ratio: number
  overs_played: number
  grade_factors: {
    score_percentage_contribution: string
    wicket_efficiency_contribution: string
    strike_rotation_contribution: string
    boundary_efficiency_contribution: string
  }
}

interface Props {
  gradeData: InningsGradeData | null
  battingTeam?: string
  bowlingTeam?: string
  theme?: 'dark' | 'light' | 'auto'
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  theme: 'dark',
  compact: false,
})

// Grade badge styling
const gradeColor = computed(() => {
  if (!props.gradeData) return '#9ca3af'
  const grade = props.gradeData.grade
  const colors: Record<string, string> = {
    'A+': '#22c55e', // Bright green
    'A': '#84cc16',  // Lime
    'B': '#eab308',  // Yellow
    'C': '#f97316',  // Orange
    'D': '#ef4444',  // Red
  }
  return colors[grade] || '#9ca3af'
})

const gradeBgColor = computed(() => {
  if (!props.gradeData) return 'rgba(156, 163, 175, 0.1)'
  const grade = props.gradeData.grade
  const colors: Record<string, string> = {
    'A+': 'rgba(34, 197, 94, 0.1)',    // Green
    'A': 'rgba(132, 204, 22, 0.1)',   // Lime
    'B': 'rgba(234, 179, 8, 0.1)',    // Yellow
    'C': 'rgba(249, 115, 22, 0.1)',   // Orange
    'D': 'rgba(239, 68, 68, 0.1)',    // Red
  }
  return colors[grade] || 'rgba(156, 163, 175, 0.1)'
})

const gradeDescription = computed(() => {
  if (!props.gradeData) return 'No grade data'
  const descriptions: Record<string, string> = {
    'A+': 'Exceptional - Outstanding performance',
    'A': 'Very Good - Excellent batting display',
    'B': 'Good - Solid innings performance',
    'C': 'Average - Acceptable but below par',
    'D': 'Below Average - Struggled against opposition',
  }
  return descriptions[props.gradeData.grade] || 'Unknown'
})

const resolvedTheme = computed<'dark' | 'light'>(() => {
  if (props.theme === 'dark') return 'dark'
  return 'light'
})
</script>

<template>
  <div class="innings-grade-widget" :class="{ compact }">
    <div v-if="gradeData" class="grade-display">
      <!-- Grade Badge -->
      <div class="grade-badge-section">
        <div
          class="grade-badge"
          :style="{ backgroundColor: gradeBgColor, borderColor: gradeColor }"
        >
          <div class="grade-letter" :style="{ color: gradeColor }">
            {{ gradeData.grade }}
          </div>
          <div class="grade-description">{{ gradeDescription }}</div>
        </div>
      </div>

      <!-- Key Metrics -->
      <div class="metrics-grid">
        <div class="metric">
          <div class="metric-label">Run Rate</div>
          <div class="metric-value">{{ gradeData.run_rate.toFixed(2) }}</div>
          <div class="metric-unit">runs/over</div>
        </div>

        <div class="metric">
          <div class="metric-label">Score vs Par</div>
          <div class="metric-value">{{ gradeData.score_percentage.toFixed(0) }}%</div>
          <div class="metric-unit">of {{ gradeData.par_score }}</div>
        </div>

        <div class="metric">
          <div class="metric-label">Wickets Lost</div>
          <div class="metric-value">{{ gradeData.wickets_lost }}</div>
          <div class="metric-unit">of 10</div>
        </div>

        <div class="metric">
          <div class="metric-label">Boundaries</div>
          <div class="metric-value">{{ gradeData.boundary_count }}</div>
          <div class="metric-unit">{{ gradeData.boundary_percentage.toFixed(0) }}% of runs</div>
        </div>
      </div>

      <!-- Grade Factors Breakdown -->
      <div v-if="!compact" class="factors-section">
        <h4 class="factors-title">Performance Factors</h4>
        <div class="factors-list">
          <div class="factor-item">
            <span class="factor-icon">📊</span>
            <span class="factor-text">{{ gradeData.grade_factors.score_percentage_contribution }}</span>
          </div>
          <div class="factor-item">
            <span class="factor-icon">🛡️</span>
            <span class="factor-text">{{ gradeData.grade_factors.wicket_efficiency_contribution }}</span>
          </div>
          <div class="factor-item">
            <span class="factor-icon">⚡</span>
            <span class="factor-text">{{ gradeData.grade_factors.strike_rotation_contribution }}</span>
          </div>
          <div class="factor-item">
            <span class="factor-icon">🎯</span>
            <span class="factor-text">{{ gradeData.grade_factors.boundary_efficiency_contribution }}</span>
          </div>
        </div>
      </div>

      <!-- Score Breakdown -->
      <div class="score-breakdown">
        <div class="breakdown-row">
          <span class="breakdown-label">Actual Score:</span>
          <span class="breakdown-value">{{ gradeData.total_runs }}/{{ gradeData.wickets_lost }}</span>
        </div>
        <div class="breakdown-row">
          <span class="breakdown-label">Overs Played:</span>
          <span class="breakdown-value">{{ gradeData.overs_played }}</span>
        </div>
        <div class="breakdown-row">
          <span class="breakdown-label">Par Score:</span>
          <span class="breakdown-value">{{ gradeData.par_score }}</span>
        </div>
      </div>
    </div>

    <div v-else class="no-data">
      <p>Grade data will be available as the innings progresses...</p>
    </div>
  </div>
</template>

<style scoped>
.innings-grade-widget {
  background: var(--pico-card-background-color);
  border: 1px solid var(--pico-card-border-color);
  border-radius: var(--pico-border-radius);
  padding: 1.25rem;
  margin: 1rem 0;
}

.innings-grade-widget.compact {
  padding: 0.75rem;
}

.grade-display {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.grade-badge-section {
  display: flex;
  justify-content: center;
}

.grade-badge {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.grade-letter {
  font-size: 3rem;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.05em;
}

.grade-description {
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 0.25rem;
  opacity: 0.9;
  line-height: 1.2;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
}

.metric {
  background: var(--pico-background-color);
  padding: 0.75rem;
  border-radius: var(--pico-border-radius);
  text-align: center;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--pico-color);
}

.metric-unit {
  font-size: 0.75rem;
  color: var(--pico-muted-color);
  margin-top: 0.25rem;
}

.factors-section {
  background: var(--pico-background-color);
  padding: 0.75rem;
  border-radius: var(--pico-border-radius);
}

.factors-title {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--pico-color);
}

.factors-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.factor-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--pico-muted-color);
}

.factor-icon {
  font-size: 1rem;
}

.factor-text {
  flex: 1;
}

.score-breakdown {
  border-top: 1px solid var(--pico-card-border-color);
  padding-top: 0.75rem;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  font-size: 0.9rem;
}

.breakdown-label {
  color: var(--pico-muted-color);
  font-weight: 500;
}

.breakdown-value {
  color: var(--pico-color);
  font-weight: 600;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: var(--pico-muted-color);
}

.no-data p {
  margin: 0;
  font-size: 0.95rem;
}

@media (max-width: 640px) {
  .grade-badge {
    width: 100px;
    height: 100px;
  }

  .grade-letter {
    font-size: 2.5rem;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
