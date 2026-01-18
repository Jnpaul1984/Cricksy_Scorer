// frontend/src/stores/pricingStore.ts
// Pinia store for Cricksy pricing data
// Fetches from backend /pricing endpoint on app load
// SINGLE SOURCE OF TRUTH - no hardcoded prices

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

import type {
  AllPricingResponse,
  IndividualPlanDetails,
  VenuePlanDetails,
  IndividualPlan,
  VenuePlan,
} from '@/services/pricingApi';
import { getAllPricing, formatPrice, calculateAnnualPrice } from '@/services/pricingApi';

// ============================================================================
// Frontend Display Plan (extends backend data)
// ============================================================================

export interface DisplayPlan {
  id: string; // Frontend slug (e.g., "coach-pro-plus")
  backendId: string; // Backend plan_id (e.g., "coach_pro_plus")
  name: string;
  tagline: string;
  monthlyPrice: number; // Parsed float for calculations
  monthlyDisplay: string; // Formatted for display ("$19.99")
  annualPrice: number; // With discount
  annualDisplay: string;
  features: string[]; // Human-readable feature list
  ctaLabel: string;
  highlight?: boolean; // Featured plan
  isContactSales?: boolean; // Contact-only pricing
  planType: 'individual' | 'venue';
}

// ============================================================================
// Store Definition
// ============================================================================

export const usePricingStore = defineStore('pricing', () => {
  // State
  const individualPlans = ref<IndividualPlanDetails[]>([]);
  const venuePlans = ref<VenuePlanDetails[]>([]);
  const scoringIsFree = ref<boolean>(true); // CRITICAL guarantee
  const contractVersion = ref<string>('');
  const lastUpdated = ref<string>('');
  const loading = ref<boolean>(false);
  const error = ref<string | null>(null);

  // ============================================================================
  // Computed - Display Plans
  // ============================================================================

  const displayPlans = computed<DisplayPlan[]>(() => {
    const plans: DisplayPlan[] = [];

    // Individual plans
    individualPlans.value.forEach((plan) => {
      const monthlyPrice = parseFloat(plan.pricing.monthly_usd);
      const slug = plan.plan_id.replace(/_/g, '-');

      plans.push({
        id: slug,
        backendId: plan.plan_id,
        name: plan.pricing.name,
        tagline: plan.pricing.tagline,
        monthlyPrice,
        monthlyDisplay: formatPrice(plan.pricing.monthly_usd),
        annualPrice: calculateAnnualPrice(plan.pricing.monthly_usd),
        annualDisplay: formatPrice(calculateAnnualPrice(plan.pricing.monthly_usd).toFixed(2)),
        features: buildFeatureList(plan.entitlements),
        ctaLabel: monthlyPrice === 0 ? 'Start Free' : `Get ${plan.pricing.name}`,
        highlight: plan.plan_id === 'analyst_pro', // Analyst Pro is featured
        planType: 'individual',
      });
    });

    // Venue plans
    venuePlans.value.forEach((plan) => {
      const monthlyPrice = parseFloat(plan.pricing.monthly_usd);
      const slug = plan.plan_id.replace(/_/g, '-');

      plans.push({
        id: slug,
        backendId: plan.plan_id,
        name: plan.pricing.name,
        tagline: plan.pricing.tagline,
        monthlyPrice,
        monthlyDisplay: formatPrice(plan.pricing.monthly_usd),
        annualPrice: calculateAnnualPrice(plan.pricing.monthly_usd),
        annualDisplay: formatPrice(calculateAnnualPrice(plan.pricing.monthly_usd).toFixed(2)),
        features: buildVenueFeatureList(plan.entitlements),
        ctaLabel: plan.plan_id === 'league_license' ? 'Contact Sales' : `Upgrade Ground`,
        isContactSales: plan.plan_id === 'league_license',
        planType: 'venue',
      });
    });

    return plans;
  });

  const individualDisplayPlans = computed(() =>
    displayPlans.value.filter((p) => p.planType === 'individual'),
  );

  const venueDisplayPlans = computed(() =>
    displayPlans.value.filter((p) => p.planType === 'venue'),
  );

  // ============================================================================
  // Actions
  // ============================================================================

  async function fetchPricing() {
    loading.value = true;
    error.value = null;

    try {
      const response: AllPricingResponse = await getAllPricing();

      individualPlans.value = response.individual_plans;
      venuePlans.value = response.venue_plans;
      scoringIsFree.value = response.scoring_is_free;
      contractVersion.value = response.contract_version;
      lastUpdated.value = response.last_updated;

      // Cache in localStorage for offline resilience
      if (typeof window !== 'undefined') {
        localStorage.setItem('cricksy_pricing_cache', JSON.stringify(response));
        localStorage.setItem('cricksy_pricing_cached_at', new Date().toISOString());
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch pricing';
      
      // Production-grade error logging
      console.error('❌ Pricing fetch failed:', err);
      console.error('Attempted endpoint: /pricing');
      console.error('Check that backend is running and CORS is configured');
      
      if (err instanceof Error) {
        console.error('Error details:', {
          message: err.message,
          name: err.name,
          stack: err.stack?.split('\n').slice(0, 3)
        });
      }

      // Fallback to cached data if available
      if (typeof window !== 'undefined') {
        const cached = localStorage.getItem('cricksy_pricing_cache');
        if (cached) {
          const cachedData: AllPricingResponse = JSON.parse(cached);
          individualPlans.value = cachedData.individual_plans;
          venuePlans.value = cachedData.venue_plans;
          scoringIsFree.value = cachedData.scoring_is_free;
          contractVersion.value = cachedData.contract_version;
          lastUpdated.value = cachedData.last_updated;
          console.warn('✅ Using cached pricing data from:', localStorage.getItem('cricksy_pricing_cached_at'));
        } else {
          console.error('❌ No cached pricing data available. User will see empty state.');
        }
      }
    } finally {
      loading.value = false;
    }
  }

  function getPlanById(planId: string): DisplayPlan | undefined {
    return displayPlans.value.find((p) => p.id === planId || p.backendId === planId);
  }

  function getPlanByBackendId(backendId: IndividualPlan | VenuePlan): DisplayPlan | undefined {
    return displayPlans.value.find((p) => p.backendId === backendId);
  }

  // ============================================================================
  // Helper Functions - Feature List Generation
  // ============================================================================

  function buildFeatureList(entitlements: any): string[] {
    const features: string[] = [];

    // Scoring (always free for individuals)
    if (entitlements.scoring_access) {
      features.push('Manual match scoring (always free)');
    }

    // Player features
    if (entitlements.player_dashboard) {
      features.push('Full career dashboard (all formats)');
      features.push('Form tracker & season graphs');
      features.push('Strength/weakness views');
    }

    // Coach features
    if (entitlements.coach_dashboard) {
      features.push('Player development dashboard');
      features.push('Coach → Player assignment');
    }

    if (entitlements.coaching_notes) {
      features.push('Session notebook (per player, per session)');
      features.push('Multi-player comparisons');
      features.push('AI session summaries');
    }

    // Video features (Coach Pro Plus)
    if (entitlements.video_sessions_enabled) {
      features.push('Video session upload & streaming');
      features.push('AI video session reports');
      if (entitlements.video_storage_gb) {
        features.push(`${entitlements.video_storage_gb} GB video storage`);
      }
      features.push('Video playlist organization');
    }

    // Analyst features
    if (entitlements.analyst_workspace) {
      features.push('Analyst workspace & saved views');
      features.push('AI dismissal pattern detection');
      features.push('AI heatmaps & ball-type clustering');
      features.push('Phase-based analysis');
    }

    if (entitlements.csv_json_export) {
      features.push('CSV/JSON data exports');
    }

    // Org features
    if (entitlements.org_level_management) {
      features.push('League/tournament management');
      features.push('Org-level dashboards');
      features.push('Role & subscription management');
    }

    return features;
  }

  function buildVenueFeatureList(entitlements: any): string[] {
    const features: string[] = [];

    if (entitlements.branding_removal) {
      features.push('Remove Cricksy watermarks');
    }

    if (entitlements.custom_logo) {
      features.push('Custom venue logo & branding');
    }

    if (entitlements.fullscreen_scoreboard) {
      features.push('Fullscreen scoreboard display');
    }

    if (entitlements.broadcast_layouts) {
      features.push('Professional broadcast overlays');
    }

    if (entitlements.multi_camera_support) {
      features.push('Multi-camera feed support');
    }

    if (entitlements.led_integration) {
      features.push('LED screen integration');
    }

    if (entitlements.custom_overlays) {
      features.push('Custom graphics & overlays');
    }

    return features;
  }

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    individualPlans,
    venuePlans,
    scoringIsFree,
    contractVersion,
    lastUpdated,
    loading,
    error,

    // Computed
    displayPlans,
    individualDisplayPlans,
    venueDisplayPlans,

    // Actions
    fetchPricing,
    getPlanById,
    getPlanByBackendId,
  };
});
