<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from "vue";
import { useRealtime } from "@/composables/useRealtime";

// Allowed roles for nice typing
type Role = "SCORER" | "COMMENTATOR" | "ANALYST" | "VIEWER";

const props = defineProps<{
  gameId: string;        // required
  role?: Role;           // optional, defaults to VIEWER
  name?: string;         // optional, defaults to role name
}>();

const { connected, join, leave, getMembers } = useRealtime();

onMounted(() => {
  const role = props.role ?? "VIEWER";
  const name = props.name ?? role;
  join(props.gameId, role, name);
});

onBeforeUnmount(() => {
  leave(props.gameId);
});

// Live members in this game room
const members = computed(() => getMembers(props.gameId));
</script>

<template>
  <div class="presence-bar w-full rounded-xl border px-3 py-2 flex items-center gap-3">
    <div class="text-xs px-2 py-1 rounded bg-gray-100">
      Socket: <b>{{ connected ? "connected" : "disconnected" }}</b>
    </div>

    <div class="text-sm font-semibold">Operators:</div>

    <div class="flex flex-wrap gap-2">
      <span
        v-for="m in members"
        :key="m.sid"
        class="inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs"
      >
        <span class="w-2 h-2 rounded-full" :class="connected ? 'bg-green-500' : 'bg-gray-400'"></span>
        <span>{{ m.name }}</span>
        <span class="opacity-60">• {{ m.role }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.presence-bar {
  background: #f8fafc;
  border-color: #e5e7eb;
}
</style>
