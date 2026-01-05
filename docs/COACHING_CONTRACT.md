# Coaching Feature API Contract

**Version:** 1.0.0
**Last Updated:** 2026-01-04
**Status:** 🔒 LOCKED - Breaking changes require major version bump

---

## Overview

This document defines the **immutable contract** between backend and frontend for Coach Notes, Video Sessions, and Video Moment Markers features. All changes must maintain backward compatibility or increment the major version.

**Contract Guarantees:**
- ✅ Response fields never removed (only deprecated)
- ✅ Enums only add new values, never remove existing
- ✅ Optional fields clearly marked with `| null`
- ✅ HTTP status codes standardized
- ✅ Error response format consistent

---

## 1. Video Sessions API

### Base Path
```
/api/coaches/plus
```

### 1.1 Create Video Session

**Endpoint:** `POST /sessions`
**Auth Required:** Yes (coach_pro_plus, org_pro, or superuser)
**Beta Feature:** `video_upload`

**Request Body:**
```typescript
{
  title: string;                    // Required, 1-255 chars
  player_ids: string[];             // Required, can be empty array
  notes?: string | null;            // Optional
  session_type?: "batting" | "bowling" | "fielding" | "wicketkeeping" | null;
  min_duration_seconds?: number;    // Optional, default: 300 (5 minutes)
}
```

**Success Response (201 Created):**
```typescript
{
  id: string;                       // UUID
  owner_type: "coach" | "org";
  owner_id: string;                 // User ID or org ID
  title: string;
  player_ids: string[];
  status: "pending" | "uploaded" | "processing" | "ready" | "failed";
  notes: string | null;
  session_type: "batting" | "bowling" | "fielding" | "wicketkeeping" | null;
  min_duration_seconds: number;
  s3_bucket: string | null;         // Null until uploaded
  s3_key: string | null;            // Null until uploaded
  file_size_bytes: number | null;   // Null until uploaded
  created_at: string;               // ISO 8601 datetime
  updated_at: string;               // ISO 8601 datetime
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - User lacks coach_pro_plus role or beta access
- `422 Unprocessable Entity` - Validation error (invalid enum, missing required field)

---

### 1.2 List Video Sessions

**Endpoint:** `GET /sessions`
**Auth Required:** Yes (coach_pro_plus, org_pro, or superuser)

**Query Parameters:**
```typescript
{
  offset?: number;   // Default: 0
  limit?: number;    // Default: 50, max: 100
}
```

**Success Response (200 OK):**
```typescript
VideoSessionRead[]  // Array of session objects (same schema as create response)
```

**Filtering Logic:**
- Org users (`org_pro`): Returns sessions where `owner_type='org'` AND `owner_id=current_user.org_id`
- Coach users (`coach_pro_plus`): Returns sessions where `owner_id=current_user.id`
- Superusers: Returns sessions where `owner_id=current_user.id`

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - User lacks coach_pro_plus role

---

### 1.3 Get Upload URL

**Endpoint:** `POST /sessions/{session_id}/upload-url`
**Auth Required:** Yes (must own the session)

**Success Response (200 OK):**
```typescript
{
  upload_url: string;        // Presigned S3 PUT URL
  fields: Record<string, string>; // Form fields for multipart upload
  expires_in: number;        // Seconds until URL expires (typically 3600)
  max_size_bytes: number;    // Maximum allowed file size
}
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not session owner
- `404 Not Found` - Session doesn't exist
- `413 Payload Too Large` - Video exceeds quota (total storage or duration limit)

---

## 2. Coach Notes API

### Base Path
```
/api/coaches
```

### 2.1 Create Coach Note

**Endpoint:** `POST /players/{player_id}/notes`
**Auth Required:** Yes (coach_pro, coach_pro_plus, org_pro, or superuser)

**Path Parameters:**
- `player_id` (integer) - Player ID from `players` table

**Request Body:**
```typescript
{
  player_id: number;                  // Required (must match path param)
  note_text: string;                  // Required, 1-10000 chars
  severity?: "info" | "improvement" | "critical";  // Default: "info"
  tags?: string[] | null;             // Optional, e.g. ["footwork", "timing"]
  video_session_id?: string | null;   // Optional UUID reference
  moment_marker_id?: string | null;   // Optional UUID reference
}
```

**Success Response (201 Created):**
```typescript
{
  id: string;                          // UUID
  coach_id: string;                    // User ID of coach who created note
  player_id: number;
  player_name: string | null;          // Enriched from players table
  video_session_id: string | null;
  video_session_title: string | null;  // Enriched from video_sessions table
  moment_marker_id: string | null;
  note_text: string;
  tags: string[] | null;
  severity: "info" | "improvement" | "critical";
  created_at: string;                  // ISO 8601 datetime
  updated_at: string;                  // ISO 8601 datetime
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - User lacks coach role
- `404 Not Found` - Player doesn't exist
- `422 Unprocessable Entity` - Validation error
  - Invalid severity enum
  - Missing note_text
  - Invalid video_session_id or moment_marker_id reference

---

### 2.2 List Player Notes

**Endpoint:** `GET /players/{player_id}/notes`
**Auth Required:** Yes (coach_pro, coach_pro_plus, org_pro, or superuser)

**Query Parameters:**
```typescript
{
  severity?: "info" | "improvement" | "critical";  // Filter by severity
  video_session_id?: string;                       // Filter by video session
  offset?: number;                                 // Default: 0
  limit?: number;                                  // Default: 50, max: 100
}
```

**Success Response (200 OK):**
```typescript
CoachNoteRead[]  // Array of note objects (same schema as create response)
```

**Ordering:** Notes returned in reverse chronological order (`created_at DESC`)

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - User lacks coach role
- `404 Not Found` - Player doesn't exist

---

### 2.3 Get Single Note

**Endpoint:** `GET /notes/{note_id}`
**Auth Required:** Yes (must be note owner or org admin)

**Success Response (200 OK):**
```typescript
CoachNoteRead  // Same schema as create response
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not note owner and not org admin
- `404 Not Found` - Note doesn't exist

---

### 2.4 Update Coach Note

**Endpoint:** `PATCH /notes/{note_id}`
**Auth Required:** Yes (must be note owner)

**Request Body:**
```typescript
{
  note_text?: string | null;                        // Update note text
  tags?: string[] | null;                           // Update tags
  severity?: "info" | "improvement" | "critical";   // Update severity
}
```

**Success Response (200 OK):**
```typescript
CoachNoteRead  // Updated note object
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not note owner
- `404 Not Found` - Note doesn't exist
- `422 Unprocessable Entity` - Invalid severity enum

---

### 2.5 Delete Coach Note

**Endpoint:** `DELETE /notes/{note_id}`
**Auth Required:** Yes (must be note owner or superuser)

**Success Response (204 No Content):**
```
(empty body)
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not note owner and not superuser
- `404 Not Found` - Note doesn't exist

---

### 2.6 Get AI Corrective Guidance

**Endpoint:** `POST /corrective-guidance`
**Auth Required:** Yes (coach_pro, coach_pro_plus, org_pro, or superuser)

**Request Body:**
```typescript
{
  player_role: "batter" | "bowler" | "wicketkeeper" | "fielder";
  skill_focus: "batting_stance" | "footwork" | "bowling_action" |
               "wicketkeeping_stance" | "catching" | "throwing";
  observed_issue: string;  // Free text describing the problem
}
```

**Success Response (200 OK):**
```typescript
{
  skill_focus: string;
  checkpoints: Array<{
    checkpoint: string;
    description: string;
  }>;
  drills: Array<{
    drill: string;
    description: string;
  }>;
  ai_explanation: string | null;  // AI-generated context (optional)
}
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - User lacks coach role
- `422 Unprocessable Entity` - Invalid player_role or skill_focus enum

---

## 3. Video Moment Markers API

### Base Path
```
/api/coaches/markers
```

### 3.1 Create Moment Marker

**Endpoint:** `POST /sessions/{session_id}/markers`
**Auth Required:** Yes (coach_pro_plus, org_pro, or superuser; must own session)

**Path Parameters:**
- `session_id` (string) - Video session UUID

**Request Body:**
```typescript
{
  timestamp_ms: number;                             // Required, milliseconds from video start
  moment_type: "setup" | "catch" | "throw" | "dive" | "stumping" | "other";
  description?: string | null;                      // Optional, max 1000 chars
}
```

**Success Response (201 Created):**
```typescript
{
  id: string;                                       // UUID
  video_session_id: string;
  timestamp_ms: number;
  moment_type: "setup" | "catch" | "throw" | "dive" | "stumping" | "other";
  description: string | null;
  created_by: string;                               // Coach user ID
  created_at: string;                               // ISO 8601 datetime
}
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not session owner
- `404 Not Found` - Session doesn't exist
- `422 Unprocessable Entity` - Validation error
  - Invalid moment_type enum
  - timestamp_ms < 0
  - Missing required field

---

### 3.2 List Session Markers

**Endpoint:** `GET /sessions/{session_id}/markers`
**Auth Required:** Yes (coach_pro_plus, org_pro, or superuser; must own session)

**Query Parameters:**
```typescript
{
  moment_type?: "setup" | "catch" | "throw" | "dive" | "stumping" | "other";
}
```

**Success Response (200 OK):**
```typescript
VideoMomentMarkerRead[]  // Array ordered by timestamp_ms ASC
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not session owner
- `404 Not Found` - Session doesn't exist

---

### 3.3 Update Moment Marker

**Endpoint:** `PATCH /markers/{marker_id}`
**Auth Required:** Yes (must be creator)

**Request Body:**
```typescript
{
  timestamp_ms?: number;
  moment_type?: "setup" | "catch" | "throw" | "dive" | "stumping" | "other";
  description?: string | null;
}
```

**Success Response (200 OK):**
```typescript
VideoMomentMarkerRead  // Updated marker
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not marker creator
- `404 Not Found` - Marker doesn't exist
- `422 Unprocessable Entity` - Invalid enum or negative timestamp

---

### 3.4 Delete Moment Marker

**Endpoint:** `DELETE /markers/{marker_id}`
**Auth Required:** Yes (must be creator or superuser)

**Success Response (204 No Content):**
```
(empty body)
```

**Error Responses:**
- `401 Unauthorized`
- `403 Forbidden` - Not creator and not superuser
- `404 Not Found` - Marker doesn't exist

---

## 4. Enums (Locked)

### 4.1 VideoSessionType
```typescript
"batting" | "bowling" | "fielding" | "wicketkeeping"
```

### 4.2 VideoSessionStatus
```typescript
"pending" | "uploaded" | "processing" | "ready" | "failed"
```

### 4.3 CoachNoteSeverity
```typescript
"info" | "improvement" | "critical"
```

### 4.4 VideoMomentType
```typescript
"setup" | "catch" | "throw" | "dive" | "stumping" | "other"
```

### 4.5 PlayerRole (for corrective guidance)
```typescript
"batter" | "bowler" | "wicketkeeper" | "fielder"
```

---

## 5. Error Response Format

All error responses follow this structure:

```typescript
{
  detail: string | object;  // Human-readable error message or validation errors
  status?: number;          // HTTP status code (for reference)
  code?: string;            // Machine-readable error code (optional)
}
```

**Standard Error Codes:**
- `401_UNAUTHENTICATED` - Missing or invalid JWT token
- `403_UNAUTHORIZED` - Valid token but insufficient permissions
- `403_FEATURE_DISABLED` - Feature not available for user's role/beta status
- `404_NOT_FOUND` - Resource doesn't exist
- `413_QUOTA_EXCEEDED` - Video storage or duration quota exceeded
- `422_VALIDATION_ERROR` - Request validation failed

---

## 6. Validation Rules

### Video Sessions
- `title`: 1-255 characters
- `min_duration_seconds`: 60-7200 (1 minute to 2 hours)
- `player_ids`: Array (can be empty)
- `session_type`: Must be valid enum or null

### Coach Notes
- `note_text`: 1-10000 characters
- `tags`: Array of strings, max 20 tags, each max 50 chars
- `severity`: Must be valid enum
- `player_id`: Must exist in `players` table
- `video_session_id`: Must exist in `video_sessions` table if provided
- `moment_marker_id`: Must exist in `video_moment_markers` table if provided

### Video Moment Markers
- `timestamp_ms`: >= 0, <= video duration (if known)
- `moment_type`: Must be valid enum
- `description`: Max 1000 characters
- `video_session_id`: Must exist and user must have access

---

## 7. Quotas & Limits

### Video Storage Quotas (by role)
- `coach_pro_plus`: 5 GB total storage
- `org_pro`: 50 GB total storage (shared across org)
- Beta access: Custom limits per `beta_access.entitlements`

### Rate Limits
- Coach Notes: 100 creates per day per user
- Moment Markers: 500 creates per day per user
- Video Uploads: 20 per day per user

### Pagination Limits
- Default `limit`: 50
- Maximum `limit`: 100
- Maximum `offset`: 10000

---

## 8. Backend Implementation Notes

### Response Stability Guarantees
1. **Never omit optional fields** - Always include with `null` value
2. **Always include enriched fields** - e.g., `player_name`, `video_session_title`
3. **Preserve field order** - Order matters for snapshot tests
4. **ISO 8601 datetime format** - Always use `YYYY-MM-DDTHH:mm:ss.sssZ`

### Database Constraints
- All `*_id` fields use appropriate foreign key constraints
- Cascade deletes configured appropriately:
  - Deleting video session cascades to markers and notes
  - Deleting player cascades to notes
  - Deleting user cascades to owned content
- Indexes on:
  - `coach_notes.coach_id`
  - `coach_notes.player_id`
  - `coach_notes.video_session_id`
  - `coach_notes.severity`
  - `coach_notes.created_at`
  - `video_moment_markers.video_session_id`
  - `video_moment_markers.timestamp_ms`
  - `video_moment_markers.moment_type`

---

## 9. Frontend Implementation Notes

### TypeScript Type Safety
- Use discriminated unions for enums
- Mark all nullable fields as `| null` (not `| undefined`)
- Use branded types for UUIDs where appropriate

### API Client Requirements
- Automatic retry with exponential backoff for 5xx errors
- Token refresh on 401 responses
- Parse ISO 8601 datetimes to Date objects
- Validate enum values before sending requests

### Error Handling
- Display user-friendly messages for all error codes
- Show quota usage when approaching limits
- Gracefully degrade features when beta access expires

---

## 10. Testing Requirements

### Backend Contract Tests
Minimum 3 tests per endpoint validating:
1. Response schema matches contract (all fields present, correct types)
2. HTTP status codes match contract
3. Error response format matches contract

### Frontend Type Tests
1. TypeScript compilation with strict mode
2. Enum exhaustiveness checks
3. API response type guards

---

## 11. Migration & Deprecation Policy

### Adding New Fields
✅ **Allowed** - Add optional fields with defaults
```typescript
// OK: Add new optional field
video_url?: string | null;
```

### Adding Enum Values
✅ **Allowed** - Add new enum values
```typescript
// OK: Add new moment type
"boundary_save"  // Added to VideoMomentType
```

### Removing Fields
❌ **Breaking Change** - Requires major version bump
```typescript
// NOT ALLOWED in v1.x
// Must deprecate in v1.x, remove in v2.0
```

### Changing Field Types
❌ **Breaking Change** - Requires major version bump

### Deprecation Process
1. Mark field as deprecated in docs
2. Add `_deprecated_` prefix to field name
3. Maintain for 1 major version
4. Remove in next major version

---

## 12. Version History

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0.0   | 2026-01-04 | Initial contract lock |

---

## Appendix A: Full TypeScript Types

See `frontend/src/types/coaching.ts` for complete type definitions.

## Appendix B: Pydantic Models

See `backend/routes/coach_notes.py` and `backend/routes/coach_pro_plus.py` for authoritative schema definitions.

## Appendix C: Database Schema

See `backend/alembic/versions/` for migration history:
- `d4e5f6g7h8i9_add_coach_notes_table.py`
- `e5f6g7h8i9j0_add_video_moment_markers.py`
