<template>
  <section class="longitudinal-card">
    <div class="header">
      <div>
        <h3>Player longitudinal progress</h3>
        <p class="subtitle">
          Comparable V2 evidence across sessions for the selected player and discipline.
        </p>
      </div>
      <button type="button" class="refresh-button" :disabled="loading" @click="loadProgress">
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="loading" class="status-text">Loading longitudinal progress…</p>
    <p v-else-if="!progress || progress.series.length === 0" class="status-text">
      No comparable longitudinal metrics are available yet.
    </p>

    <div v-else class="content">
      <div class="summary-grid">
        <div class="summary-pill improving">Improving {{ progress.summary.improving }}</div>
        <div class="summary-pill regressing">Regressing {{ progress.summary.regressing }}</div>
        <div class="summary-pill stable">Stable {{ progress.summary.stable }}</div>
        <div class="summary-pill mixed">Mixed {{ progress.summary.mixed }}</div>
        <div class="summary-pill neutral">
          Insufficient {{ progress.summary.insufficient_data + progress.summary.non_comparable }}
        </div>
      </div>

      <div class="series-list">
        <article
          v-for="series in progress.series"
          :key="`${series.metric_id}:${series.phase ?? 'all'}:${series.action_type ?? 'all'}`"
          class="series-item"
        >
          <div class="series-main">
            <div>
              <h4>{{ series.metric_label }}</h4>
              <p class="meta">
                {{ formatDiscipline(series.discipline) }}
                <span v-if="series.phase">· {{ series.phase }}</span>
                <span v-if="series.action_type">· {{ series.action_type }}</span>
                <span>· {{ series.measurement_type === 'pose_measurement' ? 'Pose measurement' : 'Pose proxy' }}</span>
              </p>
            </div>
            <span :class="['trend-badge', trendVariant(series.trend.state)]">
              {{ humanize(series.trend.state) }}
            </span>
          </div>

          <div class="metric-grid">
            <div>
              <span class="label">Baseline</span>
              <strong>{{ formatObservationValue(series.baseline) }}</strong>
            </div>
            <div>
              <span class="label">Latest</span>
              <strong>{{ formatObservationValue(series.latest) }}</strong>
            </div>
            <div>
              <span class="label">Best</span>
              <strong>{{ series.best_available ? formatObservationValue(series.best) : 'Unavailable' }}</strong>
            </div>
            <div>
              <span class="label">Comparable sessions</span>
              <strong>{{ series.comparable_session_count }}</strong>
            </div>
          </div>

          <div class="sparkline-row">
            <MiniSparkline
              :points="series.history.map((item) => item.raw_value ?? 0).filter((item) => Number.isFinite(item))"
              :highlight-last="true"
              :show-fill="true"
              :variant="sparklineVariant(series.trend.state)"
            />
            <span class="sparkline-note">
              {{ formatTrend(series) }}
            </span>
          </div>

          <ul v-if="series.trend.limitations.length" class="limitations">
            <li v-for="limitation in series.trend.limitations" :key="limitation">{{ limitation }}</li>
          </ul>

          <details class="history-details">
            <summary>Session history ({{ series.history_count }})</summary>
            <div class="history-table-wrap">
              <table class="history-table">
                <thead>
                  <tr>
                    <th>Session</th>
                    <th>Value</th>
                    <th>Version</th>
                    <th>Capture</th>
                    <th>Comparable</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in series.history" :key="item.job_id ?? item.session_id">
                    <td>
                      <div>{{ item.session_title || item.session_id }}</div>
                      <small>{{ formatTimestamp(item.session_timestamp) }}</small>
                    </td>
                    <td>{{ formatObservationValue(item) }}</td>
                    <td>{{ item.metric_version }}</td>
                    <td>{{ [item.camera_view, formatFps(item.sample_fps)].filter(Boolean).join(' · ') || 'Unknown' }}</td>
                    <td>
                      <span :class="['comparable-badge', item.comparable ? 'yes' : 'no']">
                        {{ item.comparable ? 'Comparable' : 'Excluded' }}
                      </span>
                      <ul v-if="!item.comparable && item.comparability_reasons.length" class="reason-list">
                        <li v-for="reason in item.comparability_reasons" :key="reason">{{ reason }}</li>
                      </ul>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import MiniSparkline from '@/components/MiniSparkline.vue';
import {
  getPlayerLongitudinalProgress,
  type LongitudinalObservation,
  type PlayerLongitudinalProgressResponse,
} from '@/services/coachPlusVideoService';

const props = defineProps<{
  playerId: string | null | undefined;
  discipline?: string | null;
  visible?: boolean;
}>();

const loading = ref(false);
const error = ref<string | null>(null);
const progress = ref<PlayerLongitudinalProgressResponse | null>(null);

const canLoad = computed(() => Boolean(props.visible && props.playerId));

async function loadProgress() {
  if (!props.playerId) {
    progress.value = null;
    return;
  }

  loading.value = true;
  error.value = null;
  try {
    progress.value = await getPlayerLongitudinalProgress(props.playerId, props.discipline ?? null);
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load longitudinal progress';
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.playerId, props.discipline, props.visible] as const,
  ([playerId, _discipline, visible], [previousPlayerId, previousDiscipline, previousVisible]) => {
    if (!playerId || !visible) return;
    if (playerId !== previousPlayerId || props.discipline !== previousDiscipline || visible !== previousVisible) {
      loadProgress();
    }
  },
  { immediate: true },
);

function formatObservationValue(observation: LongitudinalObservation | null | undefined): string {
  if (!observation || observation.raw_value === null || observation.raw_value === undefined) return 'Unavailable';
  const suffix = observation.unit ? ` ${observation.unit}` : '';
  return `${observation.raw_value.toFixed(observation.unit === 'degrees' ? 1 : 3)}${suffix}`;
}

function humanize(value: string | null | undefined): string {
  if (!value) return 'Unknown';
  return value.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

function trendVariant(state: string): string {
  if (state === 'improving') return 'improving';
  if (state === 'regressing') return 'regressing';
  if (state === 'stable') return 'stable';
  if (state === 'mixed') return 'mixed';
  return 'neutral';
}

function sparklineVariant(state: string): 'positive' | 'negative' | 'neutral' | 'default' {
  if (state === 'improving') return 'positive';
  if (state === 'regressing') return 'negative';
  if (state === 'stable') return 'neutral';
  return 'default';
}

function formatTimestamp(value: string | null): string {
  if (!value) return 'Unknown date';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

function formatDiscipline(value: string | null): string {
  return humanize(value);
}

function formatFps(value: number | null): string {
  return value === null ? '' : `${value} fps`;
}

function formatTrend(series: PlayerLongitudinalProgressResponse['series'][number]): string {
  const change = series.trend.change_amount;
  const changeText =
    change === null || change === undefined
      ? 'No numeric change'
      : `${change > 0 ? '+' : ''}${change.toFixed(series.unit === 'degrees' ? 1 : 3)} ${series.trend.change_unit ?? ''}`.trim();
  const confidence =
    series.trend.confidence_score === null || series.trend.confidence_score === undefined
      ? 'confidence unavailable'
      : `${(series.trend.confidence_score * 100).toFixed(0)}% confidence`;
  return `${changeText} · ${series.trend.comparable_session_count} comparable sessions · ${confidence}`;
}
</script>

<style scoped>
.longitudinal-card {
  margin-top: 24px;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  background: #f8fbff;
  padding: 20px;
}

.header,
.series-main,
.sparkline-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.header {
  align-items: center;
}

.subtitle,
.meta,
.status-text,
.sparkline-note,
.label,
.reason-list,
.limitations {
  color: #5f6f82;
}

.summary-grid,
.metric-grid {
  display: grid;
  gap: 12px;
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  margin: 16px 0 20px;
}

.metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  margin: 16px 0;
}

.summary-pill,
.trend-badge,
.comparable-badge {
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.85rem;
  font-weight: 600;
}

.summary-pill.improving,
.trend-badge.improving,
.comparable-badge.yes {
  background: #e6f6ec;
  color: #157347;
}

.summary-pill.regressing,
.trend-badge.regressing,
.comparable-badge.no {
  background: #fdeaea;
  color: #b42318;
}

.summary-pill.stable,
.trend-badge.stable {
  background: #edf2f7;
  color: #344054;
}

.summary-pill.mixed,
.trend-badge.mixed,
.summary-pill.neutral,
.trend-badge.neutral {
  background: #fff4e5;
  color: #9a6700;
}

.series-list {
  display: grid;
  gap: 16px;
}

.series-item {
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  background: #fff;
  padding: 16px;
}

.refresh-button {
  border: 1px solid #b9c8d8;
  border-radius: 8px;
  background: #fff;
  padding: 8px 12px;
  cursor: pointer;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.label {
  display: block;
  font-size: 0.8rem;
}

.history-details {
  margin-top: 14px;
}

.history-table-wrap {
  overflow-x: auto;
  margin-top: 10px;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th,
.history-table td {
  padding: 10px 8px;
  border-top: 1px solid #edf2f7;
  text-align: left;
  vertical-align: top;
}

.reason-list,
.limitations {
  margin: 8px 0 0;
  padding-left: 18px;
}

.error {
  color: #b42318;
}

@media (max-width: 720px) {
  .header,
  .series-main,
  .sparkline-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
