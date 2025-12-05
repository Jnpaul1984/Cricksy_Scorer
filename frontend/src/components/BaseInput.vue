<template>
  <div class="ds-input-group">
    <label v-if="label" :for="inputId" class="ds-input-label">
      {{ label }}
      <span v-if="required" class="ds-input-required" aria-hidden="true">*</span>
    </label>
    <input
      :id="inputId"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :required="required"
      :class="inputClasses"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      v-bind="$attrs"
      @input="onInput"
    />
    <p v-if="error" :id="errorId" class="ds-input-error" role="alert">
      {{ error }}
    </p>
    <p v-else-if="helpText" :id="helpId" class="ds-input-help">
      {{ helpText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: string | number | null
  type?: string
  label?: string
  id?: string
  placeholder?: string
  disabled?: boolean
  error?: string | null
  helpText?: string | null
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  label: undefined,
  id: undefined,
  placeholder: undefined,
  disabled: false,
  error: null,
  helpText: null,
  required: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()

// Generate unique IDs for accessibility
const inputId = computed(() => props.id ?? `input-${Math.random().toString(36).slice(2, 9)}`)
const errorId = computed(() => `${inputId.value}-error`)
const helpId = computed(() => `${inputId.value}-help`)

const describedBy = computed(() => {
  if (props.error) return errorId.value
  if (props.helpText) return helpId.value
  return undefined
})

const inputClasses = computed(() => ({
  'ds-input': true,
  'ds-input--error': !!props.error,
}))

const onInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const value = props.type === 'number' ? (target.value === '' ? null : Number(target.value)) : target.value
  emit('update:modelValue', value)
}
</script>
