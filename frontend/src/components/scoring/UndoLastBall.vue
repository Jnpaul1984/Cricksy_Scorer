<script setup lang="ts">
const props = defineProps<{
  gameId: string
  disabled?: boolean
}>()

function undo() {
  // TODO: Implement when backend API exists
  // await apiService.undoLastDelivery(props.gameId)
  alert(`Undo last delivery for game ${props.gameId} is not available yet. Backend endpoint pending.`)
}
</script>

<template>
  <button class="undo" :disabled="disabled" title="Backend endpoint pending" @click="undo">
    ↩️ Undo Last Ball
  </button>
</template>

<style scoped>
.undo{width:100%;padding:.9rem;border:none;border-radius:10px;color:#fff;font-weight:600;cursor:not-allowed;background:linear-gradient(135deg,#6c757d 0%,#5a6268 100%)}
.undo:not(:disabled){cursor:pointer}
</style>
