<template>
  <div v-if="show" class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Correct Delivery</h3>
        <button class="close-btn" @click="close">&times;</button>
      </div>

      <div class="modal-body">
        <div v-if="delivery" class="delivery-summary">
          <p><strong>Over {{ delivery.over_number }}.{{ delivery.ball_number + 1 }}</strong></p>
          <p>{{ bowlerName || delivery.bowler_id }} to {{ batterName || delivery.striker_id }}</p>
        </div>

        <form @submit.prevent="submitCorrection">
          <!-- Extra Type -->
          <div class="form-group">
            <label>Extra Type</label>
            <select v-model="form.extra">
              <option :value="null">None (legal ball)</option>
              <option value="wd">Wide</option>
              <option value="nb">No Ball</option>
              <option value="b">Bye</option>
              <option value="lb">Leg Bye</option>
            </select>
          </div>

          <!-- Runs -->
          <div class="form-group">
            <label v-if="form.extra === 'nb'">Runs off Bat</label>
            <label v-else-if="form.extra && form.extra in ['wd', 'b', 'lb']">Extra Runs</label>
            <label v-else>Runs Scored</label>
            <input
              v-model.number="runsInput"
              type="number"
              min="0"
              max="6"
              required
            />
          </div>

          <!-- Wicket -->
          <div class="form-group">
            <label>
              <input v-model="form.is_wicket" type="checkbox" />
              Wicket
            </label>
          </div>

          <div v-if="form.is_wicket" class="wicket-details">
            <div class="form-group">
              <label>Dismissal Type</label>
              <select v-model="form.dismissal_type">
                <option value="">Select...</option>
                <option value="bowled">Bowled</option>
                <option value="caught">Caught</option>
                <option value="lbw">LBW</option>
                <option value="run_out">Run Out</option>
                <option value="stumped">Stumped</option>
                <option value="hit_wicket">Hit Wicket</option>
              </select>
            </div>
          </div>

          <!-- Commentary -->
          <div class="form-group">
            <label>Commentary (optional)</label>
            <textarea v-model="form.commentary" rows="3"></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="close">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? 'Saving...' : 'Save Correction' }}
            </button>
          </div>
        </form>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

import type { DeliveryCorrectionRequest } from '@/services/api';

export interface DeliveryData {
  id: number;
  over_number: number;
  ball_number: number;
  bowler_id: string;
  striker_id: string;
  runs_off_bat?: number;
  extra_type?: string | null;
  extra_runs?: number;
  runs_scored?: number;
  is_wicket?: boolean;
  dismissal_type?: string | null;
  dismissed_player_id?: string | null;
  commentary?: string | null;
}

interface Props {
  show: boolean;
  delivery: DeliveryData | null;
  bowlerName?: string;
  batterName?: string;
}

interface Emits {
  (e: 'close'): void;
  (e: 'submit', payload: { deliveryId: number; correction: DeliveryCorrectionRequest }): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const form = ref<DeliveryCorrectionRequest>({
  runs_scored: undefined,
  runs_off_bat: undefined,
  extra: null,
  is_wicket: false,
  dismissal_type: null,
  dismissed_player_id: null,
  commentary: null,
});

const runsInput = ref<number>(0);
const submitting = ref(false);
const error = ref<string | null>(null);

// Sync runs based on extra type
const syncRuns = () => {
  if (form.value.extra === 'nb') {
    form.value.runs_off_bat = runsInput.value;
    form.value.runs_scored = undefined;
  } else if (form.value.extra === 'wd' || form.value.extra === 'b' || form.value.extra === 'lb') {
    form.value.runs_scored = runsInput.value;
    form.value.runs_off_bat = undefined;
  } else {
    // Legal ball
    form.value.runs_off_bat = runsInput.value;
    form.value.runs_scored = runsInput.value;
  }
};

watch(() => form.value.extra, syncRuns);
watch(runsInput, syncRuns);

// Pre-fill form when delivery changes
watch(() => props.delivery, (newDelivery) => {
  if (!newDelivery) return;

  const extraType = newDelivery.extra_type?.toLowerCase() || null;
  form.value.extra = (extraType === 'wd' || extraType === 'nb' || extraType === 'b' || extraType === 'lb')
    ? extraType as 'wd' | 'nb' | 'b' | 'lb'
    : null;

  if (extraType === 'nb') {
    runsInput.value = newDelivery.runs_off_bat || 0;
  } else if (extraType && extraType !== 'nb') {
    runsInput.value = newDelivery.extra_runs || 0;
  } else {
    runsInput.value = newDelivery.runs_off_bat || newDelivery.runs_scored || 0;
  }

  form.value.is_wicket = newDelivery.is_wicket || false;
  form.value.dismissal_type = newDelivery.dismissal_type || null;
  form.value.dismissed_player_id = newDelivery.dismissed_player_id || null;
  form.value.commentary = newDelivery.commentary || null;

  syncRuns();
}, { immediate: true });

// Reset wicket details if unchecked
watch(() => form.value.is_wicket, (isWicket) => {
  if (!isWicket) {
    form.value.dismissal_type = null;
    form.value.dismissed_player_id = null;
  }
});

const close = () => {
  error.value = null;
  emit('close');
};

const submitCorrection = async () => {
  if (!props.delivery) return;

  syncRuns();
  submitting.value = true;
  error.value = null;

  try {
    emit('submit', {
      deliveryId: props.delivery.id,
      correction: { ...form.value },
    });
    close();
  } catch (err: any) {
    error.value = err?.message || 'Failed to submit correction';
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: var(--color-bg, #fff);
  color: var(--color-text, #333);
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border, #ddd);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text, #333);
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  opacity: 0.7;
}

.modal-body {
  padding: 20px;
}

.delivery-summary {
  background: var(--color-bg-secondary, #f5f5f5);
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.delivery-summary p {
  margin: 4px 0;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--color-border, #ccc);
  border-radius: 4px;
  background: var(--color-bg, #fff);
  color: var(--color-text, #333);
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

.wicket-details {
  padding-left: 20px;
  border-left: 3px solid var(--color-primary, #007bff);
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background: var(--color-primary, #007bff);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark, #0056b3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-bg-secondary, #6c757d);
  color: var(--color-text, #333);
}

.btn-secondary:hover {
  opacity: 0.8;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 12px;
  border-radius: 4px;
  margin-top: 16px;
  border: 1px solid #f5c6cb;
}
</style>
