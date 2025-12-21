# Frontend Coach Pro Plus Implementation Summary

## Overview
Successfully integrated Coach Pro Plus ($19.99/month) tier into the Cricksy Scorer frontend, including pricing display, authentication role handling, and feature gating via role precedence.

**Status:** ✅ COMPLETE

---

## Changes Made

### 1. **frontend/src/types/auth.ts** - Add UserRole Type
**Purpose:** Extend TypeScript types to recognize coach_pro_plus role

**Changes:**
```typescript
// BEFORE:
export type UserRole = 'free' | 'player_pro' | 'coach_pro' | 'analyst_pro' | 'org_pro' | 'superuser'

// AFTER:
export type UserRole =
  | 'free'
  | 'player_pro'
  | 'coach_pro'
  | 'coach_pro_plus'  // ← ADDED
  | 'analyst_pro'
  | 'org_pro'
  | 'superuser'
```

**Impact:** TypeScript now recognizes `coach_pro_plus` as valid UserRole value throughout frontend

---

### 2. **frontend/src/stores/authStore.ts** - Update Role Precedence

**Purpose:** Implement >= tier logic so coach_pro_plus users satisfy all coach_pro checks

**Changes Made:**

#### A. Add isCoachProPlus Getter
```typescript
// NEW GETTER (Line 36):
isCoachProPlus: (state) => state.user?.role === 'coach_pro_plus' || isSuperuser(state),
```

#### B. Update isCoachPro to Include coach_pro_plus
```typescript
// BEFORE:
isCoachPro: (state) => state.user?.role === 'coach_pro' || isSuperuser(state),

// AFTER:
isCoachPro: (state) => state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || isSuperuser(state),
```

#### C. Update canScore to Include coach_pro_plus
```typescript
// BEFORE:
canScore: (state) =>
  isSuperuser(state) || state.user?.role === 'coach_pro' || state.user?.role === 'org_pro',

// AFTER:
canScore: (state) =>
  isSuperuser(state) || state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || state.user?.role === 'org_pro',
```

#### D. Update isCoach Legacy Helper
```typescript
// BEFORE:
isCoach: (state) => state.user?.role === 'coach_pro' || isSuperuser(state),

// AFTER:
isCoach: (state) => state.user?.role === 'coach_pro' || state.user?.role === 'coach_pro_plus' || isSuperuser(state),
```

**Impact:**
- coach_pro_plus users are treated as >= coach_pro tier
- Existing coach_pro checks automatically include coach_pro_plus users
- Router guards (requiresCoach) automatically allow coach_pro_plus users
- No changes needed to router guards themselves

---

### 3. **frontend/src/views/PricingPageView.vue** - Add Coach Pro Plus Plan Card

**Purpose:** Display Coach Pro Plus ($19.99/month) on pricing page with video features

**Changes:**

#### A. Add Plan Definition (Lines 221-233)
```typescript
{
  id: 'coach-pro-plus',
  name: 'Coach Pro Plus',
  shortName: 'Coach+',
  tagline: 'Coach Pro with video session management and AI insights.',
  monthly: 19.99,
  ctaLabel: 'Choose Coach Pro Plus',
  features: [
    'Everything in Coach Pro',
    'Video session upload & streaming',
    'AI video session reports',
    '25 GB video storage',
    'Video playlist organization',
  ],
},
```

**Placement:** Between Coach Pro ($9.99) and Analyst Pro ($14.99) in plan order

#### B. Update Feature Matrix Order (Line 389)
```typescript
// BEFORE:
const order = [
  'free',
  'player-pro',
  'coach-pro',
  'analyst-pro',
  'org-starter',
  'org-growth',
  'org-elite',
] as const

// AFTER:
const order = [
  'free',
  'player-pro',
  'coach-pro',
  'coach-pro-plus',  // ← ADDED
  'analyst-pro',
  'org-starter',
  'org-growth',
  'org-elite',
] as const
```

#### C. Update Trial Info Function (Line 352)
```typescript
// BEFORE:
case 'player-pro':
case 'coach-pro':
case 'analyst-pro':
  return { trialLabel: '14-day free trial' }

// AFTER:
case 'player-pro':
case 'coach-pro':
case 'coach-pro-plus':  // ← ADDED
case 'analyst-pro':
  return { trialLabel: '14-day free trial' }
```

**Impact:**
- Coach Pro Plus displays on pricing page with clear video feature differentiation
- Appears between Coach Pro and Analyst Pro (logical tier progression)
- Consistent styling with existing plan cards
- 14-day free trial applied
- Included in feature comparison matrix

---

### 4. **frontend/src/router/index.ts** - No Changes Required ✅

**Reason:** Router already uses `auth.isCoach` and `auth.isAnalyst` getters (not hardcoded role checks), so automatically supports coach_pro_plus after authStore updates.

**Confirmed Guard Logic:**
```typescript
// Coach-protected routes:
if (to.meta.requiresCoach) {
  if (!auth.isCoach && !auth.isOrg && !auth.isSuper) {
    return next('/')  // auth.isCoach now includes coach_pro_plus ✅
  }
}
```

---

## Feature Gating via Role Precedence

The implementation uses **implicit feature gating** based on role hierarchy:

| Feature | Free | Player Pro | Coach Pro | Coach Pro Plus | Analyst Pro | Org Pro |
|---------|------|-----------|-----------|---|-----------|---------|
| Video Upload | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Video Streaming | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| AI Session Reports | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 25GB Storage | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Coach Tools | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |

**Backend Protection:** Feature gating is enforced server-side via:
- `billing_service.require_feature('video_upload_enabled')` dependency in routes
- Prevents access even if frontend doesn't gate properly

---

## Frontend-Backend Alignment

### Role ID Mapping
| Frontend | Backend | Status |
|----------|---------|--------|
| coach_pro_plus (TypeScript) | coach_pro_plus (Python enum) | ✅ Matched |

### Plan ID Mapping
| Frontend ID | Backend ID | Plan Price | Trial |
|-------------|-----------|-----------|-------|
| coach-pro-plus (kebab-case) | coach_pro_plus (snake_case) | $19.99/month | 14 days |

**Note:** `goToSignup(planId)` passes plan ID as query parameter to signup route; backend handles ID normalization via API contract.

---

## Testing Checklist

- [x] TypeScript types updated (coach_pro_plus in UserRole union)
- [x] Auth store getters recognize coach_pro_plus role
- [x] isCoachProPlus getter created
- [x] isCoachPro returns true for coach_pro_plus users
- [x] canScore includes coach_pro_plus
- [x] isCoach includes coach_pro_plus (router guard support)
- [x] Coach Pro Plus card displays on pricing page
- [x] Plan features clearly differentiate from Coach Pro
- [x] Feature matrix includes coach-pro-plus
- [x] Trial info applies 14-day free trial
- [x] Signup CTA links correctly to plan
- [x] No router guard changes needed
- [ ] E2E test: User with coach_pro_plus role can access video upload (requires backend setup)

---

## Deployment Notes

1. **No Database Migration Required:** coach_pro_plus is already added to backend RoleEnum; users can be assigned this role immediately via API

2. **Feature Access Timeline:**
   - Tier tier displays: Immediate (pricing page live)
   - Video features: Available once backend video upload routes deployed
   - Feature gating: Backend enforces; frontend role precedence ensures consistency

3. **Backward Compatibility:** All existing role checks are preserved; coach_pro_plus is additive (doesn't break existing logic)

---

## Files Modified

1. [frontend/src/types/auth.ts](frontend/src/types/auth.ts) - UserRole type (1 line added)
2. [frontend/src/stores/authStore.ts](frontend/src/stores/authStore.ts) - 4 getters updated, 1 new getter added (5 lines added/modified)
3. [frontend/src/views/PricingPageView.vue](frontend/src/views/PricingPageView.vue) - Plan card, feature matrix, trial info (20+ lines added)

---

## Diff Summary

**Total Changes:**
- 1 new getter (isCoachProPlus)
- 3 updated getters (isCoachPro, canScore, isCoach)
- 1 new plan definition (coach-pro-plus)
- 1 updated feature matrix order
- 1 updated trial info switch case
- 1 new TypeScript type union member

**Lines Added:** ~35 lines (plan definition + getters + matrix updates)
**Lines Deleted:** 0
**Files Modified:** 3

---

## Related Backend Implementation

Coach Pro Plus backend tier is already implemented (see [BACKEND_COACH_PRO_PLUS_IMPLEMENTATION.md](BACKEND_COACH_PRO_PLUS_IMPLEMENTATION.md)):
- ✅ RoleEnum extended with coach_pro_plus
- ✅ PLAN_FEATURES defined with $19.99 pricing and video features
- ✅ Feature gating helpers implemented (get_user_plan_id, get_user_features, user_has_feature, require_feature)
- ✅ Tests passing (10/10)
- ✅ /billing/plans endpoint returns coach_pro_plus

Frontend implementation now completes the integration loop, allowing users to select and use Coach Pro Plus tier.

---

## Next Steps (Optional)

1. **Video Feature Components** (if not yet built):
   - VideoUploadView.vue - Gated behind isCoachProPlus
   - VideoPlaylistComponent.vue - Display user's video sessions
   - AISessionReportComponent.vue - Show AI-generated insights

2. **UI Polish** (optional):
   - Add "Video-Enabled" or "NEW" badge to Coach Pro Plus card
   - Highlight video features with icon/color distinction in plan card
   - Show storage quota in subscription info sidebar

3. **Upgrade Flow** (future):
   - Add "Upgrade to Plus" button in Coach Pro UI when video features attempted
   - Pre-select coach-pro-plus in upgrade flow from coach-pro

---

## Summary

Frontend integration of Coach Pro Plus is **complete**. The tier is now:
- Recognized by TypeScript type system
- Displayed on pricing page with clear feature differentiation
- Handled by auth role precedence (coach_pro_plus >= coach_pro)
- Automatically granted access to coach-protected routes
- Ready for backend video feature routes to be implemented

Users can now sign up for or upgrade to Coach Pro Plus ($19.99/month) and will receive video upload/streaming features once backend video routes are deployed.
