<template>
  <div v-if="visible" class="error-message" :class="typeClass" role="alert">
    <div class="error-icon">
      {{ errorIcon }}
    </div>
    <div class="error-content">
      <div class="error-title" v-if="title">
        {{ title }}
      </div>
      <div class="error-text">
        {{ message }}
      </div>
      <div v-if="details" class="error-details">
        {{ details }}
      </div>
    </div>
    <button 
      v-if="dismissible" 
      @click="handleDismiss"
      class="dismiss-button"
      type="button"
      aria-label="Dismiss error"
    >
      ✕
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// Props
interface Props {
  message: string;
  title?: string;
  details?: string;
  type?: 'error' | 'warning' | 'info';
  dismissible?: boolean;
  visible?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  details: '',
  type: 'error',
  dismissible: true,
  visible: true,
});

// Emits
interface Emits {
  (e: 'dismiss'): void;
}

const emit = defineEmits<Emits>();

// Computed
const typeClass = computed(() => ({
  'type-error': props.type === 'error',
  'type-warning': props.type === 'warning',
  'type-info': props.type === 'info',
}));

const errorIcon = computed(() => {
  switch (props.type) {
    case 'error':
      return '❌';
    case 'warning':
      return '⚠️';
    case 'info':
      return 'ℹ️';
    default:
      return '❌';
  }
});

// Methods
const handleDismiss = () => {
  emit('dismiss');
};
</script>

<style scoped>
.error-message {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid;
  margin-bottom: 1rem;
  animation: slideIn 0.3s ease-out;
}

.type-error {
  background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
  border-color: #fed7d7;
  color: #e53e3e;
}

.type-warning {
  background: linear-gradient(135deg, #fffbf0 0%, #ffeaa7 100%);
  border-color: #ffeaa7;
  color: #d69e2e;
}

.type-info {
  background: linear-gradient(135deg, #f0f8ff 0%, #bee3f8 100%);
  border-color: #bee3f8;
  color: #3182ce;
}

.error-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.error-content {
  flex: 1;
  min-width: 0;
}

.error-title {
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.error-text {
  font-size: 0.9rem;
  line-height: 1.4;
  margin-bottom: 0.5rem;
}

.error-details {
  font-size: 0.8rem;
  opacity: 0.8;
  font-style: italic;
  line-height: 1.3;
}

.dismiss-button {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
  opacity: 0.6;
}

.dismiss-button:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

.dismiss-button:focus {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .error-message {
    padding: 0.75rem;
    gap: 0.75rem;
  }
  
  .error-icon {
    font-size: 1rem;
  }
  
  .error-title {
    font-size: 0.9rem;
  }
  
  .error-text {
    font-size: 0.85rem;
  }
}
</style>

