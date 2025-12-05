<template>
  <span :class="badgeClasses" v-bind="$attrs">
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type BadgeVariant = 'neutral' | 'primary' | 'success' | 'warning' | 'danger'

interface Props {
  variant?: BadgeVariant
  uppercase?: boolean
  pill?: boolean
  condensed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'neutral',
  uppercase: true,
  pill: true,
  condensed: false,
})

const badgeClasses = computed(() => {
  const classes: string[] = ['ds-badge', `ds-badge--${props.variant}`]

  if (!props.uppercase) {
    classes.push('ds-badge--lowercase')
  }

  if (!props.pill) {
    classes.push('ds-badge--square')
  }

  if (props.condensed) {
    classes.push('ds-badge--condensed')
  }

  return classes
})
</script>
