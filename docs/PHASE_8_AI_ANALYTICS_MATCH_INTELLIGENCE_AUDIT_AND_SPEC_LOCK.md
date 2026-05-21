# Phase 8 — AI Analytics + Match Intelligence Audit and Spec Lock

**Document status:** Locked
**Phase:** 8 (active)
**Repository:** `Jnpaul1984/Cricksy_Scorer`
**Preceding phase:** Phase 7 (governance-closed; OCR sub-phases deferred)
**Date:** 2026-05-15

---

## 1. Executive Summary

Phase 8 is an audit-first, enhancement-only phase. Its purpose is to improve
the usefulness, confidence, and explainability of AI/match intelligence outputs
without modifying any deterministic cricket truth — scoring, DLS, results,
innings state, player stats, or historical-import eligibility remain entirely
unchanged.

**Audit outcome:** The codebase has a mature Phase 6B deterministic-vs-AI
boundary that is working well. The smallest safe Phase 8 implementation slice
has been identified and implemented:

1. Two new optional, backward-compatible fields — `confidence_score` and
   `limitations` — have been added to the shared `AiOutputMetadata` Pydantic
   model so every AI surface can expose model uncertainty and advisory caveats.
2. The win-probability prediction API (`GET /predictions/games/{id}/win-probability`)
   now includes an `ai_metadata` block in its response, making its advisory
   nature explicit to all consumers.
3. New Phase 8 tests validate the new fields and confirm no deterministic truth
   mutation occurs.
4. No model behaviour, scoring logic, DLS, or official cricket truth was changed.

---

## 2. Existing AI/Match Intelligence Inventory

| Surface | Module | Output Type | `ai_metadata` present | Notes |
|---------|--------|-------------|----------------------|-------|
| Delivery commentary | `backend/services/ai_commentary.py` | `COMMENTARY` | ✅ | Rule-based V1; LLM TODO |
| Match AI summary | `backend/services/ai_match_summary.py` | `SUMMARY` | ✅ | Rule-based V1; LLM TODO |
| Match AI summary (rich) | `backend/services/match_ai_service.py` + `backend/sql_app/match_ai.py` | `SUMMARY` | ✅ | Full schema incl. decisive phases, momentum shifts |
| Player AI insights | `backend/services/ai_player_insights.py` | `INSIGHT` | ✅ | Rule-based V1; LLM TODO |
| Win probability | `backend/services/prediction_service.py` + `backend/routes/prediction.py` | `INSIGHT` | ❌ → ✅ (Phase 8) | ML (XGBoost) + rule-based fallback; `ai_metadata` **added in Phase 8** |
| Case study AI block | `backend/services/match_context_service.py` | Rule-based narrative | Partial | No `AiOutputMetadata`; in case-study composite; not surfaced standalone |
| Coach report | `backend/services/coach_report_service.py` | `REPORT` | Via coach-report schemas | Requires human review |
| Tactical suggestions | `backend/services/tactical_suggestion_engine.py` | `RECOMMENDATION` | Via suggestion schema | Advisory only |

---

## 3. Deterministic vs Advisory Boundary Assessment

### 3.1 Boundary enforcement infrastructure (Phase 6B — unchanged)

| Component | Location | Status |
|-----------|----------|--------|
| `AiOutputType` enum | `backend/domain/ai_boundary.py` | Stable ✅ |
| `OFFICIAL_TRUTH_FIELDS` frozenset | `backend/domain/ai_boundary.py` | Stable ✅ |
| `AiOutputMetadata` Pydantic model | `backend/domain/ai_boundary.py` | Extended in Phase 8 (additive only) |
| `validate_no_official_truth_mutation()` guard | `backend/domain/ai_boundary.py` | Stable ✅ |

### 3.2 Deterministic systems (protected — must not change)

- Scoring: `backend/services/scoring_service.py`
- DLS: `backend/services/dls_service.py` / `dls.py`
- Results: `backend/routes/results.py`
- Innings state: managed in `backend/sql_app/models.py:Game`
- Official player stats: `backend/sql_app/models.py:PlayerProfile`
- Historical import truth: `backend/routes/historical_import.py` + `backend/services/historical_stats_aggregation_service.py`
- Training eligibility: `backend/services/historical_stats_aggregation_service.py`

### 3.3 Advisory AI systems (in scope for Phase 8 improvements)

All outputs carry `ai_metadata.is_official_truth = False`.
AI services may explain, summarise, recommend, or communicate — not calculate official facts.

---

## 4. Model/Prediction Endpoint Audit

### 4.1 Win Probability (`GET /predictions/games/{game_id}/win-probability`)

**Input contract (from `prediction_service.py`):**

| Field | Type | Source |
|-------|------|--------|
| `current_inning` | int (1 or 2) | `Game.current_inning` |
| `total_runs` | int | `Game.total_runs` |
| `total_wickets` | int | `Game.total_wickets` |
| `overs_completed` | int | `Game.overs_completed` |
| `balls_this_over` | int | `Game.balls_this_over` |
| `overs_limit` | int \| None | `Game.overs_limit` |
| `target` | int \| None | `Game.target` |
| `match_type` | str | `Game.match_type` |

**Output contract (pre-Phase 8):**

```json
{
  "batting_team_win_prob": 65.3,
  "bowling_team_win_prob": 34.7,
  "confidence": 75.5,
  "factors": { ... },
  "batting_team": "...",
  "bowling_team": "...",
  "game_id": "..."
}
```

**Output contract (Phase 8 addition — additive only):**

```json
{
  "batting_team_win_prob": 65.3,
  "bowling_team_win_prob": 34.7,
  "confidence": 75.5,
  "factors": { ... },
  "batting_team": "...",
  "bowling_team": "...",
  "game_id": "...",
  "ai_metadata": {
    "output_type": "insight",
    "is_official_truth": false,
    "requires_review": false,
    "grounded_in_data": true,
    "confidence_score": 0.755,
    "limitations": [
      "Advisory only — not official match truth.",
      "Prediction accuracy increases as the match progresses.",
      "Rule-based fallback is used when ML model is unavailable.",
      "Does not account for weather, pitch, or tactical changes."
    ]
  }
}
```

**Notes:**
- `confidence` (0–100, from prediction_service) is normalised to `confidence_score` (0.0–1.0) in `ai_metadata`.
- All other existing fields are unchanged.
- No official truth fields appear in `ai_metadata`.

### 4.2 ML Models

| Model | Location | Format | Fallback |
|-------|----------|--------|---------|
| Win probability predictor | `backend/services/ml_model_service.py` | XGBoost | Rule-based (`prediction_service.py`) |
| Score predictor | `backend/services/ml_model_service.py` | XGBoost | Rule-based |

Both models are loaded lazily. If unavailable, the rule-based fallback runs
silently and `prediction_method` in `factors` reflects which path was taken.

---

## 5. Frontend Dashboard/Analyst Workspace Audit

### 5.1 AI surfaces in frontend

| View | Component | AI surface | `ai_metadata` displayed |
|------|-----------|-----------|------------------------|
| Analyst Workspace | `AnalystWorkspaceView.vue` | AI match summary tab | Partially (advisory label present) |
| Match Case Study | `MatchCaseStudyView.vue` | AI block (`ai.match_summary`) | No dedicated metadata rendering |
| Win Probability Widget | In-game overlay | `prediction:update` Socket.IO event | No (advisory label not yet shown) |
| Player Profile | PlayerProfileView | AI insights block | No dedicated metadata rendering |

### 5.2 Phase 8 frontend scope decision

No frontend changes are in scope for this Phase 8 implementation slice.
The `ai_metadata` field is now available in the win-probability API response
for future frontend consumption. A follow-on slice (Phase 8.1 or later) may
render `confidence_score` and `limitations` in the win-probability widget and
other AI surfaces.

**Rationale:** The issue guidance specifies "prefer an audit-first PR" and
"keep implementation small". Frontend rendering of confidence/limitations is
a separate, visible change and will be gated on explicit user approval.

---

## 6. Data Quality and Source-Grounding Assessment

| Service | Data source | Grounded | Quality |
|---------|------------|---------|---------|
| Commentary | Per-delivery game state (`Game`, `Delivery` models) | ✅ | High |
| Match AI summary | MatchCaseStudy (derived from game + deliveries) | ✅ | High |
| Player AI insights | `PlayerProfile` + `PlayerForm` models | ✅ | Medium (dependent on data entry completeness) |
| Win probability | `Game` live state + ML model | ✅ | Medium (ML accuracy depends on training data) |
| Case study AI block | MatchCaseStudy composite | ✅ | High |

All services set `grounded_in_data=True` (default) because outputs are derived
from stored, validated match data — not hallucinated. The ML win predictor
relies on historical training data whose completeness varies by match format.

---

## 7. Confidence/Explainability/Limitations Gaps

### Pre-Phase 8 gaps identified

| Gap | Severity | Phase 8 action |
|-----|---------|----------------|
| `AiOutputMetadata` has no `confidence_score` field | Medium | **Fixed** — `confidence_score: float | None` added |
| `AiOutputMetadata` has no `limitations` field | Medium | **Fixed** — `limitations: list[str]` added |
| Win-probability API response has no `ai_metadata` | High | **Fixed** — `ai_metadata` block added to response |
| Frontend win-probability widget shows no advisory label | Low | Deferred to follow-on slice |
| Match case study AI block has no `AiOutputMetadata` | Low | Deferred (composite endpoint; low risk) |
| Player insights API missing `model_version` | Low | Out of scope for Phase 8 |

---

## 8. Latency/Cost/Caching Assessment

| Service | Latency | Cost | Caching |
|---------|---------|------|---------|
| Commentary (rule-based) | <5 ms | Zero | No cache needed |
| Match AI summary (rule-based) | 50–200 ms (DB query) | Zero | No change |
| Player AI insights (rule-based) | 50–200 ms (DB query) | Zero | No change |
| Win probability (ML) | 1–20 ms (CPU inference) | Zero | Emitted per delivery via Socket.IO |
| Win probability (rule-based fallback) | <1 ms | Zero | No change |

No expensive LLM calls are made in any of the above paths. All AI services are
rule-based or local ML inference. Event-triggered, not always-running loops.
No caching changes are required in this phase.

---

## 9. Proposed Smallest Safe Implementation Slice

**Implemented in this PR:**

1. **`backend/domain/ai_boundary.py`** — Add optional `confidence_score` and
   `limitations` fields to `AiOutputMetadata`. Both have safe defaults (`None`
   and `[]` respectively) so all existing schemas requiring no arguments are
   unaffected.

2. **`backend/routes/prediction.py`** — Import `AiOutputMetadata`/`AiOutputType`
   and attach an `ai_metadata` block to the win-probability response, converting
   the existing `confidence` (0–100) field to `confidence_score` (0.0–1.0) in
   the metadata.

3. **`backend/tests/test_phase_8_ai_analytics.py`** — New test module covering:
   - Phase 8 field validation (confidence range, limitations type)
   - Normalisation from 0–100 to 0.0–1.0
   - No official truth fields in advisory metadata
   - `validate_no_official_truth_mutation` guard on advisory payloads
   - Regression tests confirming existing Phase 6B schema behaviour is unchanged

---

## 10. Allowed and Protected Files

### Files changed in Phase 8

| File | Change type | Reason |
|------|------------|--------|
| `backend/domain/ai_boundary.py` | Additive extension | Add `confidence_score`, `limitations` to `AiOutputMetadata` |
| `backend/routes/prediction.py` | Additive extension | Add `ai_metadata` to win-probability response |
| `backend/tests/test_phase_8_ai_analytics.py` | New file | Phase 8 test coverage |
| `docs/PHASE_8_AI_ANALYTICS_MATCH_INTELLIGENCE_AUDIT_AND_SPEC_LOCK.md` | New file | Required deliverable |

### Protected files (must not be changed in Phase 8)

| File | Protection reason |
|------|------------------|
| `backend/services/scoring_service.py` | Official cricket truth — scoring |
| `backend/services/dls_service.py` / `dls.py` | Official cricket truth — DLS |
| `backend/routes/results.py` | Official cricket truth — match results |
| `backend/sql_app/models.py` (scoring fields) | Official data models |
| `backend/services/historical_stats_aggregation_service.py` | Training eligibility |
| `backend/routes/historical_import.py` | Historical import truth |
| `backend/domain/ai_boundary.py:OFFICIAL_TRUTH_FIELDS` | Core protection set — add only, never remove |
| `backend/domain/ai_boundary.py:validate_no_official_truth_mutation` | Core guard — must not be weakened |

---

## 11. Tests Required

| Test | File | Status |
|------|------|--------|
| `confidence_score` defaults to None | `test_phase_8_ai_analytics.py` | ✅ |
| `limitations` defaults to empty list | `test_phase_8_ai_analytics.py` | ✅ |
| `confidence_score` valid range (0.0–1.0) | `test_phase_8_ai_analytics.py` | ✅ |
| `confidence_score` rejects values >1 | `test_phase_8_ai_analytics.py` | ✅ |
| `confidence_score` rejects values <0 | `test_phase_8_ai_analytics.py` | ✅ |
| `limitations` accepts list of strings | `test_phase_8_ai_analytics.py` | ✅ |
| `is_official_truth` still False with new fields | `test_phase_8_ai_analytics.py` | ✅ |
| `model_dump()` includes Phase 8 fields | `test_phase_8_ai_analytics.py` | ✅ |
| `_PREDICTION_LIMITATIONS` is non-empty list | `test_phase_8_ai_analytics.py` | ✅ |
| Confidence normalised from 0–100 to 0.0–1.0 | `test_phase_8_ai_analytics.py` | ✅ |
| Prediction output type is INSIGHT | `test_phase_8_ai_analytics.py` | ✅ |
| `is_official_truth` is False in prediction metadata | `test_phase_8_ai_analytics.py` | ✅ |
| No official truth fields in `ai_metadata` dump | `test_phase_8_ai_analytics.py` | ✅ |
| Guard passes on clean advisory payload | `test_phase_8_ai_analytics.py` | ✅ |
| Guard blocks payload with `runs` field | `test_phase_8_ai_analytics.py` | ✅ |
| Existing commentary schema regression | `test_phase_8_ai_analytics.py` | ✅ |
| Existing match summary schema regression | `test_phase_8_ai_analytics.py` | ✅ |
| Existing player insights schema regression | `test_phase_8_ai_analytics.py` | ✅ |

---

## 12. Rollback Plan

All Phase 8 changes are additive and backward-compatible. Rolling back is safe
at any point:

1. Revert `backend/domain/ai_boundary.py` to remove `confidence_score` and
   `limitations` fields. All existing schemas use default values and will be
   unaffected.
2. Revert `backend/routes/prediction.py` to remove the `ai_metadata` injection.
   The existing `confidence` field and all other prediction response fields are
   unchanged.
3. Delete `backend/tests/test_phase_8_ai_analytics.py`.
4. Delete this document.

No database migrations were required. No official cricket truth systems were
modified. Rollback is a pure code revert.

---

## 13. Phase 8 Readiness Recommendation

**Status: ✅ Ready — smallest safe slice implemented.**

- Audit complete. Existing AI/match intelligence inventory is fully documented.
- Deterministic vs advisory boundaries are clear and intact.
- The smallest safe implementation slice has been identified and delivered.
- `AiOutputMetadata` now supports `confidence_score` and `limitations` for all
  AI surfaces.
- Win-probability API explicitly exposes advisory `ai_metadata` in its response.
- All new Phase 8 tests pass.
- No official cricket truth was changed.
- No model behaviour was changed.
- No Phase 9 work was started.

**Remaining opportunities (deferred, require separate spec lock):**

- Frontend rendering of `confidence_score` and `limitations` in the
  win-probability widget and other AI surfaces.
- Adding `confidence_score` and `limitations` to the match AI summary and
  player insights endpoints (values can now be set via `AiOutputMetadata`).
- LLM integration to replace rule-based commentary/summary/insights (Phase 8.x
  or later; requires separate cost/governance approval).
- `model_version` field on AI insight outputs (useful for debugging).
