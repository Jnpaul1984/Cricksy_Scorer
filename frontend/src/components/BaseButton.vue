<template>
  <button
    :type="type"
    :class="buttonClasses"
    :disabled="disabled || loading"
    :aria-label="ariaLabel"
    :aria-busy="loading"
    v-bind="$attrs"
  >
    <span v-if="loading" class="ds-btn__spinner" aria-hidden="true"></span>
    <slot v-else />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'
export type ButtonType = 'button' | 'submit' | 'reset'

interface Props {
  variant?: ButtonVariant
  size?: ButtonSize
  type?: ButtonType
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
  disabled: false,
  loading: false,
  fullWidth: false,
  ariaLabel: undefined,
})

const buttonClasses = computed(() => {
  const classes: string[] = ['ds-btn', `ds-btn--${props.variant}`]

  // Only add size modifier for non-default sizes
  if (props.size !== 'md') {
    classes.push(`ds-btn--${props.size}`)
  }

  if (props.fullWidth) {
    classes.push('ds-btn--full-width')
  }

  if (props.loading) {
    classes.push('ds-btn--loading')
  }

  return classes
})
</script>
