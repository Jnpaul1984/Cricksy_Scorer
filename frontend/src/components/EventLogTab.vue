<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import { storeToRefs } from 'pinia'

type EventType = 'drinks' | 'injury' | 'delay' | 'ball_change' | 'other'
type TimelineItem = {
  id: string
  type: 'delivery' | 'event'
  timestamp: string
  content: string
  metadata?: Record<string, any>
}

interface GameEvent {
  id: string
  type: EventType
  timestamp: string
  note: string
  enteredBy: string
}

// ---- Props & Emits
defineProps<{
  gameId: string
}>()

// ---- Stores
const gameStore = useGameStore()
const authStore = useAuthStore()
const { liveSnapshot } = storeToRefs(gameStore)
const { user } = storeToRefs(authStore)

// ---- Event Management
const gameEvents = ref<GameEvent[]>([])
const newEventType = ref<EventType>('other')
const newEventNote = ref<string>('')
const showAddEvent = ref<boolean>(false)

// ---- Timeline & Display
const timelineItems = computed<TimelineItem[]>(() => {
  const items: TimelineItem[] = []

  // Add deliveries from liveSnapshot
  if (liveSnapshot.value?.deliveries) {
    for (const d of liveSnapshot.value.deliveries) {
      const over = d.over_number ?? 0
      const ball = d.ball_number ?? 0
      const strikerName = getPlayerName(d.striker_id) || 'Unknown'
      const bowlerName = getPlayerName(d.bowler_id) || 'Unknown'

      let label = `${strikerName} vs ${bowlerName}: ${d.runs_scored ?? 0}${getExtraLabel(d)}`
      if (d.is_wicket) {
        const dismissedName = getPlayerName(d.dismissed_player_id) || 'Unknown'
        label += ` - WICKET! ${dismissedName}`
      }

      items.push({
        id: `delivery-${over}-${ball}`,
        type: 'delivery',
        timestamp: d.at_utc || new Date().toISOString(),
        content: label,
        metadata: { over, ball },
      })
    }
  }

  // Add non-delivery events
  for (const event of gameEvents.value) {
    items.push({
      id: `event-${event.id}`,
      type: 'event',
      timestamp: event.timestamp,
      content: formatEventContent(event),
      metadata: { eventType: event.type, enteredBy: event.enteredBy },
    })
  }

  // Sort by timestamp (newest first for log view)
  return items.sort((a, b) => {
    const aTime = new Date(a.timestamp).getTime()
    const bTime = new Date(b.timestamp).getTime()
    return bTime - aTime // Descending
  })
})

// Scroll to bottom when items change
const timelineContainer = ref<HTMLDivElement | null>(null)
watch(timelineItems, async () => {
  await nextTick()
  if (timelineContainer.value) {
    timelineContainer.value.scrollTop = timelineContainer.value.scrollHeight
  }
})

// ---- Over Summary
const lastCompletedOver = computed<{ over: number; balls: any[] } | null>(() => {
  if (!liveSnapshot.value?.deliveries || liveSnapshot.value.deliveries.length === 0) {
    return null
  }

  const deliveries = liveSnapshot.value.deliveries
  const lastDelivery = deliveries[deliveries.length - 1]
  const lastOverNum = lastDelivery?.over_number ?? 0

  // If we're in the middle of an over (ball_number > 0), show the previous completed over
  const targetOver = (lastDelivery?.ball_number ?? 0) === 0 ? lastOverNum - 1 : lastOverNum

  if (targetOver <= 0) return null

  const overBalls = deliveries.filter((d: any) => d.over_number === targetOver)
  if (overBalls.length === 0) return null

  return { over: targetOver, balls: overBalls }
})

const overSummaryText = computed<string>(() => {
  if (!lastCompletedOver.value) {
    return 'Unavailable'
  }

  const { over, balls } = lastCompletedOver.value
  const bowlerName = getPlayerName(balls[0]?.bowler_id) || 'Unknown bowler'
  const totalRuns = balls.reduce((sum: number, b: any) => sum + (b.runs_scored ?? 0), 0)
  const wickets = balls.filter((b: any) => b.is_wicket).length
  const maidens = balls.every((b: any) => (b.runs_scored ?? 0) === 0) ? 'Maiden' : ''

  return `Over ${over} (${bowlerName}): ${totalRuns} runs, ${wickets} wicket(s) ${maidens}`.trim()
})

// ---- Helpers
function getPlayerName(playerId?: string | null): string | null {
  if (!playerId) return null
  // Try from current game state batting/bowling cards
  const allPlayers = new Map<string, string>()

  if (liveSnapshot.value?.current_state?.batting_scorecard) {
    for (const [playerId, entry] of Object.entries(
      liveSnapshot.value.current_state.batting_scorecard as Record<string, any>
    )) {
      allPlayers.set(playerId, entry.player_name ?? 'Unknown')
    }
  }

  if (liveSnapshot.value?.current_state?.bowling_scorecard) {
    for (const [playerId, entry] of Object.entries(
      liveSnapshot.value.current_state.bowling_scorecard as Record<string, any>
    )) {
      allPlayers.set(playerId, entry.player_name ?? 'Unknown')
    }
  }

  return allPlayers.get(playerId) ?? null
}

function getExtraLabel(delivery: any): string {
  if (!delivery.extra_type) return ''
  const map: Record<string, string> = {
    wd: ' (Wide)',
    nb: ' (No-ball)',
    b: ' (Bye)',
    lb: ' (Leg-bye)',
  }
  return map[delivery.extra_type] ?? ''
}

function formatEventContent(event: GameEvent): string {
  const typeLabel = {
    drinks: '🥤 Drinks break',
    injury: '🏥 Injury',
    delay: '⏸️ Delay',
    ball_change: '⚪ Ball change',
    other: '📌 Event',
  }[event.type] || 'Event'

  return `${typeLabel}${event.note ? ': ' + event.note : ''}`
}

async function addEvent() {
  if (!newEventType.value) return

  const eventId = `evt-${Date.now()}`
  const now = new Date().toISOString()
  const enteredBy = user.value?.name || user.value?.email || 'Operator'

  gameEvents.value.push({
    id: eventId,
    type: newEventType.value,
    timestamp: now,
    note: newEventNote.value,
    enteredBy,
  })

  // Reset form
  newEventType.value = 'other'
  newEventNote.value = ''
  showAddEvent.value = false
}

function copyOverSummary() {
  const text = overSummaryText.value
  if (text === 'Unavailable') {
    alert('No completed overs yet')
    return
  }

  navigator.clipboard.writeText(text).then(() => {
    alert('Over summary copied!')
  })
}

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return 'Unknown time'
  }
}
</script>

<template>
  <div class="event-log-tab">
    <!-- Header with Add Event button -->
    <div class="event-log-header">
      <h3>Event Log</h3>
      <button class="btn-add-event" @click="showAddEvent = !showAddEvent">
        {{ showAddEvent ? '✕ Close' : '+ Add Event' }}
      </button>
    </div>

    <!-- Add Event Form -->
    <div v-if="showAddEvent" class="add-event-form">
      <div class="form-group">
        <label class="lbl">Event Type</label>
        <select v-model="newEventType" class="sel">
          <option value="drinks">🥤 Drinks break</option>
          <option value="injury">🏥 Injury</option>
          <option value="delay">⏸️ Delay</option>
          <option value="ball_change">⚪ Ball change</option>
          <option value="other">📌 Other</option>
        </select>
      </div>
      <div class="form-group">
        <label class="lbl">Note (optional)</label>
        <input
          v-model="newEventNote"
          type="text"
          class="inp"
          placeholder="e.g., Rain delay, player injury..."
          maxlength="200"
        />
      </div>
      <div class="form-actions">
        <button class="btn-cancel" @click="showAddEvent = false">Cancel</button>
        <button class="btn-submit" @click="addEvent" :disabled="!newEventType">
          Add Event
        </button>
      </div>
    </div>

    <!-- Over Summary Section -->
    <div class="over-summary-section">
      <h4>Last Completed Over</h4>
      <div class="summary-box">
        <p class="summary-text">{{ overSummaryText }}</p>
        <button
          v-if="overSummaryText !== 'Unavailable'"
          class="btn-copy"
          @click="copyOverSummary"
          title="Copy to clipboard"
        >
          📋 Copy
        </button>
      </div>
    </div>

    <!-- Timeline -->
    <div ref="timelineContainer" class="timeline-container">
      <div v-if="timelineItems.length === 0" class="empty-state">
        No events or deliveries yet
      </div>

      <div v-for="item in timelineItems" :key="item.id" :class="['timeline-item', item.type]">
        <div class="item-timestamp">
          {{ formatTime(item.timestamp) }}
        </div>
        <div class="item-content">
          <span class="item-text">{{ item.content }}</span>
          <span v-if="item.metadata?.enteredBy" class="item-by">
            — {{ item.metadata.enteredBy }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.event-log-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 1rem;
  padding: 1rem;
  background-color: var(--color-bg-primary, #1a1a1a);
  color: var(--color-text-primary, #ffffff);
  font-family: var(--font-family-base, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
}

.event-log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border, #333333);
}

.event-log-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary, #ffffff);
}

.btn-add-event {
  padding: 0.4rem 0.8rem;
  background-color: var(--color-accent, #0066cc);
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-add-event:hover {
  background-color: var(--color-accent-hover, #0052a3);
}

/* Add Event Form */
.add-event-form {
  padding: 1rem;
  background-color: var(--color-bg-secondary, #242424);
  border: 1px solid var(--color-border, #333333);
  border-radius: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.lbl {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-secondary, #cccccc);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sel,
.inp {
  padding: 0.5rem 0.75rem;
  background-color: var(--color-bg-primary, #1a1a1a);
  color: var(--color-text-primary, #ffffff);
  border: 1px solid var(--color-border, #333333);
  border-radius: 0.25rem;
  font-size: 0.9rem;
  font-family: inherit;
}

.sel:focus,
.inp:focus {
  outline: none;
  border-color: var(--color-accent, #0066cc);
  box-shadow: 0 0 0 2px rgba(0, 102, 204, 0.1);
}

.sel option {
  background-color: var(--color-bg-primary, #1a1a1a);
  color: var(--color-text-primary, #ffffff);
}

.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-cancel,
.btn-submit {
  flex: 1;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.btn-cancel {
  background-color: var(--color-bg-secondary, #242424);
  color: var(--color-text-primary, #ffffff);
  border: 1px solid var(--color-border, #333333);
}

.btn-cancel:hover {
  background-color: var(--color-bg-tertiary, #2d2d2d);
}

.btn-submit {
  background-color: var(--color-accent, #0066cc);
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background-color: var(--color-accent-hover, #0052a3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Over Summary */
.over-summary-section {
  padding: 0.75rem;
  background-color: var(--color-bg-secondary, #242424);
  border: 1px solid var(--color-border, #333333);
  border-radius: 0.25rem;
}

.over-summary-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-secondary, #cccccc);
}

.summary-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background-color: var(--color-bg-primary, #1a1a1a);
  border: 1px solid var(--color-border, #333333);
  border-radius: 0.25rem;
  min-height: 2.5rem;
}

.summary-text {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-primary, #ffffff);
  flex: 1;
  word-break: break-word;
}

.btn-copy {
  padding: 0.4rem 0.8rem;
  background-color: var(--color-success, #00aa00);
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.btn-copy:hover {
  background-color: var(--color-success-hover, #009900);
}

/* Timeline */
.timeline-container {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--color-border, #333333);
  border-radius: 0.25rem;
  background-color: var(--color-bg-primary, #1a1a1a);
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary, #999999);
  font-size: 0.9rem;
  min-height: 8rem;
}

.timeline-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-left: 3px solid var(--color-border, #333333);
  border-radius: 0.25rem;
  background-color: var(--color-bg-secondary, #242424);
  font-size: 0.85rem;
  transition: border-color 0.2s, background-color 0.2s;
}

.timeline-item.delivery {
  border-left-color: var(--color-accent, #0066cc);
}

.timeline-item.delivery:hover {
  background-color: var(--color-bg-tertiary, #2d2d2d);
}

.timeline-item.event {
  border-left-color: var(--color-warning, #ff9900);
}

.timeline-item.event:hover {
  background-color: var(--color-bg-tertiary, #2d2d2d);
}

.item-timestamp {
  min-width: 5rem;
  color: var(--color-text-secondary, #999999);
  font-family: var(--font-family-mono, 'Courier New', monospace);
  font-size: 0.75rem;
  line-height: 1.4;
}

.item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  color: var(--color-text-primary, #ffffff);
  word-break: break-word;
}

.item-text {
  font-weight: 500;
  color: var(--color-text-primary, #ffffff);
}

.item-by {
  font-size: 0.75rem;
  color: var(--color-text-secondary, #999999);
  font-style: italic;
}

/* Scrollbar styling */
.timeline-container::-webkit-scrollbar {
  width: 0.5rem;
}

.timeline-container::-webkit-scrollbar-track {
  background: var(--color-bg-primary, #1a1a1a);
}

.timeline-container::-webkit-scrollbar-thumb {
  background: var(--color-border, #333333);
  border-radius: 0.25rem;
}

.timeline-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-secondary, #666666);
}
</style>
