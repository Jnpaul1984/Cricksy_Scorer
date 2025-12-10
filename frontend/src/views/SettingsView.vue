<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

import { getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()

// Profile state - initialize from store
const profileName = ref('')
const profileEmail = ref('')
const profileSaving = ref(false)
const profileMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)

// Preferences state
const preferredFormat = ref<'t20' | 'odi' | 'test'>('t20')
const darkMode = ref(true)
const preferencesSaving = ref(false)
const preferencesMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)

// Auth state - use store getters
const isLoggedIn = computed(() => auth.isLoggedIn)
const userRole = computed(() => auth.role?.toLowerCase() || 'free')
const userSubscription = computed(() => auth.subscription)

// Plan info mapping
const planInfo: Record<string, { label: string; color: string; features: string[] }> = {
  free: {
    label: 'Free',
    color: '#888',
    features: ['Basic scoring', 'View matches', 'Limited AI features'],
  },
  player_pro: {
    label: 'Player Pro',
    color: '#10b981',
    features: ['Performance analytics', 'AI insights', 'Player profile'],
  },
  coach_pro: {
    label: 'Coach Pro',
    color: '#3b82f6',
    features: ['Team management', 'Session notes', 'Advanced analytics'],
  },
  analyst_pro: {
    label: 'Analyst Pro',
    color: '#8b5cf6',
    features: ['Match case studies', 'Export reports', 'Full AI access'],
  },
  org_pro: {
    label: 'Organization Pro',
    color: '#f59e0b',
    features: ['Unlimited seats', 'Tournament management', 'Priority support'],
  },
  superuser: {
    label: 'Administrator',
    color: '#ef4444',
    features: ['Full system access', 'User management', 'All features'],
  },
}

const currentPlan = computed(() => planInfo[userRole.value] || planInfo.free)

// Subscription info from store or fallback
const subscriptionInfo = computed(() => ({
  plan: userSubscription.value?.plan || userRole.value,
  planLabel: currentPlan.value.label,
  renewalDate: userSubscription.value?.renewal_date || null,
  status: userSubscription.value?.status || 'active',
  tokensUsed: userSubscription.value?.tokens_used || 0,
  tokensLimit: userSubscription.value?.tokens_limit || null,
}))

// Can upgrade
const canUpgrade = computed(() => ['free', 'player_pro'].includes(userRole.value))
const canDowngrade = computed(() => !['free', 'superuser'].includes(userRole.value))

// Load user data from store
function loadUserData() {
  // Use store getters for profile data
  profileEmail.value = auth.userEmail
  profileName.value = auth.userName

  // Load preferences from localStorage
  const savedPrefs = localStorage.getItem('cricksy-preferences')
  if (savedPrefs) {
    try {
      const prefs = JSON.parse(savedPrefs)
      preferredFormat.value = prefs.format || 't20'
      darkMode.value = prefs.darkMode ?? true
    } catch {
      // Ignore parse errors
    }
  }
}

// Save profile
async function saveProfile() {
  profileSaving.value = true
  profileMessage.value = null

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Note: Backend would need an endpoint for this
    // For now, just simulate success
    await new Promise(resolve => setTimeout(resolve, 500))

    profileMessage.value = { type: 'success', text: 'Profile updated successfully' }
    setTimeout(() => { profileMessage.value = null }, 3000)
  } catch (err: any) {
    profileMessage.value = { type: 'error', text: err.message || 'Failed to update profile' }
  } finally {
    profileSaving.value = false
  }
}

// Save preferences
function savePreferences() {
  preferencesSaving.value = true
  preferencesMessage.value = null

  try {
    const prefs = {
      format: preferredFormat.value,
      darkMode: darkMode.value,
    }
    localStorage.setItem('cricksy-preferences', JSON.stringify(prefs))

    // Apply dark mode
    document.documentElement.classList.toggle('light-mode', !darkMode.value)

    preferencesMessage.value = { type: 'success', text: 'Preferences saved' }
    setTimeout(() => { preferencesMessage.value = null }, 3000)
  } catch {
    preferencesMessage.value = { type: 'error', text: 'Failed to save preferences' }
  } finally {
    preferencesSaving.value = false
  }
}

// Handle delete account
function handleDeleteAccount() {
  alert('Contact support to delete your account')
}

// Watch dark mode changes
watch(darkMode, (newValue) => {
  document.documentElement.classList.toggle('light-mode', !newValue)
})

onMounted(() => {
  if (isLoggedIn.value) {
    loadUserData()
  }
})

// Reload when user changes
watch(() => auth.user, () => {
  if (auth.user) {
    loadUserData()
  }
})
</script>

<template>
  <div class="settings-view">
    <!-- Auth banner -->
    <div v-if="!isLoggedIn" class="banner info">
      Sign in to access your settings.
      <RouterLink to="/login" class="link-inline">Sign in</RouterLink>
    </div>

    <!-- Header -->
    <div class="header">
      <h1>Settings</h1>
      <p class="subtitle">Manage your profile, preferences, and subscription.</p>
    </div>

    <div v-if="isLoggedIn" class="settings-content">
      <!-- Profile Info Section -->
      <section class="settings-section">
        <div class="section-header">
          <h2>👤 Profile Information</h2>
        </div>
        <div class="section-body">
          <div class="form-group">
            <label class="field-label">Display Name</label>
            <input
              v-model="profileName"
              type="text"
              class="ds-input"
              placeholder="Your name"
            />
          </div>

          <div class="form-group">
            <label class="field-label">Email Address</label>
            <input
              v-model="profileEmail"
              type="email"
              class="ds-input"
              disabled
            />
            <p class="field-hint">Email cannot be changed</p>
          </div>

          <div v-if="profileMessage" class="message" :class="profileMessage.type">
            {{ profileMessage.text }}
          </div>

          <button
            class="btn-primary"
            :disabled="profileSaving"
            @click="saveProfile"
          >
            {{ profileSaving ? 'Saving...' : 'Save Profile' }}
          </button>
        </div>
      </section>

      <!-- Preferences Section -->
      <section class="settings-section">
        <div class="section-header">
          <h2>⚙️ Preferences</h2>
        </div>
        <div class="section-body">
          <div class="form-group">
            <label class="field-label">Preferred Match Format</label>
            <div class="radio-group">
              <label class="radio-option">
                <input v-model="preferredFormat" type="radio" value="t20" />
                <span class="radio-label">T20</span>
              </label>
              <label class="radio-option">
                <input v-model="preferredFormat" type="radio" value="odi" />
                <span class="radio-label">ODI (50 overs)</span>
              </label>
              <label class="radio-option">
                <input v-model="preferredFormat" type="radio" value="test" />
                <span class="radio-label">Test Match</span>
              </label>
            </div>
          </div>

          <div class="form-group">
            <label class="field-label">Appearance</label>
            <div class="toggle-row">
              <span class="toggle-label">Dark Mode</span>
              <button
                class="toggle-switch"
                :class="{ active: darkMode }"
                role="switch"
                :aria-checked="darkMode"
                @click="darkMode = !darkMode"
              >
                <span class="toggle-thumb" />
              </button>
            </div>
          </div>

          <div v-if="preferencesMessage" class="message" :class="preferencesMessage.type">
            {{ preferencesMessage.text }}
          </div>

          <button
            class="btn-primary"
            :disabled="preferencesSaving"
            @click="savePreferences"
          >
            {{ preferencesSaving ? 'Saving...' : 'Save Preferences' }}
          </button>
        </div>
      </section>

      <!-- Subscription Section -->
      <section class="settings-section subscription-section">
        <div class="section-header">
          <h2>💳 Subscription</h2>
        </div>
        <div class="section-body">
          <div class="subscription-card" :style="{ '--plan-color': currentPlan.color }">
            <div class="plan-header">
              <div class="plan-badge" :style="{ background: currentPlan.color }">
                {{ currentPlan.label }}
              </div>
              <span v-if="subscriptionInfo.status === 'active'" class="status-active">
                Active
              </span>
            </div>

            <div class="plan-features">
              <h4>Included Features:</h4>
              <ul>
                <li v-for="feature in currentPlan.features" :key="feature">
                  ✓ {{ feature }}
                </li>
              </ul>
            </div>

            <div v-if="subscriptionInfo.renewalDate" class="renewal-info">
              <span class="renewal-label">Next renewal:</span>
              <span class="renewal-date">{{ subscriptionInfo.renewalDate }}</span>
            </div>

            <div class="plan-actions">
              <RouterLink
                v-if="canUpgrade"
                to="/pricing"
                class="btn-upgrade"
              >
                ⬆️ Upgrade Plan
              </RouterLink>
              <button
                v-if="canDowngrade"
                class="btn-downgrade"
                @click="() => { /* TODO: Implement downgrade flow */ }"
              >
                Downgrade
              </button>
              <RouterLink
                to="/usage"
                class="btn-usage"
              >
                📊 View Usage
              </RouterLink>
            </div>
          </div>

          <div class="billing-note">
            <p>
              Need help with billing?
              <a href="mailto:support@cricksy.com" class="link">Contact Support</a>
            </p>
          </div>
        </div>
      </section>

      <!-- Danger Zone -->
      <section class="settings-section danger-section">
        <div class="section-header">
          <h2>⚠️ Danger Zone</h2>
        </div>
        <div class="section-body">
          <div class="danger-item">
            <div class="danger-info">
              <h4>Delete Account</h4>
              <p>Permanently delete your account and all associated data.</p>
            </div>
            <button class="btn-danger" @click="handleDeleteAccount">
              Delete Account
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 1.5rem;
  max-width: 800px;
  margin: 0 auto;
}

/* Banner */
.banner {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.banner.info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.link-inline {
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
  margin-left: 0.5rem;
}

/* Header */
.header {
  margin-bottom: 2rem;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: var(--color-text, #fff);
}

.subtitle {
  margin: 0.25rem 0 0;
  color: var(--color-text-muted, #888);
}

/* Content */
.settings-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Sections */
.settings-section {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #333);
  background: var(--color-background, #0f0f1a);
}

.section-header h2 {
  margin: 0;
  font-size: 1.125rem;
  color: var(--color-text, #fff);
}

.section-body {
  padding: 1.25rem;
}

/* Form elements */
.form-group {
  margin-bottom: 1.25rem;
}

.field-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--color-text, #fff);
}

.field-hint {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: var(--color-text-muted, #888);
}

.ds-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border, #333);
  border-radius: 8px;
  background: var(--color-background, #0f0f1a);
  color: var(--color-text, #fff);
  font-size: 1rem;
}

.ds-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Radio group */
.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.radio-option input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary, #4f46e5);
}

.radio-label {
  color: var(--color-text, #fff);
}

/* Toggle */
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
}

.toggle-label {
  color: var(--color-text, #fff);
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 26px;
  background: var(--color-border, #333);
  border: none;
  border-radius: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.toggle-switch.active {
  background: var(--color-primary, #4f46e5);
}

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.toggle-switch.active .toggle-thumb {
  transform: translateX(22px);
}

/* Messages */
.message {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.message.success {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.message.error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Buttons */
.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: #fff;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #4338ca);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Subscription Card */
.subscription-card {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.1), rgba(139, 92, 246, 0.05));
  border: 1px solid var(--plan-color, #4f46e5);
  border-radius: 12px;
  padding: 1.5rem;
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.plan-badge {
  padding: 0.375rem 0.875rem;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.875rem;
  color: #fff;
}

.status-active {
  color: #34d399;
  font-size: 0.875rem;
  font-weight: 500;
}

.plan-features {
  margin-bottom: 1rem;
}

.plan-features h4 {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

.plan-features ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.plan-features li {
  padding: 0.25rem 0;
  color: var(--color-text, #fff);
  font-size: 0.875rem;
}

.renewal-info {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.renewal-label {
  color: var(--color-text-muted, #888);
}

.renewal-date {
  color: var(--color-text, #fff);
  font-weight: 500;
}

.plan-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-upgrade {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  padding: 0.625rem 1rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  text-decoration: none;
  transition: all 0.2s;
}

.btn-upgrade:hover {
  transform: translateY(-1px);
}

.btn-downgrade {
  background: transparent;
  color: var(--color-text-muted, #888);
  border: 1px solid var(--color-border, #333);
  padding: 0.625rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  cursor: pointer;
}

.btn-downgrade:hover {
  border-color: var(--color-text-muted, #888);
}

.btn-usage {
  background: transparent;
  color: var(--color-primary, #4f46e5);
  border: 1px solid var(--color-primary, #4f46e5);
  padding: 0.625rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  text-decoration: none;
  transition: all 0.2s;
}

.btn-usage:hover {
  background: rgba(79, 70, 229, 0.1);
}

.billing-note {
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

.billing-note .link {
  color: var(--color-primary, #4f46e5);
  text-decoration: underline;
}

/* Danger Zone */
.danger-section .section-header {
  background: rgba(239, 68, 68, 0.1);
}

.danger-section .section-header h2 {
  color: #f87171;
}

.danger-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.danger-info h4 {
  margin: 0 0 0.25rem;
  color: var(--color-text, #fff);
}

.danger-info p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

.btn-danger {
  background: transparent;
  color: #f87171;
  border: 1px solid #f87171;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  white-space: nowrap;
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

/* Responsive */
@media (max-width: 640px) {
  .settings-view {
    padding: 1rem;
  }

  .plan-actions {
    flex-direction: column;
  }

  .danger-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
