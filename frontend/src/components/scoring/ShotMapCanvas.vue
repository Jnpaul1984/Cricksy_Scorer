<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import defaultBackgroundImage from '@/assets/shot-map-field.png'

type Point = { x: number; y: number }

const props = defineProps<{
  modelValue: string | null
  width?: number
  height?: number
  backgroundImage?: string | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const strokes = ref<Point[][]>([])
const currentStroke = ref<Point[]>([])
const isDrawing = ref(false)
const lastEmitted = ref<string | null>(null)

const canvasWidth = computed(() => props.width ?? 220)
const canvasHeight = computed(() => props.height ?? 220)

const hasHistory = computed(() => strokes.value.length > 0)
const hasActiveStroke = computed(() => hasHistory.value || currentStroke.value.length > 1)

const surfaceStyle = computed(() => ({
  width: `${canvasWidth.value}px`,
  height: `${canvasHeight.value}px`,
  backgroundImage: `url(${props.backgroundImage ?? defaultBackgroundImage})`,
  backgroundSize: 'contain',
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'center',
}))

function setupCanvas(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  canvas.width = canvasWidth.value
  canvas.height = canvasHeight.value
  canvas.style.width = `${canvasWidth.value}px`
  canvas.style.height = `${canvasHeight.value}px`
  render()
}

function pointFromEvent(event: PointerEvent): Point {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  const x = Math.min(Math.max(event.clientX - rect.left, 0), canvasWidth.value)
  const y = Math.min(Math.max(event.clientY - rect.top, 0), canvasHeight.value)
  return { x, y }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Point[]): void {
  if (stroke.length < 2) return
  ctx.beginPath()
  ctx.moveTo(stroke[0].x, stroke[0].y)
  for (let i = 1; i < stroke.length; i += 1) {
    ctx.lineTo(stroke[i].x, stroke[i].y)
  }
  ctx.stroke()
}

function render(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#f8fafc'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = 2.5
  ctx.strokeStyle = '#2563eb'

  for (const stroke of strokes.value) {
    drawStroke(ctx, stroke)
  }
  drawStroke(ctx, currentStroke.value)
}

function encodeSvg(): string | null {
  if (!strokes.value.length) {
    return null
  }
  const segments: string[] = []
  for (const stroke of strokes.value) {
    if (!stroke.length) continue
    const path = stroke
      .map((point, idx) => `${idx === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
      .join(' ')
    if (path) segments.push(path)
  }
  if (!segments.length) return null
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${canvasWidth.value} ${canvasHeight.value}" fill="none"><path d="${segments.join(
    ' '
  )}" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

function emitValue(): void {
  const encoded = encodeSvg()
  lastEmitted.value = encoded
  emit('update:modelValue', encoded)
}

function onPointerDown(event: PointerEvent): void {
  if (event.button !== 0 && event.pointerType === 'mouse') return
  event.preventDefault()
  isDrawing.value = true
  const start = pointFromEvent(event)
  currentStroke.value = [start]
  render()
}

function onPointerMove(event: PointerEvent): void {
  if (!isDrawing.value) return
  event.preventDefault()
  const next = pointFromEvent(event)
  const last = currentStroke.value[currentStroke.value.length - 1]
  if (!last || Math.hypot(next.x - last.x, next.y - last.y) < 1) return
  currentStroke.value = [...currentStroke.value, next]
  render()
}

function finishStroke(): void {
  if (!isDrawing.value) return
  isDrawing.value = false
  if (currentStroke.value.length > 1) {
    strokes.value = [...strokes.value, [...currentStroke.value]]
    emitValue()
  }
  currentStroke.value = []
  render()
}

function undo(): void {
  if (!strokes.value.length) return
  strokes.value = strokes.value.slice(0, -1)
  render()
  emitValue()
}

function clearAll(): void {
  if (!hasActiveStroke.value) return
  strokes.value = []
  currentStroke.value = []
  render()
  lastEmitted.value = null
  emit('update:modelValue', null)
}

onMounted(() => {
  setupCanvas()
})

watch([canvasWidth, canvasHeight], () => {
  setupCanvas()
})

watch(
  () => props.modelValue,
  (value) => {
    if (value === lastEmitted.value) return
    if (value == null) {
      strokes.value = []
      currentStroke.value = []
      render()
    }
  }
)
</script>

<template>
  <div class="shot-map-canvas">
    <div class="shot-map-canvas__surface-wrapper" :style="surfaceStyle">
      <canvas
        ref="canvasRef"
        class="shot-map-canvas__surface"
        :width="canvasWidth"
        :height="canvasHeight"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="finishStroke"
        @pointerleave="finishStroke"
        @pointercancel="finishStroke"
      />
    </div>
    <div class="shot-map-canvas__actions">
      <button class="btn" type="button" :disabled="!hasHistory" @click="undo">Undo</button>
      <button class="btn" type="button" :disabled="!hasActiveStroke" @click="clearAll">Clear</button>
    </div>
  </div>
</template>

<style scoped>
.shot-map-canvas {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.shot-map-canvas__surface-wrapper {
  position: relative;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 12px;
  background-color: #f8fafc;
  overflow: hidden;
}

.shot-map-canvas__surface {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
}

.shot-map-canvas__actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.6);
  background: #fff;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
