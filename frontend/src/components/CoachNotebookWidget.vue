<template>
  <div class="coach-notebook-widget">
    <div class="notebook-header">
      <h3 class="notebook-title">📓 Coach Notebook</h3>
      <div class="notebook-info">
        <span v-if="lastSaved" class="save-status" :class="{ saving: isSaving }">
          {{ isSaving ? '💾 Saving...' : `✓ Saved ${formatTime(lastSaved)}` }}
        </span>
      </div>
    </div>

    <div class="notebook-container">
      <textarea
        v-model="noteText"
        class="notebook-textarea"
        placeholder="Write your coaching notes here... (autosaves every 30 seconds)"
        @input="onNoteChange"
      />
    </div>

    <div class="notebook-footer">
      <div class="footer-stats">
        <span class="stat">{{ wordCount }} words</span>
        <span class="stat">{{ charCount }} characters</span>
      </div>
      <div v-if="noteHistory.length > 0" class="footer-history">
        <button class="history-btn" @click="showHistory = !showHistory">
          📅 {{ noteHistory.length }} auto-save{{ noteHistory.length !== 1 ? 's' : '' }}
        </button>
      </div>
    </div>

    <!-- Auto-save History -->
    <div v-if="showHistory && noteHistory.length > 0" class="notebook-history">
      <div class="history-header">
        <h4>Auto-Save History</h4>
        <button class="close-btn" @click="showHistory = false">✕</button>
      </div>
      <div class="history-list">
        <div v-for="(entry, idx) in noteHistory" :key="`history-${idx}`" class="history-entry">
          <div class="history-time">{{ formatFullTime(entry.timestamp) }}</div>
          <div class="history-preview">{{ truncateText(entry.content, 60) }}</div>
          <button class="restore-btn" title="Restore this version" @click="restoreVersion(entry.content)">
            ↶
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed, onMounted, onUnmounted, watch } from 'vue'

import type { PlayerProfile } from '@/types/player'

interface HistoryEntry {
  timestamp: Date
  content: string
}

const props = defineProps<{
  profile: PlayerProfile | null
}>()

const noteText = ref('')
const lastSaved = ref<Date | null>(null)
const isSaving = ref(false)
const showHistory = ref(false)
const noteHistory = ref<HistoryEntry[]>([])
let autoSaveInterval: ReturnType<typeof setInterval> | null = null
const STORAGE_KEY_PREFIX = 'coach-notebook-'
const MAX_HISTORY = 10 // Keep last 10 saves

// Load note from localStorage on mount
onMounted(() => {
  if (props.profile?.player_id) {
    const storageKey = STORAGE_KEY_PREFIX + props.profile.player_id
    const savedNote = localStorage.getItem(storageKey)
    if (savedNote) {
      try {
        const parsed = JSON.parse(savedNote)
        noteText.value = parsed.content || ''
        lastSaved.value = parsed.lastSaved ? new Date(parsed.lastSaved) : null
        noteHistory.value = (parsed.history || []).map((entry: any) => ({
          ...entry,
          timestamp: new Date(entry.timestamp),
        }))
      } catch (err) {
        console.warn('Failed to restore coach notebook:', err)
      }
    }
  }

  // Start autosave interval
  autoSaveInterval = setInterval(autoSave, 30000) // Every 30 seconds
})

// Cleanup on unmount
onUnmounted(() => {
  if (autoSaveInterval) clearInterval(autoSaveInterval)
  // Final save on unmount
  if (noteText.value || lastSaved.value) {
    autoSave()
  }
})

// Watch profile changes to reload notes
watch(
  () => props.profile?.player_id,
  () => {
    if (props.profile?.player_id) {
      const storageKey = STORAGE_KEY_PREFIX + props.profile.player_id
      const savedNote = localStorage.getItem(storageKey)
      if (savedNote) {
        try {
          const parsed = JSON.parse(savedNote)
          noteText.value = parsed.content || ''
          lastSaved.value = parsed.lastSaved ? new Date(parsed.lastSaved) : null
          noteHistory.value = (parsed.history || []).map((entry: any) => ({
            ...entry,
            timestamp: new Date(entry.timestamp),
          }))
        } catch (err) {
          console.warn('Failed to restore coach notebook:', err)
        }
      }
    }
  },
)

// Auto-save function
function autoSave() {
  if (!props.profile?.player_id) return
  if (!noteText.value && !lastSaved.value) return

  isSaving.value = true

  // Simulate network delay for realism
  setTimeout(() => {
    try {
      const storageKey = STORAGE_KEY_PREFIX + props.profile!.player_id
      const currentTime = new Date()

      // Add to history
      const historyEntry: HistoryEntry = {
        timestamp: currentTime,
        content: noteText.value,
      }
      noteHistory.value = [historyEntry, ...noteHistory.value].slice(0, MAX_HISTORY)

      // Save to localStorage
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          content: noteText.value,
          lastSaved: currentTime.toISOString(),
          playerId: props.profile!.player_id,
          history: noteHistory.value.map((entry) => ({
            timestamp: entry.timestamp.toISOString(),
            content: entry.content,
          })),
        }),
      )

      lastSaved.value = currentTime
      isSaving.value = false
    } catch (err) {
      console.error('Failed to save coach notebook:', err)
      isSaving.value = false
    }
  }, 300)
}

// Manual note change handler
function onNoteChange() {
  // Autosave will handle it on timer
}

// Restore a previous version
function restoreVersion(content: string) {
  if (confirm('Restore this version? Current notes will be overwritten.')) {
    noteText.value = content
    autoSave()
    showHistory.value = false
  }
}

// Formatting utilities
function formatTime(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return date.toLocaleDateString()
}

function formatFullTime(date: Date): string {
  return date.toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function truncateText(text: string, length: number): string {
  return text.length > length ? text.substring(0, length) + '...' : text
}

// Stats
const wordCount = computed(() => {
  return noteText.value.trim().split(/\s+/).filter((word) => word.length > 0).length
})

const charCount = computed(() => {
  return noteText.value.length
})
</script>

<style scoped>
.coach-notebook-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

/* Header */
.notebook-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.notebook-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.notebook-info {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.save-status {
  font-size: var(--text-xs);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-weight: 500;
  transition: all 0.2s ease;
}

.save-status.saving {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

/* Textarea */
.notebook-container {
  flex: 1;
  display: flex;
  min-height: 300px;
}

.notebook-textarea {
  flex: 1;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--text-sm);
  line-height: 1.6;
  resize: vertical;
  transition: border-color 0.2s ease;
}

.notebook-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.notebook-textarea::placeholder {
  color: var(--color-text-muted);
}

/* Footer */
.notebook-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.footer-stats {
  display: flex;
  gap: var(--space-6);
}

.stat {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.footer-history {
  flex-shrink: 0;
}

.history-btn {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-btn:hover {
  background: var(--color-bg-secondary);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* History Panel */
.notebook-history {
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  max-height: 400px;
  overflow-y: auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.history-header h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: var(--text-lg);
  cursor: pointer;
  padding: 0;
  transition: color 0.2s ease;
}

.close-btn:hover {
  color: var(--color-text);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.history-entry {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
}

.history-entry:hover {
  background: var(--color-bg-secondary);
  border-color: var(--color-primary);
}

.history-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 600;
  white-space: nowrap;
  min-width: 120px;
}

.history-preview {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: 1.4;
  word-break: break-word;
}

.restore-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: var(--text-base);
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
  transition: color 0.2s ease;
}

.restore-btn:hover {
  color: var(--color-primary);
}

/* Responsive */
@media (max-width: 640px) {
  .notebook-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .notebook-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .footer-stats {
    width: 100%;
  }

  .history-entry {
    flex-wrap: wrap;
  }

  .history-time {
    width: 100%;
  }
}
</style>
