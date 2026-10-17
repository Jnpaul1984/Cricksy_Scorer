<script setup lang="ts">
type Tab = 'recent' | 'batting' | 'bowling' | 'events' | 'analytics' | 'extras';
defineProps<{ tabs: readonly Tab[]; activeTab: Tab }>();
const emit = defineEmits<{ (event: 'update:activeTab', value: Tab): void }>();
</script>

<template>
  <footer class="broadcast-footer"><nav class="tabs-nav" aria-label="Scorer views"><button v-for="tab in tabs" :key="tab" type="button" :class="{ active: activeTab === tab }" @click="emit('update:activeTab', tab)">{{ tab === 'events' ? 'EVENT LOG' : tab.toUpperCase() }}</button></nav><div class="tab-content"><slot /></div></footer>
</template>

<style scoped>
.broadcast-footer{background:#192735;color:#fff;border-top:1px solid #41515f;min-height:132px}.tabs-nav{display:flex;border-bottom:1px solid #41515f}.tabs-nav button{flex:1;border:0;background:transparent;color:#d8e6f0;padding:8px;cursor:pointer}.tabs-nav button.active{background:#223342;color:#fff;border-bottom:3px solid #60a5fa}.tab-content{padding:10px 12px;font-size:13px}@media(max-width:768px){.broadcast-footer{min-height:150px}}
</style>
