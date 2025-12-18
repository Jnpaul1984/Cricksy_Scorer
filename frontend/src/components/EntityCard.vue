<template>
  <div class="entity-card">
    <div class="card-header">
      <div class="entity-badge">{{ entityType }}</div>
      <FollowButton
        :entity-id="id"
        :entity-type="entityType"
        :initial-following="isFollowed"
        variant="secondary"
        size="sm"
        @follow="handleFollow"
        @unfollow="handleUnfollow"
      />
    </div>

    <div class="card-body">
      <div class="entity-icon">{{ icon }}</div>
      <h3 class="entity-name">{{ name }}</h3>
      <p class="entity-subtitle">{{ subtitle }}</p>

      <div v-if="stats" class="entity-stats">
        <div v-for="(value, label) in stats" :key="label" class="stat">
          <span class="stat-label">{{ label }}</span>
          <span class="stat-value">{{ value }}</span>
        </div>
      </div>
    </div>

    <div class="card-footer">
      <router-link :to="detailsLink" class="details-link">
        View Details →
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import FollowButton from './FollowButton.vue'
import { useFollowSystem } from '@/composables/useFollowSystem'

interface Props {
  id: string
  name: string
  entityType: 'team' | 'player' | 'tournament'
  icon: string
  subtitle: string
  detailsLink: string
  stats?: Record<string, string | number>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  followed: [id: string]
  unfollowed: [id: string]
}>()

const { isFollowed, follow, unfollow } = useFollowSystem()

const isEntityFollowed = computed(() => isFollowed(props.id))

function handleFollow() {
  follow(props.id, props.entityType, props.name)
  emit('followed', props.id)
}

function handleUnfollow() {
  unfollow(props.id)
  emit('unfollowed', props.id)
}
</script>

<style scoped>
.entity-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.entity-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.entity-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
}

.card-body {
  flex: 1;
  padding: var(--space-4) var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-3);
}

.entity-icon {
  font-size: 3rem;
}

.entity-name {
  margin: 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.entity-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.entity-stats {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
}

.card-footer {
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.details-link {
  font-size: var(--text-sm);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s ease;
}

.details-link:hover {
  color: var(--color-primary-dark);
  text-decoration: underline;
}

@media (max-width: 768px) {
  .entity-stats {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
