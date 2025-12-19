<template>
  <div class="phase-timeline-widget">
    <!-- Header -->
    <div class="widget-header">
      <h3>Match Phase Timeline</h3>
      <div class="header-actions">
        <span v-if="currentPhase" class="current-phase-badge" :class="currentPhase">
          Current: {{ formatPhaseName(currentPhase) }}
        </span>
        <button v-if="onRefresh" @click="onRefresh" class="refresh-btn" :disabled="loading">
          ⟳
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Analyzing match phases...</p>
    </div>

    <!-- Error State -->
    <div v-if="error && !loading" class="error-state">
      <p>⚠️ {{ error }}</p>
    </div>

    <!-- Phase Timeline -->
    <div v-if="phaseData && !loading && !error" class="timeline-container">
      <!-- Phase Cards -->
      <div class="phases-grid">
        <div
          v-for="phase in phaseData.phases"
          :key="`phase-${phase.phase_number}`"
          class="phase-card"
          :class="{
            active: phase.phase_name === currentPhase,
            completed: isPhaseCompleted(phase),
          }"
        >
          <!-- Phase Name & Range -->
          <div class="phase-header">
            <h4>{{ formatPhaseName(phase.phase_name) }}</h4>
            <span class="over-range">Overs {{ phase.start_over }}-{{ phase.end_over }}</span>
          </div>

          <!-- Phase Stats Grid -->
          <div class="phase-stats">
            <!-- Runs -->
            <div class="stat-item">
              <span class="stat-label">Runs</span>
              <span class="stat-value">{{ phase.total_runs }}/{{ Math.round(phase.expected_runs_in_phase) }}</span>
              <div class="stat-bar">
                <div
                  class="stat-fill"
                  :style="{ width: `${Math.min(phase.actual_vs_expected_pct, 100)}%` }"
                  :class="getEfficiencyClass(phase.actual_vs_expected_pct)"
                ></div>
              </div>
              <span class="stat-pct">{{ Math.round(phase.actual_vs_expected_pct) }}%</span>
            </div>

            <!-- Run Rate -->
            <div class="stat-item">
              <span class="stat-label">RR</span>
              <span class="stat-value">{{ phase.run_rate.toFixed(1) }} /over</span>
            </div>

            <!-- Wickets -->
            <div class="stat-item">
              <span class="stat-label">Wickets</span>
              <span class="stat-value">{{ phase.total_wickets }}</span>
            </div>

            <!-- Boundaries -->
            <div class="stat-item">
              <span class="stat-label">Fours/Sixes</span>
              <span class="stat-value">{{ phase.boundary_count }}</span>
            </div>
          </div>

          <!-- Phase Indicators -->
          <div class="phase-indicators">
            <!-- Aggressive Index -->
            <div class="indicator">
              <span class="indicator-label">Aggression</span>
              <div class="indicator-bar">
                <div
                  class="indicator-fill aggression"
                  :style="{ width: `${Math.min(phase.aggressive_index * 100, 100)}%` }"
                ></div>
              </div>
              <span class="indicator-value">{{ (phase.aggressive_index * 100).toFixed(0) }}%</span>
            </div>

            <!-- Dot Balls -->
            <div class="indicator">
              <span class="indicator-label">Dots</span>
              <div class="indicator-bar">
                <div
                  class="indicator-fill dots"
                  :style="{ width: `${(phase.dot_ball_count / phase.total_deliveries) * 100}%` }"
                ></div>
              </div>
              <span class="indicator-value">{{ phase.dot_ball_count }}/{{ phase.total_deliveries }}</span>
            </div>

            <!-- Wicket Rate -->
            <div class="indicator">
              <span class="indicator-label">Wicket Rate</span>
              <div class="indicator-bar">
                <div
                  class="indicator-fill wickets"
                  :style="{ width: `${Math.min(phase.wicket_rate * 20, 100)}%` }"
                ></div>
              </div>
              <span class="indicator-value">{{ phase.wicket_rate.toFixed(2) }}/over</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Summary Section -->
      <div class="summary-section">
        <h4>Overall Performance</h4>
        <div class="summary-grid">
          <div class="summary-item">
            <span>Total Runs</span>
            <span class="value">{{ phaseData.summary.total_runs }}</span>
          </div>
          <div class="summary-item">
            <span>Wickets Lost</span>
            <span class="value">{{ phaseData.summary.total_wickets }}</span>
          </div>
          <div class="summary-item">
            <span>Run Rate</span>
            <span class="value">{{ phaseData.summary.overall_run_rate.toFixed(1) }}</span>
          </div>
          <div class="summary-item">
            <span>Expected Total</span>
            <span class="value">{{ Math.round(phaseData.summary.overall_expected_runs) }}</span>
          </div>
          <div class="summary-item">
            <span>Acceleration</span>
            <span :class="`trend-${phaseData.summary.acceleration_trend}`">
              {{ formatTrend(phaseData.summary.acceleration_trend) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Predictions Section -->
      <div v-if="predictions" class="predictions-section">
        <h4>Predictions</h4>
        <div class="predictions-grid">
          <div class="prediction-item">
            <span>Expected Total</span>
            <span class="value">{{ predictions.match_prediction.projected_total }} runs</span>
          </div>
          <div v-if="predictions.match_prediction.win_probability" class="prediction-item">
            <span>Win Probability</span>
            <span :class="getProbabilityClass(predictions.match_prediction.win_probability)">
              {{ (predictions.match_prediction.win_probability * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="prediction-item">
            <span>Confidence</span>
            <span class="value">{{ (predictions.match_prediction.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!phaseData && !loading && !error" class="empty-state">
      <p>No phase data available</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PhaseAnalysisData, PhasePredictionData } from '@/composables/usePhaseAnalytics'

interface Props {
  phaseData: PhaseAnalysisData | null
  predictions?: PhasePredictionData | null
  loading?: boolean
  error?: string | null
  onRefresh?: () => void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  predictions: null,
  onRefresh: undefined,
})

const currentPhase = computed(() => props.phaseData?.current_phase || 'powerplay')

function formatPhaseName(phase: string): string {
  const names: Record<string, string> = {
    powerplay: '⚡ Powerplay',
    middle: '📊 Middle Overs',
    death: '🔥 Death Overs',
    mini_death: '⚠️ Mini-Death',
  }
  return names[phase] || phase
}

function formatTrend(trend: string): string {
  const icons: Record<string, string> = {
    increasing: '📈 Increasing',
    decreasing: '📉 Decreasing',
    stable: '➡️ Stable',
  }
  return icons[trend] || trend
}

function isPhaseCompleted(phase: any): boolean {
  return phase.phase_number < (props.phaseData?.phase_index || 0)
}

function getEfficiencyClass(efficiency: number): string {
  if (efficiency >= 100) return 'excellent'
  if (efficiency >= 85) return 'good'
  if (efficiency >= 70) return 'average'
  return 'poor'
}

function getProbabilityClass(prob: number): string {
  if (prob >= 0.8) return 'very-high'
  if (prob >= 0.6) return 'high'
  if (prob >= 0.4) return 'moderate'
  return 'low'
}
</script>

<style scoped lang="scss">
.phase-timeline-widget {
  background: linear-gradient(135deg, #1a1d2e 0%, #16192b 100%);
  border-radius: 12px;
  padding: 20px;
  color: #e0e0e0;

  .widget-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 12px;

    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .current-phase-badge {
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      background: rgba(255, 255, 255, 0.1);

      &.powerplay {
        background: rgba(100, 200, 255, 0.2);
        color: #64c8ff;
      }
      &.middle {
        background: rgba(255, 200, 100, 0.2);
        color: #ffc864;
      }
      &.death {
        background: rgba(255, 100, 100, 0.2);
        color: #ff6464;
      }
      &.mini_death {
        background: rgba(255, 100, 200, 0.2);
        color: #ff64c8;
      }
    }

    .refresh-btn {
      background: rgba(100, 200, 255, 0.2);
      border: 1px solid rgba(100, 200, 255, 0.3);
      color: #64c8ff;
      width: 32px;
      height: 32px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        background: rgba(100, 200, 255, 0.3);
        transform: rotate(180deg);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }

  .loading-state,
  .error-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
    color: #999;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: #64c8ff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .timeline-container {
    .phases-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin-bottom: 24px;

      .phase-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 16px;
        transition: all 0.3s ease;

        &.active {
          background: rgba(100, 200, 255, 0.1);
          border-color: rgba(100, 200, 255, 0.3);
          box-shadow: 0 0 16px rgba(100, 200, 255, 0.1);
        }

        &.completed {
          opacity: 0.7;
        }

        .phase-header {
          margin-bottom: 12px;

          h4 {
            margin: 0 0 4px 0;
            font-size: 14px;
            font-weight: 600;
          }

          .over-range {
            font-size: 12px;
            color: #999;
          }
        }

        .phase-stats {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;

          .stat-item {
            display: flex;
            flex-direction: column;
            gap: 4px;

            .stat-label {
              font-size: 11px;
              color: #999;
              text-transform: uppercase;
            }

            .stat-value {
              font-size: 13px;
              font-weight: 600;
            }

            .stat-bar {
              height: 4px;
              background: rgba(255, 255, 255, 0.1);
              border-radius: 2px;
              overflow: hidden;

              .stat-fill {
                height: 100%;
                transition: all 0.3s ease;

                &.excellent {
                  background: #4ade80;
                }
                &.good {
                  background: #60a5fa;
                }
                &.average {
                  background: #fbbf24;
                }
                &.poor {
                  background: #f87171;
                }
              }
            }

            .stat-pct {
              font-size: 11px;
              color: #999;
            }
          }
        }

        .phase-indicators {
          display: flex;
          flex-direction: column;
          gap: 8px;

          .indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;

            .indicator-label {
              width: 60px;
              color: #999;
            }

            .indicator-bar {
              flex: 1;
              height: 4px;
              background: rgba(255, 255, 255, 0.1);
              border-radius: 2px;
              overflow: hidden;

              .indicator-fill {
                height: 100%;
                transition: width 0.3s ease;

                &.aggression {
                  background: #ff6b6b;
                }
                &.dots {
                  background: #4ecdc4;
                }
                &.wickets {
                  background: #ffa726;
                }
              }
            }

            .indicator-value {
              width: 50px;
              text-align: right;
              color: #ddd;
            }
          }
        }
      }
    }

    .summary-section,
    .predictions-section {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;

      h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
      }

      .summary-grid,
      .predictions-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;

        .summary-item,
        .prediction-item {
          display: flex;
          flex-direction: column;
          gap: 4px;

          > span:first-child {
            font-size: 12px;
            color: #999;
          }

          .value {
            font-size: 16px;
            font-weight: 600;
          }

          .trend-increasing {
            color: #4ade80;
          }
          .trend-decreasing {
            color: #f87171;
          }
          .trend-stable {
            color: #fbbf24;
          }

          .very-high {
            color: #4ade80;
          }
          .high {
            color: #60a5fa;
          }
          .moderate {
            color: #fbbf24;
          }
          .low {
            color: #f87171;
          }
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .phase-timeline-widget {
    .timeline-container .phases-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>
