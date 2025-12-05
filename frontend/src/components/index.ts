/**
 * Base UI Components
 * Re-exports for convenient importing across the app.
 *
 * Usage:
 *   import { BaseButton, BaseCard, BaseBadge, BaseInput } from '@/components'
 */

export { default as BaseButton } from './BaseButton.vue'
export { default as BaseCard } from './BaseCard.vue'
export { default as BaseBadge } from './BaseBadge.vue'
export { default as BaseInput } from './BaseInput.vue'

// Data visualization primitives
export { default as ImpactBar } from './ImpactBar.vue'
export { default as MiniSparkline } from './MiniSparkline.vue'

// AI components
export { default as AiCalloutsPanel } from './AiCalloutsPanel.vue'
export type { CalloutSeverity, AiCallout } from './AiCalloutsPanel.vue'

// Re-export types for consumers
export type { ButtonVariant, ButtonSize, ButtonType } from './BaseButton.vue'
export type { CardPadding } from './BaseCard.vue'
export type { BadgeVariant } from './BaseBadge.vue'
