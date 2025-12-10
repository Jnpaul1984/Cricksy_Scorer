<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export interface Player {
  id: string
  name: string
}

export interface Coach {
  id: string
  name: string
}

export interface Team {
  id?: string
  name: string
  home_ground?: string
  season?: string
  coach_id?: string
  coach_name?: string
  players: Player[]
  competitions?: { id: string; name: string }[]
}

const props = defineProps<{
  visible: boolean
  team?: Team | null
  availablePlayers?: Player[]
  availableCoaches?: Coach[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  saved: [team: Team]
}>()

const isEditing = computed(() => !!props.team?.id)
const modalTitle = computed(() => isEditing.value ? 'Edit Team' : 'Create Team')

// Form state
const teamName = ref('')
const homeGround = ref('')
const season = ref('')
const selectedCoachId = ref<string | null>(null)
const selectedPlayerIds = ref<Set<string>>(new Set())
const isSubmitting = ref(false)

// Reset form when modal opens/closes or team changes
watch(
  () => [props.visible, props.team],
  () => {
    if (props.visible && props.team) {
      teamName.value = props.team.name
      homeGround.value = props.team.home_ground || ''
      season.value = props.team.season || ''
      selectedCoachId.value = props.team.coach_id || null
      selectedPlayerIds.value = new Set(props.team.players.map(p => p.id))
    } else if (props.visible && !props.team) {
      teamName.value = ''
      homeGround.value = ''
      season.value = ''
      selectedCoachId.value = null
      selectedPlayerIds.value = new Set()
    }
  },
  { immediate: true }
)

const canSubmit = computed(() => teamName.value.trim().length > 0 && !isSubmitting.value)

const selectedCoach = computed(() => {
  if (!selectedCoachId.value) return null
  return props.availableCoaches?.find(c => c.id === selectedCoachId.value) || null
})

const selectedPlayers = computed(() => {
  if (!props.availablePlayers) return []
  return props.availablePlayers.filter(p => selectedPlayerIds.value.has(p.id))
})

function togglePlayer(playerId: string) {
  const newSet = new Set(selectedPlayerIds.value)
  if (newSet.has(playerId)) {
    newSet.delete(playerId)
  } else {
    newSet.add(playerId)
  }
  selectedPlayerIds.value = newSet
}

function isPlayerSelected(playerId: string) {
  return selectedPlayerIds.value.has(playerId)
}

function close() {
  emit('update:visible', false)
}

async function submit() {
  if (!canSubmit.value) return

  isSubmitting.value = true
  try {
    const teamData: Team = {
      id: props.team?.id,
      name: teamName.value.trim(),
      home_ground: homeGround.value.trim() || undefined,
      season: season.value.trim() || undefined,
      coach_id: selectedCoachId.value || undefined,
      coach_name: selectedCoach.value?.name,
      players: selectedPlayers.value,
      competitions: props.team?.competitions || []
    }
    emit('saved', teamData)
    close()
  } finally {
    isSubmitting.value = false
  }
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    close()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="modal-backdrop"
        @click="handleBackdropClick"
      >
        <div class="modal-content">
          <header class="modal-header">
            <h3>{{ modalTitle }}</h3>
            <button aria-label="Close" class="close-btn" @click="close">×</button>
          </header>

          <form class="modal-body" @submit.prevent="submit">
            <div class="form-group">
              <label class="field-label">
                Team Name <span class="required">*</span>
              </label>
              <input
                v-model="teamName"
                type="text"
                class="ds-input"
                placeholder="e.g., Sunrisers Hyderabad"
                required
              />
            </div>

            <div class="form-group">
              <label class="field-label">
                Home Ground <span class="optional">(optional)</span>
              </label>
              <input
                v-model="homeGround"
                type="text"
                class="ds-input"
                placeholder="e.g., Rajiv Gandhi Stadium"
              />
            </div>

            <div class="form-group">
              <label class="field-label">
                Season <span class="optional">(optional)</span>
              </label>
              <input
                v-model="season"
                type="text"
                class="ds-input"
                placeholder="e.g., 2024-25"
              />
            </div>

            <div class="form-group">
              <label class="field-label">
                Coach <span class="optional">(optional)</span>
              </label>
              <select
                v-model="selectedCoachId"
                class="ds-input ds-select"
              >
                <option :value="null">-- Select Coach --</option>
                <option
                  v-for="coach in availableCoaches"
                  :key="coach.id"
                  :value="coach.id"
                >
                  {{ coach.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label class="field-label">
                Players <span class="optional">(select multiple)</span>
              </label>
              <div class="players-multiselect">
                <div
                  v-if="availablePlayers && availablePlayers.length > 0"
                  class="players-list"
                >
                  <label
                    v-for="player in availablePlayers"
                    :key="player.id"
                    class="player-checkbox"
                  >
                    <input
                      type="checkbox"
                      :checked="isPlayerSelected(player.id)"
                      @change="togglePlayer(player.id)"
                    />
                    <span class="player-name">{{ player.name }}</span>
                  </label>
                </div>
                <p v-else class="no-players-hint">
                  No players available. Add players in the Player Management section first.
                </p>
              </div>
              <p class="field-hint">{{ selectedPlayers.length }} player(s) selected</p>
            </div>
          </form>

          <footer class="modal-footer">
            <button class="ds-btn ds-btn--secondary" type="button" @click="close">
              Cancel
            </button>
            <button
              class="ds-btn ds-btn--primary"
              :disabled="!canSubmit"
              @click="submit"
            >
              {{ isSubmitting ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Team') }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--color-surface, #1a1a2e);
  border-radius: 12px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border, #333);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-text, #fff);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-muted, #888);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: var(--color-text, #fff);
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.field-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--color-text, #fff);
}

.required {
  color: var(--color-error, #f44336);
}

.optional {
  color: var(--color-text-muted, #888);
  font-weight: normal;
  font-size: 0.875rem;
}

.ds-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border, #333);
  border-radius: 8px;
  background: var(--color-background, #0f0f1a);
  color: var(--color-text, #fff);
  font-size: 1rem;
}

.ds-input:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
}

.ds-select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23888'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1rem;
  padding-right: 2.5rem;
}

.players-multiselect {
  border: 1px solid var(--color-border, #333);
  border-radius: 8px;
  background: var(--color-background, #0f0f1a);
  max-height: 200px;
  overflow-y: auto;
}

.players-list {
  padding: 0.5rem;
}

.player-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.player-checkbox:hover {
  background: var(--color-surface-hover, #252540);
}

.player-checkbox input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-primary, #4f46e5);
  cursor: pointer;
}

.player-name {
  color: var(--color-text, #fff);
  font-size: 0.875rem;
}

.no-players-hint {
  padding: 1rem;
  text-align: center;
  color: var(--color-text-muted, #888);
  font-size: 0.875rem;
  margin: 0;
}

.players-textarea {
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}

.field-hint {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-text-muted, #888);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border, #333);
}

.ds-btn {
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.ds-btn--primary {
  background: var(--color-primary, #4f46e5);
  color: #fff;
  border: none;
}

.ds-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #4338ca);
}

.ds-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ds-btn--secondary {
  background: transparent;
  color: var(--color-text, #fff);
  border: 1px solid var(--color-border, #333);
}

.ds-btn--secondary:hover {
  background: var(--color-surface-hover, #252540);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
