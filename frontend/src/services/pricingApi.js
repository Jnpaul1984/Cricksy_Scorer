// frontend/src/services/pricingApi.ts
// Typed API client for Cricksy pricing endpoints
// Consumes backend/routes/pricing.py - SINGLE SOURCE OF TRUTH
import { API_BASE } from './api';
// ============================================================================
// API Functions
// ============================================================================
/**
 * Fetch all pricing plans (individual + venue)
 * @returns All plans with pricing and entitlements
 * @throws Error if API call fails
 */
export async function getAllPricing() {
    const url = `${API_BASE}/pricing`;
    // Production-grade logging
    console.log('🔍 Fetching pricing from:', url);
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        console.log('📡 Pricing API response status:', response.status, response.statusText);
        if (!response.ok) {
            // Read response body for debugging
            const errorText = await response.text().catch(() => 'Unable to read response');
            const errorPreview = errorText.substring(0, 200);
            console.error('❌ Pricing API error:', {
                status: response.status,
                statusText: response.statusText,
                url,
                preview: errorPreview
            });
            throw new Error(`Pricing API returned ${response.status}: ${errorPreview}`);
        }
        const data = await response.json();
        // Validate response shape
        if (!data.individual_plans || !Array.isArray(data.individual_plans)) {
            console.error('❌ Invalid pricing response - missing individual_plans array:', data);
            throw new Error('Invalid pricing response format');
        }
        if (!data.venue_plans || !Array.isArray(data.venue_plans)) {
            console.error('❌ Invalid pricing response - missing venue_plans array:', data);
            throw new Error('Invalid pricing response format');
        }
        console.log('✅ Pricing loaded:', {
            individualPlans: data.individual_plans.length,
            venuePlans: data.venue_plans.length,
            scoringIsFree: data.scoring_is_free
        });
        return data;
    }
    catch (error) {
        // Re-throw with context
        if (error instanceof Error) {
            console.error('❌ Pricing fetch failed:', error.message);
            throw error;
        }
        throw new Error('Unknown error fetching pricing');
    }
}
/**
 * Fetch specific individual plan details
 * @param planId - Individual plan identifier
 * @returns Plan pricing and entitlements
 */
export async function getIndividualPlan(planId) {
    const response = await fetch(`${API_BASE}/pricing/individual/${planId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!response.ok) {
        throw new Error(`Failed to fetch plan ${planId}: ${response.status} ${response.statusText}`);
    }
    return response.json();
}
/**
 * Fetch specific venue plan details
 * @param planId - Venue plan identifier
 * @returns Plan pricing and entitlements
 */
export async function getVenuePlan(planId) {
    const response = await fetch(`${API_BASE}/pricing/venue/${planId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!response.ok) {
        throw new Error(`Failed to fetch venue plan ${planId}: ${response.status} ${response.statusText}`);
    }
    return response.json();
}
// ============================================================================
// Helper Functions
// ============================================================================
/**
 * Convert backend plan_id to frontend-friendly slug
 * @example "coach_pro_plus" → "coach-pro-plus"
 */
export function planIdToSlug(planId) {
    return planId.replace(/_/g, '-');
}
/**
 * Convert frontend slug back to backend plan_id
 * @example "coach-pro-plus" → "coach_pro_plus"
 */
export function slugToPlanId(slug) {
    return slug.replace(/-/g, '_');
}
/**
 * Format monthly price for display
 * @param monthlyUsd - Price as Decimal string ("19.99")
 * @returns Formatted price ("$19.99")
 */
export function formatPrice(monthlyUsd) {
    const price = parseFloat(monthlyUsd);
    if (price === 0)
        return '$0';
    return `$${price.toFixed(2)}`;
}
/**
 * Calculate annual price with discount
 * @param monthlyUsd - Monthly price as string
 * @param discountMonths - Number of months free (default: 2)
 * @returns Annual price
 */
export function calculateAnnualPrice(monthlyUsd, discountMonths = 2) {
    const monthly = parseFloat(monthlyUsd);
    return monthly * (12 - discountMonths);
}
