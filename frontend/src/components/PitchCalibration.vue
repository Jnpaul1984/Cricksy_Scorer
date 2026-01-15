<template>
  <div class="pitch-calibration">
    <div class="calibration-header">
      <h2>Pitch Calibration</h2>
      <p>Click the 4 corners of the pitch in order: Top-Left, Top-Right, Bottom-Left, Bottom-Right</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading calibration frame...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadFrame" class="retry-btn">Retry</button>
    </div>

    <div v-else class="calibration-content">
      <div class="image-container">
        <img
          v-if="frameUrl"
          ref="frameImage"
          :src="frameUrl"
          @click="handleImageClick"
          @load="onImageLoad"
          alt="Calibration frame"
          class="calibration-frame"
        />
        <svg
          v-if="imageLoaded"
          class="overlay-svg"
          :viewBox="`0 0 ${imageWidth} ${imageHeight}`"
          @click="handleImageClick"
        >
          <!-- Draw selected corners -->
          <circle
            v-for="(corner, index) in corners"
            :key="index"
            :cx="corner.x"
            :cy="corner.y"
            r="8"
            :fill="getCornerColor(index)"
            stroke="white"
            stroke-width="2"
          />
          <!-- Draw lines connecting corners -->
          <polyline
            v-if="corners.length >= 2"
            :points="getPolylinePoints()"
            fill="none"
            stroke="cyan"
            stroke-width="2"
            stroke-dasharray="5,5"
          />
          <!-- Labels -->
          <text
            v-for="(corner, index) in corners"
            :key="`label-${index}`"
            :x="corner.x + 15"
            :y="corner.y - 10"
            fill="white"
            font-size="14"
            font-weight="bold"
            stroke="black"
            stroke-width="0.5"
          >
            {{ getCornerLabel(index) }}
          </text>
        </svg>
      </div>

      <div class="corner-list">
        <h3>Selected Corners ({{ corners.length }}/4)</h3>
        <ul>
          <li v-for="(corner, index) in corners" :key="index" :class="{ active: index === corners.length - 1 }">
            <span class="corner-number" :style="{ backgroundColor: getCornerColor(index) }">{{ index + 1 }}</span>
            {{ getCornerLabel(index) }}: ({{ Math.round(corner.x) }}, {{ Math.round(corner.y) }})
            <button @click="removeCorner(index)" class="remove-btn">×</button>
          </li>
        </ul>
      </div>

      <div class="actions">
        <button @click="resetCorners" :disabled="corners.length === 0" class="btn-secondary">
          Reset
        </button>
        <button @click="saveCalibration" :disabled="corners.length !== 4 || saving" class="btn-primary">
          {{ saving ? 'Saving...' : 'Save Calibration' }}
        </button>
      </div>

      <div v-if="saveSuccess" class="success-message">
        ✅ Calibration saved successfully!
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

interface Corner {
  x: number
  y: number
}

const route = useRoute()
const sessionId = computed(() => route.params.sessionId as string)

const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)
const saveSuccess = ref(false)

const frameUrl = ref<string | null>(null)
const frameImage = ref<HTMLImageElement | null>(null)
const imageLoaded = ref(false)
const imageWidth = ref(0)
const imageHeight = ref(0)

const corners = ref<Corner[]>([])

const cornerLabels = ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right']
const cornerColors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24']

async function loadFrame() {
  loading.value = true
  error.value = null

  try {
    const response = await fetch(`/api/coaches/plus/sessions/${sessionId.value}/calibration-frame`)
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to load calibration frame')
    }

    if (!data.frame_url) {
      throw new Error(data.message || 'Calibration frame not available')
    }

    frameUrl.value = data.frame_url
  } catch (err: any) {
    error.value = err.message || 'Failed to load calibration frame'
  } finally {
    loading.value = false
  }
}

function onImageLoad(event: Event) {
  const img = event.target as HTMLImageElement
  imageWidth.value = img.naturalWidth
  imageHeight.value = img.naturalHeight
  imageLoaded.value = true
}

function handleImageClick(event: MouseEvent) {
  if (corners.value.length >= 4) {
    return
  }

  const img = frameImage.value
  if (!img) return

  const rect = img.getBoundingClientRect()
  const scaleX = imageWidth.value / rect.width
  const scaleY = imageHeight.value / rect.height

  const x = (event.clientX - rect.left) * scaleX
  const y = (event.clientY - rect.top) * scaleY

  corners.value.push({ x, y })
}

function removeCorner(index: number) {
  corners.value.splice(index, 1)
}

function resetCorners() {
  corners.value = []
  saveSuccess.value = false
}

function getCornerLabel(index: number): string {
  return cornerLabels[index] || `Corner ${index + 1}`
}

function getCornerColor(index: number): string {
  return cornerColors[index] || '#888'
}

function getPolylinePoints(): string {
  if (corners.value.length < 2) return ''

  const points = corners.value.map(c => `${c.x},${c.y}`).join(' ')

  // Close the polygon if we have all 4 corners
  if (corners.value.length === 4) {
    return points + ` ${corners.value[0].x},${corners.value[0].y}`
  }

  return points
}

async function saveCalibration() {
  if (corners.value.length !== 4) {
    error.value = 'Please select exactly 4 corners'
    return
  }

  saving.value = true
  error.value = null
  saveSuccess.value = false

  try {
    const response = await fetch(`/api/coaches/plus/sessions/${sessionId.value}/pitch-calibration`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        corners: corners.value.map(c => ({ x: c.x, y: c.y }))
      })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to save calibration')
    }

    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (err: any) {
    error.value = err.message || 'Failed to save calibration'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadFrame()
})
</script>

<style scoped>
.pitch-calibration {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.calibration-header {
  margin-bottom: 24px;
}

.calibration-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937;
}

.calibration-header p {
  color: #6b7280;
  font-size: 14px;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 48px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p {
  color: #dc2626;
  margin-bottom: 16px;
}

.retry-btn {
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: #2563eb;
}

.calibration-content {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
}

.image-container {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.calibration-frame {
  width: 100%;
  height: auto;
  display: block;
  cursor: crosshair;
}

.overlay-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.corner-list {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
}

.corner-list h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1f2937;
}

.corner-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.corner-list li {
  padding: 8px;
  margin-bottom: 8px;
  background: white;
  border-radius: 6px;
  border: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.corner-list li.active {
  border-color: #3b82f6;
}

.corner-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 12px;
  flex-shrink: 0;
}

.remove-btn {
  margin-left: auto;
  width: 24px;
  height: 24px;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  flex-shrink: 0;
}

.remove-btn:hover {
  background: #dc2626;
}

.actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.success-message {
  grid-column: 1 / -1;
  padding: 12px 16px;
  background: #d1fae5;
  color: #065f46;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
}

@media (max-width: 768px) {
  .calibration-content {
    grid-template-columns: 1fr;
  }
}
</style>
