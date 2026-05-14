# PHASE 6B — DETERMINISTIC VS AI BOUNDARY ENFORCEMENT

## Status

Complete. Boundary enforcement only.

No agents, skills, routers, LLM workflows, dependencies, migrations, or runtime
scoring/DLS/historical-import behavior changed in this phase.

---

## 1) Purpose

Turn the Phase 6A architecture rules into enforceable repo-level boundaries so
that AI-adjacent code cannot calculate, overwrite, or mutate official cricket
truth.

Core rule:

```text
Deterministic systems calculate facts.
AI systems explain, summarize, recommend, or communicate.
```

Hard gate:

```text
No LLM may calculate, overwrite, or mutate official cricket truth.
```

---

## 2) Pre-Phase Audit Summary

### A. Deterministic systems audited (protected, unchanged)

| File | Role |
|------|------|
| `backend/services/scoring_service.py` | Per-ball scoring mutations |
| `backend/routes/gameplay.py` | Gameplay endpoints + live-bus emission |
| `backend/routes/dls.py` | DLS revised-target and par-score |
| `backend/routes/games_dls.py` | DLS preview/apply/reduce-overs |
| `backend/services/dls_service.py` | DLS calculation |
| `backend/domain/constants.py` | Cricket dismissal/extra rules |
| `backend/routes/gameplay.py` result endpoints | Official match result |
| `backend/services/snapshot_service.py` | Game state snapshot |
| `backend/routes/historical_import.py` | Historical import/training gates |
| `backend/routes/analytics_case_study.py` | Registry/provenance/training eligibility |

None of these files were changed. They remain the sole owners of official
cricket truth.

### B. AI-adjacent services audited

| File | Nature | Mutation risk before 6B |
|------|--------|------------------------|
| `backend/routes/ai.py` | Commentary endpoint | Low — reads only, returns text |
| `backend/services/ai_commentary.py` | Rule-based delivery commentary | No mutation — rule-based text generation |
| `backend/services/match_ai_service.py` | Mock match summary/commentary | No mutation — reads Game, returns summaries |
| `backend/services/ai_player_insights.py` | Rule-based player insights | No mutation — reads PlayerProfile, returns insights |
| `backend/services/coach_ai_pipeline.py` | Pose + ball tracking orchestration | No mutation — processes video files only |
| `backend/services/agent_budget.py` | Agent run budget scaffolding | No direct mutation — advisory only |
| `backend/sql_app/match_ai.py` | AI response Pydantic schemas | Schemas only — no DB writes |

**Audit conclusion:** No existing AI-adjacent service directly writes to official
cricket truth fields (runs, wickets, result, DLS target, training eligibility,
etc.). However, without explicit non-authoritative labelling and a guard module,
future AI code could silently add these fields to response payloads, and callers
could confuse AI summaries for official truth.

### C. Risky patterns identified

1. AI summary schemas (`MatchAiSummaryResponse`, `AiCommentaryResponse`,
   `PlayerAiInsights`) contained no `is_official_truth` flag or `output_type`
   classification before this phase. A caller could not distinguish them from
   authoritative data without reading the code.

2. No service-level guard existed to reject AI payloads that attempt to set
   official truth fields such as `runs`, `result`, `training_eligible`, etc.

3. Module docstrings for AI-adjacent services did not state that outputs are
   non-authoritative.

---

## 3) Guardrails Added

### 3A. `backend/domain/ai_boundary.py` (new file)

A small, zero-dependency boundary module containing:

- **`AiOutputType`** enum — classifies every AI output as one of:
  `commentary`, `insight`, `recommendation`, `report`, `summary`, `draft`.

- **`OFFICIAL_TRUTH_FIELDS`** frozenset — the complete set of field names
  representing official cricket truth that AI code must never write to.
  Covers: scoring fields (runs, balls, wickets), innings state, match result,
  scorecards, DLS fields, and historical-import/training-eligibility gates.

- **`AiOutputMetadata`** Pydantic model — embedded in every AI response schema.
  Fields: `output_type`, `is_official_truth = False`, `requires_review`,
  `grounded_in_data`. Makes the non-authoritative nature machine-readable.

- **`validate_no_official_truth_mutation(payload, context)`** — service-level
  guard function that raises `ValueError` if a dict produced by an AI-adjacent
  service contains any `OFFICIAL_TRUTH_FIELDS` key. Prevents AI code from
  accidentally producing payloads that could overwrite official match data.

### 3B. AI response schemas updated (non-breaking additions only)

All existing AI response schemas now embed `AiOutputMetadata` as a new field
with a safe default. No existing fields were removed or renamed.

| Schema | Location | `output_type` | `is_official_truth` |
|--------|----------|---------------|---------------------|
| `AiCommentaryResponse` | `backend/services/ai_commentary.py` | `commentary` | `False` |
| `MatchAiCommentaryResponse` | `backend/sql_app/match_ai.py` | `commentary` | `False` |
| `MatchAiSummaryResponse` | `backend/sql_app/match_ai.py` | `summary` | `False` |
| `PlayerAiInsights` | `backend/services/ai_player_insights.py` | `insight` | `False` |

### 3C. Non-authoritative docstrings added

The following AI-adjacent service files received updated module and/or class
docstrings that explicitly state the Phase 6B boundary rule:

- `backend/services/ai_commentary.py` — module docstring
- `backend/services/match_ai_service.py` — module docstring + class docstring
- `backend/services/ai_player_insights.py` — module docstring
- `backend/services/coach_ai_pipeline.py` — module docstring
- `backend/services/agent_budget.py` — module comment

---

## 4) Tests Added

File: `backend/tests/test_phase_6b_ai_boundary.py` — 37 tests in 6 classes.

| Class | What it proves |
|-------|---------------|
| `TestAiBoundaryModule` | Boundary module imports; `OFFICIAL_TRUTH_FIELDS` completeness |
| `TestValidateNoOfficialTruthMutation` | Guard rejects runs, wickets, result, dls_target, training_eligible, batting_scorecard; clean payloads pass |
| `TestAiCommentaryResponseMetadata` | `AiCommentaryResponse` carries `is_official_truth=False` and `output_type=commentary` |
| `TestMatchAiSummaryResponseMetadata` | `MatchAiSummaryResponse` carries `is_official_truth=False` and `output_type=summary` |
| `TestMatchAiCommentaryResponseMetadata` | `MatchAiCommentaryResponse` carries `is_official_truth=False` |
| `TestPlayerAiInsightsMetadata` | `PlayerAiInsights` carries `is_official_truth=False` and `output_type=insight` |
| `TestDeterministicSystemsAreAiIndependent` | `scoring_service`, `dls_service`, `domain/constants` do not import AI-adjacent modules |
| `TestTrainingEligibilityProtected` | Guard blocks `training_eligible`, `is_finalized`, `validation_status`, `applied_game_id` |
| `TestAiOutputTypeCoverage` | Every `AiOutputType` value produces valid `AiOutputMetadata` with `is_official_truth=False` |

---

## 5) Files Changed

| File | Change | Why |
|------|--------|-----|
| `backend/domain/ai_boundary.py` | **New** | Core boundary guard module |
| `backend/services/ai_commentary.py` | Updated module docstring + import + `AiCommentaryResponse.ai_metadata` field | Non-authoritative labelling |
| `backend/services/ai_player_insights.py` | Updated module docstring + import + `PlayerAiInsights.ai_metadata` field | Non-authoritative labelling |
| `backend/services/match_ai_service.py` | Updated module docstring + class docstring | Non-authoritative labelling |
| `backend/services/coach_ai_pipeline.py` | Updated module docstring | Non-authoritative labelling |
| `backend/services/agent_budget.py` | Updated module comment | Non-authoritative labelling |
| `backend/sql_app/match_ai.py` | Updated module docstring + import + `ai_metadata` fields on `MatchAiCommentaryResponse` and `MatchAiSummaryResponse` | Non-authoritative labelling |
| `backend/tests/test_phase_6b_ai_boundary.py` | **New** | 37 boundary tests |
| `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md` | **New** | This spec-lock document |
| `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` | Updated Phase 6B entry | Completion evidence |

---

## 6) Files NOT Changed

The following protected files were audited but not changed:

- `backend/services/scoring_service.py`
- `backend/routes/gameplay.py`
- `backend/routes/dls.py`
- `backend/routes/games_dls.py`
- `backend/services/dls_service.py`
- `backend/domain/constants.py`
- `backend/routes/historical_import.py`
- `backend/routes/analytics_case_study.py`
- `backend/services/historical_import_apply_service.py`
- `backend/services/historical_import_preview.py`
- All migrations under `backend/alembic/versions/`
- All frontend files

No scoring, DLS, results, gameplay, historical import, or training-eligibility
behavior was changed.

---

## 7) Confirmation Statements

- **Boundary enforcement only.** No agents, skills, routers, or LLM workflows
  were implemented.
- **No runtime AI provider calls** were added.
- **No official cricket truth behavior changed.** Scoring, DLS, results, and
  historical import systems are identical to their pre-6B state.
- **No migrations added.** The `ai_metadata` field is a pure Pydantic schema
  addition with a safe default; it requires no database column.
- **No new runtime dependencies added.** The boundary module uses only stdlib +
  Pydantic (already a project dependency).
- **No frontend files touched.** Frontend CI (type-check, build, fake-data guard)
  is unaffected.

---

## 8) Test Validation Evidence

```
pytest backend/tests/test_health.py backend/tests/test_results_endpoint.py
→ 9 passed

pytest backend/tests/test_dls_calculations.py -v --tb=short
→ 21 passed

pytest backend/tests/test_analyst_pro_features.py -v --tb=short
→ 18 passed

pytest backend/tests/test_match_ai_summary.py -v
→ 5 passed

pytest backend/tests/test_phase_6b_ai_boundary.py -v
→ 37 passed
```

---

## 9) Acceptance Criteria Checklist

- [x] Phase 6B audit is documented in PR body and this spec-lock.
- [x] Deterministic vs AI boundary is enforceable through tests and guard code.
- [x] AI-adjacent systems are explicitly non-authoritative for official cricket truth.
- [x] Tests prove AI cannot mutate official scoring/result/DLS/historical-training truth.
- [x] Existing scoring/result/DLS/historical import behavior is unchanged.
- [x] No new agents, skills, routers, or LLM workflows built.
- [x] No new infrastructure added.
- [x] No unnecessary migrations or dependencies added.
- [x] CI passes.

---

## 10) Files Reviewed For This Audit

- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md`
- `backend/routes/ai.py`
- `backend/services/ai_commentary.py`
- `backend/services/match_ai_service.py`
- `backend/services/ai_player_insights.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/services/agent_budget.py`
- `backend/services/scoring_service.py`
- `backend/routes/gameplay.py`
- `backend/routes/dls.py`
- `backend/routes/games_dls.py`
- `backend/services/dls_service.py`
- `backend/domain/constants.py`
- `backend/sql_app/match_ai.py`
- `backend/routes/historical_import.py`
- `backend/routes/analytics_case_study.py`
- `backend/tests/test_results_endpoint.py`
- `backend/tests/test_dls_calculations.py`
- `backend/tests/test_analyst_pro_features.py`
- `backend/tests/test_match_ai_summary.py`
