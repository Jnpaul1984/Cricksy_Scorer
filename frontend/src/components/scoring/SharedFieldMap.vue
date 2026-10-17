<script setup lang="ts">
const props = defineProps<{ modelValue: number | null; disabled?: boolean }>();
const emit = defineEmits<{ (event: 'update:modelValue', value: number): void }>();

const select = (zone: number) => {
  if (!props.disabled) emit('update:modelValue', zone);
};
</script>

<template>
  <div class="shared-field-map" aria-label="Shot map">
    <div class="field-oval">
      <div class="pitch-rect" />
      <div class="zone-overlay" aria-label="Tap zone to record shot">
        <button v-for="zone in [1, 2, 3, 4, 5, 6, 7, 8]" :key="zone" type="button"
          class="zone" :class="[`z${zone}`, { 'zone--selected': props.modelValue === zone }]"
          :aria-label="`Field zone ${zone}`" :aria-pressed="props.modelValue === zone" :disabled="props.disabled"
          @click="select(zone)" />
      </div>
    </div>
    <div class="map-label">TAP ZONE TO RECORD SHOT</div>
  </div>
</template>

<style scoped>
.shared-field-map { flex: 1; position: relative; width: 100%; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.field-oval { width: 80%; height: 80%; border: 2px solid #4caf50; border-radius: 50%; position: relative; background: rgba(76, 175, 80, .1); }
.pitch-rect { width: 40px; height: 120px; background: #d7ccc8; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.zone-overlay { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; }
.zone { position: absolute; width: 50%; height: 50%; cursor: pointer; appearance: none; border: 0; background: transparent; }
.zone:hover:not(:disabled), .zone--selected { background: rgba(37, 99, 235, .22); outline: 2px solid rgba(37, 99, 235, .7); outline-offset: -2px; }
.zone:focus-visible { outline: 3px solid #fff; outline-offset: -4px; }
.zone:disabled { cursor: not-allowed; }
.z1 { top: 0; right: 0; border-left: 1px dashed #ccc; border-bottom: 1px dashed #ccc; }.z2 { top: 0; left: 0; border-right: 1px dashed #ccc; border-bottom: 1px dashed #ccc; }.z3 { bottom: 0; left: 0; border-right: 1px dashed #ccc; border-top: 1px dashed #ccc; }.z4 { bottom: 0; right: 0; border-left: 1px dashed #ccc; border-top: 1px dashed #ccc; }.z5 { top: 25%; left: 25%; }.z6 { top: 25%; right: 25%; }.z7 { bottom: 25%; left: 25%; }.z8 { bottom: 25%; right: 25%; }
.map-label { position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); font-weight: 700; color: #2e7d32; pointer-events: none; font-size: 11px; letter-spacing: .04em; }
</style>
