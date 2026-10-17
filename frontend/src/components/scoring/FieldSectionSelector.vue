<script setup lang="ts">
const props = defineProps<{ modelValue: number | null; disabled?: boolean }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: number | null): void }>()

const sections = [1, 2, 3, 4, 5, 6, 7, 8] as const
</script>

<template>
  <section class="field-section-selector" aria-label="Field section selector">
    <div class="field-section-selector__field" role="group" aria-label="Select where the ball was hit">
      <button
        v-for="section in sections"
        :key="section"
        type="button"
        class="field-section-selector__section"
        :class="[`field-section-selector__section--${section}`, { 'is-selected': props.modelValue === section }]"
        :data-testid="`field-section-${section}`"
        :aria-pressed="props.modelValue === section"
        :disabled="props.disabled"
        @click="emit('update:modelValue', section)"
      >
        {{ section }}
      </button>
    </div>
    <button type="button" class="field-section-selector__clear" data-testid="clear-field-section" :disabled="props.disabled || props.modelValue === null" @click="emit('update:modelValue', null)">Clear section</button>
  </section>
</template>

<style scoped>
.field-section-selector{display:flex;flex-direction:column;gap:.5rem}.field-section-selector__field{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);width:220px;height:220px;border:2px solid #4caf50;border-radius:50%;overflow:hidden;background:#e8f5e9}.field-section-selector__section{min-width:0;min-height:0;border:1px dashed #94a3b8;background:transparent;color:#334155;font-weight:800;cursor:pointer}.field-section-selector__section:hover,.field-section-selector__section.is-selected{background:#2563eb33}.field-section-selector__section:disabled{cursor:not-allowed;opacity:.55}.field-section-selector__section--1{grid-column:2;grid-row:1}.field-section-selector__section--2{grid-column:3;grid-row:1}.field-section-selector__section--3{grid-column:3;grid-row:2}.field-section-selector__section--4{grid-column:3;grid-row:3}.field-section-selector__section--5{grid-column:2;grid-row:3}.field-section-selector__section--6{grid-column:1;grid-row:3}.field-section-selector__section--7{grid-column:1;grid-row:2}.field-section-selector__section--8{grid-column:1;grid-row:1}.field-section-selector__clear{align-self:flex-start;border:1px solid #64748b;background:#fff;color:#334155;border-radius:6px;padding:.35rem .6rem}
</style>
