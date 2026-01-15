<template>
  <div class="goal-setter">
    <div class="modal-header">
      <h2>Set Goals for Analysis</h2>
      <button class="close-btn" @click="$emit('close')">&times;</button>
    </div>

    <div class="modal-body">
      <!-- Zone Goals Section -->
      <section class="goals-section">
        <h3>Target Zone Accuracy</h3>
        <p class="section-description">
          Set accuracy targets for pitch zones (e.g., "Land 80% of deliveries in Yorker Zone")
        </p>

        <div v-for="(zoneGoal, index) in zoneGoals" :key="index" class="goal-row">
          <select v-model="zoneGoal.zone_id" class="zone-select">
            <option value="">Select Zone...</option>
            <option v-for="zone in availableZones" :key="zone.id" :value="zone.id">
              {{ zone.name }}
            </option>
          </select>

          <div class="accuracy-input">
            <label>Target: {{ (zoneGoal.target_accuracy * 100).toFixed(0) }}%</label>
            <input
              v-model.number="zoneGoal.target_accuracy"
              type="range"
              min="0"
              max="1"
              step="0.05"
              class="accuracy-slider"
            />
          </div>

          <button class="remove-btn" title="Remove" @click="removeZoneGoal(index)">
            🗑️
          </button>
        </div>

        <button class="add-btn" @click="addZoneGoal">+ Add Zone Goal</button>
      </section>

      <!-- Metric Goals Section -->
      <section class="goals-section">
        <h3>Performance Metric Targets</h3>
        <p class="section-description">
          Set performance thresholds for technique metrics (e.g., "Head Stability ≥ 0.70")
        </p>

        <div v-for="(metricGoal, index) in metricGoals" :key="index" class="goal-row">
          <select v-model="metricGoal.code" class="metric-select">
            <option value="">Select Metric...</option>
            <option v-for="metric in availableMetrics" :key="metric.code" :value="metric.code">
              {{ metric.title }}
            </option>
          </select>

          <div class="score-input">
            <label>Target: {{ metricGoal.target_score.toFixed(2) }}</label>
            <input
              v-model.number="metricGoal.target_score"
              type="range"
              min="0"
              max="1"
              step="0.05"
              class="score-slider"
            />
          </div>

          <button class="remove-btn" title="Remove" @click="removeMetricGoal(index)">
            🗑️
          </button>
        </div>

        <button class="add-btn" @click="addMetricGoal">+ Add Metric Goal</button>
      </section>
    </div>

    <div class="modal-footer">
      <button class="cancel-btn" @click="$emit('close')">Cancel</button>
      <button class="save-btn" :disabled="!hasValidGoals || saving" @click="saveGoals">
        {{ saving ? 'Saving...' : 'Save Goals' }}
      </button>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

import { setJobGoals, type SetGoalsRequest } from '@/services/coachPlusVideoService';

interface Props {
  jobId: string;
  sessionId: string;
  existingGoals?: SetGoalsRequest;
  availableZones?: Array<{ id: string; name: string }>;
  availableMetrics?: Array<{ code: string; title: string }>;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  goalsSaved: [goals: SetGoalsRequest];
}>();

// Zone goals state
const zoneGoals = ref<Array<{ zone_id: string; target_accuracy: number }>>([]);

// Metric goals state
const metricGoals = ref<Array<{ code: string; target_score: number }>>([]);

// UI state
const saving = ref(false);
const error = ref<string | null>(null);

// Available metrics (common across all analysis modes)
const defaultMetrics = [
  { code: 'HEAD_MOVEMENT', title: 'Head Stability' },
  { code: 'FRONT_ELBOW', title: 'Front Elbow Position' },
  { code: 'BACK_ELBOW', title: 'Back Elbow Position' },
  { code: 'FRONT_KNEE', title: 'Front Knee Bend' },
  { code: 'BACK_KNEE', title: 'Back Knee Drive' },
  { code: 'SHOULDER_ROTATION', title: 'Shoulder Rotation' },
  { code: 'HIP_ROTATION', title: 'Hip Rotation' },
  { code: 'BALANCE', title: 'Balance Score' },
  { code: 'FOLLOW_THROUGH', title: 'Follow Through' },
  { code: 'STRIDE_LENGTH', title: 'Stride Length' },
];

const availableMetrics = computed(() => props.availableMetrics || defaultMetrics);

// Computed
const hasValidGoals = computed(() => {
  const validZoneGoals = zoneGoals.value.filter((zg) => zg.zone_id).length > 0;
  const validMetricGoals = metricGoals.value.filter((mg) => mg.code).length > 0;
  return validZoneGoals || validMetricGoals;
});

// Methods
function addZoneGoal() {
  zoneGoals.value.push({ zone_id: '', target_accuracy: 0.8 });
}

function removeZoneGoal(index: number) {
  zoneGoals.value.splice(index, 1);
}

function addMetricGoal() {
  metricGoals.value.push({ code: '', target_score: 0.7 });
}

function removeMetricGoal(index: number) {
  metricGoals.value.splice(index, 1);
}

async function saveGoals() {
  saving.value = true;
  error.value = null;

  try {
    // Filter out incomplete goals
    const validZoneGoals = zoneGoals.value.filter((zg) => zg.zone_id);
    const validMetricGoals = metricGoals.value.filter((mg) => mg.code);

    const goals: SetGoalsRequest = {
      zones: validZoneGoals,
      metrics: validMetricGoals,
    };

    await setJobGoals(props.jobId, goals);
    emit('goalsSaved', goals);
    emit('close');
  } catch (err: any) {
    error.value = err.message || 'Failed to save goals';
  } finally {
    saving.value = false;
  }
}

// Initialize with existing goals
onMounted(() => {
  if (props.existingGoals) {
    zoneGoals.value = [...(props.existingGoals.zones || [])];
    metricGoals.value = [...(props.existingGoals.metrics || [])];
  }

  // Add at least one empty row if no existing goals
  if (zoneGoals.value.length === 0) {
    addZoneGoal();
  }
  if (metricGoals.value.length === 0) {
    addMetricGoal();
  }
});
</script>

<style scoped>
.goal-setter {
  background: white;
  border-radius: 8px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: #7f8c8d;
  padding: 0;
  width: 32px;
  height: 32px;
  line-height: 1;
}

.close-btn:hover {
  color: #2c3e50;
}

.modal-body {
  padding: 20px;
}

.goals-section {
  margin-bottom: 30px;
}

.goals-section h3 {
  color: #34495e;
  font-size: 1.2rem;
  margin-bottom: 8px;
}

.section-description {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.goal-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.zone-select,
.metric-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
}

.accuracy-input,
.score-input {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.accuracy-input label,
.score-input label {
  font-size: 0.85rem;
  color: #555;
  font-weight: 500;
}

.accuracy-slider,
.score-slider {
  width: 100%;
  cursor: pointer;
}

.remove-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.remove-btn:hover {
  background: #c0392b;
}

.add-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
}

.add-btn:hover {
  background: #2980b9;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.cancel-btn,
.save-btn {
  padding: 10px 24px;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.cancel-btn {
  background: #95a5a6;
  color: white;
}

.cancel-btn:hover {
  background: #7f8c8d;
}

.save-btn {
  background: #27ae60;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #229954;
}

.save-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.error-message {
  margin: 12px 20px;
  padding: 12px;
  background: #fee;
  color: #c0392b;
  border-radius: 4px;
  border-left: 4px solid #e74c3c;
}
</style>
