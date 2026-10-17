<script setup lang="ts">
const props = defineProps<{ modelValue: number | null; disabled?: boolean }>();
const emit = defineEmits<{ (event: 'update:modelValue', value: number | null): void }>();

const select = (zone: number) => {
  if (!props.disabled) emit('update:modelValue', props.modelValue === zone ? null : zone);
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
    <div class="map-label">TAP ZONE TO RECORD SHOT · TAP AGAIN TO CLEAR</div>
  </div>
</template>

<style scoped>
.shared-field-map { flex: 1; position: relative; width: 100%; overflow: hidden; display: flex; align-items: center; justify-content: center; padding-bottom: 34px; box-sizing: border-box; }
.field-oval { width: 80%; height: calc(80% - 18px); border: 2px solid #4caf50; border-radius: 50%; position: relative; background: rgba(76, 175, 80, .1); }
.pitch-rect { width: 40px; height: 120px; background: #d7ccc8; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.zone-overlay { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; }
.zone { position: absolute; cursor: pointer; appearance: none; border: 0; background: transparent; }
.zone:hover:not(:disabled), .zone--selected { background: rgba(37, 99, 235, .22); outline: 2px solid rgba(37, 99, 235, .7); outline-offset: -2px; }
.zone:focus-visible { outline: 3px solid #fff; outline-offset: -4px; }
.zone:disabled { cursor: not-allowed; }
.z1,.z2,.z3,.z4,.z5,.z6,.z7,.z8{width:25%;height:50%;border:1px dashed #ccc}.z1{top:0;left:0}.z2{top:0;left:25%}.z3{top:0;left:50%}.z4{top:0;left:75%}.z5{bottom:0;left:0}.z6{bottom:0;left:25%}.z7{bottom:0;left:50%}.z8{bottom:0;left:75%}
.map-label { position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); font-weight: 700; color: #166534; pointer-events: none; font-size: 11px; letter-spacing: .04em; white-space: nowrap; }
</style>
