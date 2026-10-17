<script setup lang="ts">
defineProps<{ overs: string }>();
</script>

<template>
  <section class="panel map-panel">
    <div v-if="$slots['recent-balls']" class="recent-strip"><div class="recent-label">LAST 6 <span class="active-ball-text">(Over {{ overs }})</span></div><div class="recent-balls"><slot name="recent-balls" /></div></div>
    <slot />
  </section>
</template>

<style scoped>
.map-panel{background:var(--color-surface-raised,#fff);display:flex;flex-direction:column;border-left:1px solid var(--color-border,#ccd);min-height:0}.recent-strip{height:40px;padding:0 12px;gap:12px;border-bottom:1px solid var(--color-border,#ccd);display:flex;align-items:center}.recent-label{font-size:11px;font-weight:800;color:var(--color-text,#334155)}.active-ball-text{font-weight:400}.recent-balls{display:flex;align-items:center;gap:5px}.recent-balls :slotted(.ball-badge){width:24px;height:24px;border-radius:50%;display:grid;place-items:center;border:1px dashed #9aa;color:#64748b;font-size:12px}@media(max-width:768px){.map-panel{border-left:0;border-top:1px solid var(--color-border,#ccd)}}
</style>
