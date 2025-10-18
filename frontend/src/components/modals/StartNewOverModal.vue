<template>
  <dialog v-if="open" class="modal">
    <h3>Start new over</h3>
    <select v-model="selectedId">
      <option disabled value="">Choose bowler</option>
      <option v-for="p in bowlers" :key="p.id" :value="p.id">{{ p.name }}</option>
    </select>
    <footer class="actions">
      <button @click="$emit('close')">Cancel</button>
      <button :disabled="!selectedId || busy" @click="submit">Start Over</button>
    </footer>
  </dialog>
</template>

<script setup lang="ts">
import { ref, toRefs, withDefaults } from 'vue';

import type { Player } from '@/types';

const props = withDefaults(defineProps<{
  open: boolean;
  busy?: boolean;
  bowlers: Player[]; // supply from view/team state
}>(), {
  busy: false,
});

const { open, busy, bowlers } = toRefs(props);

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm', id: string): void;
}>();

const selectedId = ref<string>('');
function submit() {
  if (!selectedId.value) return;
  emit('confirm', selectedId.value);
}
</script>

<style scoped>
.modal {}
.actions { display: flex; gap: .5rem; justify-content: flex-end; }
</style>
