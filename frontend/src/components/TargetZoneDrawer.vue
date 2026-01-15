<template>
  <div class="target-zone-panel">
    <div class="panel-header">
      <h3>🎯 Target Zones</h3>
      <button @click="toggleDrawMode" :class="{ active: drawMode }" class="draw-toggle">
        {{ drawMode ? '✓ Drawing' : '+ Draw Zone' }}
      </button>
    </div>

    <!-- Zone List -->
    <div v-if="zones.length > 0" class="zone-list">
      <div
        v-for="zone in zones"
        :key="zone.id"
        :class="{ selected: selectedZoneId === zone.id }"
        class="zone-item"
        @click="selectZone(zone.id)"
      >
        <div class="zone-info">
          <span class="zone-name">{{ zone.name }}</span>
          <span v-if="zoneReports[zone.id]" class="zone-stats">
            {{ zoneReports[zone.id].hit_rate.toFixed(1) }}% hit rate
          </span>
        </div>
        <button @click.stop="deleteZone(zone.id)" class="delete-btn">×</button>
      </div>
    </div>

    <!-- Pitch SVG with zones -->
    <div class="pitch-container">
      <svg
        ref="pitchSvg"
        class="pitch-svg"
        viewBox="0 0 100 100"
        @mousedown="startDrawing"
        @mousemove="updateDrawing"
        @mouseup="finishDrawing"
      >
        <!-- Pitch background -->
        <rect x="0" y="0" width="100" height="100" fill="#0d5a2c" />

        <!-- Pitch markings -->
        <line x1="0" y1="50" x2="100" y2="50" stroke="white" stroke-width="0.3" opacity="0.3" />
        <line x1="50" y1="0" x2="50" y2="100" stroke="white" stroke-width="0.3" opacity="0.3" />
        
        <!-- Stumps -->
        <circle cx="50" cy="5" r="0.8" fill="yellow" />
        <circle cx="50" cy="95" r="0.8" fill="yellow" />

        <!-- Creases -->
        <line x1="20" y1="10" x2="80" y2="10" stroke="white" stroke-width="0.2" />
        <line x1="20" y1="90" x2="80" y2="90" stroke="white" stroke-width="0.2" />

        <!-- Pitch map points -->
        <circle
          v-for="(point, idx) in pitchPoints"
          :key="`point-${idx}`"
          :cx="point.x_coordinate"
          :cy="point.y_coordinate"
          r="1.5"
          fill="rgba(255, 255, 0, 0.7)"
          stroke="rgba(255, 200, 0, 0.9)"
          stroke-width="0.3"
        />

        <!-- Saved zones -->
        <g v-for="zone in zones" :key="`zone-${zone.id}`">
          <rect
            :x="zone.definition_json.x"
            :y="zone.definition_json.y"
            :width="zone.definition_json.width"
            :height="zone.definition_json.height"
            :fill="getZoneFill(zone.id)"
            :stroke="getZoneStroke(zone.id)"
            stroke-width="0.5"
            :opacity="selectedZoneId === zone.id ? 0.5 : 0.3"
          />
          <text
            :x="zone.definition_json.x + 2"
            :y="zone.definition_json.y + 4"
            font-size="3"
            fill="white"
            font-weight="bold"
          >
            {{ zone.name }}
          </text>
        </g>

        <!-- Drawing preview -->
        <rect
          v-if="drawMode && drawStart && currentMouse"
          :x="Math.min(drawStart.x, currentMouse.x)"
          :y="Math.min(drawStart.y, currentMouse.y)"
          :width="Math.abs(currentMouse.x - drawStart.x)"
          :height="Math.abs(currentMouse.y - drawStart.y)"
          fill="rgba(59, 130, 246, 0.3)"
          stroke="#3b82f6"
          stroke-width="0.5"
          stroke-dasharray="1,1"
        />
      </svg>
    </div>

    <!-- Zone details -->
    <div v-if="selectedZoneId && zoneReports[selectedZoneId]" class="zone-details">
      <h4>{{ getZoneName(selectedZoneId) }} Accuracy</h4>
      <div class="stats-grid">
        <div class="stat">
          <span class="stat-label">Hit Rate</span>
          <span class="stat-value">{{ zoneReports[selectedZoneId].hit_rate.toFixed(1) }}%</span>
        </div>
        <div class="stat">
          <span class="stat-label">Hits</span>
          <span class="stat-value">{{ zoneReports[selectedZoneId].hits }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Misses</span>
          <span class="stat-value">{{ zoneReports[selectedZoneId].misses }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Total</span>
          <span class="stat-value">{{ zoneReports[selectedZoneId].total_deliveries }}</span>
        </div>
      </div>
      
      <div v-if="zoneReports[selectedZoneId].misses > 0" class="miss-breakdown">
        <h5>Miss Distribution</h5>
        <ul>
          <li v-for="(count, direction) in zoneReports[selectedZoneId].miss_breakdown" :key="direction">
            {{ direction }}: {{ count }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Create zone dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click="cancelCreate">
      <div class="dialog" @click.stop>
        <h3>Name Your Target Zone</h3>
        <input
          v-model="newZoneName"
          type="text"
          placeholder="e.g., Yorker Line, Off Stump Channel"
          class="zone-name-input"
          @keyup.enter="saveNewZone"
        />
        <div class="dialog-actions">
          <button @click="cancelCreate" class="btn-secondary">Cancel</button>
          <button @click="saveNewZone" :disabled="!newZoneName.trim()" class="btn-primary">
            Create Zone
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface PitchPoint {
  x_coordinate: number
  y_coordinate: number
  value: number
}

interface TargetZone {
  id: string
  name: string
  shape: string
  definition_json: {
    x: number
    y: number
    width: number
    height: number
  }
}

interface ZoneReport {
  hit_rate: number
  hits: number
  misses: number
  total_deliveries: number
  miss_breakdown: Record<string, number>
}

const props = defineProps<{
  sessionId: string
}>()

const pitchPoints = ref<PitchPoint[]>([])
const zones = ref<TargetZone[]>([])
const zoneReports = ref<Record<string, ZoneReport>>({})
const selectedZoneId = ref<string | null>(null)

const drawMode = ref(false)
const drawStart = ref<{ x: number; y: number } | null>(null)
const currentMouse = ref<{ x: number; y: number } | null>(null)
const showCreateDialog = ref(false)
const newZoneName = ref('')
const pendingZone = ref<{ x: number; y: number; width: number; height: number } | null>(null)

const pitchSvg = ref<SVGSVGElement | null>(null)

function toggleDrawMode() {
  drawMode.value = !drawMode.value
  if (!drawMode.value) {
    drawStart.value = null
    currentMouse.value = null
  }
}

function getSVGCoordinates(event: MouseEvent): { x: number; y: number } | null {
  if (!pitchSvg.value) return null
  
  const svg = pitchSvg.value
  const rect = svg.getBoundingClientRect()
  
  // Convert mouse position to SVG coordinates (0-100 scale)
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100
  
  return { x, y }
}

function startDrawing(event: MouseEvent) {
  if (!drawMode.value) return
  
  const coords = getSVGCoordinates(event)
  if (coords) {
    drawStart.value = coords
    currentMouse.value = coords
  }
}

function updateDrawing(event: MouseEvent) {
  if (!drawMode.value || !drawStart.value) return
  
  const coords = getSVGCoordinates(event)
  if (coords) {
    currentMouse.value = coords
  }
}

function finishDrawing(event: MouseEvent) {
  if (!drawMode.value || !drawStart.value) return
  
  const coords = getSVGCoordinates(event)
  if (!coords) return
  
  const x = Math.min(drawStart.value.x, coords.x)
  const y = Math.min(drawStart.value.y, coords.y)
  const width = Math.abs(coords.x - drawStart.value.x)
  const height = Math.abs(coords.y - drawStart.value.y)
  
  // Minimum zone size
  if (width < 5 || height < 5) {
    drawStart.value = null
    currentMouse.value = null
    return
  }
  
  pendingZone.value = { x, y, width, height }
  showCreateDialog.value = true
  drawMode.value = false
  drawStart.value = null
  currentMouse.value = null
}

async function saveNewZone() {
  if (!newZoneName.value.trim() || !pendingZone.value) return
  
  try {
    const response = await fetch('/api/coaches/plus/target-zones', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: props.sessionId,
        name: newZoneName.value.trim(),
        shape: 'rect',
        definition_json: pendingZone.value
      })
    })
    
    if (!response.ok) {
      throw new Error('Failed to create zone')
    }
    
    const zone = await response.json()
    zones.value.push(zone)
    
    // Load report for new zone
    await loadZoneReport(zone.id)
    
    showCreateDialog.value = false
    newZoneName.value = ''
    pendingZone.value = null
  } catch (err) {
    console.error('Failed to create zone:', err)
  }
}

function cancelCreate() {
  showCreateDialog.value = false
  newZoneName.value = ''
  pendingZone.value = null
}

function selectZone(zoneId: string) {
  selectedZoneId.value = selectedZoneId.value === zoneId ? null : zoneId
}

async function deleteZone(zoneId: string) {
  if (!confirm('Delete this target zone?')) return
  
  // TODO: Implement delete endpoint
  zones.value = zones.value.filter(z => z.id !== zoneId)
  delete zoneReports.value[zoneId]
  
  if (selectedZoneId.value === zoneId) {
    selectedZoneId.value = null
  }
}

function getZoneName(zoneId: string): string {
  return zones.value.find(z => z.id === zoneId)?.name || 'Unknown Zone'
}

function getZoneFill(zoneId: string): string {
  return selectedZoneId.value === zoneId ? '#3b82f6' : '#10b981'
}

function getZoneStroke(zoneId: string): string {
  return selectedZoneId.value === zoneId ? '#2563eb' : '#059669'
}

async function loadPitchMap() {
  try {
    const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/pitch-map`)
    const data = await response.json()
    pitchPoints.value = data.points || []
  } catch (err) {
    console.error('Failed to load pitch map:', err)
  }
}

async function loadZones() {
  try {
    const response = await fetch(`/api/coaches/plus/target-zones?session_id=${props.sessionId}`)
    const data = await response.json()
    zones.value = data || []
    
    // Load reports for all zones
    for (const zone of zones.value) {
      await loadZoneReport(zone.id)
    }
  } catch (err) {
    console.error('Failed to load zones:', err)
  }
}

async function loadZoneReport(zoneId: string) {
  try {
    const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/zone-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        zone_id: zoneId,
        tolerance: 2.0
      })
    })
    
    const report = await response.json()
    zoneReports.value[zoneId] = report
  } catch (err) {
    console.error('Failed to load zone report:', err)
  }
}

onMounted(() => {
  loadPitchMap()
  loadZones()
})
</script>

<style scoped>
.target-zone-panel {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.draw-toggle {
  padding: 8px 16px;
  background: white;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.draw-toggle:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.draw-toggle.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.zone-list {
  margin-bottom: 16px;
  max-height: 200px;
  overflow-y: auto;
}

.zone-item {
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.zone-item:hover {
  background: #f3f4f6;
}

.zone-item.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.zone-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zone-name {
  font-weight: 500;
  color: #1f2937;
}

.zone-stats {
  font-size: 12px;
  color: #6b7280;
}

.delete-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: white;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.delete-btn:hover {
  background: #dc2626;
}

.pitch-container {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.pitch-svg {
  width: 100%;
  height: auto;
  display: block;
  cursor: crosshair;
}

.zone-details {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
}

.zone-details h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1f2937;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.miss-breakdown h5 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937;
}

.miss-breakdown ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.miss-breakdown li {
  padding: 4px 0;
  font-size: 13px;
  color: #6b7280;
  text-transform: capitalize;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}

.dialog h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f2937;
}

.zone-name-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 16px;
}

.zone-name-input:focus {
  outline: none;
  border-color: #3b82f6;
  ring: 2px;
  ring-color: rgba(59, 130, 246, 0.2);
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 8px 16px;
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

.btn-secondary:hover {
  background: #f9fafb;
}
</style>
