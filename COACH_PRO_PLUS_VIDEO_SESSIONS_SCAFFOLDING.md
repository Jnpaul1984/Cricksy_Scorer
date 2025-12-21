# Coach Pro Plus Video Sessions - Scaffolding Implementation

## Overview

Added **placeholder scaffolding** for Coach Pro Plus video sessions feature with tier gating and role-based access control. No real video upload/streaming yet—just the structure to safely implement it later.

**Status:** ✅ COMPLETE - Ready for feature development

---

## What Was Added

### Backend

#### File: `backend/routes/coach_pro_plus.py` (New)
- **Purpose:** Video sessions endpoints with feature gating
- **Endpoints (Stubs):**
  - `POST /api/coaches/plus/sessions` - Create session
  - `GET /api/coaches/plus/sessions` - List sessions (paginated)
  - `GET /api/coaches/plus/sessions/{id}` - Get session detail
- **Feature Gating:** All endpoints protected by `@require_feature('video_upload_enabled')` dependency
- **Data Storage:** In-memory dict (placeholder for future DB model)
- **Response Schema:** `VideoSessionRead` with id, title, player_ids, status, notes, timestamps

**Key Design:**
```python
# Feature gating: Only coach_pro_plus and org_pro users allowed
_: Annotated[None, Depends(require_feature("video_upload_enabled"))]

# Status validation
if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
    raise HTTPException(status_code=403, detail="...")
```

#### File: `backend/app.py` (Modified)
- **Import:** Added `from backend.routes.coach_pro_plus import router as coach_pro_plus_router`
- **Registration:** Added `fastapi_app.include_router(coach_pro_plus_router)` after coach_pro router
- **Impact:** Routes now available at `/api/coaches/plus/*`

### Frontend

#### File: `frontend/src/views/CoachProPlusVideoSessionsView.vue` (New)
- **Purpose:** Video sessions management UI
- **Features:**
  - Feature gate: Shows upgrade card if user not coach_pro_plus
  - List view: Grid of session cards with status badges
  - Create/edit form: Modal for session metadata
  - Pagination: Limit/offset controls
  - Empty state: Helpful messaging when no sessions
  - Responsive design: Mobile-friendly layout

**Key Components:**
```vue
<!-- Feature gate with upgrade CTA -->
<div v-if="!authStore.isCoachProPlus" class="feature-gate">
  <UpgradeCard to="/pricing" />
</div>

<!-- Session cards with actions -->
<div v-for="session in sessions" :key="session.id" class="session-card">
  <!-- Status badge, metadata, actions -->
</div>

<!-- Create/edit modal with form -->
<form @submit.prevent="submitForm">
  <input v-model="formData.title" />
  <textarea v-model="formData.notes" />
</form>
```

**Placeholder Endpoints:**
```typescript
// Mock data for now
const response = await fetch('/api/coaches/plus/sessions?limit=10&offset=0')

// TODO: Real implementation once backend API finalized
```

#### File: `frontend/src/router/index.ts` (Modified)
- **New Route:**
  ```typescript
  {
    path: '/coaches/video-sessions',
    name: 'CoachProPlusVideoSessions',
    component: () => import('@/views/CoachProPlusVideoSessionsView.vue'),
    meta: { requiresAuth: true, title: 'Video Sessions — Cricksy' },
  }
  ```

#### File: `frontend/src/views/CoachesDashboardView.vue` (Modified)
- **Added:** Quick Links button "Video Sessions (Plus)" in dashboard
- **Action:** Navigates to `/coaches/video-sessions`
- **Styling:** Consistent with existing buttons

---

## Architecture & Design Decisions

### Feature Gating Strategy

**Backend (Enforcement):**
```python
@require_feature('video_upload_enabled')
```
- Enforces access control at API level
- Works for all roles that have the feature flag
- Returns 403 Forbidden if feature not enabled

**Frontend (User Experience):**
```typescript
if (!authStore.isCoachProPlus) {
  // Show upgrade card instead of content
}
```
- Prevents users from seeing features they don't have
- Provides clear upgrade CTA
- No API calls made for non-premium users

### Role Precedence
```
coach_pro_plus >= coach_pro >= free
org_pro >= all (includes video features)
```

Coach Pro Plus users automatically get:
- All Coach Pro features (session notes, AI summaries, PDF exports)
- New video session management (pending upload feature)

### Data Model (Placeholder)

**In-Memory Store:**
```python
_video_sessions: dict[str, dict] = {
  "session_id": {
    "id": "uuid",
    "coach_id": "user_id",
    "title": "Batting Technique",
    "player_ids": ["player1", "player2"],
    "status": "pending",  # pending, uploaded, processing, ready
    "notes": "...",
    "created_at": "2025-12-21T...",
    "updated_at": "2025-12-21T...",
  }
}
```

**Future SQLAlchemy Model:**
```python
class VideoSession(Base):
    __tablename__ = "video_sessions"
    id: str (PK)
    coach_user_id: str (FK → users)
    title: str
    player_ids: list[str]  # JSON array
    status: enum
    notes: str | None
    video_url: str | None  # S3 presigned URL
    ai_report: dict | None
    created_at, updated_at
```

---

## Testing Instructions

### Backend API Testing

#### 1. Create a Video Session
```bash
curl -X POST http://localhost:8000/api/coaches/plus/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Batting Technique Session",
    "player_ids": ["player1_id", "player2_id"],
    "notes": "Focus on front foot technique"
  }'
```

**Expected Response (201):**
```json
{
  "id": "uuid-xxx",
  "coach_id": "user_id",
  "title": "Batting Technique Session",
  "player_ids": ["player1_id", "player2_id"],
  "status": "pending",
  "notes": "Focus on front foot technique",
  "created_at": "2025-12-21T...",
  "updated_at": "2025-12-21T..."
}
```

#### 2. List Video Sessions
```bash
curl http://localhost:8000/api/coaches/plus/sessions?limit=10&offset=0 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200):**
```json
[
  { "id": "...", "title": "...", "status": "pending" },
  { "id": "...", "title": "...", "status": "ready" }
]
```

#### 3. Get Specific Session
```bash
curl http://localhost:8000/api/coaches/plus/sessions/session_id \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200):**
```json
{ "id": "session_id", "title": "...", ... }
```

#### 4. Test Feature Gating
Create a free user and try to access endpoints:
```bash
# As free user - should get 403 Forbidden
curl http://localhost:8000/api/coaches/plus/sessions \
  -H "Authorization: Bearer FREE_USER_TOKEN"
```

**Expected Response (403):**
```json
{
  "detail": "Insufficient feature access: video_upload_enabled"
}
```

### Frontend Testing

#### 1. Navigate to Video Sessions
1. **As coach_pro_plus user:**
   - Login with coach_pro_plus account
   - Go to `/coaches` (Coaches Dashboard)
   - Click "Video Sessions (Plus)" button
   - Should see list view with mock data
   - Click "+ New Video Session" to open create form

2. **As non-plus user (coach_pro):**
   - Login with coach_pro account
   - Go to `/coaches/video-sessions`
   - Should see "Unlock Video Sessions" upgrade card
   - Click "Upgrade to Coach Pro Plus" → routes to `/pricing`

#### 2. Test Create Form
- Click "+ New Video Session"
- Fill form:
  - Title: "Bowling Technique"
  - Players: "player1, player2"
  - Notes: "Fast bowling drills"
- Click "Create Session"
- Check console for mock API call
- Modal should close
- New session should appear in list

#### 3. Test Pagination
- List has multiple sessions
- Click "Next >" button
- offset value changes
- fetchSessions() called again

#### 4. Test Responsive Design
- Open DevTools → mobile view
- Session cards should stack vertically
- Modal should be 90% width
- Buttons should be full-width on mobile

---

## File Changes Summary

```
✅ backend/routes/coach_pro_plus.py
   └─ New file: 190 lines
   └─ 3 endpoints: POST, GET (list), GET (detail)
   └─ Feature gating via @require_feature()
   └─ In-memory data store (placeholder)

✅ backend/app.py
   └─ Import: coach_pro_plus_router
   └─ Register: fastapi_app.include_router(coach_pro_plus_router)

✅ frontend/src/views/CoachProPlusVideoSessionsView.vue
   └─ New file: 500+ lines (Vue 3 SFC)
   └─ Feature gate, CRUD UI, modal, pagination
   └─ Responsive grid layout
   └─ Placeholder API integration

✅ frontend/src/router/index.ts
   └─ New route: /coaches/video-sessions
   └─ Component: CoachProPlusVideoSessionsView
   └─ Meta: { requiresAuth: true }

✅ frontend/src/views/CoachesDashboardView.vue
   └─ Button: "Video Sessions (Plus)"
   └─ Handler: goToVideoSessions()
   └─ Styling: Consistent with existing buttons
```

---

## Integration Path to Real Feature

### Phase 1: Current (Scaffolding)
- ✅ Routes created (stubs)
- ✅ Feature gating in place
- ✅ UI scaffolding complete
- ✅ Data placeholders ready

### Phase 2: Database Integration
1. Create `VideoSession` SQLAlchemy model
2. Add Alembic migration
3. Replace in-memory store with DB queries
4. Update schemas/tests

### Phase 3: Video Upload
1. Add S3 bucket configuration
2. Implement multipart file upload endpoint
3. Add video processing queue (background job)
4. Update status from "pending" → "uploaded" → "processing" → "ready"

### Phase 4: Video Streaming
1. Implement presigned S3 URL generation
2. Add video player component (frontend)
3. Stream endpoint with authentication
4. Transcoding/HLS support

### Phase 5: AI Analysis
1. Connect to ML pipeline for video analysis
2. Generate session insights (bowling angle, batting mechanics, etc.)
3. Store AI report in VideoSession model
4. Display report in UI

---

## Code Examples for Future Implementation

### Example: Switching from In-Memory to Database

**Before (Current):**
```python
_video_sessions: dict[str, dict] = {}

@router.post("/sessions")
async def create_video_session(...):
    session_id = str(uuid4())
    session = { "id": session_id, ... }
    _video_sessions[session_id] = session
    return session
```

**After (Phase 2):**
```python
@router.post("/sessions")
async def create_video_session(...):
    session = VideoSession(
        coach_user_id=current_user.id,
        title=session_data.title,
        player_ids=session_data.player_ids,
        notes=session_data.notes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return VideoSessionRead.from_orm(session)
```

### Example: Frontend API Integration

**Before (Mock):**
```typescript
const response = [
  { id: 'mock-1', title: '...', status: 'ready' }
]
```

**After (Real):**
```typescript
async function fetchSessions() {
  const response = await fetch(
    `/api/coaches/plus/sessions?limit=${limit.value}&offset=${offset.value}`,
    {
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
      },
    }
  )
  const data = await response.json()
  sessions.value = data
}
```

---

## Deployment Checklist

- [x] Backend routes created and registered
- [x] Feature gating implemented (@require_feature)
- [x] Frontend views created
- [x] Router entries added
- [x] Navigation menu updated
- [x] Responsive design verified
- [x] Feature gate UX tested
- [ ] Backend tests written (pytest)
- [ ] Frontend tests written (Vitest)
- [ ] API documentation updated
- [ ] Staging deployment
- [ ] Load testing
- [ ] Production deployment

---

## Known Limitations & TODOs

### Backend
- [ ] No database persistence (in-memory only)
- [ ] No file upload handling
- [ ] No S3 integration
- [ ] No video processing pipeline
- [ ] No AI analysis
- [ ] Missing DELETE endpoint
- [ ] Missing PATCH/PUT endpoints

### Frontend
- [ ] Mock data only (no real API calls)
- [ ] No file input/upload UI
- [ ] No video player component
- [ ] No AI report display
- [ ] Edit/delete not functional
- [ ] No error retry logic
- [ ] No optimistic updates

### Comments in Code
```python
# TODO: Real video upload
# TODO: S3 integration
# TODO: Video processing queue
# TODO: AI analysis
```

```typescript
// TODO: Replace with actual API call
// TODO: Add retry logic
// TODO: Add loading skeleton
```

---

## Questions & Answers

**Q: Can users upload videos now?**
A: No. The infrastructure is scaffolded, but real upload is Phase 3. For now, they can create sessions and add metadata.

**Q: What happens if a coach_pro user tries to access /coaches/video-sessions?**
A: Frontend shows "Unlock Video Sessions" upgrade card. Backend API returns 403 Forbidden if they somehow bypass it.

**Q: Where is the video stored?**
A: Not yet implemented. Will use S3 in Phase 3 with presigned URLs.

**Q: How does AI analysis work?**
A: Not yet implemented. Will queue video for ML pipeline in Phase 5.

**Q: Is there a video player?**
A: Not yet. Will add in Phase 4 (streaming phase).

**Q: Can I delete sessions?**
A: Button exists in UI, but DELETE endpoint not implemented yet (simple addition for Phase 2).

---

## Summary

✅ **Scaffolding Complete:** Coach Pro Plus video sessions feature is fully scaffolded with:
- Feature-gated API endpoints
- Feature-gated frontend UI
- Placeholder data storage
- Navigation integration
- Responsive design
- Clear TODOs for future phases

✅ **Safe to Deploy:** Changes are purely additive; no breaking changes to existing code

✅ **Ready for Development:** Each phase can be implemented independently without refactoring the scaffold

🚀 **Next Step:** Phase 2 (Database Integration) can begin immediately with Alembic migration for VideoSession model
