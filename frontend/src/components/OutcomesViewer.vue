<template>
  <div class="outcomes-viewer">
    <div class="header">
      <h3>Goals vs Actual Outcomes</h3>
      <div class="compliance-badge" :class="complianceClass">
        Overall: {{ overallCompliance }}%
      </div>
    </div>

    <!-- Zone Outcomes Table -->
    <section v-if="zoneOutcomes.length > 0" class="outcomes-section">
      <h4>Target Zone Accuracy</h4>
      <table class="outcomes-table">
        <thead>
          <tr>
            <th>Zone</th>
            <th>Target %</th>
            <th>Actual %</th>
            <th>Delta</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="outcome in zoneOutcomes" :key="outcome.zone_name" :class="outcome.pass ? 'pass' : 'fail'">
            <td class="zone-name">{{ outcome.zone_name }}</td>
            <td class="target">{{ (outcome.target_accuracy * 100).toFixed(0) }}%</td>
            <td class="actual">{{ (outcome.actual_accuracy * 100).toFixed(0) }}%</td>
            <td class="delta" :class="deltaClass(outcome.delta)">
              {{ formatDelta(outcome.delta) }}
            </td>
            <td class="status">{{ outcome.pass ? '✅' : '❌' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="v2GoalEvidence.length > 0" class="outcomes-section">
      <h4>Deterministic V2 Goal Progress</h4>
      <table class="outcomes-table">
        <thead>
          <tr>
            <th>Goal</th>
            <th>Baseline</th>
            <th>Latest</th>
            <th>Status</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="goal in v2GoalEvidence" :key="goal.goal_id">
            <td>{{ goal.metric_id || goal.technical_area || goal.goal_id }}</td>
            <td>{{ formatObservation(goal.baseline) }}</td>
            <td>{{ formatObservation(goal.latest) }}</td>
            <td>{{ goal.status.replace(/_/g, ' ') }}</td>
            <td>{{ goal.confidence === null ? 'N/A' : `${Math.round(goal.confidence * 100)}%` }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="interventionItems.length > 0" class="outcomes-section">
      <h4>Recorded Interventions</h4>
      <ul class="no-outcomes" style="text-align: left; padding: 0;">
        <li v-for="(item, idx) in interventionItems" :key="idx">
          <strong>{{ String(item.activity || item.title || item.intervention_type || 'Intervention') }}</strong>
          <span v-if="item.completion_state"> · {{ String(item.completion_state) }}</span>
          <span v-if="item.frequency"> · {{ String(item.frequency) }}</span>
        </li>
      </ul>
    </section>

    <!-- Metric Outcomes Table -->
    <section v-if="metricOutcomes.length > 0" class="outcomes-section">
      <h4>Performance Metric Scores</h4>
      <table class="outcomes-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Target</th>
            <th>Actual</th>
            <th>Delta</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="outcome in metricOutcomes" :key="outcome.code" :class="outcome.pass ? 'pass' : 'fail'">
            <td class="metric-name">{{ outcome.title }}</td>
            <td class="target">{{ outcome.target_score.toFixed(2) }}</td>
            <td class="actual">{{ outcome.actual_score !== null ? outcome.actual_score.toFixed(2) : 'N/A' }}</td>
            <td class="delta" :class="deltaClass(outcome.delta)">
              {{ formatDelta(outcome.delta) }}
            </td>
            <td class="status">{{ outcome.pass ? '✅' : '❌' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- No Outcomes Message -->
    <div v-if="zoneOutcomes.length === 0 && metricOutcomes.length === 0" class="no-outcomes">
      <p>No outcomes available. Set goals and calculate compliance first.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { OutcomesResponse } from '@/services/coachPlusVideoService';

interface Props {
  goals?: {
    zones?: Array<{ zone_id: string; target_accuracy: number }>;
    metrics?: Array<{ code: string; target_score: number }>;
  };
  outcomes?: OutcomesResponse;
}

const props = defineProps<Props>();

// Computed: Overall compliance percentage
const overallCompliance = computed(() => {
  if (props.outcomes?.overall_compliance_pct === null || props.outcomes?.overall_compliance_pct === undefined) return 0;
  return Math.round(props.outcomes.overall_compliance_pct);
});

// Computed: Compliance badge CSS class
const complianceClass = computed(() => {
  const pct = overallCompliance.value;
  if (pct >= 80) return 'excellent';
  if (pct >= 60) return 'good';
  if (pct >= 40) return 'fair';
  return 'poor';
});

// Computed: Zone outcomes with enriched data
const zoneOutcomes = computed(() => {
  if (!props.outcomes?.zones) return [];
  return props.outcomes.zones.map((zone) => ({
    ...zone,
    delta: zone.actual_accuracy - zone.target_accuracy,
  }));
});

// Computed: Metric outcomes with enriched data
const metricOutcomes = computed(() => {
  if (!props.outcomes?.metrics) return [];
  return props.outcomes.metrics.map((metric) => ({
    ...metric,
    delta: metric.actual_score !== null ? metric.actual_score - metric.target_score : null,
  }));
});

const v2GoalEvidence = computed(() => props.outcomes?.v2_target_evidence || []);
const interventionItems = computed(() => props.outcomes?.interventions || []);

// Utility: Format delta with + or - prefix
function formatDelta(delta: number | null): string {
  if (delta === null) return 'N/A';
  const formatted = (delta * 100).toFixed(0);
  return delta >= 0 ? `+${formatted}%` : `${formatted}%`;
}

// Utility: CSS class for delta (positive = green, negative = red)
function deltaClass(delta: number | null): string {
  if (delta === null) return '';
  if (delta >= 0.05) return 'positive';
  if (delta <= -0.05) return 'negative';
  return 'neutral';
}

function formatObservation(observation: { raw_value?: number | null; unit?: string | null } | null): string {
  if (!observation || observation.raw_value === null || observation.raw_value === undefined) return 'N/A';
  return `${observation.raw_value.toFixed(3)}${observation.unit ? ` ${observation.unit}` : ''}`;
}
</script>

<style scoped>
.outcomes-viewer {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e0e0e0;
}

.header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.4rem;
}

.compliance-badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 1rem;
  color: white;
}

.compliance-badge.excellent {
  background: #27ae60;
}

.compliance-badge.good {
  background: #3498db;
}

.compliance-badge.fair {
  background: #f39c12;
}

.compliance-badge.poor {
  background: #e74c3c;
}

.outcomes-section {
  margin-bottom: 32px;
}

.outcomes-section:last-child {
  margin-bottom: 0;
}

.outcomes-section h4 {
  color: #34495e;
  font-size: 1.1rem;
  margin-bottom: 12px;
}

.outcomes-table {
  width: 100%;
  border-collapse: collapse;
  background: #f8f9fa;
  border-radius: 6px;
  overflow: hidden;
}

.outcomes-table thead {
  background: #34495e;
  color: white;
}

.outcomes-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 0.9rem;
}

.outcomes-table tbody tr {
  border-bottom: 1px solid #e0e0e0;
}

.outcomes-table tbody tr:last-child {
  border-bottom: none;
}

.outcomes-table tbody tr.pass {
  background: #eafaf1;
}

.outcomes-table tbody tr.fail {
  background: #fadbd8;
}

.outcomes-table td {
  padding: 12px;
  font-size: 0.95rem;
}

.zone-name,
.metric-name {
  font-weight: 500;
  color: #2c3e50;
}

.target {
  color: #7f8c8d;
}

.actual {
  font-weight: 600;
  color: #2c3e50;
}

.delta {
  font-weight: 500;
}

.delta.positive {
  color: #27ae60;
}

.delta.negative {
  color: #e74c3c;
}

.delta.neutral {
  color: #95a5a6;
}

.status {
  font-size: 1.2rem;
  text-align: center;
}

.no-outcomes {
  text-align: center;
  padding: 40px 20px;
  color: #7f8c8d;
}

.no-outcomes p {
  margin: 0;
  font-size: 1rem;
}
</style>
