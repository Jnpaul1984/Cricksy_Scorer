<template>
  <div class="session-comparison">
    <div class="header">
      <h3>Session Comparison: Progress Tracking</h3>
      <p class="subtitle">Comparing {{ selectedJobIds.length }} analysis sessions</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading comparison data...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error">
      <p>❌ {{ error }}</p>
    </div>

    <!-- Comparison Results -->
    <div v-if="!loading && !error && comparisonData" class="comparison-results">
      <!-- Timeline Chart -->
      <section class="timeline-section">
        <h4>Performance Timeline</h4>
        <div class="chart-container">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </section>

      <!-- Improvements Table -->
      <section v-if="allImprovements.length > 0" class="improvements-section">
        <h4>🎯 Improvements Detected</h4>
        <table class="delta-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>From Score</th>
              <th>To Score</th>
              <th>Delta</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(improvement, idx) in allImprovements" :key="idx" class="improvement-row">
              <td class="metric-name">{{ improvement.code }}</td>
              <td class="from-session">{{ (improvement.from_score * 100).toFixed(0) }}%</td>
              <td class="to-session">{{ (improvement.to_score * 100).toFixed(0) }}%</td>
              <td class="delta positive">+{{ (improvement.delta * 100).toFixed(0) }}%</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Regressions Table -->
      <section v-if="allRegressions.length > 0" class="regressions-section">
        <h4>⚠️ Regressions Detected</h4>
        <table class="delta-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>From Score</th>
              <th>To Score</th>
              <th>Delta</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(regression, idx) in allRegressions" :key="idx" class="regression-row">
              <td class="metric-name">{{ regression.code }}</td>
              <td class="from-session">{{ (regression.from_score * 100).toFixed(0) }}%</td>
              <td class="to-session">{{ (regression.to_score * 100).toFixed(0) }}%</td>
              <td class="delta negative">{{ (regression.delta * 100).toFixed(0) }}%</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Persistent Issues Table -->
      <section v-if="comparisonData.persistent_issues.length > 0" class="persistent-issues-section">
        <h4>🔴 Persistent Issues (Avg &lt; 60%)</h4>
        <table class="delta-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Average Score</th>
              <th>Occurrences</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="issue in comparisonData.persistent_issues" :key="issue.code" class="issue-row">
              <td class="metric-name">{{ issue.title }}</td>
              <td class="avg-score">{{ (issue.avg_score * 100).toFixed(0) }}%</td>
              <td class="sessions-count">{{ issue.occurrences }}</td>
              <td class="trend">
                <span :class="['trend-badge', issue.trend]">{{ issue.trend }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- No Significant Changes -->
      <div v-if="!hasSignificantChanges" class="no-changes">
        <p>✅ Performance is stable across all sessions. No significant improvements or regressions detected.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartData,
  type ChartOptions,
} from 'chart.js';
import { ref, computed, onMounted } from 'vue';
import { Line } from 'vue-chartjs';

import { compareJobs, type CompareJobsResponse } from '@/services/coachPlusVideoService';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface Props {
  sessionId: string;
  selectedJobIds: string[];
}

const props = defineProps<Props>();

// State
const loading = ref(false);
const error = ref<string | null>(null);
const comparisonData = ref<CompareJobsResponse | null>(null);

// Computed: Flatten all improvements from deltas
const allImprovements = computed(() => {
  if (!comparisonData.value?.deltas) return [];
  return comparisonData.value.deltas.flatMap((d) => d.improvements);
});

// Computed: Flatten all regressions from deltas
const allRegressions = computed(() => {
  if (!comparisonData.value?.deltas) return [];
  return comparisonData.value.deltas.flatMap((d) => d.regressions);
});

// Computed: Chart data for timeline
const chartData = computed<ChartData<'line'>>(() => {
  if (!comparisonData.value?.timeline) {
    return {
      labels: [],
      datasets: [],
    };
  }

  const timeline = comparisonData.value.timeline;
  const labels = timeline.map((point, idx) => `Job ${idx + 1}`);

  // Extract unique metric codes
  const metricCodes = new Set<string>();
  timeline.forEach((point) => {
    Object.keys(point.metric_scores).forEach((code) => metricCodes.add(code));
  });

  // Generate color palette
  const colors = [
    '#3498db',
    '#e74c3c',
    '#2ecc71',
    '#f39c12',
    '#9b59b6',
    '#1abc9c',
    '#34495e',
    '#e67e22',
  ];

  // Create dataset for each metric
  const datasets = Array.from(metricCodes).map((code, index) => {
    const color = colors[index % colors.length];
    return {
      label: code.replace(/_/g, ' '),
      data: timeline.map((point) => (point.metric_scores[code] !== undefined ? point.metric_scores[code] * 100 : null)),
      borderColor: color,
      backgroundColor: color + '33', // Add transparency
      tension: 0.3,
      fill: false,
    };
  });

  return {
    labels,
    datasets,
  };
});

// Computed: Chart options
const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
    },
    title: {
      display: true,
      text: 'Metric Scores Over Time',
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const label = context.dataset.label || '';
          const value = context.parsed.y !== null ? context.parsed.y.toFixed(1) + '%' : 'N/A';
          return `${label}: ${value}`;
        },
      },
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      ticks: {
        callback: (value) => value + '%',
      },
      title: {
        display: true,
        text: 'Score (%)',
      },
    },
    x: {
      title: {
        display: true,
        text: 'Session',
      },
    },
  },
}));

// Computed: Check if there are significant changes
const hasSignificantChanges = computed(() => {
  if (!comparisonData.value) return false;
  return (
    allImprovements.value.length > 0 ||
    allRegressions.value.length > 0 ||
    comparisonData.value.persistent_issues.length > 0
  );
});

// Methods
async function fetchComparison() {
  loading.value = true;
  error.value = null;

  try {
    const response = await compareJobs(props.sessionId, props.selectedJobIds);
    comparisonData.value = response;
  } catch (err: any) {
    error.value = err.message || 'Failed to load comparison data';
  } finally {
    loading.value = false;
  }
}

// Lifecycle
onMounted(() => {
  if (props.selectedJobIds.length >= 2) {
    fetchComparison();
  } else {
    error.value = 'Please select at least 2 sessions to compare';
  }
});
</script>

<style scoped>
.session-comparison {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e0e0e0;
}

.header h3 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.subtitle {
  margin: 0;
  color: #7f8c8d;
  font-size: 0.95rem;
}

.loading,
.error {
  text-align: center;
  padding: 40px 20px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
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

.error {
  color: #e74c3c;
  font-size: 1rem;
}

.comparison-results section {
  margin-bottom: 32px;
}

.comparison-results section:last-child {
  margin-bottom: 0;
}

.comparison-results h4 {
  color: #34495e;
  font-size: 1.2rem;
  margin-bottom: 16px;
}

.timeline-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.chart-container {
  height: 400px;
  position: relative;
}

.delta-table {
  width: 100%;
  border-collapse: collapse;
  background: #f8f9fa;
  border-radius: 6px;
  overflow: hidden;
}

.delta-table thead {
  background: #34495e;
  color: white;
}

.delta-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 0.9rem;
}

.delta-table tbody tr {
  border-bottom: 1px solid #e0e0e0;
}

.delta-table tbody tr:last-child {
  border-bottom: none;
}

.improvement-row {
  background: #eafaf1;
}

.regression-row {
  background: #fadbd8;
}

.issue-row {
  background: #fdecea;
}

.delta-table td {
  padding: 12px;
  font-size: 0.95rem;
}

.metric-name {
  font-weight: 500;
  color: #2c3e50;
}

.delta {
  font-weight: 600;
  font-size: 1rem;
}

.delta.positive {
  color: #27ae60;
}

.delta.negative {
  color: #e74c3c;
}

.trend-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
}

.trend-badge.improving {
  background: #27ae60;
}

.trend-badge.declining {
  background: #e74c3c;
}

.no-changes {
  text-align: center;
  padding: 40px 20px;
  background: #eafaf1;
  border-radius: 8px;
  color: #27ae60;
  font-size: 1rem;
}

.no-changes p {
  margin: 0;
}
</style>
