<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  value?: string | null
  size?: number
}>()

const sizePx = computed(() => `${(props.size ?? 72)}px`)

const safeSrc = computed<string | null>(() => {
  const raw = props.value
  if (!raw) return null
  const trimmed = raw.trim()
  if (trimmed.startsWith('data:image/svg+xml')) {
    return trimmed
  }
  if (trimmed.startsWith('<svg')) {
    const encoded = encodeURIComponent(trimmed)
    return `data:image/svg+xml,${encoded}`
  }
  return null
})
</script>

<template>
  <div v-if="safeSrc" class="shot-map-preview">
    <img :src="safeSrc" :style="{ width: sizePx, height: sizePx }" alt="Shot map sketch" />
  </div>
</template>

<style scoped>
.shot-map-preview {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: #f9fafb;
  padding: 4px;
}

.shot-map-preview img {
  display: block;
  object-fit: contain;
}
</style>
