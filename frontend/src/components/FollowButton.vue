<template>
  <button
    class="follow-btn"
    :class="[
      `variant-${variant}`,
      `size-${size}`,
      {
        'is-following': isFollowing,
        'is-loading': isLoading,
      },
    ]"
    :disabled="isLoading"
    @click="toggleFollow"
  >
    <span v-if="isLoading" class="spinner"></span>
    <span v-else-if="isFollowing" class="icon">✓</span>
    <span v-else class="icon">+</span>
    {{ isFollowing ? 'Following' : 'Follow' }}
  </button>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  entityId: string
  entityType: 'team' | 'player' | 'tournament'
  initialFollowing?: boolean
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  initialFollowing: false,
  variant: 'primary',
  size: 'md',
})

const emit = defineEmits<{
  follow: [entityId: string]
  unfollow: [entityId: string]
}>()

const isFollowing = ref(props.initialFollowing)
const isLoading = ref(false)

async function toggleFollow() {
  isLoading.value = true

  try {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 300))

    if (isFollowing.value) {
      emit('unfollow', props.entityId)
      isFollowing.value = false
    } else {
      emit('follow', props.entityId)
      isFollowing.value = true
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.follow-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.follow-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* Sizes */
.follow-btn.size-sm {
  padding: 0.4rem 0.75rem;
  font-size: var(--text-xs);
}

.follow-btn.size-md {
  padding: 0.6rem 1rem;
  font-size: var(--text-sm);
}

.follow-btn.size-lg {
  padding: 0.8rem 1.25rem;
  font-size: var(--text-base);
}

/* Variants */
.follow-btn.variant-primary {
  background: var(--color-primary);
  color: white;
}

.follow-btn.variant-primary:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.follow-btn.variant-primary.is-following {
  background: var(--color-success);
}

.follow-btn.variant-primary.is-following:hover:not(:disabled) {
  background: #16a34a;
}

.follow-btn.variant-secondary {
  background: var(--color-bg-secondary);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.follow-btn.variant-secondary:hover:not(:disabled) {
  background: var(--color-bg);
  border-color: var(--color-primary);
}

.follow-btn.variant-secondary.is-following {
  border-color: var(--color-success);
  color: var(--color-success);
  background: rgba(34, 197, 94, 0.1);
}

.follow-btn.variant-ghost {
  background: transparent;
  color: var(--color-text);
  padding: 0.4rem 0.5rem;
}

.follow-btn.variant-ghost:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary);
}

.follow-btn.variant-ghost.is-following {
  color: var(--color-success);
}

/* Icon & Spinner */
.icon {
  display: inline-block;
  font-weight: 700;
  font-size: 1.1em;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
