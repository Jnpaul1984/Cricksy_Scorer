<template>
  <div class="strength-weakness-widget">
    <div class="sw-container">
      <!-- Strengths Section -->
      <div class="sw-section strengths-section">
        <div class="sw-header">
          <h3 class="sw-title">💪 Strengths</h3>
          <span class="sw-count">{{ strengths.length }}</span>
        </div>
        <div v-if="strengths.length > 0" class="sw-list">
          <div v-for="(strength, idx) in strengths" :key="`strength-${idx}`" class="sw-item strength-item">
            <div class="sw-item-badge good">{{ idx + 1 }}</div>
            <div class="sw-item-content">
              <p class="sw-item-text">{{ strength }}</p>
            </div>
          </div>
        </div>
        <p v-else class="sw-empty">No strengths identified yet. Keep playing to build a profile!</p>
      </div>

      <!-- Weaknesses Section -->
      <div class="sw-section weaknesses-section">
        <div class="sw-header">
          <h3 class="sw-title">🎯 Areas to Improve</h3>
          <span class="sw-count">{{ weaknesses.length }}</span>
        </div>
        <div v-if="weaknesses.length > 0" class="sw-list">
          <div v-for="(weakness, idx) in weaknesses" :key="`weakness-${idx}`" class="sw-item weakness-item">
            <div class="sw-item-badge poor">{{ idx + 1 }}</div>
            <div class="sw-item-content">
              <p class="sw-item-text">{{ weakness }}</p>
              <p class="sw-item-tip">💡 Focus on this area in practice</p>
            </div>
          </div>
        </div>
        <p v-else class="sw-empty">Great! No major weaknesses to work on right now.</p>
      </div>
    </div>

    <!-- Development Focus -->
    <div class="development-focus">
      <div class="focus-header">
        <h4 class="focus-title">📋 Recommended Focus Areas</h4>
      </div>
      <div v-if="weaknesses.length > 0" class="focus-tips">
        <div v-for="(weakness, idx) in weaknesses.slice(0, 2)" :key="`tip-${idx}`" class="focus-tip">
          <div class="tip-number">{{ idx + 1 }}</div>
          <div class="tip-content">
            <p class="tip-text">{{ weakness }}</p>
            <p class="tip-action">Practice drills focusing on this weakness</p>
          </div>
        </div>
      </div>
      <div v-else class="focus-tips">
        <p class="focus-empty">Continue improving by taking on more challenging match scenarios!</p>
      </div>
    </div>

    <!-- Progress Indicator -->
    <div class="sw-progress">
      <div class="progress-bar-container">
        <div class="progress-label">Overall Profile Strength</div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${strengthScore}%` }" :class="strengthClass" />
        </div>
        <div class="progress-value">{{ strengthLabel }} ({{ strengthScore }}%)</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed } from 'vue'
import type { PlayerProfile } from '@/types/player'

const props = defineProps<{
  profile: PlayerProfile | null
  strengths?: string[]
  weaknesses?: string[]
}>()

// Default strengths and weaknesses based on profile stats
const defaultStrengths = computed<string[]>(() => {
  const strengths: string[] = []
  if (!props.profile) return strengths

  if (props.profile.strike_rate > 140) strengths.push('Aggressive batting with excellent strike rate')
  if (props.profile.batting_average > 40) strengths.push('Consistent batting performance')
  if (props.profile.total_fours + props.profile.total_sixes > 20)
    strengths.push('Strong boundary hitting ability')
  if (props.profile.total_wickets > 10) strengths.push('Reliable bowling skills')
  if (props.profile.economy_rate < 8) strengths.push('Economical bowling')
  if (props.profile.catches > 5) strengths.push('Good fielding consistency')

  return strengths.length > 0 ? strengths : ['Developing player with potential']
})

const defaultWeaknesses = computed<string[]>(() => {
  const weaknesses: string[] = []
  if (!props.profile) return weaknesses

  if (props.profile.strike_rate < 100)
    weaknesses.push('Strike rate could be improved - work on attacking more')
  if (props.profile.batting_average < 25)
    weaknesses.push('Batting consistency - focus on playing more match situations')
  if (props.profile.times_out > 5)
    weaknesses.push('Dismissal patterns - reduce reckless shots')
  if (props.profile.total_wickets === 0) weaknesses.push('Bowling - develop bowling variations')
  if (props.profile.economy_rate > 10)
    weaknesses.push('Economy rate - practice bowling at right pace')

  return weaknesses.length > 0 ? weaknesses : []
})

const strengths = computed(() => props.strengths || defaultStrengths.value)
const weaknesses = computed(() => props.weaknesses || defaultWeaknesses.value)

// Calculate overall strength score
const strengthScore = computed(() => {
  if (!props.profile) return 0

  let score = 0
  // Scale: 0-100 based on various metrics
  score += Math.min(props.profile.strike_rate / 150 * 25, 25) // Strike rate (25 points)
  score += Math.min((props.profile.batting_average / 50) * 20, 20) // Average (20 points)
  score += Math.min((props.profile.total_wickets / 20) * 20, 20) // Bowling (20 points)
  score += Math.min((props.profile.catches / 10) * 15, 15) // Fielding (15 points)
  score += Math.min((props.profile.total_matches / 50) * 20, 20) // Experience (20 points)

  return Math.round(Math.min(score, 100))
})

const strengthClass = computed(() => {
  if (strengthScore.value >= 80) return 'strength-excellent'
  if (strengthScore.value >= 60) return 'strength-good'
  if (strengthScore.value >= 40) return 'strength-average'
  return 'strength-developing'
})

const strengthLabel = computed(() => {
  if (strengthScore.value >= 80) return 'Excellent'
  if (strengthScore.value >= 60) return 'Good'
  if (strengthScore.value >= 40) return 'Average'
  return 'Developing'
})
</script>

<style scoped>
.strength-weakness-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Container Layout */
.sw-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.sw-section {
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* Section Header */
.sw-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sw-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.sw-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  font-weight: 600;
}

/* List Items */
.sw-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.sw-item {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.sw-item-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: var(--text-sm);
  flex-shrink: 0;
}

.sw-item-badge.good {
  background: rgb(220, 252, 231);
  color: rgb(22, 101, 52);
}

.sw-item-badge.poor {
  background: rgb(254, 226, 226);
  color: rgb(127, 29, 29);
}

.sw-item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.sw-item-text {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text);
  line-height: 1.4;
}

.sw-item-tip {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

.sw-empty {
  margin: 0;
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px dashed var(--color-border);
}

/* Development Focus */
.development-focus {
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-primary);
}

.focus-header {
  margin-bottom: var(--space-3);
}

.focus-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
}

.focus-tips {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.focus-tip {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.tip-number {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: var(--text-sm);
}

.tip-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tip-text {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text);
}

.tip-action {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.focus-empty {
  margin: 0;
  padding: var(--space-4);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px dashed var(--color-border);
}

/* Progress Bar */
.sw-progress {
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.progress-bar-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.progress-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-bg);
  border-radius: var(--radius-pill);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  border-radius: var(--radius-pill);
}

.strength-excellent {
  background: rgb(34, 197, 94);
}

.strength-good {
  background: rgb(59, 130, 246);
}

.strength-average {
  background: rgb(234, 179, 8);
}

.strength-developing {
  background: rgb(239, 68, 68);
}

.progress-value {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: right;
}

/* Responsive */
@media (max-width: 768px) {
  .sw-container {
    grid-template-columns: 1fr;
  }
}
</style>
