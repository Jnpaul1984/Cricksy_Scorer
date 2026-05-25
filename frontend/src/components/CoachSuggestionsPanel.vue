<template>
  <div class="coach-suggestions-panel">
    <div v-if="!suggestions" class="empty-state">
      <p>No coaching suggestions generated yet.</p>
      <button @click="$emit('generate')" class="btn-generate">
        🤖 Generate AI Suggestions
      </button>
    </div>

    <div v-else class="suggestions-content">
      <!-- Primary Focus -->
      <section class="focus-section primary">
        <h3>🎯 Primary Focus</h3>
        <div class="focus-card">
          <div class="focus-header">
            <strong>{{ suggestions.primary_focus.title }}</strong>
            <span :class="['severity-badge', suggestions.primary_focus.severity]">
              {{ suggestions.primary_focus.severity.toUpperCase() }}
            </span>
          </div>
          <p class="rationale">{{ suggestions.primary_focus.rationale }}</p>
        </div>
      </section>

      <!-- Secondary Focus (if any) -->
      <section v-if="suggestions.secondary_focus" class="focus-section secondary">
        <h3>🔍 Secondary Focus</h3>
        <div class="focus-card">
          <div class="focus-header">
            <strong>{{ suggestions.secondary_focus.title }}</strong>
            <span :class="['severity-badge', suggestions.secondary_focus.severity]">
              {{ suggestions.secondary_focus.severity.toUpperCase() }}
            </span>
          </div>
          <p class="rationale">{{ suggestions.secondary_focus.rationale }}</p>
        </div>
      </section>

      <!-- Coaching Cues -->
      <section class="cues-section">
        <h3>💡 Coaching Cues</h3>
        <ul class="cues-list">
          <li v-for="(cue, idx) in suggestions.coaching_cues" :key="idx">
            {{ cue }}
          </li>
        </ul>
      </section>

      <!-- Recommended Drills -->
      <section class="drills-section">
        <h3>🏋️ Recommended Drills</h3>
        <div class="drills-grid">
          <div v-for="(drill, idx) in suggestions.drills" :key="idx" class="drill-card">
            <h4>{{ drill.name }}</h4>
            <p class="drill-desc">{{ drill.description }}</p>
            <div class="drill-meta">
              <span class="drill-tag">📦 {{ drill.equipment }}</span>
              <span class="drill-tag">🎯 {{ drill.focus }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Proposed Next Goal -->
      <section class="next-goal-section">
        <h3>🚀 Proposed Next Session Goal</h3>
        <div class="goal-card">
          <div v-if="suggestions.proposed_next_goal.zones.length > 0" class="goal-zones">
            <strong>Target Zones:</strong>
            <ul>
              <li v-for="zone in suggestions.proposed_next_goal.zones" :key="zone.zone_id">
                {{ zone.zone_name }} - {{ zone.target_accuracy }}% accuracy
              </li>
            </ul>
          </div>
          <div v-if="suggestions.proposed_next_goal.metrics.length > 0" class="goal-metrics">
            <strong>Target Metrics:</strong>
            <ul>
              <li v-for="metric in suggestions.proposed_next_goal.metrics" :key="metric.code">
                {{ metric.code }}: {{ (metric.target_score * 100).toFixed(0) }}% or better
              </li>
            </ul>
          </div>
        </div>
        <p class="goal-rationale"><em>{{ suggestions.rationale }}</em></p>
        <button @click="$emit('approve-goal', suggestions.proposed_next_goal)" class="btn-approve">
          ✅ Approve as Next Session Goal
        </button>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CoachSuggestionsResponse } from '@/services/coachPlusVideoService';

defineProps<{
  suggestions: CoachSuggestionsResponse | null;
}>();

defineEmits<{
  generate: [];
  'approve-goal': [goal: CoachSuggestionsResponse['proposed_next_goal']];
}>();
</script>

<style scoped>
.coach-suggestions-panel {
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 8px;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
}

.btn-generate {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-generate:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.suggestions-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.focus-section h3,
.cues-section h3,
.drills-section h3,
.next-goal-section h3 {
  margin-bottom: 1rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
}

.focus-card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.focus-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.focus-header strong {
  font-size: 1.1rem;
  color: #111827;
}

.severity-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.severity-badge.critical {
  background: #fee2e2;
  color: #991b1b;
}

.severity-badge.major {
  background: #fed7aa;
  color: #9a3412;
}

.severity-badge.minor {
  background: #fef3c7;
  color: #92400e;
}

.rationale {
  color: #6b7280;
  line-height: 1.6;
}

.cues-list {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  list-style: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.cues-list li {
  padding: 0.75rem 0;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.cues-list li:last-child {
  border-bottom: none;
}

.cues-list li::before {
  content: '✓';
  color: #10b981;
  font-weight: 700;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.drills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.drill-card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.drill-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.drill-card h4 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
}

.drill-desc {
  color: #6b7280;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

.drill-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.drill-tag {
  padding: 0.25rem 0.5rem;
  background: #f3f4f6;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #4b5563;
}

.goal-card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.goal-zones,
.goal-metrics {
  margin-bottom: 1rem;
}

.goal-zones:last-child,
.goal-metrics:last-child {
  margin-bottom: 0;
}

.goal-card strong {
  display: block;
  margin-bottom: 0.5rem;
  color: #111827;
}

.goal-card ul {
  list-style: none;
  padding-left: 1rem;
}

.goal-card li {
  padding: 0.25rem 0;
  color: #4b5563;
}

.goal-card li::before {
  content: '→';
  margin-right: 0.5rem;
  color: #6366f1;
}

.goal-rationale {
  color: #6b7280;
  font-style: italic;
  margin-bottom: 1rem;
  line-height: 1.6;
}

.btn-approve {
  padding: 0.75rem 1.5rem;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.btn-approve:hover {
  background: #059669;
  transform: translateY(-2px);
}
</style>
