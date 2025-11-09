<template>
  <dialog v-if="open" class="modal">
    <h3>Select next batter</h3>
    <select v-model="selectedId">
      <option disabled value="">Choose batter</option>
      <option v-for="p in candidateBatters" :key="p.id" :value="p.id">{{ p.name }}</option>
    </select>
    <footer class="actions">
      <button @click="$emit('close')">Cancel</button>
      <button :disabled="!selectedId || busy" @click="submit">Confirm</button>
    </footer>
  </dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

import type { Player } from '@/types';

const props = defineProps<{
  open: boolean;
  busy?: boolean;
  remainingBatters: Player[]; // supply from view (filter: not out & not used)
}>();
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm', id: string): void;
}>();

const selectedId = ref<string>('');
const candidateBatters = computed(() => props.remainingBatters);
function submit() {
  if (!selectedId.value) return;
  emit('confirm', selectedId.value);
}
</script>

<style scoped>
.modal { /* minimal styling */ }
.actions { display: flex; gap: .5rem; justify-content: flex-end; }
</style>
