<template>
  <div class="loading-spinner" :class="sizeClass">
    <div class="spinner" :style="spinnerStyle">
      <div class="spinner-circle"></div>
    </div>
    <div v-if="message" class="loading-message">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// Props
interface Props {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  message?: string;
  overlay?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  color: '#3498db',
  message: '',
  overlay: false,
});

// Computed
const sizeClass = computed(() => ({
  'size-small': props.size === 'small',
  'size-medium': props.size === 'medium',
  'size-large': props.size === 'large',
  'with-overlay': props.overlay,
}));

const spinnerStyle = computed(() => ({
  '--spinner-color': props.color,
}));
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.loading-spinner.with-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  z-index: 9999;
}

.spinner {
  position: relative;
  display: inline-block;
}

.spinner-circle {
  border: 3px solid #f3f3f3;
  border-top: 3px solid var(--spinner-color, #3498db);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.size-small .spinner-circle {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

.size-medium .spinner-circle {
  width: 40px;
  height: 40px;
  border-width: 3px;
}

.size-large .spinner-circle {
  width: 60px;
  height: 60px;
  border-width: 4px;
}

.loading-message {
  color: #6c757d;
  font-size: 0.9rem;
  text-align: center;
  max-width: 200px;
}

.size-small .loading-message {
  font-size: 0.8rem;
}

.size-large .loading-message {
  font-size: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>

