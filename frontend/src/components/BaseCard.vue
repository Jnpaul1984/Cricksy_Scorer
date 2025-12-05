<template>
  <component
    :is="as"
    :class="cardClasses"
    :style="cardStyle"
    v-bind="$attrs"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

export type CardPadding = 'none' | 'sm' | 'md' | 'lg'

interface Props {
  as?: string | Component
  interactive?: boolean
  padding?: CardPadding
  fullHeight?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  as: 'div',
  interactive: false,
  padding: 'md',
  fullHeight: false,
})

const cardClasses = computed(() => {
  const classes: string[] = ['ds-card']

  if (props.interactive) {
    classes.push('ds-card--interactive')
  }

  return classes
})

const paddingMap: Record<CardPadding, string> = {
  none: '0',
  sm: 'var(--space-2)',
  md: 'var(--space-4)',
  lg: 'var(--space-6)',
}

const cardStyle = computed(() => {
  const styles: Record<string, string> = {}

  // Apply padding based on prop
  styles.padding = paddingMap[props.padding]

  // Apply full height if needed
  if (props.fullHeight) {
    styles.height = '100%'
  }

  return styles
})
</script>
