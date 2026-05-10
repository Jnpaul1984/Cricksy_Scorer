// frontend/src/stores/pricingStore.ts
// Pinia store for Cricksy pricing data
// Fetches from backend /pricing endpoint on app load
// SINGLE SOURCE OF TRUTH - no hardcoded prices
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getAllPricing, formatPrice, calculateAnnualPrice } from '@/services/pricingApi';
// ============================================================================
// Store Definition
// ============================================================================
export const usePricingStore = defineStore('pricing', () => {
    // State
    const individualPlans = ref([]);
    const venuePlans = ref([]);
    const scoringIsFree = ref(true); // CRITICAL guarantee
    const contractVersion = ref('');
    const lastUpdated = ref('');
    const loading = ref(false);
    const error = ref(null);
    const lastFetchAttempt = ref(null);
    const httpStatus = ref(null);
    // ============================================================================
    // Computed - Display Plans
    // ============================================================================
    const displayPlans = computed(() => {
        const plans = [];
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
    const individualDisplayPlans = computed(() => displayPlans.value.filter((p) => p.planType === 'individual'));
    const venueDisplayPlans = computed(() => displayPlans.value.filter((p) => p.planType === 'venue'));
    // ============================================================================
    // Actions
    // ============================================================================
    async function fetchPricing() {
        loading.value = true;
        error.value = null;
        httpStatus.value = null;
        lastFetchAttempt.value = new Date().toISOString();
        try {
            const response = await getAllPricing();
            individualPlans.value = response.individual_plans;
            venuePlans.value = response.venue_plans;
            scoringIsFree.value = response.scoring_is_free;
            contractVersion.value = response.contract_version;
            lastUpdated.value = response.last_updated;
            httpStatus.value = 200;
            // Cache in localStorage for offline resilience
            if (typeof window !== 'undefined') {
                localStorage.setItem('cricksy_pricing_cache', JSON.stringify(response));
                localStorage.setItem('cricksy_pricing_cached_at', new Date().toISOString());
            }
        }
        catch (err) {
            // Extract HTTP status if available
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch pricing';
            const statusMatch = errorMessage.match(/returned (\d+)/);
            if (statusMatch) {
                httpStatus.value = parseInt(statusMatch[1]);
            }
            error.value = errorMessage;
            // Production-grade error logging
            console.error('❌ Pricing fetch failed:', err);
            console.error('Attempted endpoint: /pricing');
            console.error('API_BASE:', import.meta.env.VITE_API_BASE || 'not set');
            console.error('Last attempt:', lastFetchAttempt.value);
            if (err instanceof Error) {
                console.error('Error details:', {
                    message: err.message,
                    name: err.name,
                    stack: import.meta.env.DEV ? err.stack?.split('\n').slice(0, 5) : 'Hidden in production'
                });
            }
            // Fallback to cached data if available
            if (typeof window !== 'undefined') {
                const cached = localStorage.getItem('cricksy_pricing_cache');
                if (cached) {
                    try {
                        const cachedData = JSON.parse(cached);
                        individualPlans.value = cachedData.individual_plans;
                        venuePlans.value = cachedData.venue_plans;
                        scoringIsFree.value = cachedData.scoring_is_free;
                        contractVersion.value = cachedData.contract_version;
                        lastUpdated.value = cachedData.last_updated;
                        console.warn('✅ Using cached pricing data from:', localStorage.getItem('cricksy_pricing_cached_at'));
                        error.value = null; // Clear error since we have cached data
                    }
                    catch (parseError) {
                        console.error('❌ Failed to parse cached pricing:', parseError);
                    }
                }
                else {
                    console.error('❌ No cached pricing data available. User will see empty state.');
                }
            }
        }
        finally {
            loading.value = false;
        }
    }
    function getPlanById(planId) {
        return displayPlans.value.find((p) => p.id === planId || p.backendId === planId);
    }
    function getPlanByBackendId(backendId) {
        return displayPlans.value.find((p) => p.backendId === backendId);
    }
    // ============================================================================
    // Helper Functions - Feature List Generation
    // ============================================================================
    function buildFeatureList(entitlements) {
        const features = [];
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
    function buildVenueFeatureList(entitlements) {
        const features = [];
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
        httpStatus,
        lastFetchAttempt,
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
