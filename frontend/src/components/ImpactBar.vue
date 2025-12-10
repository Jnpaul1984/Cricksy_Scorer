<script setup lang="ts">
import { computed } from "vue"

type Size = "sm" | "md" | "lg"
type VariantOverride = "neutral" | "good" | "bad" | "warn"

interface Props {
  value: number
  min?: number
  max?: number
  size?: Size
  showLabel?: boolean
  label?: string | null
  invert?: boolean
  positiveLabel?: string | null
  negativeLabel?: string | null
  variant?: VariantOverride | null
}

const props = withDefaults(defineProps<Props>(), {
  min: -100,
  max: 100,
  size: "md",
  showLabel: true,
  label: null,
  invert: false,
  positiveLabel: null,
  negativeLabel: null,
  variant: null,
})

const clamped = computed(() => Math.min(Math.max(props.value, props.min), props.max))

const effectiveValue = computed(() => (props.invert ? -clamped.value : clamped.value))

const isPositive = computed(() => effectiveValue.value > 0)
const isNegative = computed(() => effectiveValue.value < 0)

// Variant can be explicitly set or auto-detected from value
const computedVariant = computed<"positive" | "negative" | "neutral" | "good" | "bad" | "warn">(() => {
  // If explicit variant is provided, use it
  if (props.variant) return props.variant

  // Auto-detect from value
  if (effectiveValue.value > 0) return "positive"
  if (effectiveValue.value < 0) return "negative"
  return "neutral"
})

// Width as percentage of half-track (50% = full half)
const computedWidth = computed(() => {
  const halfRange = (props.max - props.min) / 2
  if (halfRange === 0) return "0%"
  const widthPct = Math.min(Math.abs(clamped.value) / halfRange, 1) * 50
  return `${widthPct}%`
})

const fillStyle = computed(() => {
  if (isPositive.value) {
    // Positive: fill grows from center (50%) to the right
    return { left: "50%", width: computedWidth.value }
  } else if (isNegative.value) {
    // Negative: fill grows from center (50%) to the left
    return { right: "50%", width: computedWidth.value }
  }
  return { left: "50%", width: "0%" }
})

const formattedValue = computed(() => {
  if (props.label !== null) return props.label

  const val = clamped.value
  const absVal = Math.abs(val)

  // Format with 1 decimal for small ranges, otherwise integer
  const range = props.max - props.min
  const formatted = range <= 20 ? absVal.toFixed(1) : Math.round(absVal).toString()

  if (val > 0) return `+${formatted}`
  if (val < 0) return `−${formatted}`
  return formatted
})

const sideLabel = computed(() => {
  if (effectiveValue.value > 0 && props.positiveLabel) {
    return props.positiveLabel
  }
  if (effectiveValue.value < 0 && props.negativeLabel) {
    return props.negativeLabel
  }
  return null
})
</script>

<template>
  <div class="impact-bar" :data-size="size">
    <div class="impact-bar__track">
      <div class="impact-bar__zero-marker" />
      <div
        class="impact-bar__fill"
        :class="['impact-bar__fill--' + computedVariant]"
        :style="fillStyle"
      />
    </div>

    <div v-if="showLabel" class="impact-bar__labels">
      <span class="impact-bar__value">{{ formattedValue }}</span>
      <span v-if="sideLabel" class="impact-bar__side-label">
        {{ sideLabel }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.impact-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-xs);
}

.impact-bar__track {
  position: relative;
  height: 0.6rem;
  border-radius: var(--radius-full);
  background: var(--color-surface-alt);
  overflow: hidden;
}

.impact-bar__zero-marker {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--color-border-subtle);
  opacity: 0.7;
}

.impact-bar__fill {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  transition:
    width 160ms ease-out,
    background-color 160ms ease-out;
}

.impact-bar__fill--positive {
  background: color-mix(in srgb, var(--color-success) 60%, transparent 40%);
}

.impact-bar__fill--negative {
  background: color-mix(in srgb, var(--color-danger) 60%, transparent 40%);
}

.impact-bar__fill--neutral {
  background: var(--color-surface-alt);
}

/* Explicit variant overrides */
.impact-bar__fill--good {
  background: color-mix(in srgb, var(--color-success) 70%, transparent 30%);
}

.impact-bar__fill--bad {
  background: color-mix(in srgb, var(--color-danger) 70%, transparent 30%);
}

.impact-bar__fill--warn {
  background: color-mix(in srgb, var(--color-warning) 70%, transparent 30%);
}

.impact-bar__labels {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
}

.impact-bar__value {
  font-weight: var(--font-semibold);
}

.impact-bar__side-label {
  color: var(--color-text-muted);
}

[data-size="sm"] .impact-bar__track {
  height: 0.4rem;
}

[data-size="lg"] .impact-bar__track {
  height: 0.8rem;
}
</style>
