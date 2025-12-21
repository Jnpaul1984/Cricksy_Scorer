# Cricksy Tier & Entitlement Architecture Blueprint

**Version**: 1.0
**Date**: December 21, 2025
**Author**: Technical Program Manager + Architect
**Status**: APPROVED FOR IMPLEMENTATION

---

## EXECUTIVE SUMMARY

This document defines the complete tier and entitlement architecture for Cricksy, including:

1. **Current State**: 6 tiers (Free, Player Pro, Coach Pro, Analyst Pro, Org Pro variants, Superuser)
2. **New "Plus" Tiers**: Coach Pro Plus, Analyst Pro Plus, Scorers Pro Plus, Player Pro Plus
3. **Implementation**: Staged rollout starting with **Coach Pro Plus** (video sessions + AI session reports)
4. **Architecture**: Clean separation between core tier logic, feature gates, and premium features

---

## A. REPOSITORY MAP & TECH STACK

### Tech Stack Overview

| Layer | Tech | Notes |
|-------|------|-------|
| **Frontend** | Vue 3 + Vite + TypeScript + Pinia | State: `authStore.ts` (role/tier tracking) |
| **Backend** | FastAPI + SQLAlchemy AsyncORM | Python 3.12, async routes |
| **Database** | PostgreSQL (prod) / SQLite (test) | Alembic migrations for schema |
| **Auth** | Custom JWT (no OAuth, no Stripe yet) | `security.py`: role-based access (RBAC) |
| **State Mgmt** | Pinia (frontend), SQLAlchemy sessions (backend) | Centralized in stores + DB models |

### Backend Directory Structure

```
backend/
├── sql_app/
│   ├── models.py                          # Core: User, RoleEnum, CoachingSession, etc.
│   ├── schemas.py                         # Pydantic DTOs for API requests/responses
│   └── database.py                        # AsyncSession factory, get_db()
├── routes/                                # FastAPI route handlers
│   ├── auth_router.py                     # Login/register
│   ├── users_router.py                    # User profile, settings
│   ├── coach_pro.py                       # Coach tier routes (assignments, sessions)
│   ├── analyst_pro.py                     # Analyst tier routes (analytics, exports)
│   ├── fan_mode.py                        # Free tier match creation/viewing
│   ├── billing.py                         # Plan features, entitlement checks
│   └── [other domain routes]              # Scoring, games, teams, etc.
├── services/
│   ├── billing_service.py                 # PLAN_FEATURES dict, check_feature_access()
│   ├── coaching_service.py                # (future) Coach tier business logic
│   ├── video_service.py                   # (future) Video session recording/playback
│   └── [other domain services]            # Analytics, predictions, etc.
├── security.py                            # JWT encode/decode, require_roles(), RBAC
├── middleware/                            # Observability, request logging
├── config.py                              # ENV vars, database URL, JWT secret
└── main.py / app.py                       # FastAPI app initialization
```

### Frontend Directory Structure

```
frontend/src/
├── stores/
│   ├── authStore.ts                       # Pinia: user, role, tier, permissions
│   ├── gameStore.ts                       # Game state + Socket.IO sync
│   └── index.ts                           # Store exports
├── views/
│   ├── PricingPageView.vue                # Plan cards, feature matrix
│   ├── CoachesDashboardView.vue           # Coach tier page
│   ├── AnalystWorkspaceView.vue           # Analyst tier page
│   ├── FanModeView.vue                    # Free tier match creation
│   └── [other domain views]               # Games, players, etc.
├── components/
│   ├── Paywall.vue                        # (future) Upgrade prompt
│   ├── FeatureGate.vue                    # (future) "Upgrade to unlock" overlay
│   └── [other components]
├── types/
│   ├── auth.ts                            # UserRole, AuthUser type definitions
│   ├── pricing.ts                         # (new) PlanDef, EntitlementLevel
│   └── [domain types]
├── services/
│   ├── api.ts                             # HTTP client with auth header injection
│   ├── auth.ts                            # Login, getCurrentUser()
│   └── [domain services]
└── router/
    └── index.ts                           # Vue Router with role-based redirects
```

### Key Files & Ownership

| File | Purpose | Frequency of Change |
|------|---------|---------------------|
| `backend/sql_app/models.py` | User, RoleEnum, entitlement models | *Low* (schema migrations) |
| `backend/services/billing_service.py` | PLAN_FEATURES, check_feature_access() | *High* (feature additions) |
| `backend/security.py` | require_roles() decorator, RBAC | *Low* (core auth logic) |
| `frontend/src/stores/authStore.ts` | Role/tier state, permissions getters | *Medium* (new tier logic) |
| `frontend/src/views/PricingPageView.vue` | Plan cards, feature matrix UI | *High* (marketing updates) |
| `backend/routes/coach_pro.py` | Coach tier endpoints | *High* (new features) |
| `backend/routes/analyst_pro.py` | Analyst tier endpoints | *High* (new features) |

---

## B. CURRENT FEATURE MAP

### Current Tiers (7 total)

```
FREE TIER
├── Live scoring (basic, single game)
├── Fan-mode match creation (up to 10 matches)
├── AI predictions (5 reports/month)
├── Public player profiles (view-only)
├── Fan favorites (follow players/teams)
└── Max 10 games, 1 tournament

PLAYER PRO ($1.99/month) — NEW
├── Everything in Free
├── Full career dashboard (all formats)
├── Form tracker & season graphs
├── Strength/weakness views (zones & dismissals)
├── AI-powered career summary (monthly)
├── Unlimited games
├── 10 tournaments max
└── Basic analytics

SCORERS PRO ($9.99/month) — SPECIALIST FOR PROFESSIONAL SCORERS
├── Advanced scoring templates (custom delivery patterns)
├── Offline scoring mode (sync when online)
├── Error correction (undo last 3 balls in-over)
├── Multi-match concurrent scoring (2-3 simultaneous games)
├── Pro scoreboard overlays (HD broadcast graphics)
├── Live multi-device sync (prioritized, low latency)
├── Max 3 concurrent games
└── Tournament support priority line

COACH PRO ($9.99/month)
├── Everything in Player Pro
├── Player development dashboard
├── Coach → Player assignment (1:many)
├── Session notebook (per player, per session)
├── Multi-player comparisons
├── AI session summaries (text-based)
├── 50 tournaments max
├── 100K API tokens/month
├── 100 AI reports/month
└── Priority support (basic)

ANALYST PRO ($29.99/month)
├── Everything in Coach Pro
├── Analyst workspace + saved views
├── AI dismissal pattern detection
├── AI heatmaps (location-based)
├── Ball-type clustering (fast, slow, spin)
├── Phase analysis (powerplay, middle, death)
├── Flexible query engine
├── Analyst notebook (custom queries)
├── CSV/JSON data exports
├── Case study tagging
└── 200 AI reports/month

ORG PRO (Freemium 3-tier model)
├── Org Pro Starter ($39/month):  4 teams, 4 Coach Pro seats, 1 Analyst Pro seat
├── Org Pro Growth ($79/month):   10 teams, 8 Coach Pro seats, 3 Analyst Pro seats
├── Org Pro Elite ($149/month):   20 teams, 15 Coach Pro seats, 5 Analyst Pro seats
├── All with: league/tournament management, org dashboards, sponsor panel, custom branding

SUPERUSER (admin)
├── Unlimited everything
├── All AI features
├── System admin access
└── No token limits
```

### Feature Categories

| Category | Features | Current Owner |
|----------|----------|----------------|
| **Live Scoring** | Score entry, ball-by-ball tracking, delivery history | All tiers |
| **Game Viewing** | Public scoreboard, live updates, match recap | Free (limited) → All tiers |
| **Player Analytics** | Career summary, match stats, dismissal analysis | Player Pro+ |
| **Coaching** | Session notes, player assignment, comparison tools | Coach Pro+ |
| **Advanced Analytics** | Heatmaps, ball clustering, phase analysis, exports | Analyst Pro+ |
| **Organization** | Team/tournament management, role management, sponsors | Org Pro |
| **AI Features** | Session summaries, predictions, insights, reports | Varies by tier (token-limited) |

### Current Entitlement Checks

| Check Location | Method | Coverage |
|----------------|--------|----------|
| `backend/security.py` | `require_roles()` decorator | Route-level RBAC |
| `backend/services/billing_service.py` | `check_feature_access()` | Feature flags by plan |
| `backend/services/billing_service.py` | `check_usage_limit()` | Token/API rate limits |
| `frontend/src/stores/authStore.ts` | Getters: `isCoachPro`, `canAnalyze`, etc. | UI-level show/hide |
| Not yet implemented | No explicit paywall | No "upgrade now" prompts |

---

## C. CURRENT TIER ENTITLEMENT MATRIX

| Feature | Free | Player Pro | Coach Pro | Analyst Pro | Org Pro | Plus Tier |
|---------|------|-----------|-----------|------------|---------|-----------|
| **Live Scoring** | ✓ Basic | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Fan Mode** | ✓ (≤10) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Player Profile** | ✓ (view) | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Career Summary** | ✗ | ✓ Monthly | ✓ | ✓ | ✓ | ✓ |
| **Player Assignment** | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ Add-on |
| **Session Notebook** | ✗ | ✗ | ✓ Basic | ✓ | ✓ | ✓ Enhanced |
| **Multi-Player Compare** | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| **Heatmap Visualizer** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Ball Clustering** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Phase Analysis** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **CSV/JSON Export** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Case Study Tags** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Analyst Workspace** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ Enhanced |
| **Tournament Mgmt** | ✗ | ✓ (≤10) | ✓ (≤50) | ✓ (unlimited) | ✓ | ✓ |
| **AI Session Summary** | ✗ | ✗ | ✓ (text) | ✓ (text) | ✓ (text) | **✓ Video + Text** |
| **Video Lessons** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ NEW** |
| **Clip Library** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ NEW** |
| **Priority Support** | ✗ | ✗ | ✓ Basic | ✓ | ✓ | ✓ Premium |
| **Max Games** | 10 | ∞ | ∞ | ∞ | ∞ | ∞ |
| **AI Tokens/Month** | 10K | 100K | 100K | 100K | ∞ | 100K |
| **AI Reports/Month** | 5 | 50 | 100 | 200 | ∞ | 150 |

---

## D. NEW "PLUS" TIER SPECIFICATIONS

### Overview: Plus Tiers Strategy

**Goal**: Create premium tiers that add specialized features to existing base tiers without full tier overlap.

**Pricing Model**:
- Player Pro Plus: **$4.99/month** (+$3 from Player Pro, ~150% premium)
- Scorers Pro Plus: **$14.99/month** (+$5 from Scorers Pro, ~50% premium)
- Coach Pro Plus: **$19.99/month** (+$10 from Coach Pro, ~100% premium)
- Analyst Pro Plus: **$24.99/month** (+$10 from Analyst Pro, ~33% premium)

**Key Principle**: Plus tiers are additive (extend base), not replacement tiers.

---

### PLAYER PRO PLUS

**Current Player Pro**: Career dashboard, form tracking, AI career summary
**Target User**: Serious players who want AI coaching feedback and peer benchmarking

#### Value Proposition
- **AI Coaching Feedback**: Weekly auto-generated tips based on recent performance
- **Peer Comparison Dashboard**: Bench self vs. teammates/league average
- **Goal Tracking**: Set targets (avg, runs, wickets), track progress
- **Dismissal Breakdown**: AI analysis of each dismissal (angle, bowler type)
- **Mobile App Priority**: Early access to beta features

#### Premium Features

| Feature | Player Pro | Player Pro Plus | Notes |
|---------|-----------|-----------------|-------|
| Career Dashboard | ✓ | ✓ | Existing |
| Form Tracker | ✓ | ✓ | Existing |
| AI Career Summary | ✓ (Monthly) | ✓ (Weekly) | Enhanced frequency |
| **AI Weekly Feedback** | ✗ | ✓ NEW | Auto tips + TTS message |
| **Peer Comparison** | ✗ | ✓ NEW | vs. teammates/league |
| **Goal Tracking** | ✗ | ✓ NEW | Target avg, runs, wickets |
| **Dismissal Breakdown** | ✗ | ✓ NEW | "Why was I out?" AI |
| **Mobile Priority** | ✗ | ✓ NEW | Beta features, fast track |
| **AI Tokens/Month** | 50 | 100 | +50 for weekly AI |
| **Monthly Price** | $1.99 | $4.99 | 150% premium |

---

### SCORERS PRO PLUS

**Current Scorers Pro**: Offline mode, error correction, pro overlays, multi-match
**Target User**: State/national level tournament directors who need broadcast-grade scoring

#### Value Proposition
- **Broadcast Integration**: OBS/vMix overlay templates (live score graphics)
- **Real-Time Multi-Venue**: Aggregate scores from multiple grounds in one dashboard
- **Advanced Cloud Sync**: Conflict-free merge when multiple scorers rejoin online
- **HD Custom Overlays**: Team colors, sponsor logos, tournament branding
- **Priority Tournament Support**: Dedicated ops team during matches (30min response)

#### Premium Features

| Feature | Scorers Pro | Scorers Pro Plus | Notes |
|---------|------------|------------------|-------|
| Offline Scoring | ✓ | ✓ | Existing |
| Error Correction | ✓ (3 balls) | ✓ (5 balls) | Enhanced undo depth |
| Multi-Match View | ✓ (3 games) | ✓ (5 games) | Enhanced capacity |
| Pro Overlays | ✓ (Basic) | ✓ (HD Custom) | Enhanced graphics |
| **Broadcast Integration** | ✗ | ✓ NEW | OBS/vMix templates |
| **Multi-Venue Aggregation** | ✗ | ✓ NEW | Tournament-wide dashboard |
| **Advanced Cloud Sync** | ✗ | ✓ NEW | Conflict-free merge |
| **Custom Branding** | ✗ | ✓ NEW | Logo, colors, sponsors |
| **Tournament Ops Support** | Basic email | Premium (chat 30min) | SLA upgrade |
| **Max Concurrent Games** | 3 | 5 | Scoreboard capacity |
| **Monthly Price** | $9.99 | $14.99 | 50% premium |

#### Risks & Constraints
- **Broadcast Integration**: Requires OBS/vMix plugin development (new domain)
- **Multi-Venue Aggregation**: Complex real-time sync logic
- **Custom Branding**: UI builder complexity

#### Scope Split
- **MVP (v1)**: OBS overlay templates + multi-venue aggregation
- **v2**: Custom branding UI builder + advanced cloud sync conflict resolution

---

### COACH PRO PLUS

**Current Coach Pro**: Player assignment, session notebook, multi-player comparison, AI text summaries
**Target User**: School coaches, academy coaches who want multimedia coaching tools

#### Value Proposition
- **Record & Share Video Sessions**: Coach records or uploads session footage (e.g., Zoom, recorded practice)
- **AI-Generated Session Report**: Video + text analysis with key moments flagged
- **Interactive Clip Workflow**: Create clips from video, tag key moments, share to player
- **Session Library**: Archive sessions by player/date for historical coaching trends
- **Priority Support**: Phone/chat support (SLA ≤4 hours)

#### Premium Features

| Feature | Coach Pro | Coach Pro Plus | Notes |
|---------|-----------|----------------|-------|
| Session Notebook (text notes) | ✓ | ✓ | Existing |
| Video Upload (per session) | ✗ | ✓ NEW | MP4/MOV, up to 2GB per session |
| Video Playback + Timeline | ✗ | ✓ NEW | Linked to session notes |
| AI Video Analysis | ✗ | ✓ NEW | Generate highlights, key moments |
| Clip Creation Tool | ✗ | ✓ NEW | Trim video, tag moments, export |
| Clip Library (shared) | ✗ | ✓ NEW | Auto-organized by player/date |
| Priority Support | Basic (email 24h) | Premium (chat/phone 4h) | SLA upgrade |
| AI Reports/Month | 100 | 150 | +50 video analysis tokens |
| Storage Quota | N/A | 500GB/year | Video storage (S3 or equivalent) |

#### Risks & Constraints
- **Video Storage Cost**: S3 at 500GB/year ≈ $5/month in storage (margin concern)
- **AI Video Analysis**: OpenAI's video_understanding costs 8× text analysis; token consumption can spike
- **Live Video Streaming**: Deferred to v2 (added complexity: RTMP server, WebRTC)
- **Mobile App**: Required for in-field clip capture; scope creep risk

#### Scope Split
- **MVP (v1)**: Recorded video upload + replay + text notes + basic clip trim
- **v2**: AI highlights detection + clip recommendations + live streaming preview

---

### ANALYST PRO PLUS

**Current Analyst Pro**: Heatmaps, ball clustering, phase analysis, exports
**Target User**: Analysts at high-performance programs who need automated insights

#### Value Proposition
- **Automated Report Generation**: Scheduled daily/weekly/monthly AI reports (no manual trigger)
- **SHAP Explainability**: Understand WHY a player is vulnerable (e.g., "Weak to yorkers at death: 3 dismissals in last 12 matches")
- **Team Comparison Dashboard**: Bench this team's heatmap vs. opponent (side-by-side)
- **Advanced Exports**: Bulk export + filtered CSV (e.g., "All leg-side dismissals vs. fast bowlers in powerplay")
- **Priority Support**: Priority response queue, dedicated Slack channel (future)

#### Premium Features

| Feature | Analyst Pro | Analyst Pro Plus | Notes |
|---------|-------------|------------------|-------|
| Heatmaps | ✓ | ✓ | Existing |
| Ball Clustering | ✓ | ✓ | Existing |
| Phase Analysis | ✓ | ✓ | Existing |
| CSV/JSON Export | ✓ | ✓ | Existing |
| **Automated Reports** | ✗ | ✓ NEW | Scheduled (daily/weekly/monthly) |
| **SHAP Explainability** | ✗ | ✓ NEW | "Why this pattern?" explanations |
| **Team Comparison** | ✗ | ✓ NEW | Side-by-side vs. opponent/league avg |
| **Advanced Filters** | ✗ | ✓ NEW | Filter exports by phase, bowler type, outcome |
| **Bulk Operations** | ✗ | ✓ NEW | Multi-match exports, batch analysis |
| **Priority Support** | Basic (email) | Premium (email + Slack) | Faster response |
| **AI Tokens/Month** | 100K | 200K | +100K for automation |

#### Risks & Constraints
- **SHAP Computation**: Expensive for large datasets; may require background jobs (add Celery/worker infrastructure)
- **Automated Reports**: New email/scheduling system needed (email templating, job queue)
- **Team Comparison**: Requires preprocessing opponent data; complex data pipeline

#### Scope Split
- **MVP (v1)**: Automated weekly report generation (template-based, no SHAP yet)
- **v2**: SHAP explainability + ML-driven insights ("This bowler is weak to X")

---

## E. IMPLEMENTATION PLAN FOR COACH PRO PLUS

### Phase 1: Foundation (Week 1-2)

#### 1.1 Database Schema Changes

**New Tables**:

```python
# backend/sql_app/models.py - ADD:

class CoachingSessionVideo(Base):
    """Video artifact for coaching session (v1: single upload, future: multi-clip)"""
    __tablename__ = "coaching_session_videos"

    id: str = PK
    coaching_session_id: str = FK(CoachingSession)
    video_url: str                          # S3 path
    duration_seconds: int
    upload_status: Enum["pending", "ready", "failed"]
    ai_analysis_status: Enum["pending", "done", "failed"]
    ai_analysis_summary: dict | None        # JSON: highlights, key_moments, etc.
    created_at: datetime
    updated_at: datetime

class VideoClip(Base):
    """Extracted clip from session video (v2)"""
    __tablename__ = "video_clips"

    id: str = PK
    coaching_session_video_id: str = FK(CoachingSessionVideo)
    start_seconds: int
    end_seconds: int
    title: str
    moment_type: Enum["key_moment", "dismissal", "form_issue", "highlight"]
    created_at: datetime
```

**Schema Migration**:
```bash
# backend/alembic/versions/XXXXXXX_add_coach_plus_video_tables.py
# Command: alembic revision --autogenerate -m "add_coach_plus_video_tables"
```

**File Locations**:
- `backend/sql_app/models.py` → Add classes above
- `backend/alembic/versions/[timestamp]_add_coach_pro_plus_video_tables.py` → Auto-generated

#### 1.2 Entitlement Model

**Update**: `backend/services/billing_service.py`

```python
PLAN_FEATURES["coach_pro_plus"] = {
    "name": "Coach Pro Plus",
    "price_monthly": 24.99,
    "base_plan": "coach_pro",  # NEW: indicator this is a Plus tier
    "tokens_limit": 100_000,
    "ai_reports_per_month": 150,  # +50 vs Coach Pro
    # ... inherit all coach_pro features ...
    "video_upload_enabled": True,  # NEW
    "video_analysis_enabled": True,  # NEW
    "clip_creation_enabled": True,  # NEW
    "storage_quota_gb": 500,  # NEW: annual storage
    "priority_support_tier": "plus",  # NEW
}

# Add new entitlement checks:
def check_video_upload_access(user_role: RoleEnum) -> bool:
    """Check if user can upload session videos"""
    return user_role in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)

def get_video_storage_quota(user_role: RoleEnum) -> int:
    """Return storage quota in GB"""
    quotas = {
        RoleEnum.coach_pro_plus: 500,
        RoleEnum.org_pro: 5000,
    }
    return quotas.get(user_role, 0)
```

**File Location**: `backend/services/billing_service.py` (add 20-30 lines)

#### 1.3 Add New RoleEnum Entry

**Update**: `backend/sql_app/models.py`

```python
class RoleEnum(str, enum.Enum):
    free = "free"
    player_pro = "player_pro"
    coach_pro = "coach_pro"
    coach_pro_plus = "coach_pro_plus"  # NEW
    analyst_pro = "analyst_pro"
    org_pro = "org_pro"
```

**File Location**: `backend/sql_app/models.py` (1-line addition)

#### 1.4 Update RBAC Decorators

**Update**: `backend/security.py`

```python
# Add convenience decorators:
coach_pro_or_plus_required = Depends(require_roles(["coach_pro_plus", "org_pro"]))
coach_pro_plus_only = Depends(require_roles(["coach_pro_plus"]))
```

**File Location**: `backend/security.py` (add 2 lines at end)

---

### Phase 2: Backend Video Endpoints (Week 2-3)

#### 2.1 Video Upload Endpoint

**New File**: `backend/routes/coach_pro_plus.py`

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from backend.security import coach_pro_plus_only, get_current_user
from backend.services.video_service import upload_session_video, get_upload_progress

router = APIRouter(prefix="/api/coaches/plus", tags=["coach_pro_plus"])

@router.post("/sessions/{session_id}/videos/upload")
async def upload_session_video_endpoint(
    session_id: str,
    file: UploadFile = File(...),
    current_user = Depends(coach_pro_plus_only),
    db: AsyncSession = Depends(get_db),
):
    """Upload video for coaching session (MVP: single video per session)"""
    # Validate: session belongs to current_user (coach)
    # Validate: file size < 2GB
    # Queue async upload to S3
    # Return upload_id and progress URL
    ...

@router.get("/sessions/{session_id}/videos")
async def list_session_videos(
    session_id: str,
    current_user = Depends(coach_pro_plus_only),
    db: AsyncSession = Depends(get_db),
):
    """List videos for a coaching session"""
    ...

@router.get("/sessions/{session_id}/videos/{video_id}")
async def get_session_video(
    session_id: str,
    video_id: str,
    current_user = Depends(coach_pro_plus_only),
    db: AsyncSession = Depends(get_db),
):
    """Get video details + playback URL"""
    ...
```

**File Location**: `backend/routes/coach_pro_plus.py` (new file)

#### 2.2 Video Service (Core Logic)

**New File**: `backend/services/video_service.py`

```python
import asyncio
import boto3
from typing import Optional
from backend.sql_app.models import CoachingSessionVideo

async def upload_session_video(
    session_id: str,
    file_path: str,
    user_id: str,
    db: AsyncSession,
) -> CoachingSessionVideo:
    """
    Upload video to S3, create DB record, queue AI analysis
    """
    # 1. Check user quota (storage_quota_gb)
    # 2. Upload file to S3 with chunked upload
    # 3. Create CoachingSessionVideo record with upload_status="ready"
    # 4. Queue background job: trigger_ai_analysis(video_id)
    ...

async def trigger_ai_analysis(video_id: str, db: AsyncSession):
    """
    Queue OpenAI video understanding call (async background task)
    Save results to ai_analysis_summary
    """
    # Use OpenAI's video_understanding model
    # Extract: key_moments, highlights, duration, etc.
    # Store JSON in ai_analysis_summary
    ...

def get_video_presigned_url(video_url: str, expiration_seconds: int = 3600) -> str:
    """Generate S3 presigned URL for video playback"""
    s3_client = boto3.client('s3')
    return s3_client.generate_presigned_url(...)
```

**File Location**: `backend/services/video_service.py` (new file)

#### 2.3 Register Routes in App

**Update**: `backend/app.py`

```python
from backend.routes import coach_pro_plus

def create_app():
    app = FastAPI()
    ...
    app.include_router(coach_pro_plus.router)
    ...
```

**File Location**: `backend/app.py` (add 2 lines in create_app())

#### 2.4 Background Task Configuration

**Update**: `backend/config.py` (add S3/video settings)

```python
# S3 video storage
S3_BUCKET_VIDEOS = os.getenv("S3_BUCKET_VIDEOS", "cricksy-videos-dev")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
VIDEO_MAX_SIZE_MB = int(os.getenv("VIDEO_MAX_SIZE_MB", 2048))  # 2GB
VIDEO_ANALYSIS_MODEL = "gpt-4-vision"  # Future: video_understanding
```

**File Location**: `backend/config.py` (add 5 lines)

---

### Phase 3: Frontend UI Components (Week 3-4)

#### 3.1 Video Upload Component

**New File**: `frontend/src/components/CoachingSessionVideoUploader.vue`

```vue
<template>
  <div class="video-uploader">
    <div v-if="!videoUploaded" class="upload-zone">
      <input
        type="file"
        @change="handleFileSelect"
        accept="video/*"
      />
      <ProgressBar v-if="uploading" :progress="uploadProgress" />
    </div>
    <div v-else class="video-preview">
      <video :src="videoUrl" controls></video>
      <div class="video-analysis" v-if="analysisComplete">
        <h4>AI Analysis Summary</h4>
        <p>{{ videoAnalysis.summary }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { uploadCoachingSessionVideo } from '@/services/coaching'

const props = defineProps<{ sessionId: string }>()

const videoFile = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const videoUrl = ref('')
const analysisComplete = ref(false)
const videoAnalysis = ref({})

const videoUploaded = computed(() => !!videoUrl.value)

async function handleFileSelect(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (!files) return
  videoFile.value = files[0]

  uploading.value = true
  try {
    const result = await uploadCoachingSessionVideo(
      props.sessionId,
      videoFile.value,
      (progress) => { uploadProgress.value = progress }
    )
    videoUrl.value = result.playbackUrl
  } finally {
    uploading.value = false
  }
}
</script>
```

**File Location**: `frontend/src/components/CoachingSessionVideoUploader.vue` (new file)

#### 3.2 Update CoachingSession Page

**Update**: `frontend/src/views/CoachesDashboardView.vue`

```vue
<!-- Add to coaching session detail modal/page: -->
<section v-if="userStore.isCoachPro && userStore.subscription.plan === 'coach_pro_plus'">
  <h3>Session Video</h3>
  <CoachingSessionVideoUploader :sessionId="sessionId" />
</section>
```

**File Location**: `frontend/src/views/CoachesDashboardView.vue` (add ~10 lines)

#### 3.3 Update Pricing Page

**Update**: `frontend/src/views/PricingPageView.vue`

```typescript
// Add to plans array:
{
  id: 'coach-pro-plus',
  name: 'Coach Pro Plus',
  shortName: 'Coach+',
  tagline: 'Video coaching + AI session reports',
  monthly: 24.99,
  features: [
    'Everything in Coach Pro',
    'Video session recording & playback',
    'AI-generated session highlights',
    'Interactive clip creation',
    'Priority support (4h response)',
    '500GB annual video storage',
  ],
}
```

**File Location**: `frontend/src/views/PricingPageView.vue` (~15 lines added)

#### 3.4 Update Auth Store

**Update**: `frontend/src/stores/authStore.ts`

```typescript
getters: {
  // ... existing ...
  isCoachProPlus: (state) => state.user?.role === 'coach_pro_plus' || isSuperuser(state),
  canUploadVideos: (state) =>
    state.user?.role === 'coach_pro_plus' ||
    state.user?.role === 'org_pro' ||
    isSuperuser(state),
}
```

**File Location**: `frontend/src/stores/authStore.ts` (add 4 lines)

---

### Phase 4: Integration & Testing (Week 4)

#### 4.1 Backend Tests

**New File**: `backend/tests/test_coach_pro_plus_video.py`

```python
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.mark.asyncio
async def test_upload_session_video_requires_coach_pro_plus():
    """Verify only Coach Pro Plus users can upload videos"""
    ...

@pytest.mark.asyncio
async def test_upload_respects_storage_quota():
    """Verify users cannot exceed storage quota"""
    ...

@pytest.mark.asyncio
async def test_ai_analysis_triggered_on_upload():
    """Verify background job is queued after upload"""
    ...
```

**File Location**: `backend/tests/test_coach_pro_plus_video.py` (new file, ~50 lines)

#### 4.2 Frontend E2E Tests

**New File**: `frontend/cypress/e2e/coach-pro-plus-video.cy.ts`

```typescript
describe('Coach Pro Plus - Video Upload', () => {
  it('should render video uploader for Coach Pro Plus users', () => {
    // Login as coach_pro_plus user
    // Navigate to session detail
    // Assert video uploader visible
    // Upload mock video
    // Assert upload success
  })

  it('should NOT render uploader for Coach Pro users', () => {
    // Login as coach_pro user
    // Navigate to session detail
    // Assert video uploader NOT visible
  })
})
```

**File Location**: `frontend/cypress/e2e/coach-pro-plus-video.cy.ts` (new file)

#### 4.3 Manual QA Checklist

- [ ] Coach Pro Plus user can upload ≤2GB video
- [ ] Video appears in session detail
- [ ] Playback works (controls, seek, pause)
- [ ] AI analysis badge appears when ready
- [ ] Non-Plus users see "Upgrade" prompt
- [ ] Storage quota enforced (reject if >500GB total)
- [ ] Email notification sent when analysis complete
- [ ] Video URL is signed/authenticated (not public S3)

---

### Phase 5: Deployment & Monitoring (Week 5)

#### 5.1 Database Migration

```bash
cd backend/
alembic upgrade head
```

#### 5.2 Environment Variables

```bash
# .env.production
S3_BUCKET_VIDEOS=cricksy-videos-prod
S3_REGION=us-east-1
VIDEO_MAX_SIZE_MB=2048
OPENAI_API_KEY=sk-...  # For video analysis
```

#### 5.3 Monitoring

**File**: `backend/logging_setup.py` (add metrics)

```python
# Track:
- coach_pro_plus_video_uploads (counter)
- video_analysis_latency_seconds (histogram)
- s3_upload_failures (counter)
```

#### 5.4 Staged Rollout

- **Day 1**: Deploy to staging, internal testing
- **Day 2-3**: Beta access to 5-10 Coach Pro Plus pilot users
- **Day 4**: Full production release
- **Day 5-7**: Monitor metrics, support on-call

---

### Phase 6: Documentation & Support (Week 5)

#### 6.1 User-Facing Docs

- Video upload troubleshooting guide
- Recommended file formats (MP4 preferred)
- Storage quota management
- How to interpret AI analysis summary

#### 6.2 Developer Docs

- Video service API reference
- S3 bucket setup instructions
- Background job configuration (Celery)
- New RoleEnum value: coach_pro_plus

---

## F. BRANCH PLAN & COMMIT SEQUENCE

### Branch Name
```
feat/coach-pro-plus-video-sessions
```

**Rationale**: Feature-focused name; clear scope; easy to track/review.

### Commit Sequence

#### Commit 1: DB Schema + RoleEnum
```bash
commit: "feat(db): add coach_pro_plus role and video tables

- Add RoleEnum.coach_pro_plus
- Add CoachingSessionVideo table (video_url, ai_analysis_status, etc.)
- Add VideoClip table for v2 (future clip extraction)
- Create Alembic migration
- Files: models.py, alembic/versions/XXX.py"
```

#### Commit 2: Entitlement & Config
```bash
commit: "feat(billing): add coach_pro_plus entitlements

- Add PLAN_FEATURES['coach_pro_plus'] with video_upload_enabled flag
- Add check_video_upload_access() and get_video_storage_quota()
- Update security.py: add coach_pro_plus_only decorator
- Files: billing_service.py, security.py, config.py"
```

#### Commit 3: Backend Video Service
```bash
commit: "feat(video): implement video upload and S3 integration

- Add video_service.py with upload_session_video(), trigger_ai_analysis()
- Add presigned URL generation for secure playback
- Implement storage quota validation
- Queue background task for AI analysis
- Files: services/video_service.py, requirements.txt (boto3, openai)"
```

#### Commit 4: Backend Endpoints
```bash
commit: "feat(api): add coach_pro_plus video endpoints

- Add POST /api/coaches/plus/sessions/{id}/videos/upload
- Add GET /api/coaches/plus/sessions/{id}/videos
- Add GET /api/coaches/plus/sessions/{id}/videos/{video_id}
- RBAC via coach_pro_plus_only decorator
- Files: routes/coach_pro_plus.py, app.py"
```

#### Commit 5: Frontend Components
```bash
commit: "feat(ui): add video uploader and integration

- Add CoachingSessionVideoUploader.vue component
- Update CoachesDashboardView to render uploader (conditional on Plus tier)
- Update authStore with isCoachProPlus getter
- Files: components/CoachingSessionVideoUploader.vue,
         views/CoachesDashboardView.vue, stores/authStore.ts"
```

#### Commit 6: Pricing Page & Marketing
```bash
commit: "feat(pricing): add coach_pro_plus to pricing page

- Add coach_pro_plus plan card ($24.99/month)
- Update feature matrix to show video features
- Add feature comparison callout
- Files: views/PricingPageView.vue"
```

#### Commit 7: Tests
```bash
commit: "test: add coach_pro_plus video upload tests

- Backend: test_coach_pro_plus_video.py (pytest)
- Frontend: coach-pro-plus-video.cy.ts (Cypress E2E)
- Mock S3 uploads in tests
- Files: tests/test_coach_pro_plus_video.py,
         cypress/e2e/coach-pro-plus-video.cy.ts"
```

#### Commit 8: Docs
```bash
commit: "docs: add coach_pro_plus implementation guide

- User guide: video upload, troubleshooting, quotas
- Dev guide: video service API, S3 setup, background jobs
- Files: docs/COACH_PRO_PLUS_GUIDE.md"
```

### PR Template

```markdown
## Coach Pro Plus: Video Session Feature

### Changes
- [x] DB schema (role, video tables)
- [x] Entitlements (plan features, RBAC)
- [x] Backend service (S3 upload, AI analysis)
- [x] REST endpoints (video CRUD)
- [x] Frontend UI (uploader, preview)
- [x] Tests (backend + E2E)

### Validation Checklist
- [ ] All tests pass (pytest, Cypress)
- [ ] MyPy type checks pass
- [ ] Ruff lint passes
- [ ] DB migration tested locally
- [ ] Video upload works (mock S3)
- [ ] Non-Plus users see upgrade prompt
- [ ] Storage quota enforced

### Risk Mitigation
- Video storage cost capped at 500GB/user/year
- AI analysis costs monitored (OpenAI API budget alert set)
- Rollback: Disable coach_pro_plus in security.py, hide UI

### Deployment
- Stage: 2024-01-XX (internal testing)
- Beta: 2024-01-XY (5-10 pilot users)
- Prod: 2024-01-XZ (full release)
```

---

## G. FULL TIER MATRIX WITH PLUS TIERS

| Feature | Free | Player Pro | Player Pro Plus | Scorers Pro | Scorers Pro Plus | Coach Pro | Coach Pro Plus | Analyst Pro | Analyst Pro Plus | Org Pro |
|---------|------|-----------|-----------------|-----------|----------------|-------------|-----------------|---------|------------------|
| **Live Scoring** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Offline Scoring** | ✗ | ✗ | ✗ | ✓ | ✓ Enhanced | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Offline Error Undo** | ✗ | ✗ | ✗ | ✓ (3 balls) | ✓ (5 balls) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Advanced Scoring Templates** | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Multi-Match View** | ✗ | ✗ | ✗ | ✓ (3 games) | ✓ (5 games) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Pro Scoreboard Overlays** | ✗ | ✗ | ✗ | ✓ (Basic) | ✓ (HD Custom) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **AI Career Summary** | ✗ | ✓ Monthly | ✓ Weekly | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Peer Comparison** | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Goal Tracking** | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Broadcast Integration** | ✗ | ✗ | ✗ | ✗ | ✓ NEW | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Multi-Venue Aggregation** | ✗ | ✗ | ✗ | ✗ | ✓ NEW | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Player Assignment** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Session Notebook** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ Basic | ✓ Enhanced | ✓ | ✓ | ✓ |
| **Multi-Player Compare** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **AI Session Summary** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ Text | ✓ Video+Text | ✓ | ✓ | ✓ |
| **Video Sessions** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ |
| **Heatmap Visualizer** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Ball Clustering** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Phase Analysis** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **CSV/JSON Export** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| **Automated Reports** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| **SHAP Explainability** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| **Priority Support** | ✗ | ✗ | ✗ | Basic email | Premium chat | Basic email | Premium (4h) | Basic email | Premium chat | Premium |
| **Monthly Price** | Free | $1.99 | $4.99 | $9.99 | $14.99 | $9.99 | $19.99 | $14.99 | $24.99 | $39-149 |

---

## H. FOLDER & FILE REFERENCE GUIDE

### Database Layer

| Path | Purpose | Ownership |
|------|---------|-----------|
| `backend/sql_app/models.py` | ORM models (User, CoachingSession, CoachingSessionVideo) | DB Team |
| `backend/sql_app/schemas.py` | Pydantic DTO schemas | API Team |
| `backend/sql_app/database.py` | AsyncSession factory | DB Team |
| `backend/alembic/versions/` | Migration files | DB Team |

### Billing & Entitlements

| Path | Purpose | Ownership |
|------|---------|-----------|
| `backend/services/billing_service.py` | PLAN_FEATURES, check_feature_access() | Product Team |
| `backend/security.py` | RBAC decorators (require_roles) | Auth Team |
| `backend/config.py` | ENV vars, feature flags | DevOps Team |

### Coach Pro Plus (NEW)

| Path | Purpose | Ownership |
|------|---------|-----------|
| `backend/services/video_service.py` | S3 upload, AI analysis queueing | Video Team |
| `backend/routes/coach_pro_plus.py` | Video endpoints (upload, list, get) | API Team |
| `frontend/src/components/CoachingSessionVideoUploader.vue` | Video upload UI | Frontend Team |
| `frontend/src/views/CoachesDashboardView.vue` | Coach dashboard (video uploader integrated) | Frontend Team |
| `frontend/src/stores/authStore.ts` | Role/tier state (isCoachProPlus getter) | Frontend Team |

### Testing

| Path | Purpose | Ownership |
|------|---------|-----------|
| `backend/tests/test_coach_pro_plus_video.py` | Backend unit tests | QA Team |
| `frontend/cypress/e2e/coach-pro-plus-video.cy.ts` | E2E tests | QA Team |

### Documentation

| Path | Purpose | Ownership |
|------|---------|-----------|
| `docs/COACH_PRO_PLUS_GUIDE.md` | User + dev guide | Documentation Team |

---

## I. ROLLOUT ROADMAP

### Release Schedule

```
Week 1-2:  Foundation (DB + entitlements)
Week 2-3:  Backend video service + endpoints
Week 3-4:  Frontend UI components
Week 4:    Integration + testing
Week 5:    Staging → Beta → Production
Week 6+:   Monitor + iterate
```

### Rollout Stages

1. **Staging** (Internal only)
   - Test with full test suite
   - Manual QA verification
   - Load test video upload

2. **Beta** (5-10 Coach Pro Plus early access users)
   - Monitor error rates + performance
   - Collect user feedback (form + support)
   - Fix critical bugs

3. **Production** (Full release)
   - Monitor all metrics (upload success, storage quota usage, AI latency)
   - Scale to expected load
   - Prepare rollback plan

### Success Metrics

- **Adoption**: % of Coach Pro users who upgrade to Plus in first month
- **Engagement**: Avg videos uploaded per Coach Pro Plus user/month
- **Quality**: Video upload success rate > 99%
- **Support**: Support ticket volume for video feature < 5/week
- **Revenue**: ARPU increase from Coach Pro tier

---

## J. FUTURE ROADMAP (POST-MVP)

### Coach Pro Plus v2 (Q2 2024)
- Live video streaming (RTMP → WebRTC)
- Multi-clip extraction + sharing
- Mobile app video capture
- Annotation tools (draw on video)

### Analyst Pro Plus v2 (Q2 2024)
- ML-driven SHAP explainability
- Scheduled automated reports (email + dashboard)
- Slack integration for insights
- Custom dashboards + widgets

### Scorers Pro Plus v2 (Q3 2024)
- Multi-match concurrent scoring
- Broadcast overlay integration (OBS)
- Mobile app (iOS/Android)
- Offline mode conflict resolution

### Platform-Wide (Q3 2024+)
- Paywall UI component (upgrade prompts)
- Stripe integration (actual payments)
- Usage analytics dashboard
- Feature flag system (Launchdarkly/similar)
- A/B testing framework

---

## K. IMPLEMENTATION CHECKLIST

### Pre-Development

- [ ] Review this blueprint with team
- [ ] Assign owners (Backend, Frontend, QA, DevOps)
- [ ] Set up AWS S3 bucket (videos dev + prod)
- [ ] Get OpenAI API key (video analysis)
- [ ] Create feature branch: `feat/coach-pro-plus-video-sessions`

### Development (Weeks 1-4)

- [ ] Commit 1: DB schema + RoleEnum
- [ ] Commit 2: Entitlements + config
- [ ] Commit 3: Video service + S3
- [ ] Commit 4: Backend endpoints
- [ ] Commit 5: Frontend components
- [ ] Commit 6: Pricing page
- [ ] Commit 7: Tests (backend + E2E)
- [ ] Commit 8: Documentation

### Testing (Week 4)

- [ ] All pytest tests pass
- [ ] Cypress E2E tests pass
- [ ] MyPy type checks pass
- [ ] Ruff lint + format pass
- [ ] Manual QA checklist completed
- [ ] Storage quota enforced
- [ ] Non-Plus users see upgrade prompt

### Staging (Week 5, Day 1-2)

- [ ] Deploy to staging environment
- [ ] Internal team testing (30 min)
- [ ] Smoke test: upload video, verify analysis, delete video
- [ ] Load test: 100 concurrent uploads
- [ ] Monitor: no errors in logs

### Beta (Week 5, Day 3-4)

- [ ] Invite 5-10 Coach Pro Plus pilot users
- [ ] Provide support Slack channel
- [ ] Collect feedback (form + direct interview)
- [ ] Monitor: error rates, upload latency, storage usage
- [ ] Fix critical bugs

### Production (Week 5-6, Day 5+)

- [ ] Deploy to production
- [ ] Monitor all metrics (real-time dashboard)
- [ ] Release notes published
- [ ] Support team trained
- [ ] Rollback plan documented
- [ ] Day 7: Celebrate 🎉

---

## L. RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| S3 storage cost overruns | $$ High | Cap quota at 500GB/user/year; daily quota check |
| Video analysis latency (OpenAI) | User UX | Queue as background job; set 5min timeout |
| Malicious video uploads | Security | Scan for viruses; validate file type (magic bytes) |
| Video access from non-owners | Security | Presigned URLs + timestamp validation |
| DB migration failure | Prod outage | Test locally; create rollback script; dry-run in staging |
| High churn on Plus tier | Revenue | Launch only if 25%+ Coach Pro users interested (pre-survey) |

---

## M. CONCLUSION & NEXT STEPS

### Decision Points

1. **Approve Plus tier strategy?** (Coach Pro Plus as MVP)
2. **Approve tech stack?** (S3 + OpenAI for video analysis)
3. **Approve pricing?** ($24.99/month for Coach Pro Plus)
4. **Green light development?** (5-week timeline)

### Next Actions

1. **Week of Jan 22**: Engineering kickoff, assign owners
2. **Jan 25**: Create feature branch, start DB migrations
3. **Jan 29**: Backend API review (security team)
4. **Feb 5**: Frontend review (UX team)
5. **Feb 12**: Staging release
6. **Feb 19**: Production release

### Questions?

- **Video Format Support**: Only MP4 initially; MOV in v1.1
- **AI Analysis Cost**: Estimate $0.30/video (5 min analysis); absorbed in plan margin
- **Storage After Cancellation**: Videos deleted after 30-day grace period
- **Data Export**: Users can download their videos (GDPR compliance)

---

**Document Approved By**: [CTO/Product Lead]
**Date**: December 21, 2025
**Version**: 1.0 (FINAL)
