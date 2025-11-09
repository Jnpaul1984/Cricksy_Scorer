<script setup lang="ts">
import { toRefs, withDefaults } from 'vue'

const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string }>(), {
  placeholder: '',
})
const { modelValue, placeholder } = toRefs(props)
const emit = defineEmits<{ (e:'update:modelValue', v: string): void }>()

function onInput(e: Event) {
  const v = (e.target as HTMLTextAreaElement).value
  emit('update:modelValue', v)
}
</script>

<template>
  <div class="commentary">
    <label>Commentary</label>
    <textarea
      :value="modelValue"
      rows="2"
      :placeholder="placeholder || 'Optional note for this delivery…'"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
.commentary{display:flex;flex-direction:column;gap:.5rem}
label{color:#fff;opacity:.9}
textarea{padding:.6rem;border-radius:8px;background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.3)}
</style>
