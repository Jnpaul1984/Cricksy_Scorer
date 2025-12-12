<script setup lang="ts">
import { ref, computed } from 'vue'

import { BaseButton, BaseCard, BaseInput, BaseBadge } from '@/components'
import apiService from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()

// Form state
const email = ref('')
const role = ref('player_pro')
const plan = ref('player_pro')
const orgId = ref('')
const betaTag = ref('beta_phase1')
const password = ref('')

// UI state
const loading = ref(false)
const error = ref<string | null>(null)
const createdUser = ref<{
  id: string
  email: string
  role: string
  plan: string
  org_id: string | null
  beta_tag: string | null
  temp_password: string
} | null>(null)
const copied = ref(false)

// Auth check
const isSuperAdmin = computed(() => auth.isSuper)

// Role options matching backend RoleEnum
const roleOptions = [
  { value: 'free', label: 'Free' },
  { value: 'player_pro', label: 'Player Pro' },
  { value: 'coach_pro', label: 'Coach Pro' },
  { value: 'analyst_pro', label: 'Analyst Pro' },
  { value: 'org_pro', label: 'Organization Pro' },
]

// Plan options (same as roles in this app)
const planOptions = [
  { value: 'free', label: 'Free' },
  { value: 'player_pro', label: 'Player Pro' },
  { value: 'coach_pro', label: 'Coach Pro' },
  { value: 'analyst_pro', label: 'Analyst Pro' },
  { value: 'org_pro', label: 'Organization Pro' },
]

async function handleSubmit() {
  // Validate
  if (!email.value.trim()) {
    error.value = 'Email is required'
    return
  }

  loading.value = true
  error.value = null
  createdUser.value = null

  try {
    const result = await apiService.createBetaUser({
      email: email.value.trim(),
      role: role.value,
      plan: plan.value,
      org_id: orgId.value.trim() || null,
      beta_tag: betaTag.value.trim() || null,
      password: password.value.trim() || null,
    })

    createdUser.value = result

    // Clear form except email for quick reference
    password.value = ''
  } catch (err: any) {
    error.value = err.message || 'Failed to create user'
    console.error('Error creating beta user:', err)
  } finally {
    loading.value = false
  }
}

function clearForm() {
  email.value = ''
  role.value = 'player_pro'
  plan.value = 'player_pro'
  orgId.value = ''
  betaTag.value = 'beta_phase1'
  password.value = ''
  createdUser.value = null
  error.value = null
  copied.value = false
}

async function copyPassword() {
  if (!createdUser.value?.temp_password) return

  try {
    await navigator.clipboard.writeText(createdUser.value.temp_password)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<template>
  <div class="admin-page">
    <h1 class="page-title">Beta User Management</h1>

    <!-- Access denied for non-superadmins -->
    <BaseCard v-if="!isSuperAdmin" padding="lg">
      <div class="access-denied">
        <span class="access-icon">🔒</span>
        <h2>Access Denied</h2>
        <p>You must be a super admin to access this page.</p>
      </div>
    </BaseCard>

    <!-- Main content for superadmins -->
    <template v-else>
      <!-- Info banner -->
      <BaseCard padding="md" class="info-banner">
        <div class="banner-content">
          <BaseBadge variant="primary">ℹ️ Info</BaseBadge>
          <p>
            Create beta user accounts here. Temporary passwords are shown only once —
            make sure to send the credentials to the tester securely.
          </p>
        </div>
      </BaseCard>

      <!-- Success state -->
      <BaseCard v-if="createdUser" padding="lg" class="success-card">
        <div class="success-content">
          <h2>✅ User Created Successfully</h2>

          <div class="user-details">
            <div class="detail-row">
              <span class="label">Email:</span>
              <span class="value">{{ createdUser.email }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Role:</span>
              <BaseBadge variant="primary">{{ createdUser.role }}</BaseBadge>
            </div>
            <div class="detail-row">
              <span class="label">Plan:</span>
              <BaseBadge variant="neutral">{{ createdUser.plan }}</BaseBadge>
            </div>
            <div v-if="createdUser.org_id" class="detail-row">
              <span class="label">Org ID:</span>
              <span class="value">{{ createdUser.org_id }}</span>
            </div>
            <div v-if="createdUser.beta_tag" class="detail-row">
              <span class="label">Beta Tag:</span>
              <BaseBadge variant="primary">{{ createdUser.beta_tag }}</BaseBadge>
            </div>
          </div>

          <div class="password-section">
            <p class="password-label">Temporary password for {{ createdUser.email }}:</p>
            <div class="password-display">
              <BaseBadge variant="warning" class="password-badge">
                {{ createdUser.temp_password }}
              </BaseBadge>
              <BaseButton
                size="sm"
                :variant="copied ? 'primary' : 'secondary'"
                @click="copyPassword"
              >
                {{ copied ? '✓ Copied' : '📋 Copy' }}
              </BaseButton>
            </div>
          </div>

          <div class="reminder-banner">
            <p>
              ⚠️ Make sure to send this email + temporary password to the tester.
              They should log in and change it immediately.
            </p>
          </div>

          <BaseButton variant="secondary" @click="clearForm">
            Create Another User
          </BaseButton>
        </div>
      </BaseCard>

      <!-- Create form -->
      <BaseCard v-else padding="lg">
        <h2 class="card-title">Create Beta User</h2>

        <form class="beta-form" @submit.prevent="handleSubmit">
          <!-- Email -->
          <BaseInput
            v-model="email"
            type="email"
            label="Email"
            placeholder="user@example.com"
            required
          />

          <!-- Role -->
          <div class="form-group">
            <label class="ds-input-label">Role <span class="ds-input-required">*</span></label>
            <select v-model="role" class="ds-input">
              <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <!-- Plan -->
          <div class="form-group">
            <label class="ds-input-label">Plan <span class="ds-input-required">*</span></label>
            <select v-model="plan" class="ds-input">
              <option v-for="opt in planOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <!-- Org ID -->
          <BaseInput
            v-model="orgId"
            type="text"
            label="Organization ID"
            placeholder="org-uuid (optional)"
            help-text="Leave empty if not part of an organization"
          />

          <!-- Beta Tag -->
          <BaseInput
            v-model="betaTag"
            type="text"
            label="Beta Tag"
            placeholder="beta_phase1"
          />

          <!-- Password -->
          <BaseInput
            v-model="password"
            type="password"
            label="Password (optional)"
            placeholder="Leave empty to auto-generate"
            help-text="If empty, a secure 16-character password will be generated"
          />

          <!-- Error -->
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <!-- Submit -->
          <div class="form-actions">
            <BaseButton type="submit" variant="primary" :disabled="loading">
              {{ loading ? 'Creating...' : 'Create User' }}
            </BaseButton>
          </div>
        </form>
      </BaseCard>
    </template>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-lg);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-lg);
  color: var(--color-text-primary);
}

.card-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-lg);
  color: var(--color-text-primary);
}

.info-banner {
  margin-bottom: var(--space-lg);
  background: var(--color-surface-alt);
}

.banner-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
}

.banner-content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.beta-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.form-actions {
  padding-top: var(--space-md);
}

.error-message {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  padding: var(--space-sm);
  background: var(--color-error-bg, rgba(239, 68, 68, 0.1));
  border-radius: var(--radius-sm);
}

.success-card {
  border: 2px solid var(--color-success, #10b981);
}

.success-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.success-content h2 {
  color: var(--color-success, #10b981);
  margin: 0;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.detail-row .label {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  min-width: 80px;
}

.detail-row .value {
  color: var(--color-text-primary);
}

.password-section {
  background: var(--color-surface-alt);
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.password-label {
  margin: 0 0 var(--space-sm) 0;
  font-weight: var(--font-weight-medium);
}

.password-display {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.password-badge {
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
  padding: var(--space-sm) var(--space-md);
}

.reminder-banner {
  background: var(--color-warning-bg, rgba(245, 158, 11, 0.1));
  border: 1px solid var(--color-warning, #f59e0b);
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.reminder-banner p {
  margin: 0;
  color: var(--color-warning, #f59e0b);
  font-size: var(--font-size-sm);
}

.access-denied {
  text-align: center;
  padding: var(--space-xl);
}

.access-icon {
  font-size: 3rem;
}

.access-denied h2 {
  margin: var(--space-md) 0;
  color: var(--color-text-primary);
}

.access-denied p {
  color: var(--color-text-secondary);
}

/* Dark theme select styling */
select.ds-input {
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
}

select.ds-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-alpha);
}
</style>
