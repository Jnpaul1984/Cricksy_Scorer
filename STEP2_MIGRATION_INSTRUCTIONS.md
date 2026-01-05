"""
MIGRATION SCRIPT: Update _check_feature_access calls

After updating the _check_feature_access function signature to include db parameter,
update all 11 call sites in coach_pro_plus.py:

FIND:    if not await _check_feature_access(current_user, "
REPLACE: if not await _check_feature_access(db, current_user, "

Lines to update (approximate):
- Line 186
- Line 246
- Line 295
- Line 356
- Line 404
- Line 446
- Line 512
- Line 579
- Line 712
- Line 900
- Line 1238

Use global find/replace in your editor:
1. Open backend/routes/coach_pro_plus.py
2. Find: `_check_feature_access(current_user,`
3. Replace with: `_check_feature_access(db, current_user,`
4. Replace All (11 occurrences)

This updates all feature access checks to use the new entitlement service.
"""
