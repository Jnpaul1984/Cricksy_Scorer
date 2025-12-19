<template>
  <div class="clustering-panel">
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="icon">🎯</span> Ball Type Clustering
      </h2>
      <button v-if="!loading" @click="refreshData" class="refresh-btn">🔄</button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Analyzing delivery types...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="clearError" class="retry-btn">Retry</button>
    </div>

    <div v-else class="content">
      <div class="controls">
        <select v-model="analysisType" class="select-control" @change="refreshData">
          <option value="bowler">Bowler Clusters</option>
          <option value="batter">Batter Vulnerabilities</option>
        </select>

        <select v-model="selectedPlayer" class="select-control" @change="refreshData">
          <option value="">Select Player</option>
          <option value="b1">Bowler 1</option>
          <option value="b2">Bowler 2</option>
          <option value="p1">Player 1</option>
          <option value="p2">Player 2</option>
        </select>
      </div>

      <!-- Bowler Clusters View -->
      <div v-if="analysisType === 'bowler' && bowlerProfile" class="bowler-section">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Total Deliveries</div>
            <div class="stat-value">{{ bowlerProfile.total_deliveries }}</div>
          </div>

          <div class="stat-card">
            <div class="stat-label">Variation Score</div>
            <div class="stat-value">{{ bowlerProfile.variation_score }}%</div>
          </div>

          <div class="stat-card">
            <div class="stat-label">Accuracy</div>
            <div class="stat-value">{{ Math.round(bowlerProfile.clustering_accuracy) }}%</div>
          </div>

          <div class="stat-card">
            <div class="stat-label">Most Effective</div>
            <div class="stat-value text-sm">{{ bowlerProfile.most_effective_cluster }}</div>
          </div>
        </div>

        <h3>Primary Delivery Clusters</h3>
        <div class="clusters-grid">
          <div
            v-for="cluster in bowlerProfile.delivery_clusters"
            :key="cluster.cluster_id"
            class="cluster-card"
          >
            <div class="cluster-header">
              <div class="cluster-name">{{ cluster.cluster_name }}</div>
              <div
                class="effectiveness-badge"
                :class="getEffectivenessClass(cluster.effectiveness_percentage)"
              >
                {{ Math.round(cluster.effectiveness_percentage) }}%
              </div>
            </div>

            <div class="cluster-stats">
              <div class="stat">
                <span class="label">Samples:</span>
                <span class="value">{{ cluster.sample_count }}</span>
              </div>
              <div class="stat">
                <span class="label">Wickets:</span>
                <span class="value">{{ Math.round(cluster.success_rate) }}%</span>
              </div>
              <div class="stat">
                <span class="label">Avg Runs:</span>
                <span class="value">{{ cluster.average_runs_conceded }}</span>
              </div>
            </div>

            <p class="description">{{ cluster.description }}</p>
          </div>
        </div>
      </div>

      <!-- Batter Vulnerabilities View -->
      <div v-if="analysisType === 'batter' && batterVulnerability" class="batter-section">
        <div v-if="batterVulnerability.vulnerable_clusters.length > 0" class="vulnerability-container">
          <h3>Vulnerable To</h3>
          <div class="tags-list">
            <span
              v-for="cluster in batterVulnerability.vulnerable_clusters"
              :key="cluster"
              class="tag tag-danger"
            >
              {{ formatClusterName(cluster) }}
            </span>
          </div>
        </div>

        <div v-if="batterVulnerability.strong_against.length > 0" class="strength-container">
          <h3>Strong Against</h3>
          <div class="tags-list">
            <span
              v-for="cluster in batterVulnerability.strong_against"
              :key="cluster"
              class="tag tag-success"
            >
              {{ formatClusterName(cluster) }}
            </span>
          </div>
        </div>

        <div v-if="batterVulnerability.recommended_bowling_strategy" class="strategy-container">
          <h3>Recommended Strategy</h3>
          <div class="strategy-box">
            {{ batterVulnerability.recommended_bowling_strategy }}
          </div>
        </div>

        <div v-if="batterVulnerability.dismissal_delivery_types.length > 0" class="dismissal-container">
          <h3>Dismissal Delivery Types</h3>
          <div class="tags-list">
            <span
              v-for="dtype in batterVulnerability.dismissal_delivery_types"
              :key="dtype"
              class="tag tag-warning"
            >
              {{ formatClusterName(dtype) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="footer">
        <label class="refresh-toggle">
          <input v-model="autoRefresh" type="checkbox" />
          Auto-refresh every {{ refreshIntervalSeconds }}s
        </label>
        <span class="last-updated">{{ lastUpdated }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useBallClustering } from "../composables/useBallClustering";

interface ClusterData {
  cluster_id: string;
  cluster_name: string;
  delivery_type: string;
  description: string;
  sample_count: number;
  effectiveness_percentage: number;
  success_rate: number;
  average_runs_conceded: number;
}

interface BowlerProfile {
  total_deliveries: number;
  delivery_clusters: ClusterData[];
  primary_clusters: string[];
  variation_score: number;
  clustering_accuracy: number;
  most_effective_cluster: string;
  least_effective_cluster: string;
}

interface BatterVulnerability {
  vulnerable_clusters: string[];
  vulnerable_delivery_types: Record<string, number>;
  strong_against: string[];
  dismissal_delivery_types: string[];
  recommended_bowling_strategy: string;
}

const props = withDefaults(
  defineProps<{
    playerId?: string;
    autoRefresh?: boolean;
    refreshIntervalSeconds?: number;
  }>(),
  {
    autoRefresh: true,
    refreshIntervalSeconds: 20,
  }
);

const { fetchBowlerClusters, fetchBatterVulnerabilities } = useBallClustering();

// State
const analysisType = ref<"bowler" | "batter">("bowler");
const selectedPlayer = ref(props.playerId || "");
const bowlerProfile = ref<BowlerProfile | null>(null);
const batterVulnerability = ref<BatterVulnerability | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const autoRefresh = ref(props.autoRefresh);
const refreshIntervalSeconds = ref(props.refreshIntervalSeconds);
const lastUpdated = ref("");
let refreshInterval: number | null = null;

// Methods
function getEffectivenessClass(effectiveness: number): string {
  if (effectiveness > 70) return "high-effectiveness";
  if (effectiveness > 40) return "medium-effectiveness";
  return "low-effectiveness";
}

function formatClusterName(cluster: string): string {
  return cluster.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

async function loadData() {
  if (!selectedPlayer.value) return;

  loading.value = true;
  error.value = null;

  try {
    if (analysisType.value === "bowler") {
      const result = await fetchBowlerClusters(selectedPlayer.value);
      bowlerProfile.value = result?.profile || null;
    } else {
      const result = await fetchBatterVulnerabilities(selectedPlayer.value);
      batterVulnerability.value = result?.vulnerability || null;
    }

    lastUpdated.value = new Date().toLocaleTimeString();
  } catch (err: any) {
    error.value = err.message || "Failed to load data";
  } finally {
    loading.value = false;
  }
}

function refreshData() {
  loadData();
}

function clearError() {
  error.value = null;
}

function startAutoRefresh() {
  if (autoRefresh.value && !refreshInterval) {
    refreshInterval = window.setInterval(() => {
      loadData();
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
    loadData();
  }
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.clustering-panel {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
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
}

.loading-state,
.error-state {
  text-align: center;
  padding: 40px;
  color: #666;
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
  color: #742a2a;
  border-radius: 6px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.controls {
  display: flex;
  gap: 10px;
}

.select-control {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-size: 14px;
  background: white;
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

.stat-value.text-sm {
  font-size: 14px;
  word-break: break-word;
}

h3 {
  margin: 15px 0 10px;
  font-size: 16px;
  color: #2d3748;
}

.clusters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.cluster-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.cluster-name {
  font-weight: 600;
  color: #2d3748;
}

.effectiveness-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  color: white;
}

.high-effectiveness {
  background: #48bb78;
}

.medium-effectiveness {
  background: #ecc94b;
  color: #744210;
}

.low-effectiveness {
  background: #fc8181;
}

.cluster-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

.stat {
  display: flex;
  justify-content: space-between;
}

.stat .label {
  color: #666;
}

.stat .value {
  font-weight: 600;
  color: #2d3748;
}

.description {
  font-size: 12px;
  color: #666;
  margin: 0;
  line-height: 1.4;
}

.vulnerability-container,
.strength-container,
.strategy-container,
.dismissal-container {
  background: white;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.tag-danger {
  background: #fc8181;
}

.tag-success {
  background: #48bb78;
}

.tag-warning {
  background: #ecc94b;
  color: #744210;
}

.strategy-box {
  background: #f7fafc;
  padding: 12px;
  border-left: 4px solid #4299e1;
  border-radius: 4px;
  color: #2d3748;
  font-size: 14px;
  line-height: 1.6;
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

@media (max-width: 768px) {
  .clustering-panel {
    padding: 15px;
  }

  .clusters-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
