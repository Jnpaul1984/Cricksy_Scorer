// frontend/src/services/pricingApi.ts
// Typed API client for Cricksy pricing endpoints
// Consumes backend/routes/pricing.py - SINGLE SOURCE OF TRUTH

import { API_BASE } from './api';

// ============================================================================
// Type Definitions (mirror backend/config/pricing.py)
// ============================================================================

export type IndividualPlan =
  | 'free_scoring'
  | 'player_pro'
  | 'coach_pro'
  | 'coach_pro_plus'
  | 'coach_live_ai'
  | 'coach_live_ai_advanced'
  | 'analyst_pro'
  | 'org_pro';

export type VenuePlan =
  | 'venue_scoring_pro'
  | 'venue_broadcast_plus'
  | 'league_license';

export interface PlanPricing {
  monthly_usd: string; // Decimal as string (e.g., "19.99")
  name: string;
  tagline: string;
}

export interface IndividualEntitlements {
  scoring_access: boolean; // CRITICAL: Always true for individuals
  live_scoring?: boolean;
  player_dashboard?: boolean;
  coach_dashboard?: boolean;
  coaching_notes?: boolean;
  video_sessions_enabled?: boolean;
  video_upload_enabled?: boolean;
  video_analysis_enabled?: boolean;
  ai_session_reports_enabled?: boolean;
  video_storage_gb?: number;
  analyst_workspace?: boolean;
  ai_dismissal_patterns?: boolean;
  csv_json_export?: boolean;
  org_level_management?: boolean;
  [key: string]: boolean | number | undefined; // Allow dynamic features
}

export interface VenueEntitlements {
  branding_removal?: boolean;
  custom_logo?: boolean;
  fullscreen_scoreboard?: boolean;
  broadcast_layouts?: boolean;
  multi_camera_support?: boolean;
  led_integration?: boolean;
  custom_overlays?: boolean;
  [key: string]: boolean | number | undefined;
}

export interface IndividualPlanDetails {
  plan_id: IndividualPlan;
  pricing: PlanPricing;
  entitlements: IndividualEntitlements;
}

export interface VenuePlanDetails {
  plan_id: VenuePlan;
  pricing: PlanPricing;
  entitlements: VenueEntitlements;
}

export interface AllPricingResponse {
  individual_plans: IndividualPlanDetails[];
  venue_plans: VenuePlanDetails[];
  scoring_is_free: boolean; // CRITICAL guarantee from backend
  contract_version: string;
  last_updated: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all pricing plans (individual + venue)
 * @returns All plans with pricing and entitlements
 * @throws Error if API call fails
 */
export async function getAllPricing(): Promise<AllPricingResponse> {
  const response = await fetch(`${API_BASE}/pricing`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch pricing: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch specific individual plan details
 * @param planId - Individual plan identifier
 * @returns Plan pricing and entitlements
 */
export async function getIndividualPlan(planId: IndividualPlan): Promise<IndividualPlanDetails> {
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
export async function getVenuePlan(planId: VenuePlan): Promise<VenuePlanDetails> {
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
export function planIdToSlug(planId: string): string {
  return planId.replace(/_/g, '-');
}

/**
 * Convert frontend slug back to backend plan_id
 * @example "coach-pro-plus" → "coach_pro_plus"
 */
export function slugToPlanId(slug: string): string {
  return slug.replace(/-/g, '_');
}

/**
 * Format monthly price for display
 * @param monthlyUsd - Price as Decimal string ("19.99")
 * @returns Formatted price ("$19.99")
 */
export function formatPrice(monthlyUsd: string): string {
  const price = parseFloat(monthlyUsd);
  if (price === 0) return '$0';
  return `$${price.toFixed(2)}`;
}

/**
 * Calculate annual price with discount
 * @param monthlyUsd - Monthly price as string
 * @param discountMonths - Number of months free (default: 2)
 * @returns Annual price
 */
export function calculateAnnualPrice(monthlyUsd: string, discountMonths: number = 2): number {
  const monthly = parseFloat(monthlyUsd);
  return monthly * (12 - discountMonths);
}
