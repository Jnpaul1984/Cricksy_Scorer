# CORS Configuration & ECS Deployment - Memory Notes

## Critical Issue History
**Date**: December 26, 2025  
**Problem**: Frontend at `https://cricksy-ai.web.app` couldn't login - received "No 'Access-Control-Allow-Origin' header" CORS errors  
**Root Cause**: ECS task definition had wrong `BACKEND_CORS_ORIGINS` environment variable value  

## Root Causes (Multiple Layers)

### 1. **ECS Task Definition Environment Variable Mismatch** ⚠️ CRITICAL
The `BACKEND_CORS_ORIGINS` environment variable in the ECS task definition (revision 34) was hardcoded to:
```
https://app.cricksy-ai.com,http://localhost:5173
```

But the actual frontend deployment is at:
```
https://cricksy-ai.web.app  ← MISSING from ECS env var!
```

**Why this happened:**
- Task definition was manually created/updated with incomplete CORS whitelist
- No automation to keep ECS env vars in sync with code changes
- The `_DEFAULT_CORS` list in `backend/config.py` is correct, but Pydantic Settings reads `BACKEND_CORS_ORIGINS` env var which **overrides** the default

### 2. **Code vs. Environment Variable Precedence**
- `backend/config.py` defines `_DEFAULT_CORS` list with all domains
- `Settings.BACKEND_CORS_ORIGINS` has this as default value
- BUT: ECS environment variable **overrides** the code default
- When env var is set to wrong value, code defaults are ignored

### 3. **Forgetting Task Restart**
After code changes (app.py CORS fix), GitHub Actions deployed new image to ECR but ECS didn't auto-restart tasks. Old container still running with old code.

---

## Prevention Checklist

### Before Any Backend Deployment:

#### ✅ Step 1: Update CORS Whitelist in Code
File: `backend/config.py` (lines 11-24)

**Current correct value:**
```python
_DEFAULT_CORS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "https://cricksy-ai.web.app",        ← Firebase Frontend
    "https://api.cricksy-ai.com",        ← Production API Domain
    "https://cricksy-ai.com",
    "https://www.cricksy-ai.com",
    "https://dev.cricksy-ai.com",
]
```

**If adding new domain:**
1. Add to `_DEFAULT_CORS` list in `backend/config.py`
2. Also add to ECS task definition env var (see Step 2)
3. Test locally first: `BACKEND_CORS_ORIGINS="<your-new-domain>" python -m pytest tests/`

#### ✅ Step 2: Sync ECS Task Definition
The ECS `BACKEND_CORS_ORIGINS` environment variable MUST match `_DEFAULT_CORS`.

**Current correct value for ECS env var:**
```
https://cricksy-ai.web.app,https://app.cricksy-ai.com,https://api.cricksy-ai.com,http://localhost:5173,http://localhost:3000,http://localhost:5174,http://localhost:4173,https://cricksy-ai.com,https://www.cricksy-ai.com,https://dev.cricksy-ai.com
```

**How to update ECS task definition:**
```bash
# Get current task definition revision
aws ecs describe-task-definition --task-definition cricksy-ai-backend --region us-east-1 --query 'taskDefinition.revision'

# Extract to JSON (replace XX with current revision)
aws ecs describe-task-definition --task-definition cricksy-ai-backend:XX --region us-east-1 --query 'taskDefinition | {family: family, taskRoleArn: taskRoleArn, executionRoleArn: executionRoleArn, networkMode: networkMode, containerDefinitions: containerDefinitions, volumes: volumes, placementConstraints: placementConstraints, requiresCompatibilities: requiresCompatibilities, cpu: cpu, memory: memory}' --output json > task-def.json

# Edit task-def.json: Find BACKEND_CORS_ORIGINS and update value

# Register new revision
aws ecs register-task-definition --cli-input-json file://task-def.json --region us-east-1

# Note the new revision number (e.g., 36)
```

#### ✅ Step 3: Force New ECS Deployment
After code changes OR environment variable changes, **ALWAYS force new deployment**:

```bash
# Replace XX with new task definition revision
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-backend-service \
  --region us-east-1 \
  --task-definition cricksy-ai-backend:XX \
  --force-new-deployment

# Verify deployment succeeded
aws ecs describe-services \
  --cluster cricksy-ai-cluster \
  --services cricksy-ai-backend-service \
  --region us-east-1 \
  --query 'services[0].[serviceName, runningCount, desiredCount]'
```

---

## Debugging CORS Issues

### Quick Test: Check if CORS is working
1. Open browser DevTools → Network tab
2. Visit `https://cricksy-ai.web.app`
3. Try any API call (e.g., login)
4. Look for response header: `Access-Control-Allow-Origin`
5. Should contain: `https://cricksy-ai.web.app`

### If Still Getting CORS Errors:

**Step 1: Verify ECS env var is set correctly**
```bash
aws ecs describe-task-definition \
  --task-definition cricksy-ai-backend \
  --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment' \
  --output json
```

Look for line with `BACKEND_CORS_ORIGINS` - value must include your domain.

**Step 2: Verify new task is running (not old one)**
```bash
# Get running task details
aws ecs list-tasks --cluster cricksy-ai-cluster --region us-east-1 --query 'taskArns'

# Describe task to see what revision it's using
aws ecs describe-tasks --cluster cricksy-ai-cluster --tasks <TASK_ARN> --region us-east-1 --query 'tasks[0].taskDefinitionArn'
```

Should show the LATEST revision number, not old one.

**Step 3: Check backend logs**
```bash
# View last 50 lines of backend logs
aws logs tail /ecs/cricksy-ai-backend --region us-east-1 --follow false | tail -50
```

Look for any startup errors or CORS-related messages.

---

## Architecture Reference

### CORS Flow:
```
Frontend (https://cricksy-ai.web.app)
    ↓ API Request
ALB (api.cricksy-ai.com)
    ↓ Route to target group
ECS Task Container
    ↓ FastAPI app.py reads config
    ↓ Pydantic Settings reads BACKEND_CORS_ORIGINS env var
    ↓ If env var not set → uses _DEFAULT_CORS from config.py
    ↓ CORSMiddleware checks if Origin header is in allow_origins list
    ↓ If yes → adds Access-Control-Allow-Origin response header ✅
    ↓ If no → no CORS header, browser blocks request ❌
Frontend receives response
```

### Key Files:
- **Code defaults**: `backend/config.py` (lines 11-24) - `_DEFAULT_CORS`
- **Code that reads env var**: `backend/config.py` (lines 37-42) - `BACKEND_CORS_ORIGINS` field
- **Middleware setup**: `backend/app.py` (lines 294-305) - `CORSMiddleware` configuration
- **ECS Configuration**: AWS ECS Task Definition `cricksy-ai-backend` environment variables

---

## Common Mistakes to Avoid

❌ **Mistake 1**: Updated `_DEFAULT_CORS` in code but forgot to update ECS env var
- **Fix**: Always update BOTH code AND ECS env var together

❌ **Mistake 2**: Pushed code changes but forgot to restart ECS task
- **Fix**: ALWAYS use `--force-new-deployment` flag after code changes

❌ **Mistake 3**: Added new frontend domain to code but forgot it's production
- **Fix**: Test locally first, then update ECS BEFORE deploying frontend

❌ **Mistake 4**: Hardcoding CORS origins in `app.py` instead of config
- **Fix**: Keep all CORS lists in ONE place: `backend/config.py`

❌ **Mistake 5**: Setting `BACKEND_CORS_ORIGINS` to empty string in ECS
- **Fix**: Either set it to full list OR delete it so code default is used (remove the env var setting from task definition)

---

## Quick Reference: Copy-Paste Values

### For Code (`backend/config.py`)
```python
_DEFAULT_CORS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "https://cricksy-ai.web.app",
    "https://api.cricksy-ai.com",
    "https://cricksy-ai.com",
    "https://www.cricksy-ai.com",
    "https://dev.cricksy-ai.com",
]
```

### For ECS Task Definition Environment Variable
```
https://cricksy-ai.web.app,https://app.cricksy-ai.com,https://api.cricksy-ai.com,http://localhost:5173,http://localhost:3000,http://localhost:5174,http://localhost:4173,https://cricksy-ai.com,https://www.cricksy-ai.com,https://dev.cricksy-ai.com
```

---

## Testing

### Local Test
```bash
# Set env var and run tests
export BACKEND_CORS_ORIGINS="https://cricksy-ai.web.app"
cd backend
pytest tests/ -k cors -v
```

### Production Test
1. Visit `https://cricksy-ai.web.app`
2. Open DevTools → Network tab
3. Click login button
4. Check response headers for: `access-control-allow-origin: https://cricksy-ai.web.app`
5. If header present → CORS working ✅

---

## Emergency Rollback

If CORS is broken in production:
```bash
# Option 1: Revert to previous task definition
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-backend-service \
  --region us-east-1 \
  --task-definition cricksy-ai-backend:<PREVIOUS_REVISION> \
  --force-new-deployment

# Option 2: Temporarily disable CORS restrictions (NOT recommended for production)
# Update task definition to: BACKEND_CORS_ORIGINS="*"
```

---

## Related Issues to Watch
- Firebase frontend domain changes → update CORS
- Adding new production domain → update CORS  
- Moving ALB to different domain → update CORS
- Any "No 'Access-Control-Allow-Origin' header" error → check CORS config
