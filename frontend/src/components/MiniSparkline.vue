<script setup lang="ts">
import { computed } from "vue"

type Variant = "default" | "positive" | "negative" | "neutral"

interface Props {
  points: number[]
  width?: number
  height?: number
  strokeWidth?: number
  smooth?: boolean
  highlightLast?: boolean
  variant?: Variant
}

const props = withDefaults(defineProps<Props>(), {
  width: 120,
  height: 32,
  strokeWidth: 2,
  smooth: false,
  highlightLast: false,
  variant: "default",
})

// ViewBox constants
const VIEW_WIDTH = 100
const VIEW_HEIGHT = 30
const PADDING_X = 4
const PADDING_Y = 3

interface Point {
  x: number
  y: number
}

const normalizedPoints = computed<Point[]>(() => {
  if (props.points.length === 0) return []

  const pts = props.points
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const range = max - min

  const usableWidth = VIEW_WIDTH - 2 * PADDING_X
  const usableHeight = VIEW_HEIGHT - 2 * PADDING_Y

  return pts.map((val, index) => {
    // X coordinate: spread points evenly across width
    const x =
      pts.length === 1
        ? VIEW_WIDTH / 2
        : PADDING_X + (index / (pts.length - 1)) * usableWidth

    // Y coordinate: normalize value to height (invert because SVG y=0 is top)
    let normalizedY: number
    if (range === 0) {
      // Flat line in the middle
      normalizedY = usableHeight / 2
    } else {
      normalizedY = ((val - min) / range) * usableHeight
    }

    // Invert for SVG coordinate system and add padding
    const y = VIEW_HEIGHT - PADDING_Y - normalizedY

    return { x, y }
  })
})

const polylinePoints = computed(() => {
  return normalizedPoints.value.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")
})

const lastPoint = computed<Point | null>(() => {
  const pts = normalizedPoints.value
  return pts.length > 0 ? pts[pts.length - 1] : null
})
</script>

<template>
  <div class="mini-sparkline">
    <svg
      :width="width"
      :height="height"
      :viewBox="`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`"
      preserveAspectRatio="none"
      role="img"
      aria-hidden="true"
    >
      <!-- baseline -->
      <line x1="0" y1="28" x2="100" y2="28" class="mini-sparkline__baseline" />

      <!-- no data -->
      <line
        v-if="normalizedPoints.length === 0"
        x1="10"
        y1="15"
        x2="90"
        y2="15"
        class="mini-sparkline__nodata"
      />

      <!-- line -->
      <polyline
        v-else
        :points="polylinePoints"
        class="mini-sparkline__line"
        :data-variant="variant"
      />

      <!-- last point dot -->
      <circle
        v-if="highlightLast && lastPoint"
        :cx="lastPoint.x"
        :cy="lastPoint.y"
        r="1.6"
        class="mini-sparkline__dot"
        :data-variant="variant"
      />
    </svg>
  </div>
</template>

<style scoped>
.mini-sparkline {
  display: inline-flex;
}

.mini-sparkline__baseline {
  stroke: var(--color-border-subtle);
  stroke-width: 0.5;
}

.mini-sparkline__nodata {
  stroke: var(--color-border-subtle);
  stroke-width: 0.7;
  stroke-dasharray: 2 2;
}

.mini-sparkline__line {
  fill: none;
  stroke-width: 1.4;
}

.mini-sparkline__line[data-variant="default"] {
  stroke: var(--color-accent);
}

.mini-sparkline__line[data-variant="positive"] {
  stroke: var(--color-success);
}

.mini-sparkline__line[data-variant="negative"] {
  stroke: var(--color-danger);
}

.mini-sparkline__line[data-variant="neutral"] {
  stroke: var(--color-muted);
}

.mini-sparkline__dot {
  stroke: var(--color-surface);
  stroke-width: 0.6;
}

.mini-sparkline__dot[data-variant="default"] {
  fill: var(--color-accent);
}

.mini-sparkline__dot[data-variant="positive"] {
  fill: var(--color-success);
}

.mini-sparkline__dot[data-variant="negative"] {
  fill: var(--color-danger);
}

.mini-sparkline__dot[data-variant="neutral"] {
  fill: var(--color-muted);
}
</style>
