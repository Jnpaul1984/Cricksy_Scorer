<script setup lang="ts">
import { RouterLink } from 'vue-router'

interface PlanFeature {
  text: string
  included: boolean
}

interface Plan {
  id: string
  name: string
  price: string
  period: string
  description: string
  features: PlanFeature[]
  recommended?: boolean
  cta: string
  ctaLink: string
}

const plans: Plan[] = [
  {
    id: 'free',
    name: 'Free / Fan',
    price: '$0',
    period: 'forever',
    description: 'Follow matches and explore basic features.',
    features: [
      { text: 'View live scoreboards', included: true },
      { text: 'Follow favorite players', included: true },
      { text: 'Access leaderboards', included: true },
      { text: 'Score matches', included: false },
      { text: 'Advanced analytics', included: false },
      { text: 'Team management', included: false },
    ],
    cta: 'Get Started',
    ctaLink: '/fan',
  },
  {
    id: 'player',
    name: 'Player Pro',
    price: '$9',
    period: '/month',
    description: 'Score your own matches with full features.',
    features: [
      { text: 'Everything in Free', included: true },
      { text: 'Score unlimited matches', included: true },
      { text: 'Ball-by-ball recording', included: true },
      { text: 'Personal stats dashboard', included: true },
      { text: 'Match history export', included: true },
      { text: 'Team management', included: false },
    ],
    cta: 'Start Free Trial',
    ctaLink: '/login',
  },
  {
    id: 'coach',
    name: 'Coach Pro',
    price: '$29',
    period: '/month',
    description: 'Manage teams and access advanced analytics.',
    features: [
      { text: 'Everything in Player Pro', included: true },
      { text: 'Multi-team management', included: true },
      { text: 'Player performance tracking', included: true },
      { text: 'Advanced analytics & ML predictions', included: true },
      { text: 'Custom reports & exports', included: true },
      { text: 'Priority support', included: true },
    ],
    recommended: true,
    cta: 'Start Free Trial',
    ctaLink: '/login',
  },
  {
    id: 'org',
    name: 'Organization',
    price: '$99',
    period: '/month',
    description: 'For leagues, clubs, and cricket organizations.',
    features: [
      { text: 'Everything in Coach Pro', included: true },
      { text: 'Unlimited teams & users', included: true },
      { text: 'Tournament management', included: true },
      { text: 'Embeddable scoreboards', included: true },
      { text: 'API access', included: true },
      { text: 'Dedicated support', included: true },
    ],
    cta: 'Contact Sales',
    ctaLink: '/login',
  },
]
</script>

<template>
  <div class="pricing">
    <!-- Header -->
    <section class="pricing-header">
      <h1 class="pricing-title">Choose Your Plan</h1>
      <p class="pricing-subtitle">
        From casual fans to professional organizations, we have a plan for you.
      </p>
    </section>

    <!-- Plans Grid -->
    <section class="plans-section">
      <div class="plans-grid">
        <div
          v-for="plan in plans"
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
</template>

<style scoped>
.pricing {
  color: var(--color-text);
  padding: var(--space-6) var(--space-4);
  max-width: 1200px;
  margin: 0 auto;
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
