<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

import { usePricingStore } from '@/stores/pricingStore'
import { API_BASE } from '@/services/api'

// ============================================================================
// Pricing Store - Single Source of Truth
// ============================================================================

const pricingStore = usePricingStore()

// Fetch pricing on component mount if not already loaded
onMounted(async () => {
  if (pricingStore.displayPlans.length === 0) {
    await pricingStore.fetchPricing()
  }
})

// Retry function
const retryFetch = async () => {
  await pricingStore.fetchPricing()
}

// Error message formatting
const errorMessage = computed(() => {
  if (!pricingStore.error) return ''
  
  const isDev = import.meta.env.DEV
  const status = pricingStore.httpStatus
  
  if (isDev) {
    // Show technical details in dev
    return `Error ${status || 'Unknown'}: ${pricingStore.error}`
  } else {
    // User-friendly message in production
    if (status === 404) {
      return 'Pricing information is currently unavailable.'
    } else if (status && status >= 500) {
      return 'Our pricing service is temporarily down. Please try again in a few moments.'
    } else {
      return 'Unable to load pricing plans at this time.'
    }
  }
})

// ============================================================================
// Production API Warning Detection
// ============================================================================

const isDevelopment = import.meta.env.DEV
const isProduction = import.meta.env.PROD
const isWindowOriginFallback = computed(() => {
  if (!isProduction) return false
  const windowOrigin = typeof window !== 'undefined' 
    ? `${window.location.protocol}//${window.location.host}` 
    : ''
  return API_BASE === windowOrigin
})

// ============================================================================
// Price Formatting Helper
// ============================================================================

function formatPlanPrice(plan: any): { amount: string; period: string } {
  if (plan.isContactSales || plan.monthlyPrice === null) {
    return { amount: 'Contact us', period: '' }
  }
  if (plan.monthlyPrice === 0) {
    return { amount: 'Free', period: 'forever' }
  }
  return { amount: plan.monthlyDisplay, period: '/month' }
}

// ============================================================================
// Display Plans
// ============================================================================

const displayPlans = computed(() => {
  return pricingStore.individualDisplayPlans.map((plan) => {
    const { amount, period } = formatPlanPrice(plan)

    // Convert features array to PlanFeature format for template
    const features = plan.features.map((text: string) => ({
      text,
      included: true
    }))

    return {
      id: plan.id,
      backendId: plan.backendId,
      name: plan.name,
      price: amount,
      period: period,
      description: plan.tagline,
      features,
      recommended: plan.highlight,
      cta: plan.ctaLabel,
      ctaLink: plan.monthlyPrice === 0 ? '/fan' : '/login'
    }
  })
})

// Show scoring is free message from API
const scoringIsFreeBanner = computed(() => pricingStore.scoringIsFree)
</script>

<template>
  <div class="pricing">
    <!-- Production API Warning Banner -->
    <div v-if="isWindowOriginFallback" class="api-warning-banner" style="background: #ff6b6b; color: white; padding: 12px; text-align: center; font-weight: 600; margin-bottom: 16px;">
      ⚠️ WARNING: API_BASE misconfigured in production. Using window.origin fallback. Pricing may not load correctly.
      <br>
      <span style="font-size: 0.85em; font-weight: 400;">Configure VITE_API_BASE in environment variables.</span>
    </div>

    <!-- Loading State -->
    <div v-if="pricingStore.loading" class="pricing-loading">
      <p>Loading pricing plans...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="pricingStore.error" class="pricing-error">
      <div style="max-width: 600px; margin: 40px auto; text-align: center; padding: 20px;">
        <p style="font-size: 1.1em; color: #dc2626; margin-bottom: 16px;">{{ errorMessage }}</p>
        <button 
          @click="retryFetch" 
          :disabled="pricingStore.loading"
          style="padding: 10px 24px; font-size: 1em; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;"
          :style="pricingStore.loading ? 'opacity: 0.6; cursor: not-allowed;' : ''"
        >
          {{ pricingStore.loading ? 'Retrying...' : '🔄 Retry' }}
        </button>
        <p v-if="isDevelopment" style="margin-top: 16px; font-size: 0.85em; color: #666;">
          Dev Info: Check console for details. Last attempt: {{ pricingStore.lastFetchAttempt }}
        </p>
      </div>
    </div>

    <!-- Pricing Content -->
    <div v-else>
      <!-- Header -->
      <section class="pricing-header">
        <h1 class="pricing-title">Choose Your Plan</h1>
        <p class="pricing-subtitle">
          From casual fans to professional organizations, we have a plan for you.
        </p>
        <p v-if="scoringIsFreeBanner" class="scoring-free-badge">
          ✓ Match scoring is always free
        </p>
      </section>

      <!-- Plans Grid -->
      <section class="plans-section">
        <div class="plans-grid">
          <div
            v-for="plan in displayPlans"
            :key="plan.id"
            class="plan-card"
            :class="{ 'plan-recommended': plan.recommended }"
          >
            <div v-if="plan.recommended" class="plan-badge">Most Popular</div>
            <h2 class="plan-name">{{ plan.name }}</h2>
            <div class="plan-price">
              <span class="price-amount">{{ plan.price }}</span>
              <span class="price-period">{{ plan.period }}</span>
            </div>
            <p class="plan-description">{{ plan.description }}</p>

            <ul class="plan-features">
              <li
                v-for="feature in plan.features"
                :key="feature.text"
                class="feature-item"
                :class="{ 'feature-excluded': !feature.included }"
              >
                <span class="feature-icon">{{ feature.included ? '✓' : '✗' }}</span>
                <span class="feature-text">{{ feature.text }}</span>
              </li>
            </ul>

            <RouterLink
              :to="plan.ctaLink"
              class="plan-cta"
              :class="plan.recommended ? 'cta-primary' : 'cta-secondary'"
            >
              {{ plan.cta }}
            </RouterLink>
          </div>
        </div>
      </section>

      <!-- FAQ or additional info -->
      <section class="pricing-footer">
        <p class="pricing-note">
          All plans include a 14-day free trial. No credit card required.
        </p>
        <RouterLink to="/" class="back-link">← Back to Home</RouterLink>
      </section>
    </div>
  </div>
</template>

<style scoped>
.pricing {
  color: var(--color-text);
  padding: var(--space-6) var(--space-4);
  max-width: 1200px;
  margin: 0 auto;
}

/* Loading & Error States */
.pricing-loading,
.pricing-error {
  text-align: center;
  padding: var(--space-8);
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
}

.pricing-error {
  color: var(--color-danger);
}

/* Header */
.pricing-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.pricing-title {
  font-family: var(--font-heading);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  margin: 0 0 var(--space-3);
}

.pricing-subtitle {
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
  margin: 0;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.scoring-free-badge {
  display: inline-block;
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--color-success-bg, #d1fae5);
  color: var(--color-success-text, #065f46);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

/* Plans Grid */
.plans-section {
  margin-bottom: var(--space-8);
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-5);
}

/* Plan Card */
.plan-card {
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.plan-recommended {
  border-color: var(--color-primary);
  border-width: 2px;
}

.plan-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: #0f172a;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  letter-spacing: 0.05em;
}

.plan-name {
  font-family: var(--font-heading);
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-3);
  color: var(--color-text);
}

.plan-price {
  margin-bottom: var(--space-3);
}

.price-amount {
  font-family: var(--font-heading);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
}

.price-period {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-left: var(--space-1);
}

.plan-description {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-4);
  line-height: var(--leading-relaxed);
}

/* Features List */
.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-5);
  flex-grow: 1;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-subtle);
}

.feature-item:last-child {
  border-bottom: none;
}

.feature-excluded {
  color: var(--color-text-muted);
}

.feature-icon {
  flex-shrink: 0;
  width: 18px;
  text-align: center;
  font-weight: var(--font-bold);
}

.feature-item:not(.feature-excluded) .feature-icon {
  color: var(--color-success);
}

.feature-excluded .feature-icon {
  color: var(--color-text-muted);
}

/* CTA Buttons */
.plan-cta {
  display: block;
  text-align: center;
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.cta-primary {
  background: var(--color-primary);
  color: #0f172a;
}

.cta-primary:hover {
  background: var(--color-primary-hover);
}

.cta-secondary {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border-strong);
}

.cta-secondary:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary);
}

/* Footer */
.pricing-footer {
  text-align: center;
}

.pricing-note {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
}

.back-link {
  font-size: var(--text-sm);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: var(--font-medium);
}

.back-link:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 640px) {
  .pricing {
    padding: var(--space-4) var(--space-3);
  }

  .pricing-title {
    font-size: var(--text-2xl);
  }

  .pricing-subtitle {
    font-size: var(--text-base);
  }

  .plans-grid {
    grid-template-columns: 1fr;
  }
}
</style>
