<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

import { API_BASE, getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()

// State
const quotaUsed = ref(0)
const quotaLimit = ref<number | null>(null)
const quotaPercentage = ref(0)
const loading = ref(false)
const dismissed = ref(false)
const lastFetchTime = ref(0)

// Check if user is authenticated
const isLoggedIn = computed(() => !!auth.token)

// Should show banner (80%+ usage, not unlimited, not dismissed)
const shouldShow = computed(() => {
  if (!isLoggedIn.value) return false
  if (dismissed.value) return false
  if (quotaLimit.value === null) return false // Unlimited
  return quotaPercentage.value >= 80
})

// Can upgrade (free or player_pro)
const canUpgrade = computed(() => {
  const role = auth.role?.toLowerCase() || ''
  return ['free', 'player_pro'].includes(role)
})

// Warning level
const warningLevel = computed(() => {
  if (quotaPercentage.value >= 95) return 'critical'
  if (quotaPercentage.value >= 90) return 'danger'
  return 'warning'
})

// Message based on percentage
const message = computed(() => {
  const pct = Math.round(quotaPercentage.value)
  if (pct >= 100) {
    return `You've reached your AI allowance limit for this period.`
  }
  if (pct >= 95) {
    return `You've used ${pct}% of your AI allowance — almost at the limit!`
  }
  return `You've used ${pct}% of your AI allowance this period.`
})

// Fetch quota from API
async function fetchQuota() {
  // Rate limit: don't fetch more than once per 5 minutes
  const now = Date.now()
  if (now - lastFetchTime.value < 5 * 60 * 1000 && lastFetchTime.value > 0) {
    return
  }

  if (!isLoggedIn.value) return

  loading.value = true
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${API_BASE}/api/ai-usage/my-usage`, { headers })
    if (res.ok) {
      const data = await res.json()
      quotaUsed.value = data.quota?.used || 0
      quotaLimit.value = data.quota?.limit || null
      quotaPercentage.value = data.quota?.percentage || 0
      lastFetchTime.value = now
    }
  } catch (err) {
    console.error('Failed to fetch AI quota:', err)
  } finally {
    loading.value = false
  }
}

function dismiss() {
  dismissed.value = true
  // Store in sessionStorage so it stays dismissed for the session
  sessionStorage.setItem('quota-banner-dismissed', 'true')
}

// Restore dismissed state
onMounted(() => {
  if (sessionStorage.getItem('quota-banner-dismissed') === 'true') {
    dismissed.value = true
  }
  fetchQuota()
})

// Re-fetch when user logs in
watch(() => auth.token, (newToken) => {
  if (newToken) {
    dismissed.value = false
    sessionStorage.removeItem('quota-banner-dismissed')
    fetchQuota()
  }
})
</script>

<template>
  <Transition name="slide-down">
    <div v-if="shouldShow" class="quota-banner" :class="warningLevel">
      <div class="banner-content">
        <span class="banner-icon">
          {{ warningLevel === 'critical' ? '🚫' : warningLevel === 'danger' ? '⚠️' : '📊' }}
        </span>
        <span class="banner-message">{{ message }}</span>
        <RouterLink v-if="canUpgrade" to="/pricing" class="upgrade-btn">
          Upgrade Plan
        </RouterLink>
        <RouterLink v-else to="/usage" class="view-usage-btn">
          View Usage
        </RouterLink>
      </div>
      <button class="dismiss-btn" aria-label="Dismiss" @click="dismiss">
        ✕
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.quota-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  gap: 1rem;
}

.quota-banner.warning {
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.08));
  border-bottom: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
}

.quota-banner.danger {
  background: linear-gradient(90deg, rgba(249, 115, 22, 0.15), rgba(249, 115, 22, 0.08));
  border-bottom: 1px solid rgba(249, 115, 22, 0.3);
  color: #fb923c;
}

.quota-banner.critical {
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.08));
  border-bottom: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.banner-icon {
  font-size: 1rem;
}

.banner-message {
  font-weight: 500;
}

.upgrade-btn {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  padding: 0.375rem 0.875rem;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
}

.upgrade-btn:hover {
  background: linear-gradient(135deg, #d97706, #b45309);
  transform: translateY(-1px);
}

.view-usage-btn {
  color: inherit;
  text-decoration: underline;
  font-weight: 500;
  opacity: 0.9;
}

.view-usage-btn:hover {
  opacity: 1;
}

.dismiss-btn {
  background: transparent;
  border: none;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  padding: 0.25rem;
  font-size: 0.875rem;
  line-height: 1;
}

.dismiss-btn:hover {
  opacity: 1;
}

/* Animation */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* Responsive */
@media (max-width: 640px) {
  .quota-banner {
    padding: 0.5rem 0.75rem;
  }

  .banner-message {
    font-size: 0.8125rem;
  }

  .upgrade-btn {
    padding: 0.25rem 0.625rem;
    font-size: 0.75rem;
  }
}
</style>
