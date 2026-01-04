<!-- frontend/src/components/VenueUpgradeCTA.vue -->
<!-- Venue monetization upgrade prompt -->
<!-- Shows venue-specific pricing plans with upgrade CTA -->

<template>
  <div class="venue-upgrade-cta">
    <div class="upgrade-content">
      <div class="upgrade-icon">🏟️</div>
      <h3>Upgrade This Ground</h3>
      <p class="upgrade-tagline">
        {{ tagline }}
      </p>
      
      <div v-if="!pricingStore.loading" class="venue-plans">
        <div
          v-for="plan in pricingStore.venueDisplayPlans"
          :key="plan.id"
          class="venue-plan-option"
          :class="{ 'plan-recommended': plan.id === recommendedPlan }"
        >
          <div class="plan-header">
            <strong>{{ plan.name }}</strong>
            <BaseBadge v-if="plan.id === recommendedPlan" variant="primary" size="sm">
              Recommended
            </BaseBadge>
          </div>
          <p class="plan-price">{{ plan.monthlyDisplay }}/month</p>
          <p class="plan-tagline">{{ plan.tagline }}</p>
          
          <ul class="plan-features-compact">
            <li v-for="(feature, idx) in plan.features.slice(0, 3)" :key="idx">
              • {{ feature }}
            </li>
            <li v-if="plan.features.length > 3" class="more-features">
              + {{ plan.features.length - 3 }} more features
            </li>
          </ul>
          
          <BaseButton
            :variant="plan.id === recommendedPlan ? 'primary' : 'ghost'"
            size="sm"
            @click="handleUpgrade(plan.id)"
          >
            {{ plan.isContactSales ? 'Contact Sales' : 'Upgrade Ground' }}
          </BaseButton>
        </div>
      </div>
      
      <div v-else class="loading-state">
        Loading venue plans...
      </div>
      
      <router-link to="/pricing" class="view-all-plans">
        View all pricing →
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePricingStore } from '@/stores/pricingStore'
import { BaseButton, BaseBadge } from '@/components'

// ============================================================================
// Props
// ============================================================================

interface Props {
  /** Customizable tagline (defaults to generic venue message) */
  tagline?: string
  /** Recommended plan ID (defaults to 'venue-scoring-pro') */
  recommendedPlan?: string
}

const props = withDefaults(defineProps<Props>(), {
  tagline: 'Remove branding, add your logo, and unlock professional broadcast features.',
  recommendedPlan: 'venue-scoring-pro',
})

// ============================================================================
// Setup
// ============================================================================

const pricingStore = usePricingStore()
const router = useRouter()

// ============================================================================
// Actions
// ============================================================================

function handleUpgrade(planId: string) {
  const plan = pricingStore.getPlanById(planId)
  
  if (plan?.isContactSales) {
    // Contact sales flow
    const email = 'sales@cricksy.ai'
    const subject = `Venue Upgrade: ${plan.name}`
    const body = `Hi,\n\nI'm interested in upgrading my cricket ground with ${plan.name}.\n\nPlease contact me with more details.\n\nThanks`
    window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  } else {
    // Navigate to pricing page with plan preselected
    router.push({ path: '/pricing', query: { plan: planId, type: 'venue' } })
  }
}
</script>

<style scoped>
.venue-upgrade-cta {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 2rem;
  color: white;
  margin: 2rem 0;
}

.upgrade-content {
  max-width: 900px;
  margin: 0 auto;
  text-align: center;
}

.upgrade-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.upgrade-content h3 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.upgrade-tagline {
  font-size: 1rem;
  opacity: 0.9;
  margin-bottom: 2rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.venue-plans {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.venue-plan-option {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.venue-plan-option:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-2px);
}

.plan-recommended {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.plan-header strong {
  font-size: 1.25rem;
}

.plan-price {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.plan-tagline {
  font-size: 0.875rem;
  opacity: 0.9;
  margin-bottom: 1rem;
  min-height: 2.5rem;
}

.plan-features-compact {
  list-style: none;
  padding: 0;
  margin-bottom: 1rem;
  text-align: left;
  font-size: 0.875rem;
}

.plan-features-compact li {
  margin-bottom: 0.25rem;
  opacity: 0.9;
}

.more-features {
  font-style: italic;
  opacity: 0.7;
}

.loading-state {
  padding: 2rem;
  opacity: 0.8;
}

.view-all-plans {
  display: inline-block;
  margin-top: 1rem;
  color: white;
  text-decoration: none;
  font-weight: 600;
  opacity: 0.9;
  transition: opacity 0.2s;
}

.view-all-plans:hover {
  opacity: 1;
  text-decoration: underline;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .venue-upgrade-cta {
    padding: 1.5rem;
  }

  .venue-plans {
    grid-template-columns: 1fr;
  }

  .upgrade-icon {
    font-size: 2rem;
  }

  .upgrade-content h3 {
    font-size: 1.5rem;
  }
}
</style>
