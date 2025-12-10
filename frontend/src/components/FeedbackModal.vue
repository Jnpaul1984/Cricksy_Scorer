<script setup lang="ts">
import { ref, computed } from 'vue'

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  submitted: [payload: { text: string; email?: string }]
}>()

const feedbackText = ref('')
const email = ref('')
const isSubmitting = ref(false)

const canSubmit = computed(() => feedbackText.value.trim().length > 0 && !isSubmitting.value)

function close() {
  emit('update:visible', false)
}

async function submit() {
  if (!canSubmit.value) return

  isSubmitting.value = true
  try {
    emit('submitted', {
      text: feedbackText.value.trim(),
      email: email.value.trim() || undefined,
    })
    // Reset form
    feedbackText.value = ''
    email.value = ''
    close()
  } finally {
    isSubmitting.value = false
  }
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    close()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="modal-backdrop"
        @click="handleBackdropClick"
      >
        <div class="modal-content">
          <header class="modal-header">
            <h3>Send Feedback</h3>
            <button class="close-btn" aria-label="Close" @click="close">×</button>
          </header>

          <div class="modal-body">
            <label class="field-label">
              Your feedback <span class="required">*</span>
            </label>
            <textarea
              v-model="feedbackText"
              class="ds-input feedback-textarea"
              placeholder="Tell us what's on your mind..."
              rows="5"
            />

            <label class="field-label">
              Email <span class="optional">(optional)</span>
            </label>
            <input
              v-model="email"
              type="email"
              class="ds-input"
              placeholder="your@email.com"
            />
          </div>

          <footer class="modal-footer">
            <button class="ds-btn ds-btn--secondary" @click="close">
              Cancel
            </button>
            <button
              class="ds-btn ds-btn--primary"
              :disabled="!canSubmit"
              @click="submit"
            >
              {{ isSubmitting ? 'Sending...' : 'Send' }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--bg-surface, #1e1e2e);
  border-radius: 12px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color, #2a2a3a);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-secondary, #888);
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.close-btn:hover {
  color: var(--text-primary, #fff);
}

.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #fff);
  margin-bottom: 0.25rem;
}

.required {
  color: var(--danger, #e74c3c);
}

.optional {
  color: var(--text-muted, #666);
  font-weight: 400;
}

.ds-input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  background: var(--bg-input, #16161e);
  border: 1px solid var(--border-color, #2a2a3a);
  border-radius: 8px;
  color: var(--text-primary, #fff);
  font-size: 0.9375rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.ds-input:focus {
  outline: none;
  border-color: var(--primary, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.ds-input::placeholder {
  color: var(--text-muted, #666);
}

.feedback-textarea {
  resize: vertical;
  min-height: 100px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--border-color, #2a2a3a);
}

.ds-btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.ds-btn--primary {
  background: var(--primary, #3b82f6);
  color: #fff;
}

.ds-btn--primary:hover:not(:disabled) {
  background: var(--primary-hover, #2563eb);
}

.ds-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ds-btn--secondary {
  background: transparent;
  color: var(--text-secondary, #888);
  border: 1px solid var(--border-color, #2a2a3a);
}

.ds-btn--secondary:hover {
  background: var(--bg-hover, #252535);
  color: var(--text-primary, #fff);
}

/* Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-active .modal-content,
.fade-leave-active .modal-content {
  transition: transform 0.2s ease;
}

.fade-enter-from .modal-content,
.fade-leave-to .modal-content {
  transform: scale(0.95);
}
</style>
