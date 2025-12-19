<template>
  <div class="heatmap-panel">
    <!-- Header -->
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="icon">🗺️</span> Pitch Heatmap Overlays
      </h2>
      <button
        v-if="!loading && selectedPlayer"
        @click="refreshData"
        class="refresh-btn"
        title="Refresh heatmap"
      >
        🔄
      </button>
    </div>

    <!-- Loading/Error/No Data States -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading heatmap data...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="clearError" class="retry-btn">Retry</button>
    </div>

    <div v-else-if="!selectedPlayer && !selectedBowler" class="no-data-state">
      <p>Select a player to view heatmap overlays</p>
    </div>

    <!-- Player/Bowler Selection -->
    <div v-else class="heatmap-content">
      <div class="controls">
        <select
          v-model="heatmapType"
          class="heatmap-select"
          @change="onHeatmapTypeChange"
        >
          <option value="scoring">Scoring Zones (Batting)</option>
          <option value="dismissals">Dismissal Patterns (Batting)</option>
          <option value="release">Release Zones (Bowling)</option>
        </select>

        <select
          v-model="selectedPlayer"
          class="player-select"
          @change="onPlayerChange"
        >
          <option value="">Select Player</option>
          <option value="p1">Player 1</option>
          <option value="p2">Player 2</option>
          <option value="p3">Player 3</option>
        </select>

        <select
          v-if="heatmapType === 'release'"
          v-model="selectedBowler"
          class="player-select"
          @change="onBowlerChange"
        >
          <option value="">Select Bowler</option>
          <option value="b1">Bowler 1</option>
          <option value="b2">Bowler 2</option>
          <option value="b3">Bowler 3</option>
        </select>
      </div>

      <!-- Pitch Visualization -->
      <div class="pitch-container">
        <svg
          class="pitch-svg"
          viewBox="0 0 100 100"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Pitch background -->
          <rect x="0" y="0" width="100" height="100" fill="#0d5a2c" />

          <!-- Pitch lines -->
          <line x1="0" y1="50" x2="100" y2="50" stroke="white" stroke-width="0.5" />
          <line x1="35" y1="0" x2="35" y2="100" stroke="white" stroke-width="0.5" opacity="0.3" />
          <line x1="65" y1="0" x2="65" y2="100" stroke="white" stroke-width="0.5" opacity="0.3" />

          <!-- Stumps -->
          <circle cx="50" cy="5" r="1" fill="yellow" />
          <circle cx="50" cy="95" r="1" fill="yellow" />

          <!-- Crease lines -->
          <line x1="30" y1="10" x2="70" y2="10" stroke="white" stroke-width="0.3" />
          <line x1="30" y1="90" x2="70" y2="90" stroke="white" stroke-width="0.3" />

          <!-- Heatmap data points -->
          <circle
            v-for="point in heatmapData"
            :key="`${point.zone}-${point.x_coordinate}`"
            :cx="point.x_coordinate"
            :cy="point.y_coordinate"
            :r="Math.max(2, (point.count / maxCount) * 5 + 2)"
            :fill="getHeatColor(point.value)"
            :opacity="0.7 + (point.value / 100) * 0.3"
            :title="`${point.zone}: ${point.detail}`"
            class="heatmap-point"
          />
        </svg>

        <!-- Legend -->
        <div class="legend">
          <div class="legend-title">Intensity</div>
          <div class="legend-gradient">
            <div class="gradient-bar"></div>
            <div class="gradient-labels">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Statistics Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Events</div>
          <div class="stat-value">{{ totalEvents }}</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Average Intensity</div>
          <div class="stat-value">{{ averageIntensity }}</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Peak Zone</div>
          <div class="stat-value">{{ peakZone }}</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Coverage</div>
          <div class="stat-value">{{ coveragePercentage }}%</div>
        </div>
      </div>

      <!-- Heatmap Points Table -->
      <div class="points-table">
        <h3>Zone Analysis</h3>
        <table>
          <thead>
            <tr>
              <th>Zone</th>
              <th>Events</th>
              <th>Intensity</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="point in sortedPoints" :key="point.zone">
              <td class="zone-cell">
                <span class="zone-badge" :style="{ backgroundColor: getHeatColor(point.value) }"></span>
                {{ formatZoneName(point.zone) }}
              </td>
              <td>{{ point.count }}</td>
              <td>
                <div class="intensity-bar">
                  <div
                    class="intensity-fill"
                    :style="{
                      width: point.value + '%',
                      backgroundColor: getHeatColor(point.value),
                    }"
                  ></div>
                </div>
                {{ Math.round(point.value) }}
              </td>
              <td>{{ point.detail }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Matchup Analysis (if comparing batter vs bowler) -->
      <div v-if="matchupData" class="matchup-section">
        <h3>Matchup Analysis</h3>
        <div class="matchup-cards">
          <div class="matchup-card">
            <div class="card-label">Dangerous Areas</div>
            <div class="card-content">
              <span v-if="matchupData.dangerous_areas.length > 0">
                {{ matchupData.dangerous_areas.join(", ") }}
              </span>
              <span v-else class="text-muted">None identified</span>
            </div>
          </div>

          <div class="matchup-card">
            <div class="card-label">Weak Overlaps</div>
            <div class="card-content">
              <span v-if="matchupData.weak_overlap_areas.length > 0">
                {{ matchupData.weak_overlap_areas.join(", ") }}
              </span>
              <span v-else class="text-muted">None identified</span>
            </div>
          </div>

          <div class="matchup-card">
            <div class="card-label">Strategy</div>
            <div class="card-content">{{ matchupData.recommendation }}</div>
          </div>
        </div>
      </div>

      <!-- Auto-refresh Footer -->
      <div class="footer">
        <label class="refresh-toggle">
          <input
            v-model="autoRefresh"
            type="checkbox"
          />
          Auto-refresh every {{ refreshIntervalSeconds }}s
        </label>
        <span class="last-updated">{{ lastUpdated }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useHeatmaps } from "../composables/useHeatmaps";

interface HeatmapPoint {
  zone: string;
  x_coordinate: number;
  y_coordinate: number;
  value: number;
  count: number;
  detail: string;
}

interface MatchupData {
  dangerous_areas: string[];
  weak_overlap_areas: string[];
  dismissal_zones: string[];
  recommendation: string;
}

const props = withDefaults(
  defineProps<{
    playerId?: string;
    gameId?: string;
    teamSide?: "a" | "b";
    autoRefresh?: boolean;
    refreshIntervalSeconds?: number;
  }>(),
  {
    autoRefresh: true,
    refreshIntervalSeconds: 15,
  }
);

const { fetchScoresHeatmap, fetchDismissalHeatmap, fetchReleaseZones, fetchMatchup } = useHeatmaps();

// State
const selectedPlayer = ref(props.playerId || "");
const selectedBowler = ref("");
const heatmapType = ref<"scoring" | "dismissals" | "release">("scoring");
const heatmapData = ref<HeatmapPoint[]>([]);
const matchupData = ref<MatchupData | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const autoRefresh = ref(props.autoRefresh);
const refreshIntervalSeconds = ref(props.refreshIntervalSeconds);
const lastUpdated = ref("");
let refreshInterval: number | null = null;

// Computed properties
const totalEvents = computed(() => heatmapData.value.reduce((sum, p) => sum + p.count, 0));

const averageIntensity = computed(() => {
  const avg = heatmapData.value.reduce((sum, p) => sum + p.value, 0) / (heatmapData.value.length || 1);
  return Math.round(avg);
});

const maxCount = computed(() => Math.max(...heatmapData.value.map(p => p.count), 1));

const peakZone = computed(() => {
  if (heatmapData.value.length === 0) return "N/A";
  const peak = heatmapData.value.reduce((max, p) => (p.value > max.value ? p : max));
  return formatZoneName(peak.zone);
});

const coveragePercentage = computed(() => {
  const uniqueZones = new Set(heatmapData.value.map(p => p.zone)).size;
  return Math.round((uniqueZones / 11) * 100); // 11 total zones
});

const sortedPoints = computed(() => {
  return [...heatmapData.value].sort((a, b) => b.value - a.value);
});

// Methods
function getHeatColor(value: number): string {
  if (value > 80) return "#ff0000"; // Red - hottest
  if (value > 60) return "#ff7f00"; // Orange
  if (value > 40) return "#ffff00"; // Yellow
  if (value > 20) return "#00ff00"; // Green
  return "#0000ff"; // Blue - coolest
}

function formatZoneName(zone: string): string {
  return zone
    .split("_")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

async function loadHeatmapData() {
  if (!selectedPlayer.value && !selectedBowler.value) return;

  loading.value = true;
  error.value = null;

  try {
    if (heatmapType.value === "scoring") {
      const result = await fetchScoresHeatmap(selectedPlayer.value);
      if (result?.heatmap?.data_points) {
        heatmapData.value = result.heatmap.data_points;
      }
    } else if (heatmapType.value === "dismissals") {
      const result = await fetchDismissalHeatmap(selectedPlayer.value);
      if (result?.heatmap?.data_points) {
        heatmapData.value = result.heatmap.data_points;
      }
    } else if (heatmapType.value === "release" && selectedBowler.value) {
      const result = await fetchReleaseZones(selectedBowler.value);
      if (result?.heatmap?.data_points) {
        heatmapData.value = result.heatmap.data_points;
      }
    }

    // Load matchup if both players selected
    if (selectedPlayer.value && selectedBowler.value) {
      const matchup = await fetchMatchup(selectedPlayer.value, selectedBowler.value);
      if (matchup?.matchup) {
        matchupData.value = matchup.matchup;
      }
    }

    lastUpdated.value = new Date().toLocaleTimeString();
  } catch (err: any) {
    error.value = err.message || "Failed to load heatmap data";
  } finally {
    loading.value = false;
  }
}

async function refreshData() {
  await loadHeatmapData();
}

function clearError() {
  error.value = null;
}

function onPlayerChange() {
  selectedBowler.value = "";
  loadHeatmapData();
}

function onBowlerChange() {
  loadHeatmapData();
}

function onHeatmapTypeChange() {
  loadHeatmapData();
}

function startAutoRefresh() {
  if (autoRefresh.value && !refreshInterval) {
    refreshInterval = window.setInterval(() => {
      loadHeatmapData();
    }, refreshIntervalSeconds.value * 1000);
  }
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// Lifecycle
onMounted(() => {
  if (props.playerId) {
    selectedPlayer.value = props.playerId;
    loadHeatmapData();
  }
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.heatmap-panel {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #ddd;
  padding-bottom: 10px;
}

.panel-title {
  font-size: 24px;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon {
  font-size: 28px;
}

.refresh-btn {
  background: #4299e1;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background: #3182ce;
  transform: scale(1.05);
}

.loading-state,
.error-state,
.no-data-state {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #4299e1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  background: #fed7d7;
  border-left: 4px solid #fc8181;
  padding: 15px;
  border-radius: 6px;
  color: #742a2a;
}

.retry-btn {
  background: #fc8181;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 10px;
  transition: background 0.2s ease;
}

.retry-btn:hover {
  background: #f56565;
}

.heatmap-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.heatmap-select,
.player-select {
  padding: 10px 12px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  flex: 1;
  min-width: 150px;
}

.heatmap-select:focus,
.player-select:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.pitch-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pitch-svg {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
  display: block;
}

.heatmap-point {
  cursor: pointer;
  transition: all 0.2s ease;
}

.heatmap-point:hover {
  stroke: white;
  stroke-width: 0.5;
  filter: brightness(1.1);
}

.legend {
  margin-top: 20px;
}

.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 8px;
}

.legend-gradient {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.gradient-bar {
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(
    to right,
    #0000ff,
    #00ff00,
    #ffff00,
    #ff7f00,
    #ff0000
  );
}

.gradient-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #4a5568;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.stat-card {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  text-align: center;
}

.stat-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #4299e1;
}

.points-table {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.points-table h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: #2d3748;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

th {
  padding: 10px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
}

td {
  padding: 12px 10px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.zone-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zone-badge {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.intensity-bar {
  width: 100%;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.intensity-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.matchup-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.matchup-section h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: #2d3748;
}

.matchup-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.matchup-card {
  background: #f7fafc;
  border-left: 4px solid #4299e1;
  padding: 15px;
  border-radius: 6px;
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
}

.card-content {
  font-size: 14px;
  color: #2d3748;
  line-height: 1.5;
}

.text-muted {
  color: #999;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 15px;
  border-top: 1px solid #e2e8f0;
  font-size: 12px;
  color: #666;
}

.refresh-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.refresh-toggle input {
  cursor: pointer;
}

.last-updated {
  font-size: 11px;
  color: #999;
}

/* Responsive Design */
@media (max-width: 768px) {
  .heatmap-panel {
    padding: 15px;
  }

  .panel-title {
    font-size: 18px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .matchup-cards {
    grid-template-columns: 1fr;
  }

  table {
    font-size: 12px;
  }

  th,
  td {
    padding: 8px 5px;
  }
}

@media (max-width: 480px) {
  .heatmap-panel {
    padding: 10px;
  }

  .controls {
    flex-direction: column;
  }

  .heatmap-select,
  .player-select {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .footer {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}
</style>
