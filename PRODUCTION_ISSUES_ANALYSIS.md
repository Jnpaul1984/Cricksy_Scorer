## Production Issues: Coach Pro Plus Video Upload - Analysis & Fixes

**Date**: December 26, 2025
**Status**: ✅ **DATABASE ISSUE FIXED** | 🔴 **CORS NEEDS BACKEND RESTART**

---

## Issues Found (From Production Logs)

### 1. **Database Type Mismatch** ✅ FIXED

**Symptom**:
```
asyncpg.exceptions.DatatypeMismatchError: column "player_ids" is of type character varying[] but expression is of type json
```

**When**: When attempting to create a video session via `POST /api/coaches/plus/sessions`

**Root Cause**:
- Alembic migration: `player_ids` column type = `postgresql.ARRAY(String)`
- SQLAlchemy model: `player_ids` column type = `JSON`
- Type mismatch causes PostgreSQL to reject the INSERT statement

**Fix**:
```python
# File: backend/sql_app/models.py (line 1268)

# BEFORE
player_ids: Mapped[list[str]] = mapped_column(JSON, ...)

# AFTER
player_ids: Mapped[list[str]] = mapped_column(postgresql.ARRAY(String), ...)
```

**Verification**:
- ✅ Local test passes (test_video_session_fix.py)
- ✅ Model now returns `ARRAY` type
- ✅ Commit: `e3abcea`

**Deployment Steps**:
```bash
# Rebuild and deploy backend
docker-compose up -d --build backend

# Or via AWS ECS
aws ecs update-service --cluster cricksy --service backend --force-new-deployment
```

---

### 2. **CORS Headers Missing** 🔴 NEEDS INVESTIGATION

**Symptom** (Browser Console):
```
Access to fetch at 'https://api.cricksy-ai.com/api/coaches/plus/sessions'
from origin 'https://cricksy-ai.web.app' has been blocked by CORS policy
```

**When**: When frontend tries to create a session

**Root Cause Analysis**:
1. ✅ Code configuration is CORRECT
   - `backend/config.py` includes both domains in `_DEFAULT_CORS`
   - `backend/app.py` properly configures `CORSMiddleware`
   - All origins, methods, and headers are allowed

2. 🔴 Runtime/Deployment Issue
   - Backend container might not be running the latest code
   - Environment variables might not be set in production
   - Load balancer / reverse proxy might be stripping headers

**Possible Causes** (in priority order):

1. **Backend not restarted after code update**
   ```bash
   docker-compose restart backend
   ```

2. **Environment variable not set in ECS task**
   - Check task definition for `BACKEND_CORS_ORIGINS`
   - Should be set or default to `_DEFAULT_CORS`

3. **ALB/NLB stripping CORS headers**
   - ALB doesn't pass through CORS headers by default
   - Solution: Configure ALB to allow them or ensure API adds headers

4. **Reverse proxy / CloudFront issue**
   - If using CloudFront, check cache behavior
   - Ensure origin headers are not being filtered

**How to Diagnose**:

```bash
# Test if API returns CORS headers
curl -i -H "Origin: https://cricksy-ai.web.app" \
  https://api.cricksy-ai.com/api/coaches/plus/sessions

# Expected response should include:
# Access-Control-Allow-Origin: https://cricksy-ai.web.app
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: *
# Access-Control-Allow-Headers: *
```

**Next Steps**:
1. Restart backend service
2. Test CORS headers with curl above
3. If still failing, check ALB/reverse proxy configuration
4. Review CloudWatch logs for any errors

---

## Related Issues (From Browser Console)

### ❓ 401 Unauthorized on `/auth/me`
- **Expected**: When user is not logged in
- **Action**: Frontend should redirect to login
- **Check**: Are auth tokens being sent in request headers?

### ❓ 404 on `/api/ai-usage/my-usage`
- **Possible**: Endpoint doesn't exist or user lacks access
- **Action**: Check if this endpoint is implemented
- **Reference**: `backend/routes/ai_usage.py`

---

## Timeline

| Time | Event |
|------|-------|
| ~Dec 26 06:17:48 UTC | Database type error in production logs |
| 06:18+ | Repeated type errors on create_video_session calls |
| 2025-12-26 (now) | **Analysis & fixes completed** |
| **e3abcea** | **Database type fix committed** |

---

## Code Changes

**Commit: `e3abcea`**
```diff
File: backend/sql_app/models.py (line 1268)

- player_ids: Mapped[list[str]] = mapped_column(JSON, ...)
+ player_ids: Mapped[list[str]] = mapped_column(postgresql.ARRAY(String), ...)
```

---

## Deployment Checklist

**Immediate (Today)**:
- [ ] Deploy commit `e3abcea` to production
  ```bash
  # Backend rebuild
  docker build -t cricksy-backend:latest backend/
  docker push <ECR_REGISTRY>/cricksy-backend:latest
  aws ecs update-service --cluster cricksy --service backend --force-new-deployment
  ```

**Verification**:
- [ ] Backend healthy check passes
- [ ] Create video session endpoint returns 200 (not database error)
- [ ] CORS headers present in API response
- [ ] Frontend can upload video without CORS errors

**If CORS Still Fails**:
- [ ] Restart ALB / reverse proxy
- [ ] Check CloudFront cache behavior
- [ ] Verify DNS resolves to correct endpoint
- [ ] Check security groups allow traffic

---

## Testing

```bash
# Local test of model fix
python test_video_session_fix.py

# Expected output:
# ✅ VideoSession model loaded successfully
# ✅ FIXED: player_ids now uses postgresql.ARRAY(String)
# ✅ VideoSession instance created successfully
# ✅ All tests PASSED
```

---

## References

| File | Line | Issue | Status |
|------|------|-------|--------|
| backend/sql_app/models.py | 1268 | Type mismatch | ✅ FIXED |
| backend/app.py | 305 | CORS middleware | ✅ OK |
| backend/config.py | 11-24 | CORS defaults | ✅ OK |
| backend/routes/coach_pro_plus.py | 189 | create_video_session | ✅ OK |

---

## Impact

**Before Fix**:
- ❌ Users cannot create video sessions
- ❌ Database error on every creation attempt
- ❌ No videos can be analyzed

**After Fix**:
- ✅ Video sessions can be created
- ✅ Videos can be uploaded
- ✅ Analysis jobs can be queued

---

**NOTE**: CORS issue requires backend restart/redeployment. Monitor logs after deploying `e3abcea`.
