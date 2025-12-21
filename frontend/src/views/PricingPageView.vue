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

    <!-- PLAN CARDS (7 cards, responsive grid) -->
    <section class="plans-grid">
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
          <span class="period">
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
          @click="goToSignup(plan.id)"
        >
          {{ plan.ctaLabel }}
        </BaseButton>

        <p v-if="plan.note" class="plan-note">
          {{ plan.note }}
        </p>
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
              {{ plan.shortName }}
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge } from '@/components'

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

type BillingPeriod = 'monthly' | 'annual'

interface PlanConfig {
  id: string
  name: string
  shortName: string
  tagline: string
  monthly: number
  highlight?: boolean
  ctaLabel: string
  note?: string
  features: string[]
}

// ----------------------------------------------------------------------------
// Plan definitions
// ----------------------------------------------------------------------------

const plans: PlanConfig[] = [
  {
    id: 'free',
    name: 'Cricksy Free',
    shortName: 'Free',
    tagline: 'For casual scorers, fans, parents, and kids at school games.',
    monthly: 0,
    ctaLabel: 'Start Free',
    features: [
      'Manual match scoring',
      'Basic live text scoreboard',
      'Simple player stats (recent matches)',
      '1 active competition at a time',
      'Public viewer with basic info',
    ],
  },
  {
    id: 'player-pro',
    name: 'Player Pro',
    shortName: 'Player',
    tagline: 'For serious players who want to track their career.',
    monthly: 2.99,
    ctaLabel: 'Get Player Pro',
    features: [
      'Everything in Free',
      'Full career dashboard (all formats)',
      'Form tracker & season graphs',
      'Strength/weakness views (zones & dismissals)',
      'AI-powered career summary',
      'Monthly progress report',
    ],
  },
  {
    id: 'coach-pro',
    name: 'Coach Pro',
    shortName: 'Coach',
    tagline: 'For school coaches, academies, and serious club coaches.',
    monthly: 9.99,
    ctaLabel: 'Choose Coach Pro',
    features: [
      'Everything in Player Pro',
      'Player development dashboard',
      'Coach → Player assignment',
      'Session notebook (per player, per session)',
      'Multi-player comparisons',
      'AI session summaries',
      'Export reports to PDF',
    ],
  },
  {
    id: 'coach-pro-plus',
    name: 'Coach Pro Plus',
    shortName: 'Coach+',
    tagline: 'Coach Pro with video session management and AI insights.',
    monthly: 24.99,
    ctaLabel: 'Choose Coach Pro Plus',
    features: [
      'Everything in Coach Pro',
      'Video session upload & streaming',
      'AI video session reports',
      '25 GB video storage',
      'Video playlist organization',
    ],
  },
  {
    id: 'analyst-pro',
    name: 'Analyst Pro',
    shortName: 'Analyst',
    tagline: 'For analysts and high-performance programs.',
    monthly: 14.99,
    highlight: true,
    ctaLabel: 'Choose Analyst Pro',
    features: [
      'Everything in Coach Pro',
      'Analyst workspace & saved views',
      'AI dismissal pattern detection',
      'AI heatmaps & ball-type clustering',
      'Phase-based analysis (powerplay, middle, death)',
      'Flexible query engine',
      'Analyst notebook',
      'CSV/JSON data exports',
      'Case study tagging for matches',
    ],
  },
  {
    id: 'org-starter',
    name: 'Org Pro Starter',
    shortName: 'Starter',
    tagline: 'For single schools, clubs, or small leagues.',
    monthly: 39,
    ctaLabel: 'Choose Org Pro Starter',
    features: [
      'Includes 4 teams',
      'Includes 4 Coach Pro seats',
      'Includes 1 Analyst Pro seat',
      'League/tournament management',
      'Org-level dashboards',
      'Basic sponsor panel',
      'Branded viewers & overlays',
      'Basic streaming overlay integration',
      'Role & subscription management',
    ],
  },
  {
    id: 'org-growth',
    name: 'Org Pro Growth',
    shortName: 'Growth',
    tagline: 'For medium academies and district leagues.',
    monthly: 79,
    ctaLabel: 'Choose Org Pro Growth',
    features: [
      'Includes 10 teams',
      'Includes 8 Coach Pro seats',
      'Includes 3 Analyst Pro seats',
      'Everything in Org Pro Starter',
      'Multi-competition support',
      'Sponsor rotation logic',
      'Custom viewer templates',
      'Priority support',
    ],
  },
  {
    id: 'org-elite',
    name: 'Org Pro Elite',
    shortName: 'Elite',
    tagline: 'For national academies, big leagues, and franchises.',
    monthly: 149,
    ctaLabel: 'Talk to us',
    note: 'Invite-only at launch. Best suited for high-performance programs.',
    features: [
      'Includes 20 teams',
      'Includes 15 Coach Pro seats',
      'Includes 5 Analyst Pro seats',
      'Everything in Org Pro Growth',
      'Advanced AI tuning for your league',
      'White-label viewers (logo & colors)',
      'Optional API access',
      'Quarterly analytics health check',
    ],
  },
]

// ----------------------------------------------------------------------------
// Billing state and computed display plans
// ----------------------------------------------------------------------------

const router = useRouter()
const billingPeriod = ref<BillingPeriod>('monthly')

const displayPlans = computed(() =>
  plans.map((plan) => {
    const price = billingPeriod.value === 'monthly' ? plan.monthly : plan.monthly * 10
    const priceDisplay = price === 0 ? '$0' : `$${price % 1 === 0 ? price : price.toFixed(2)}`
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

// ----------------------------------------------------------------------------
// Trial info helper
// ----------------------------------------------------------------------------

function trialInfoFor(planId: string): { trialLabel: string; cardRequired?: boolean } | null {
  switch (planId) {
    case 'free':
      return null // Free plan has no trial
    case 'player-pro':
    case 'coach-pro':
    case 'coach-pro-plus':
    case 'analyst-pro':
      return { trialLabel: '14-day free trial' }
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

    // Player Pro and up
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
