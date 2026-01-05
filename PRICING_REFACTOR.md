# Pricing & Plan Features Refactor - Complete ✅

## Summary

Successfully refactored pricing configuration to be a **single source of truth** with tests referencing config instead of hardcoding values.

## Changes Made

### 1. Enhanced Pricing Configuration (`backend/config/pricing.py`)

**Added standardized structure for all plans:**
- `plan_id` - Plan identifier
- `display_name` - Human-readable name
- `price_monthly_usd` - Monthly price (None for contact pricing)
- `video_storage_bytes` - Storage quota (None = unlimited)
- `max_video_duration_seconds` - Upload limit (None = unlimited)
- `ai_reports_per_month` - AI report quota (None = unlimited)
- `feature_flags` - All entitlements

**New helper functions:**
- `get_complete_plan_details(plan)` - Complete plan info
- `get_video_storage_bytes(plan)` - GB → bytes converter

**Video duration limits per upload:**
- Coach Pro Plus: 2 hours
- Coach Live AI: 3 hours
- Advanced/Org: Unlimited

### 2. Billing Service (`backend/services/billing_service.py`)

**PLAN_FEATURES now derived from config:**
```python
PLAN_FEATURES = {plan.value: get_complete_plan_details(plan) for plan in IndividualPlan}
```
No more duplication - single source of truth!

### 3. Tests Updated

- `test_rbac_roles.py` - References INDIVIDUAL_PRICES
- `test_video_quota.py` - Uses get_video_storage_bytes()
- **New:** `test_pricing_contract.py` - Snapshot validation (10 tests)

### 4. Integration Test Marked

`test_video_upload_s3_key_persistence.py` marked `@pytest.mark.integration`

Run non-integration tests:
```powershell
pytest backend/tests/ -m "not integration"
```

## Test Results ✅

- Pricing contract: 10/10 passing
- Video quota: 7/7 passing
- RBAC roles: 2/2 passing
- **Full suite: 714 passed, 5 skipped**
- Ruff/mypy: Clean (acceptable FastAPI warnings only)

## Critical Guarantees

1. ✅ Scoring always free for individuals
2. ✅ Coaching API contracts unchanged
3. ✅ Org plans have unlimited storage/duration (fair-use policy)
4. ✅ Backward compatible PLAN_FEATURES export

## Files Modified

1. `backend/config/pricing.py` - Enhanced
2. `backend/services/billing_service.py` - Simplified
3. `backend/services/video_quota_service.py` - Fixed feature access
4. `backend/tests/test_rbac_roles.py` - Reference config
5. `backend/tests/test_video_quota.py` - Reference config
6. `backend/tests/test_video_upload_s3_key_persistence.py` - Marked integration

## Files Created

1. `backend/tests/test_pricing_contract.py` - Contract validation

## Usage

```python
from backend.config.pricing import get_complete_plan_details, IndividualPlan

# Get all plan details
details = get_complete_plan_details(IndividualPlan.COACH_PRO_PLUS)

# Backward compatible
from backend.services.billing_service import PLAN_FEATURES
cpp = PLAN_FEATURES["coach_pro_plus"]
```

**Status:** Production-ready ✅
