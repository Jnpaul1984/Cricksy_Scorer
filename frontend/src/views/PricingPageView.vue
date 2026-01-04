<template>
  <div class="pricing-page">
    <!-- HERO SECTION -->
    <section class="pricing-hero">
      <div class="hero-copy">
        <h1>Simple pricing for every level of cricket.</h1>
        <p class="subtitle">
          From school scorers to national academies — pick the plan that matches how you use Cricksy.
        </p>
      </div>

      <!-- Billing toggle -->
      <div class="billing-toggle">
        <span
          :class="['billing-label', billingPeriod === 'monthly' && 'is-active']"
          @click="setBilling('monthly')"
        >
          Monthly
        </span>
        <span class="billing-divider">/</span>
        <span
          :class="['billing-label', billingPeriod === 'annual' && 'is-active']"
          @click="setBilling('annual')"
        >
          Annual
          <BaseBadge variant="success" :uppercase="false">
            2 months free
          </BaseBadge>
        </span>
      </div>
    </section>

    <!-- Loading state -->
    <section v-if="pricingStore.loading" class="plans-grid">
      <div class="pricing-loading">Loading pricing...</div>
    </section>

    <!-- Error state -->
    <section v-else-if="pricingStore.error" class="plans-grid">
      <div class="pricing-error">
        Failed to load pricing. Please refresh the page.
      </div>
    </section>

    <!-- PLAN CARDS (7 cards, responsive grid) -->
    <section v-else class="plans-grid">
      <BaseCard
        v-for="plan in displayPlans"
        :key="plan.id"
        padding="lg"
        class="plan-card"
        :class="{ 'plan-card--highlight': plan.highlight }"
      >
        <header class="plan-header">
          <div class="plan-title-row">
            <h2>{{ plan.name }}</h2>
            <BaseBadge v-if="plan.highlight" variant="primary">
              Most popular
            </BaseBadge>
          </div>
          <p class="plan-tagline">{{ plan.tagline }}</p>
        </header>

        <div class="plan-price">
          <span class="amount">{{ plan.priceDisplay }}</span>
          <span v-if="!plan.isContactSales" class="period">
            /{{ billingPeriod === 'monthly' ? 'month' : 'year' }}
          </span>
        </div>

        <div v-if="trialInfoFor(plan.id)" class="plan-trial">
          <p>{{ trialInfoFor(plan.id)?.trialLabel }}</p>
          <p v-if="trialInfoFor(plan.id)?.cardRequired" class="plan-trial-hint">
            Card required
          </p>
        </div>

        <ul class="plan-features">
          <li v-for="feature in plan.features" :key="feature" class="plan-feature-item">
            • {{ feature }}
          </li>
        </ul>

        <BaseButton
          variant="primary"
          size="md"
          class="plan-cta"
          @click="plan.isContactSales ? handleContactSales(plan.id) : goToSignup(plan.id)"
        >
          {{ plan.ctaLabel }}
        </BaseButton>
      </BaseCard>
    </section>

    <!-- FEATURE MATRIX -->
    <section class="feature-matrix">
      <h2>Compare plans</h2>
      <BaseCard padding="lg" class="matrix-card">
        <div class="matrix">
          <div class="matrix-header">
            <div class="matrix-feature-col"></div>
            <div
              v-for="plan in displayPlans"
              :key="plan.id"
              class="matrix-plan-col"
            >
              {{ plan.name }}
            </div>
          </div>

          <div
            v-for="row in matrixRows"
            :key="row.key"
            class="matrix-row"
          >
            <div class="matrix-feature-col">
              {{ row.label }}
            </div>

            <div
              v-for="plan in displayPlans"
              :key="plan.id + row.key"
              class="matrix-plan-col"
            >
              <span v-if="rowIncluded(row.key, plan.id)">✔</span>
              <span v-else>—</span>
            </div>
          </div>
        </div>
      </BaseCard>
    </section>

    <!-- FINAL CTA -->
    <section class="pricing-final-cta">
      <BaseCard padding="lg" class="final-card">
        <h2>Not sure where to start?</h2>
        <p class="subtitle">
          Start with Cricksy Free, then upgrade when you're ready for AI and org-level tools.
        </p>
        <BaseButton
          variant="primary"
          size="lg"
          @click="goToSignup('free')"
        >
          Get started free
        </BaseButton>
      </BaseCard>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge } from '@/components'
import { usePricingStore } from '@/stores/pricingStore'

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

type BillingPeriod = 'monthly' | 'annual'

// ----------------------------------------------------------------------------
// Pinia Store - SINGLE SOURCE OF TRUTH
// ----------------------------------------------------------------------------

const pricingStore = usePricingStore()
const router = useRouter()
const billingPeriod = ref<BillingPeriod>('monthly')

// Fetch pricing on component mount
onMounted(async () => {
  if (pricingStore.displayPlans.length === 0) {
    await pricingStore.fetchPricing()
  }
})

// ----------------------------------------------------------------------------
// Computed display plans with billing period
// ----------------------------------------------------------------------------

const displayPlans = computed(() =>
  pricingStore.individualDisplayPlans.map((plan) => {
    const price = billingPeriod.value === 'monthly' ? plan.monthlyPrice : plan.annualPrice
    let priceDisplay: string

    if (plan.isContactSales) {
      priceDisplay = 'Contact Sales'
    } else if (price === 0) {
      priceDisplay = '$0'
    } else {
      priceDisplay = billingPeriod.value === 'monthly' ? plan.monthlyDisplay : plan.annualDisplay
    }

    return {
      ...plan,
      price,
      priceDisplay,
    }
  }),
)

function setBilling(period: BillingPeriod) {
  billingPeriod.value = period
}

function goToSignup(planId: string) {
  // Navigate to signup with plan preselected (adjust path as needed)
  router.push({ path: '/auth/register', query: { plan: planId } })
}

function handleContactSales(planId: string) {
  // Open contact form or email (could also navigate to a contact page)
  // For now, show a message and optionally open email client
  const email = 'sales@cricksy.ai'
  const subject = `Cricksy ${planId.replace(/-/g, ' ')} Pricing Inquiry`
  const body = `Hi,\n\nI'm interested in learning more about the ${planId} plan for my organization.\n\nPlease contact me with more details.\n\nThanks`
  window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

// ----------------------------------------------------------------------------
// Trial info helper
// ----------------------------------------------------------------------------

function trialInfoFor(planId: string): { trialLabel: string; cardRequired?: boolean } | null {
  switch (planId) {
    case 'free-scoring': // Backend: free_scoring
      return null // Free plan has no trial
    case 'player-pro':
    case 'coach-pro':
    case 'coach-pro-plus':
    case 'analyst-pro':
      return { trialLabel: '14-day free trial' }
    case 'org-pro': // Org plans consolidated
    case 'org-starter':
    case 'org-growth':
    case 'org-elite':
      return { trialLabel: '30-day free trial', cardRequired: true }
    default:
      return null
  }
}

// ----------------------------------------------------------------------------
// Feature matrix
// ----------------------------------------------------------------------------

const matrixRows = [
  { key: 'match_scoring', label: 'Manual match scoring' },
  { key: 'live_viewer', label: 'Live text scoreboard & public viewer' },
  { key: 'basic_stats', label: 'Basic player stats & history' },
  { key: 'career_dashboard', label: 'Full player career dashboard' },
  { key: 'form_tracker', label: 'Form & season graphs' },
  { key: 'ai_player_insights', label: 'AI player insights (career summaries)' },
  { key: 'coach_tools', label: 'Coach tools (session notes, dev dashboard)' },
  { key: 'ai_session_summaries', label: 'AI session summaries' },
  { key: 'analyst_workspace', label: 'Analyst workspace & advanced analytics' },
  { key: 'exports', label: 'Data exports (CSV/JSON/PDF)' },
  { key: 'org_dashboards', label: 'Org-level dashboards' },
  { key: 'sponsors', label: 'Sponsor panel & branded viewers' },
  { key: 'tournament_mgmt', label: 'Tournament / league management' },
]

function rowIncluded(rowKey: string, planId: string): boolean {
  const order = [
    'free',
    'player-pro',
    'coach-pro',
    'coach-pro-plus',
    'analyst-pro',
    'org-starter',
    'org-growth',
    'org-elite',
  ] as const

  const index = order.indexOf(planId as (typeof order)[number])
  if (index === -1) return false

  switch (rowKey) {
    // Free and up
    case 'match_scoring':
    case 'live_viewer':
    case 'basic_stats':
      return index >= 0

    // Scorers Pro and up
    case 'career_dashboard':
    case 'form_tracker':
    case 'ai_player_insights':
      return index >= 1

    // Coach Pro and up
    case 'coach_tools':
    case 'ai_session_summaries':
      return index >= 2

    // Analyst Pro and up
    case 'analyst_workspace':
    case 'exports':
      return index >= 3

    // Org Starter and up
    case 'org_dashboards':
    case 'sponsors':
    case 'tournament_mgmt':
      return index >= 4

    default:
      return false
  }
}
</script>

<style scoped>
.pricing-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-10);
  padding-bottom: var(--space-10);
}

/* Hero */
.pricing-hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-top: var(--space-10);
  align-items: flex-start;
}

.hero-copy {
  max-width: 640px;
}

.hero-copy h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-3);
}

.subtitle {
  color: var(--color-text-muted);
  font-size: var(--text-lg);
}

/* Billing toggle */
.billing-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-surface-subtle);
}

.billing-label {
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  transition: color 0.15s ease;
}

.billing-label:hover {
  color: var(--color-text);
}

.billing-label.is-active {
  color: var(--color-text);
  font-weight: var(--font-semibold);
}

.billing-divider {
  color: var(--color-border-subtle);
}

/* Plans grid */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-6);
}

.plan-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.plan-card--highlight {
  border: 2px solid var(--color-primary);
  box-shadow: var(--shadow-card);
}

.plan-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.plan-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.plan-title-row h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0;
}

.plan-tagline {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}

.plan-price .amount {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
}

.plan-price .period {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.plan-trial {
  margin-top: var(--space-1);
}

.plan-trial p {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.plan-trial-hint {
  opacity: 0.7;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
  flex: 1;
}

.plan-feature-item {
  color: var(--color-text-muted);
}

.plan-cta {
  margin-top: var(--space-4);
}

.plan-note {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Matrix */
.feature-matrix {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Loading & Error States */
.pricing-loading,
.pricing-error {
  text-align: center;
  padding: 3rem;
  font-size: 1.125rem;
  color: var(--color-text-muted);
}

.pricing-error {
  color: var(--color-error);
  background: var(--color-error-bg, rgba(239, 68, 68, 0.1));
  border-radius: var(--radius-md);
}

.feature-matrix {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.feature-matrix h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.matrix-card {
  overflow-x: auto;
}

.matrix {
  min-width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.matrix-header,
.matrix-row {
  display: grid;
  grid-template-columns: minmax(180px, 2fr) repeat(7, minmax(80px, 1fr));
  gap: var(--space-2);
  align-items: center;
}

.matrix-header {
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-semibold);
}

.matrix-row {
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}

.matrix-row:nth-child(odd) {
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
}

.matrix-feature-col {
  font-weight: var(--font-medium);
  padding-left: var(--space-2);
}

.matrix-plan-col {
  text-align: center;
}

/* Final CTA */
.pricing-final-cta {
  display: flex;
  justify-content: center;
}

.final-card {
  max-width: 480px;
  text-align: center;
  width: 100%;
}

.final-card h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-2);
}

.final-card .subtitle {
  margin-bottom: var(--space-5);
}
</style>
