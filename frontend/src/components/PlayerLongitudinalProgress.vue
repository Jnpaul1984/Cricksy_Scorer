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
    <p v-else-if="!playerPresentation" class="status-text">Progress summary is unavailable.</p>
    <div v-else class="content">
      <h4>{{ playerPresentation.state }}</h4>
      <p class="status-text">{{ playerPresentation.summary }}</p>
      <div v-if="playerPresentation.items.length" class="series-list">
        <article v-for="item in playerPresentation.items" :key="item.metric_id" class="series-item">
          <div class="series-main">
            <div>
              <h4>{{ item.title }}</h4>
              <p class="meta">{{ item.discipline }}</p>
            </div>
            <span :class="['trend-badge', trendVariant(item.state)]">
              {{ item.state }}
            </span>
          </div>

          <div class="metric-grid">
            <div>
              <span class="label">Baseline</span>
              <strong>{{ item.baseline }}</strong>
            </div>
            <div>
              <span class="label">Latest</span>
              <strong>{{ item.latest }}</strong>
            </div>
            <div>
              <span class="label">Comparable sessions</span>
              <strong>{{ item.comparable_session_count }}</strong>
            </div>
          </div>

          <ul v-if="item.limitations.length" class="limitations">
            <li v-for="limitation in item.limitations" :key="limitation">{{ limitation }}</li>
          </ul>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import {
  getPlayerLongitudinalProgress,
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

const playerPresentation = computed(() => progress.value?.player_presentation ?? null);

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
  (current, previous) => {
    const [playerId, _discipline, visible] = current;
    const previousPlayerId = previous?.[0];
    const previousDiscipline = previous?.[1];
    const previousVisible = previous?.[2];
    if (!playerId || !visible) return;
    if (
      playerId !== previousPlayerId ||
      props.discipline !== previousDiscipline ||
      visible !== previousVisible
    ) {
      loadProgress();
    }
  },
  { immediate: true },
);

function trendVariant(state: string): string {
  if (state === 'Improving') return 'improving';
  if (state === 'Needs attention') return 'regressing';
  if (state === 'Stable') return 'stable';
  return 'neutral';
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
