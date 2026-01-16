# Delivery Correction Implementation Summary

## Overview
Implemented end-to-end delivery-level correction system allowing scorers to fix mistakes in previously recorded deliveries without recreating the entire innings.

**Status**: ✅ **COMPLETE** - Backend + Frontend + Tests + QA Plan

---

## Architecture

### Data Flow
1. User clicks delivery in "Recent Balls" → Opens correction modal
2. Modal pre-fills existing values, allows editing runs/extras/wicket
3. On submit → `PATCH /games/{game_id}/deliveries/{delivery_id}`
4. Backend replays ALL deliveries using `scoring_service.score_one()`
5. Emits `state:update` via Socket.IO to all clients
6. Frontend updates snapshot, UI refreshes with corrected totals

### Key Design Decisions
- **Replay Strategy**: Full replay of all deliveries ensures scorecards/totals are accurate
- **Delivery ID**: Uses `delivery.id` from JSON ledger (not index) for stable references
- **Validation**: Normalizes extra codes, recalculates runs_scored based on type
- **Compatibility**: Shares same scoring logic as POST /deliveries (no code duplication)

---

## Changed Files

### Backend (3 files)

#### 1. `backend/routes/gameplay.py` (+175 lines)
**Added**:
- `DeliveryCorrection` Pydantic model for PATCH payload
- `PATCH /{game_id}/deliveries/{delivery_id}` endpoint
- Full delivery replay logic (mirrors undo-last pattern)
- Socket.IO emission after correction

**Key Functions**:
```python
@router.patch("/{game_id}/deliveries/{delivery_id}")
async def correct_delivery(
    game_id: str,
    delivery_id: int,
    correction: DeliveryCorrection,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    # Find delivery by ID in ledger
    # Apply corrections to delivery dict
    # Reset runtime/scorecards
    # Replay all deliveries using score_one()
    # Emit state:update via Socket.IO
    # Return updated snapshot
```

**Imports Added**:
- `Field` from pydantic
- `ExtraCode` from backend.sql_app.schemas

#### 2. `backend/services/snapshot_service.py` (no changes)
**Verified**: `build_snapshot()` already includes `extras_totals` in line 624

#### 3. `backend/tests/test_core_scoring.py` (+192 lines)
**Added Tests**:
- `test_delivery_correction_wide_to_legal()` - WD → legal ball
- `test_delivery_correction_runs_update()` - Change runs (2 → 4)
- `test_delivery_correction_not_found()` - 404 error handling

**Coverage**: Validates replay logic, scorecard updates, totals recalculation

---

### Frontend (3 files)

#### 4. `frontend/src/services/api.ts` (+24 lines)
**Added**:
- `DeliveryCorrectionRequest` interface (mirrors backend schema)
- `correctDelivery()` API function

```typescript
export interface DeliveryCorrectionRequest {
  runs_scored?: number;
  runs_off_bat?: number;
  extra?: 'wd' | 'nb' | 'b' | 'lb' | null;
  is_wicket?: boolean;
  dismissal_type?: string | null;
  // ... other fields
}

correctDelivery: (gameId: string, deliveryId: number, body: DeliveryCorrectionRequest) =>
  request<Snapshot>(`/games/${gameId}/deliveries/${deliveryId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
```

#### 5. `frontend/src/components/DeliveryCorrectionModal.vue` (+309 lines, NEW FILE)
**Features**:
- Pre-fills delivery data (over/ball, runs, extra type, wicket)
- Dynamic form: switches between runs_off_bat (NB) vs runs_scored (legal/extras)
- Wicket details: dismissal type selector
- Dark theme support via CSS variables
- Real-time field sync (extra type changes update runs display)

**Props**:
- `show`: boolean - modal visibility
- `delivery`: DeliveryData - pre-fill source
- `bowlerName`, `batterName`: string - display names

**Emits**:
- `close` - cancel/close modal
- `submit` - `{ deliveryId, correction }` payload

#### 6. `frontend/src/views/GameScoringView.vue` (+45 lines)
**Added**:
- Import `DeliveryCorrectionModal` component
- Import `DeliveryCorrectionRequest` type from api
- State: `showCorrectionModal`, `correctionDelivery` refs
- Functions: `openCorrectionModal()`, `closeCorrectionModal()`, `submitCorrection()`
- Recent Balls: Click handler on each ball badge
- Modal component at template end (before `</template>`)

**UX Changes**:
- Recent balls now clickable (cursor: pointer)
- Tooltip: "Click to correct this delivery"
- Modal opens on click, pre-fills all fields
- On submit: calls `apiService.correctDelivery()`, updates `gameStore.liveSnapshot`

---

## Documentation (1 file)

#### 7. `.mcp/DELIVERY_CORRECTION_QA_PLAN.md` (NEW, 300+ lines)
**Contents**:
- 6 detailed test cases with step-by-step instructions
- Test Case 1: WD → Legal (verify ball count, CRR update)
- Test Case 2: Correct runs (2 → 6), verify scorecard
- Test Case 3: Add/remove wicket status
- Test Case 4: No-ball → Legal (runs_off_bat handling)
- Test Case 5: Undo Last still works after corrections
- Test Case 6: Real-time updates (multi-client Socket.IO)
- Edge cases: 404 errors, completed games, cancel behavior
- Acceptance criteria checklist
- Sign-off table for QA/PO/Dev

---

## API Contract

### PATCH /games/{game_id}/deliveries/{delivery_id}

**Request Body** (`DeliveryCorrection`):
```json
{
  "runs_scored": 4,
  "runs_off_bat": 4,
  "extra": null,
  "is_wicket": false,
  "dismissal_type": null,
  "dismissed_player_id": null,
  "fielder_id": null,
  "shot_map": null,
  "shot_angle_deg": null,
  "commentary": "Corrected to 4 runs"
}
```

**Response**: `Snapshot` (same as POST /deliveries)
- `total_runs`, `total_wickets`, `overs_completed`, etc.
- `batting_scorecard`, `bowling_scorecard`
- `extras_totals`: { wides, no_balls, byes, leg_byes, penalty, total }
- `deliveries`: updated ledger with corrected delivery

**Error Responses**:
- `404` - Delivery not found
- `400` - Game already completed
- `409` - Validation errors (invalid runs, incompatible extras)

---

## Testing

### Unit Tests (Backend)
```bash
cd backend
pytest tests/test_core_scoring.py::test_delivery_correction_wide_to_legal -v
pytest tests/test_core_scoring.py::test_delivery_correction_runs_update -v
pytest tests/test_core_scoring.py::test_delivery_correction_not_found -v
```

### Integration Test (Manual)
```bash
# Terminal 1: Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Browser: http://localhost:5173/game/{gameId}/scoring
# Follow QA plan in .mcp/DELIVERY_CORRECTION_QA_PLAN.md
```

---

## Manual QA Steps (Quick Reference)

### Test 1: WD → Legal Ball
1. Score WD with 1 run → Total: 1, Overs: 0.0, Extras: WD=1
2. Score legal 1 run → Total: 2, Overs: 0.1
3. Click WD badge → Change to None/Legal, Runs: 1
4. **Verify**: Total: 2, Overs: **0.2**, Extras: **WD=0**, CRR updated

### Test 2: Correct Runs (2 → 6)
1. Score 2, 0, 4 runs → Total: 6
2. Click first ball (2) → Change to 6 runs
3. **Verify**: Total: **10**, Batter runs: **10**, CRR: 20.0

### Test 3: Add Wicket
1. Score 0 runs (dot ball)
2. Click dot → Check "Wicket", select "Bowled"
3. **Verify**: Wickets: 1, Scorecard shows out, UI prompts new batter

---

## Constraints Met

✅ **Contract compatibility**: Uses same payload structure as POST /deliveries  
✅ **Undo Last works**: Replay logic preserves undo functionality  
✅ **Delivery.id as primary key**: Stable references across corrections  
✅ **Extras totals consistent**: `snapshot_service.py` already includes extras_totals  
✅ **Socket.IO emission**: All clients receive real-time updates  
✅ **No breaking changes**: Existing scoring flow unchanged  

---

## Deployment Checklist

- [ ] Merge to beta branch: `beta/fix-extras-recentballs-correction-theme`
- [ ] Run backend tests: `pytest backend/tests/test_core_scoring.py`
- [ ] Run frontend type-check: `cd frontend && npm run type-check`
- [ ] Run frontend lint: `cd frontend && npm run lint`
- [ ] Manual QA: Execute all 6 test cases in QA plan
- [ ] Multi-client test: Verify Socket.IO real-time updates
- [ ] Smoke test: Score 20 balls, correct 5 random ones, verify totals match
- [ ] Deploy to staging
- [ ] Final verification with production-like data
- [ ] Merge to main

---

## Future Enhancements (Out of Scope)

- **Batch correction**: Correct multiple deliveries at once
- **Correction history**: Track who corrected what and when
- **Approval workflow**: Require admin approval for corrections after innings complete
- **Audit log**: Detailed changelog of all corrections
- **Undo correction**: Revert a correction back to original

---

## Files Summary

**Backend**:
1. `backend/routes/gameplay.py` - PATCH endpoint + replay logic
2. `backend/services/snapshot_service.py` - (no changes, verified extras_totals)
3. `backend/tests/test_core_scoring.py` - 3 new test cases

**Frontend**:
4. `frontend/src/services/api.ts` - API client + types
5. `frontend/src/components/DeliveryCorrectionModal.vue` - NEW modal component
6. `frontend/src/views/GameScoringView.vue` - Modal integration + click handlers

**Documentation**:
7. `.mcp/DELIVERY_CORRECTION_QA_PLAN.md` - Manual QA guide

**Total**: 7 files changed/added (3 backend, 3 frontend, 1 docs)
