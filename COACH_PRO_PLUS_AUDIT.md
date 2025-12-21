# Coach Pro Plus Tier Implementation - File Audit

**Status**: PRE-IMPLEMENTATION AUDIT  
**Tier**: Coach Pro Plus ($19.99/month)  
**Branch**: `feat/coach-pro-plus-tier`  
**Date**: December 21, 2025  

---

## 1. EXACT FILES THAT MUST BE EDITED

### BACKEND FILES (Required)

| File | Current State | Required Changes |
|------|---------------|------------------|
| **`backend/sql_app/models.py`** | RoleEnum has 6 entries (free, player_pro, coach_pro, analyst_pro, org_pro, superuser - implicit) | ADD: `coach_pro_plus = "coach_pro_plus"` after line 60 |
| **`backend/services/billing_service.py`** | PLAN_FEATURES dict has 6 keys (free, player_pro, coach_pro, analyst_pro, org_pro, superuser) | ADD: `"coach_pro_plus"` entry with $19.99 pricing + video features |
| **`backend/security.py`** | Lines 242-243 have `coach_or_org_required` and `analyst_or_org_required` | ADD: `coach_pro_plus_only = Depends(require_roles(["coach_pro_plus"]))` |
| **`backend/routes/coach_pro.py`** | Lines 51, 98, 115, 135, 180: checks `RoleEnum.coach_pro` OR hardcoded require_roles(["coach_pro", "org_pro"]) | UPDATE: Add `coach_pro_plus` to all role checks (6 locations) |
| **`backend/routes/billing.py`** | GET /billing/plans, GET /billing/subscription endpoints | VERIFY: Returns coach_pro_plus in plan list (should auto-work via PLAN_FEATURES) |

### FRONTEND FILES (Required)

| File | Current State | Required Changes |
|------|---------------|------------------|
| **`frontend/src/types/auth.ts`** | UserRole type union has 6 values (free, player_pro, coach_pro, analyst_pro, org_pro, superuser) | ADD: `\| 'coach_pro_plus'` to line 2-7 |
| **`frontend/src/stores/authStore.ts`** | Lines 36-48: getters for isCoachPro, isAnalystPro, etc. | ADD: `isCoachProPlus: (state) => state.user?.role === 'coach_pro_plus' \|\| isSuperuser(state)` |
| **`frontend/src/views/PricingPageView.vue`** | Plans array starts line 172, Coach Pro is at id: 'coach-pro' line 205 | ADD: New plan object after Coach Pro with id: 'coach-pro-plus', monthly: 19.99, features for video sessions |
| **`frontend/src/router/index.ts`** | May have role-based redirects | CHECK: Update any coach-specific redirects to allow coach_pro_plus |

### OPTIONAL/FUTURE FILES

| File | Purpose | Action |
|------|---------|--------|
| `backend/routes/coach_pro_plus.py` | NEW file for Plus-only endpoints | DEFER: Not needed for MVP (Plus users access same coach_pro.py routes) |
| `backend/services/video_service.py` | Video upload/streaming | DEFER: Implementation phase 2 |
| `frontend/src/components/CoachingSessionVideoUploader.vue` | Video UI component | DEFER: Implementation phase 2 |
| `frontend/src/types/pricing.ts` | Advanced pricing types | DEFER: Not needed if using simple plan objects |

---

## 2. TESTS THAT MUST BE ADDED/UPDATED

### Backend Tests (Required)

| Test File | Location | Current State | Required Change |
|-----------|----------|----------------|-----------------|
| **`backend/tests/test_rbac_roles.py`** | Lines 102-195 | Tests for free, coach_pro, org_pro roles | ADD: Test case for coach_pro_plus role (copy coach_pro test, rename) |
| **`backend/tests/test_coach_pro_features.py`** | Entire file | Tests coach_pro features | ADD: Section or new file `test_coach_pro_plus_features.py` testing Plus tier features |
| **`backend/tests/test_billing.py`** | (if exists) | Tests PLAN_FEATURES access | ADD: Assert coach_pro_plus in PLAN_FEATURES with correct pricing ($19.99) |

### Frontend Tests (Optional but Recommended)

| Test File | Purpose | Action |
|-----------|---------|--------|
| `frontend/cypress/e2e/pricing.cy.ts` | E2E pricing page | ADD: Check Coach Pro Plus card visible, pricing correct |
| `frontend/tests/unit/authStore.spec.ts` | Auth store getters | ADD: Test isCoachProPlus getter returns true for coach_pro_plus role |

---

## 3. CRITICAL PITFALLS & GOTCHAS

### Enum & Naming
- ⚠️ **Naming Convention**: Use `coach_pro_plus` (underscore) everywhere in backend, `coach-pro-plus` (hyphen) only in frontend IDs/URLs
- ⚠️ **RoleEnum Value**: Must be string: `coach_pro_plus = "coach_pro_plus"` (not `"coach_pro+plus"` or `"CoachProPlus"`)
- ⚠️ **PLAN_FEATURES Key**: Must exactly match RoleEnum value: `"coach_pro_plus"` (the dict key)

### Role Checks
- ⚠️ **6 Locations in coach_pro.py**: Lines 51, 98, 115, 135, 180 all check `RoleEnum.coach_pro` or `require_roles(["coach_pro", "org_pro"])`
  - Line 51 `_ensure_coach_user`: `if coach.role not in (RoleEnum.coach_pro, RoleEnum.org_pro)` → ADD `RoleEnum.coach_pro_plus`
  - Lines 94, 110, 131, 173 `require_roles(["coach_pro", "org_pro"])` → ADD `"coach_pro_plus"` to list
  - Lines 98, 115, 135, 180: `if current_user.role == RoleEnum.coach_pro` → Need UPDATE to handle Plus (see below)

### Coach Pro vs Coach Pro Plus Differentiation
- ⚠️ **Scope Creep Risk**: Lines 98, 115, 135, 180 in coach_pro.py use `if current_user.role == RoleEnum.coach_pro` (exact match)
  - This filters results to only that user's coach assignments
  - **coach_pro_plus users should get SAME filtering** (their assignments, not all)
  - Change lines 98, 115, 135, 180 from `==` to `in (RoleEnum.coach_pro, RoleEnum.coach_pro_plus)` OR use a helper function

### Pricing Consistency
- ⚠️ **Price Mismatch Risk**: Coach Pro is $9.99 in PLAN_FEATURES but user can set arbitrary prices in PricingPageView
  - **Verify**: PricingPageView shows Coach Pro as 9.99 (line 210), Coach Pro Plus should show 19.99 (NOT 10 or 29.99)
  - **Check**: No hardcoded pricing in backend routes (should use PLAN_FEATURES[role].price_monthly)

### Feature Flags
- ⚠️ **Video Features Required**: coach_pro_plus needs new PLAN_FEATURES flags:
  ```python
  "video_upload_enabled": True,        # NEW
  "video_analysis_enabled": True,      # NEW
  "clip_creation_enabled": True,       # NEW
  "storage_quota_gb": 500,             # NEW
  "priority_support_tier": "plus",     # NEW (or just enhance priority_support)
  ```
  - coach_pro should have these as False (or missing if not defined)
  - Ensure routes check `check_feature_access("video_upload", user_role)` before allowing upload

### Database Migrations
- ✅ **NO MIGRATION NEEDED**: RoleEnum is just a Python enum, not a database column constraint
- ❌ **DON'T CREATE**: Alembic migration for enum (unnecessary, enum values are inferred at runtime)
- ⚠️ **User Table**: Existing coach_pro users will stay as coach_pro (no automatic upgrade)

### TypeScript Type Sync
- ⚠️ **Type Mismatch Risk**: frontend/src/types/auth.ts has UserRole type union (must include 'coach_pro_plus')
- ❌ **DON'T FORGET**: Line 4 of auth.ts lists `| 'coach_pro'` → Must ADD `| 'coach_pro_plus'`
- ✅ **Good**: Type is just a union, no code generation needed

### Decorator & Role List Updates
- ⚠️ **5 Locations in security.py/coach_pro.py require require_roles() update**:
  - Line 94: `require_roles(["coach_pro", "org_pro"])` → `require_roles(["coach_pro", "coach_pro_plus", "org_pro"])`
  - Line 110: Same
  - Line 131: Same
  - Line 173: Same
  - Consider creating `coach_pro_or_plus_required` convenience decorator to avoid repetition

### Frontend Router
- ⚠️ **CHECK**: frontend/src/router/index.ts may have role-based route guards
  - If exists: `meta: { requireRole: 'coach_pro' }` → UPDATE to include coach_pro_plus
  - If not exists: No changes needed

---

## 4. IMPLEMENTATION SEQUENCE

**Phase 1: Backend Tier Definition**
1. Update `backend/sql_app/models.py` - Add RoleEnum.coach_pro_plus
2. Update `backend/services/billing_service.py` - Add PLAN_FEATURES["coach_pro_plus"]
3. Update `backend/security.py` - Add convenience decorators
4. Update `backend/routes/coach_pro.py` - Add coach_pro_plus to all role checks (6 locations)
5. Run pytest to verify RBAC tests pass

**Phase 2: Frontend Type & Store**
6. Update `frontend/src/types/auth.ts` - Add 'coach_pro_plus' to UserRole
7. Update `frontend/src/stores/authStore.ts` - Add isCoachProPlus getter
8. Update `frontend/src/router/index.ts` - Check and update role guards if needed

**Phase 3: Frontend UI**
9. Update `frontend/src/views/PricingPageView.vue` - Add Coach Pro Plus plan card

**Phase 4: Testing**
10. Update `backend/tests/test_rbac_roles.py` - Add coach_pro_plus test case
11. Run full test suite (pytest + frontend tests)

---

## 5. CHANGES SUMMARY

### Lines Changed by File

| File | Insert Lines | Update Lines | Delete Lines | Net ± |
|------|--------------|--------------|--------------|-------|
| models.py | 1 | 0 | 0 | +1 |
| billing_service.py | 15 | 0 | 0 | +15 |
| security.py | 1 | 0 | 0 | +1 |
| coach_pro.py | 0 | 6 | 0 | ~0 |
| auth.ts | 1 | 0 | 0 | +1 |
| authStore.ts | 1 | 0 | 0 | +1 |
| PricingPageView.vue | 20 | 0 | 0 | +20 |
| test_rbac_roles.py | 15 | 0 | 0 | +15 |
| **TOTAL** | **54** | **6** | **0** | **+60** |

---

## 6. VERIFICATION CHECKLIST (Before Merging)

- [ ] RoleEnum has `coach_pro_plus` entry
- [ ] PLAN_FEATURES has `coach_pro_plus` key with pricing $19.99
- [ ] All 6 role checks in coach_pro.py include coach_pro_plus
- [ ] security.py has coach_pro_plus convenience decorators (optional but recommended)
- [ ] authStore.ts has `isCoachProPlus` getter
- [ ] auth.ts UserRole type includes 'coach_pro_plus'
- [ ] PricingPageView.vue shows Coach Pro Plus card at $19.99
- [ ] `pytest backend/tests/test_rbac_roles.py -v` passes (including coach_pro_plus test)
- [ ] `pytest backend/tests/test_coach_pro_features.py -v` passes (if exists)
- [ ] No hardcoded tier names in routes (all use PLAN_FEATURES)
- [ ] Frontend linting passes (npm run lint)
- [ ] No console errors in browser when loading pricing page

---

## 7. REFERENCE LINKS

| Item | Location |
|------|----------|
| Tier Blueprint | `TIER_ENTITLEMENT_ARCHITECTURE_BLUEPRINT.md` |
| Repo Structure | `REPOSITORY_STRUCTURE.md` |
| RoleEnum Definition | `backend/sql_app/models.py:57-65` |
| Plan Features | `backend/services/billing_service.py:13-100` |
| RBAC Decorator | `backend/security.py:228-239` |
| Coach Routes | `backend/routes/coach_pro.py` |
| Auth Store | `frontend/src/stores/authStore.ts:31-56` |
| Pricing Page | `frontend/src/views/PricingPageView.vue:172-290` |
| Auth Types | `frontend/src/types/auth.ts:1-10` |
| RBAC Tests | `backend/tests/test_rbac_roles.py` |

---

**READY FOR IMPLEMENTATION** ✅  
All files identified, pitfalls documented, test strategy defined.  
Next step: Execute Phase 1 (Backend Tier Definition).
