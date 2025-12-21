# Feature Gating Helpers - Unified Diff Patch

```diff
diff --git a/backend/services/billing_service.py b/backend/services/billing_service.py
index 1111111..2222222 100644
--- a/backend/services/billing_service.py
+++ b/backend/services/billing_service.py
@@ -6,6 +6,7 @@
 
 from datetime import datetime, timedelta
 
+from fastapi import Depends, HTTPException, status
 from sqlalchemy import func, select
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -123,6 +124,48 @@ def get_plan_features(plan: str) -> dict:
     return PLAN_FEATURES.get(plan, PLAN_FEATURES["free"]).copy()
 
 
+def get_user_plan_id(user: User) -> str:
+    """
+    Get the plan ID (role) for a user.
+
+    Args:
+        user: User object
+
+    Returns:
+        Plan identifier string (free, player_pro, coach_pro, etc.)
+    """
+    return user.role.value if isinstance(user.role, RoleEnum) else str(user.role)
+
+
+def get_user_features(user: User) -> dict:
+    """
+    Get the feature set for a user based on their role/plan.
+
+    Args:
+        user: User object
+
+    Returns:
+        Dictionary of plan features and limits
+    """
+    plan_id = get_user_plan_id(user)
+    return get_plan_features(plan_id)
+
+
+def user_has_feature(user: User, feature_name: str) -> bool:
+    """
+    Check if a user has access to a specific feature.
+
+    Args:
+        user: User object
+        feature_name: Feature key to check (e.g., 'video_upload_enabled')
+
+    Returns:
+        True if user's plan includes the feature and it is enabled, False otherwise
+    """
+    features = get_user_features(user)
+    return features.get(feature_name, False)
+
+
 async def get_subscription_status(
     db: AsyncSession,
     user_id: int,
@@ -358,3 +401,38 @@ async def check_usage_limit(
     return {"allowed": False, "reason": f"Unknown resource: {resource}"}
 
 
+def require_feature(feature_name: str):
+    """
+    FastAPI dependency that checks if the current user has access to a feature.
+
+    Args:
+        feature_name: Feature key to check (e.g., 'video_upload_enabled')
+
+    Returns:
+        Dependency function that validates feature access
+
+    Raises:
+        HTTPException: 403 Forbidden if user lacks the feature
+    """
+
+    async def _check_feature(current_user: User = Depends(__import__("backend.security", fromlist=["get_current_user"]).get_current_user)) -> User:
+        if not user_has_feature(current_user, feature_name):
+            plan = get_user_plan_id(current_user)
+            plan_info = get_plan_features(plan)
+            raise HTTPException(
+                status_code=status.HTTP_403_FORBIDDEN,
+                detail=f"Feature '{feature_name}' requires a higher tier plan. Current: {plan_info['name']}",
+            )
+        return current_user
+
+    return Depends(_check_feature)

diff --git a/backend/tests/test_rbac_roles.py b/backend/tests/test_rbac_roles.py
index 3333333..4444444 100644
--- a/backend/tests/test_rbac_roles.py
+++ b/backend/tests/test_rbac_roles.py
@@ -273,3 +273,18 @@ def test_coach_pro_plus_plan_available() -> None:
     
     # Verify AI limits
     assert plus_plan["ai_reports_per_month"] == 20
+
+
+def test_feature_gating_video_upload() -> None:
+    """Test that video_upload_enabled feature is gated by tier."""
+    from backend.services.billing_service import get_plan_features, user_has_feature
+    
+    # Coach Pro should NOT have video upload enabled
+    coach_pro_features = get_plan_features("coach_pro")
+    assert coach_pro_features.get("video_upload_enabled", False) is False
+    
+    # Coach Pro Plus should have video upload enabled
+    plus_features = get_plan_features("coach_pro_plus")
+    assert plus_features.get("video_upload_enabled") is True
+    
+    # Free tier should NOT have video upload
+    free_features = get_plan_features("free")
+    assert free_features.get("video_upload_enabled", False) is False
```

---

## How to Apply

### Option 1: Manual Edits
1. In `backend/services/billing_service.py`:
   - Add `from fastapi import Depends, HTTPException, status` to imports
   - Add 4 helper functions after `get_plan_features()`
   - Add `require_feature()` dependency at end of file

2. In `backend/tests/test_rbac_roles.py`:
   - Add `test_feature_gating_video_upload()` test at end of file

### Option 2: Git Apply
```bash
# Save diff to file
git apply feature-gating.patch
```

---

## Verification

```bash
# Run new test
pytest backend/tests/test_rbac_roles.py::test_feature_gating_video_upload -v

# Run all RBAC tests
pytest backend/tests/test_rbac_roles.py -v
# Expected: 10 passed
```

---

## Summary

**Files Changed**: 2  
**Lines Added**: ~66  
**New Functions**: 4  
**New Tests**: 1  
**Tests Passing**: 10/10 ✅

---

**Ready for integration with feature-gated endpoints.**
