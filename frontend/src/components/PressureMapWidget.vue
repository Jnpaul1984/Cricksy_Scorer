<template>
  <div class="pressure-map-widget">
    <!-- Header with summary stats -->
    <div class="pressure-header">
      <h3 class="widget-title">⚡ Pressure Map</h3>
      <div class="summary-stats" v-if="pressureData?.summary">
        <div class="stat-item">
          <span class="stat-label">Avg Pressure</span>
          <span class="stat-value" :class="getPressureClass(pressureData.summary.average_pressure)">
            {{ pressureData.summary.average_pressure.toFixed(1) }}
          </span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Peak</span>
          <span class="stat-value" :class="getPressureClass(pressureData.summary.peak_pressure)">
            {{ pressureData.summary.peak_pressure.toFixed(1) }}
          </span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Critical</span>
          <span class="stat-value critical">{{ pressureData.summary.critical_moments }}</span>
        </div>
      </div>
    </div>

    <!-- Tabs for different views -->
    <div class="view-tabs">
      <button
        :class="['tab-btn', { active: activeView === 'timeline' }]"
        @click="activeView = 'timeline'"
      >
        Timeline
      </button>
      <button
        :class="['tab-btn', { active: activeView === 'phases' }]"
        @click="activeView = 'phases'"
      >
        Phases
      </button>
      <button
        :class="['tab-btn', { active: activeView === 'moments' }]"
        @click="activeView = 'moments'"
      >
        Critical Moments
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <p>Calculating pressure map...</p>
      <div class="spinner"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!pressureData || !pressureData.pressure_points?.length" class="empty-state">
      <p>No pressure data available yet</p>
    </div>

    <!-- Timeline view: Pressure line chart -->
    <div v-else-if="activeView === 'timeline'" class="pressure-timeline">
      <div class="chart-container">
        <canvas ref="pressureChart"></canvas>
      </div>
      <div class="timeline-legend">
        <div class="legend-item low">
          <span class="legend-box"></span>
          <span>Low (0-20)</span>
        </div>
        <div class="legend-item moderate">
          <span class="legend-box"></span>
          <span>Moderate (20-40)</span>
        </div>
        <div class="legend-item building">
          <span class="legend-box"></span>
          <span>Building (40-60)</span>
        </div>
        <div class="legend-item high">
          <span class="legend-box"></span>
          <span>High (60-80)</span>
        </div>
        <div class="legend-item extreme">
          <span class="legend-box"></span>
          <span>Extreme (80-100)</span>
        </div>
      </div>
    </div>

    <!-- Phases view: Phase breakdown -->
    <div v-else-if="activeView === 'phases'" class="pressure-phases">
      <div class="phases-container">
        <!-- Powerplay phase -->
        <div class="phase-card" v-if="pressureData.phases">
          <div class="phase-header powerplay">
            <h4>⚡ Powerplay (Overs 1-6)</h4>
            <span class="phase-deliveries">{{ pressureData.phases.powerplay?.length || 0 }} balls</span>
          </div>
          <div class="phase-stats">
            <div class="phase-stat">
              <span class="label">Avg Pressure:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.powerplay_stats?.avg_pressure)">
                {{ pressureData.phases.powerplay_stats?.avg_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
            <div class="phase-stat">
              <span class="label">Peak:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.powerplay_stats?.peak_pressure)">
                {{ pressureData.phases.powerplay_stats?.peak_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Middle overs phase -->
        <div class="phase-card" v-if="pressureData.phases">
          <div class="phase-header middle">
            <h4>🏏 Middle Overs (7-15)</h4>
            <span class="phase-deliveries">{{ pressureData.phases.middle?.length || 0 }} balls</span>
          </div>
          <div class="phase-stats">
            <div class="phase-stat">
              <span class="label">Avg Pressure:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.middle_stats?.avg_pressure)">
                {{ pressureData.phases.middle_stats?.avg_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
            <div class="phase-stat">
              <span class="label">Peak:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.middle_stats?.peak_pressure)">
                {{ pressureData.phases.middle_stats?.peak_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Death overs phase -->
        <div class="phase-card" v-if="pressureData.phases">
          <div class="phase-header death">
            <h4>💥 Death Overs (16+)</h4>
            <span class="phase-deliveries">{{ pressureData.phases.death?.length || 0 }} balls</span>
          </div>
          <div class="phase-stats">
            <div class="phase-stat">
              <span class="label">Avg Pressure:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.death_stats?.avg_pressure)">
                {{ pressureData.phases.death_stats?.avg_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
            <div class="phase-stat">
              <span class="label">Peak:</span>
              <span class="value" :class="getPressureClass(pressureData.phases.death_stats?.peak_pressure)">
                {{ pressureData.phases.death_stats?.peak_pressure?.toFixed(1) || 'N/A' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Critical moments view -->
    <div v-else-if="activeView === 'moments'" class="critical-moments">
      <div v-if="pressureData.peak_moments?.length" class="moments-list">
        <div
          v-for="(moment, idx) in pressureData.peak_moments.slice(0, 8)"
          :key="idx"
          class="moment-card"
          :class="getPressureClass(moment.pressure_score)"
        >
          <div class="moment-delivery">
            <span class="delivery-num">Ball {{ moment.delivery_num }}</span>
            <span class="over-num">Over {{ moment.over_num.toFixed(1) }}</span>
          </div>
          <div class="moment-pressure">
            <div class="pressure-bar">
              <div class="pressure-fill" :style="{ width: (moment.pressure_score / 100 * 100) + '%' }"></div>
            </div>
            <span class="pressure-score">{{ moment.pressure_score.toFixed(1) }}</span>
          </div>
          <div class="moment-context">
            <div v-if="moment.cumulative_stats" class="context-item">
              <span class="label">Runs:</span>
              <span class="value">{{ moment.cumulative_stats.runs }}/{{ moment.cumulative_stats.wickets }}</span>
            </div>
            <div v-if="moment.cumulative_stats" class="context-item">
              <span class="label">SR:</span>
              <span class="value">{{ moment.cumulative_stats.strike_rate?.toFixed(1) }}%</span>
            </div>
            <div v-if="moment.rates" class="context-item">
              <span class="label">RRR:</span>
              <span class="value">{{ moment.rates.required_run_rate?.toFixed(2) }}</span>
            </div>
          </div>
          <span class="moment-level">{{ moment.pressure_level?.toUpperCase() }}</span>
        </div>
      </div>
      <div v-else class="no-moments">
        <p>No critical moments above threshold</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Chart from 'chart.js/auto'

interface PressureData {
  pressure_points: Array<{
    delivery_num: number
    over_num: number
    pressure_score: number
    pressure_level: string
    factors: Record<string, number>
    rates: {
      required_run_rate: number
      actual_run_rate: number
    }
    cumulative_stats: {
      runs: number
      wickets: number
      dot_count: number
      strike_rate: number
      balls_remaining: number
      overs_remaining: number
    }
  }>
  summary: {
    total_deliveries: number
    average_pressure: number
    peak_pressure: number
    peak_pressure_at_delivery: number
    critical_moments: number
    high_pressure_count: number
  }
  peak_moments: any[]
  phases: {
    powerplay: any[]
    middle: any[]
    death: any[]
    powerplay_stats?: Record<string, number>
    middle_stats?: Record<string, number>
    death_stats?: Record<string, number>
  }
}

interface Props {
  pressureData?: PressureData | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  pressureData: null,
  loading: false
})

const activeView = ref<'timeline' | 'phases' | 'moments'>('timeline')
const pressureChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

const getPressureClass = (score: number | undefined): string => {
  if (!score) return 'low'
  if (score < 20) return 'low'
  if (score < 40) return 'moderate'
  if (score < 60) return 'building'
  if (score < 80) return 'high'
  return 'extreme'
}

const initChart = () => {
  if (!pressureChart.value || !props.pressureData?.pressure_points) return

  // Destroy existing chart
  if (chartInstance) {
    chartInstance.destroy()
  }

  const pressureScores = props.pressureData.pressure_points.map(p => p.pressure_score)
  const deliveryLabels = props.pressureData.pressure_points.map(
    p => `Over ${p.over_num.toFixed(1)}`
  )

  // Color coding by pressure level
  const backgroundColors = pressureScores.map(score => {
    if (score < 20) return 'rgba(76, 175, 80, 0.6)'     // Green - Low
    if (score < 40) return 'rgba(255, 193, 7, 0.6)'     // Yellow - Moderate
    if (score < 60) return 'rgba(255, 152, 0, 0.6)'     // Orange - Building
    if (score < 80) return 'rgba(244, 67, 54, 0.6)'     // Red - High
    return 'rgba(156, 39, 176, 0.6)'                    // Purple - Extreme
  })

  const borderColors = pressureScores.map(score => {
    if (score < 20) return 'rgba(76, 175, 80, 1)'
    if (score < 40) return 'rgba(255, 193, 7, 1)'
    if (score < 60) return 'rgba(255, 152, 0, 1)'
    if (score < 80) return 'rgba(244, 67, 54, 1)'
    return 'rgba(156, 39, 176, 1)'
  })

  const ctx = pressureChart.value.getContext('2d')
  if (!ctx) return

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: deliveryLabels,
      datasets: [
        {
          label: 'Pressure Score',
          data: pressureScores,
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointBackgroundColor: borderColors,
          pointBorderColor: borderColors,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            font: { size: 12 }
          }
        },
        tooltip: {
          callbacks: {
            afterLabel: function(context: any) {
              const point = props.pressureData?.pressure_points[context.dataIndex]
              if (point) {
                return [
                  `Level: ${point.pressure_level.toUpperCase()}`,
                  `Runs: ${point.cumulative_stats?.runs || 0}`,
                  `RRR: ${point.rates?.required_run_rate?.toFixed(2) || 'N/A'}`
                ]
              }
              return ''
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            font: { size: 11 }
          },
          title: {
            display: true,
            text: 'Pressure Score (0-100)'
          }
        },
        x: {
          ticks: {
            font: { size: 10 },
            maxRotation: 45,
            minRotation: 0
          }
        }
      }
    }
  })
}

onMounted(() => {
  initChart()
})

watch(() => props.pressureData, () => {
  initChart()
})
</script>

<style scoped lang="scss">
.pressure-map-widget {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;

  .pressure-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 15px;

    .widget-title {
      font-size: 18px;
      font-weight: bold;
      color: #333;
      margin: 0;
    }

    .summary-stats {
      display: flex;
      gap: 15px;
      flex-wrap: wrap;

      .stat-item {
        background: white;
        padding: 10px 15px;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        .stat-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 18px;
          font-weight: bold;
          padding: 4px 8px;
          border-radius: 4px;

          &.low {
            color: #4caf50;
            background: rgba(76, 175, 80, 0.1);
          }

          &.moderate {
            color: #ffc107;
            background: rgba(255, 193, 7, 0.1);
          }

          &.building {
            color: #ff9800;
            background: rgba(255, 152, 0, 0.1);
          }

          &.high {
            color: #f44336;
            background: rgba(244, 67, 54, 0.1);
          }

          &.extreme {
            color: #9c27b0;
            background: rgba(156, 39, 176, 0.1);
          }

          &.critical {
            color: #d32f2f;
            background: rgba(211, 47, 47, 0.1);
          }
        }
      }
    }
  }

  .view-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    border-bottom: 2px solid rgba(0, 0, 0, 0.1);

    .tab-btn {
      padding: 10px 16px;
      background: transparent;
      border: none;
      border-bottom: 3px solid transparent;
      color: #666;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        color: #333;
      }

      &.active {
        color: #2196f3;
        border-bottom-color: #2196f3;
      }
    }
  }

  .loading-state {
    text-align: center;
    padding: 40px;
    color: #666;

    .spinner {
      display: inline-block;
      width: 30px;
      height: 30px;
      border: 3px solid rgba(0, 0, 0, 0.1);
      border-radius: 50%;
      border-top-color: #2196f3;
      animation: spin 1s linear infinite;
    }
  }

  .empty-state,
  .no-moments {
    text-align: center;
    padding: 40px;
    color: #999;
  }

  // Timeline view
  .pressure-timeline {
    .chart-container {
      position: relative;
      height: 300px;
      margin-bottom: 20px;
      background: white;
      border-radius: 8px;
      padding: 10px;
    }

    .timeline-legend {
      display: flex;
      gap: 15px;
      flex-wrap: wrap;
      justify-content: center;
      padding-top: 15px;
      border-top: 1px solid rgba(0, 0, 0, 0.1);

      .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;

        .legend-box {
          width: 12px;
          height: 12px;
          border-radius: 2px;
        }

        &.low .legend-box {
          background: rgba(76, 175, 80, 0.6);
        }

        &.moderate .legend-box {
          background: rgba(255, 193, 7, 0.6);
        }

        &.building .legend-box {
          background: rgba(255, 152, 0, 0.6);
        }

        &.high .legend-box {
          background: rgba(244, 67, 54, 0.6);
        }

        &.extreme .legend-box {
          background: rgba(156, 39, 176, 0.6);
        }
      }
    }
  }

  // Phases view
  .pressure-phases {
    .phases-container {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 15px;

      .phase-card {
        background: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

        .phase-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          padding-bottom: 10px;
          border-bottom: 2px solid;

          h4 {
            margin: 0;
            font-size: 15px;
          }

          .phase-deliveries {
            font-size: 12px;
            color: #666;
            background: rgba(0, 0, 0, 0.05);
            padding: 4px 8px;
            border-radius: 4px;
          }

          &.powerplay {
            border-bottom-color: rgba(76, 175, 80, 0.3);
          }

          &.middle {
            border-bottom-color: rgba(255, 193, 7, 0.3);
          }

          &.death {
            border-bottom-color: rgba(244, 67, 54, 0.3);
          }
        }

        .phase-stats {
          display: flex;
          flex-direction: column;
          gap: 10px;

          .phase-stat {
            display: flex;
            justify-content: space-between;
            align-items: center;

            .label {
              font-size: 13px;
              color: #666;
            }

            .value {
              font-size: 15px;
              font-weight: bold;
              padding: 4px 8px;
              border-radius: 4px;

              &.low {
                color: #4caf50;
                background: rgba(76, 175, 80, 0.1);
              }

              &.moderate {
                color: #ffc107;
                background: rgba(255, 193, 7, 0.1);
              }

              &.building {
                color: #ff9800;
                background: rgba(255, 152, 0, 0.1);
              }

              &.high {
                color: #f44336;
                background: rgba(244, 67, 54, 0.1);
              }

              &.extreme {
                color: #9c27b0;
                background: rgba(156, 39, 176, 0.1);
              }
            }
          }
        }
      }
    }
  }

  // Critical moments view
  .critical-moments {
    .moments-list {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .moment-card {
        background: white;
        border-radius: 8px;
        padding: 14px;
        display: grid;
        grid-template-columns: 1fr 1fr 1.5fr 100px;
        gap: 15px;
        align-items: center;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

        &.low {
          border-left-color: #4caf50;
        }

        &.moderate {
          border-left-color: #ffc107;
        }

        &.building {
          border-left-color: #ff9800;
        }

        &.high {
          border-left-color: #f44336;
        }

        &.extreme {
          border-left-color: #9c27b0;
        }

        .moment-delivery {
          display: flex;
          flex-direction: column;
          gap: 2px;

          .delivery-num {
            font-weight: bold;
            font-size: 14px;
            color: #333;
          }

          .over-num {
            font-size: 12px;
            color: #999;
          }
        }

        .moment-pressure {
          display: flex;
          gap: 10px;
          align-items: center;

          .pressure-bar {
            flex: 1;
            height: 6px;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 3px;
            overflow: hidden;

            .pressure-fill {
              height: 100%;
              background: linear-gradient(90deg, #4caf50, #ffc107, #ff9800, #f44336);
              transition: width 0.3s ease;
            }
          }

          .pressure-score {
            font-weight: bold;
            font-size: 13px;
            min-width: 40px;
          }
        }

        .moment-context {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;

          .context-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;

            .label {
              color: #999;
            }

            .value {
              font-weight: bold;
              color: #333;
            }
          }
        }

        .moment-level {
          text-align: right;
          font-weight: bold;
          font-size: 11px;
          padding: 4px 8px;
          border-radius: 4px;
          color: white;

          &.low {
            background: #4caf50;
          }

          &.moderate {
            background: #ffc107;
          }

          &.building {
            background: #ff9800;
          }

          &.high {
            background: #f44336;
          }

          &.extreme {
            background: #9c27b0;
          }
        }

        @media (max-width: 768px) {
          grid-template-columns: 1fr;
          gap: 10px;

          .moment-level {
            text-align: left;
          }
        }
      }
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .pressure-map-widget {
    padding: 15px;

    .pressure-header {
      flex-direction: column;
      align-items: flex-start;

      .summary-stats {
        width: 100%;
        justify-content: space-between;
      }
    }
  }
}
</style>
