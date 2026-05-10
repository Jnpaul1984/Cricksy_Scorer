# PHASE 4A — Analyst System Architecture Audit and Spec Lock

**Repository:** `Jnpaul1984/Cricksy_Scorer`
**Date:** 2026-05-10
**Phase:** 4A — Pre-implementation audit and spec lock
**Scope:** Docs-only. No app code, migration, dependency, or workflow changes in this phase.

**Source Documents Reviewed:**
- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- `docs/PHASE_1D_OPEN_PR_TRIAGE_AND_CHECKLIST_NUMBERING.md`
- `docs/PHASE_3A_COACH_VIDEO_HARDENING_AUDIT_AND_SPEC_LOCK.md`
- `FAKE_DATA_AUDIT_REPORT.md`

---

## 1. Analyst System Vision Summary

The Cricksy Analyst System is a planned AI-assisted sports intelligence platform that will allow analysts, coaches, media teams, scouts, and organizations to transform raw cricket match data into tactical intelligence, visual storytelling, and performance insights.

It is not merely a statistics dashboard. The full vision spans:

- a cricket intelligence engine (query, aggregate, compare)
- a tactical analysis workspace (turning-point detection, pressure mapping)
- a media production support system (podcast prep, episode packages)
- a coach-assistance platform (evidence-based coaching discussions)
- a scouting and development tool (talent identification and growth curves)
- the eventual foundation of a Sports Intelligence Institute

The system is designed around a weekly production cycle: research → data pull → tactical breakdown → podcast preparation → recording support → media export → knowledge capture.

**Phase 4A does not build any part of the Analyst System.** Phase 4A converts the strategic vision documents into a repo-grounded, safe, and audited MVP build plan.

---

## 2. Source Document Synthesis

### Blueprint v1 (`docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`)

Defines eight system layers:

| Layer | Purpose | MVP Relevance |
|---|---|---|
| 1 — Data Warehouse | Structured cricket intelligence storage | Existing via Game/Delivery/Player models |
| 2 — Query Engine | Analyst search and filter | Partially exists via `/api/analyst/query` |
| 3 — Visualization Engine | Charts and dashboards | Partial: analytics chart components exist |
| 4 — AI Intelligence Engine | Insights beyond statistics | Partial: mock AI summaries only |
| 5 — Analyst Workspace | Saved reports, filters, notes | Partial: `AnalystWorkspaceView.vue` exists but data is incomplete |
| 6 — Tactical Board | Interactive cricket field | Not built |
| 7 — Story and Media Engine | Podcast/social outputs | Not built |
| 8 — Export Engine | PDF/PNG/CSV distribution | Partial: CSV/JSON in analyst routes; PDF exists for video only |

**MVP Gap Zones:** Layers 6, 7, and most of Layer 8 are unbuilt. Layers 1–5 have partial implementations.

### Workflow v1 (`docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`)

Defines a seven-day weekly production cycle driven by the podcast/media use case. Key workflow requirements:

- Day 1: Match selection, research workspace creation
- Day 2: Data pull and first analysis (innings summary, phase analysis, partnerships)
- Day 3: Tactical breakdown (matchups, pressure moments, bowling plans)
- Day 4: Podcast prep package (outline, talking points, charts, stat cards)
- Day 5: Recording support (live view, quick search, quote marking)
- Day 6: Media export (clips, graphics, captions, social assets)
- Day 7: Knowledge capture (reusable insights, player/team profiles)

**Key insight from Workflow v1:** The immediate, highest-value action is enabling the analyst to select one completed match, view it, generate a few charts, and export a brief PDF. This is the minimum success test stated in the document.

---

## 3. Existing Repo Capability Audit

### 3.1 Summary of Existing Analyst-Adjacent Systems

| Capability Area | Status | Notes |
|---|---|---|
| Match data access (completed/live) | ✅ Exists | `GET /games/{id}`, deliveries in JSON |
| Innings scorecard data | ✅ Exists | `batting_scorecard`, `bowling_scorecard` on Game model |
| Delivery-level data (ball-by-ball) | ✅ Exists | `game.deliveries` JSON; normalized `Delivery` table |
| Player profile and stats | ✅ Exists | `PlayerProfile`, `PlayerSummary`, `PlayerForm` models |
| Phase analysis API | ✅ Exists | `GET /analytics/games/{id}/phase-map` |
| Pressure map API | ✅ Exists | `GET /analytics/games/{id}/pressure-map` |
| Win probability API | ✅ Exists | `GET /predictions/games/{id}/win-probability` |
| Innings grade API | ✅ Exists | `GET /analytics/games/{id}/innings/{n}/grade` |
| Player career summary API | ✅ Exists | `GET /analytics/players/{id}/career-summary` |
| Analyst query API | ✅ Exists | `POST /api/analyst/query` |
| Analyst export API (CSV/JSON) | ✅ Exists | Players, matches, player-form exports |
| AI match summary API | ⚠️ Mock only | `GET /api/analyst/matches/{id}/ai-summary` — no LLM |
| Match context package API | ✅ Exists | `GET /api/analyst/matches/{id}/context-package` |
| AI match commentary API | ⚠️ Mock only | `GET /matches/{id}/ai-commentary` — no LLM |
| Analyst workspace (frontend) | ⚠️ Partial | `AnalystWorkspaceView.vue` exists with filters and match list |
| Match case study (frontend) | ✅ Exists | `MatchCaseStudyView.vue` with phase breakdowns |
| Chart components | ✅ Multiple | `ChartBar`, `ChartLine`, `WinProbabilityChart`, `RunRateComparison`, `PhaseSplits`, `WagonWheel`, `PartnershipHeatmap` |
| PDF export | ⚠️ Video only | `pdf_export_service.py` exists for Coach Pro Plus; not analyst-scoped |
| Frontend CSV/JSON export | ⚠️ Mock data | `ExportUI.vue` generates hardcoded fake rows — critical risk |
| RBAC / tier gating | ✅ Exists | `analyst_pro` and `org_pro` roles in pricing config |
| AI commentated delivery | ✅ Exists (mock) | `POST /ai/commentary` — deterministic, no LLM |

---

## 4. Existing Match and Scoring Data Access Audit

### Match Model (`backend/sql_app/models.py`)

The `Game` model holds:

- `id` (UUID) — primary key
- `status` (GameStatus enum: not_started, started, in_progress, innings_break, live, completed, abandoned)
- `team_a`, `team_b` (JSON) — team and player lists
- `total_runs`, `total_wickets`, `overs_completed`, `balls_this_over`
- `batting_scorecard`, `bowling_scorecard` (JSON) — current innings scorecards
- `deliveries` (JSON) — all deliveries with `inning_no`, `over_number`, `ball_number`, `runs_scored`, `is_wicket`, extras
- `target`, `result`, `toss_winner_team`, `decision`
- `match_type`, `overs_limit`, `days_limit`
- `current_inning`, `current_striker_id`, `current_bowler_id`

**Analyst-relevant findings:**

- Completed match data is accessible via `GET /games/{game_id}` (no auth required on the core game endpoint)
- Deliveries are stored in JSON format on the Game row — full ball-by-ball data is present
- Batting and bowling scorecards are stored as JSON per innings
- The dual-write scorecard service (`scorecard_service.py`) also writes normalized `BattingScorecard`, `BowlingScorecard`, and `Delivery` table rows
- Innings-level stats for prior innings must currently be aggregated from deliveries — there is no separate `InningsScore` table

### Delivery Model (normalized)

`Delivery` ORM model exists with:

- `game_id`, `inning_no`, `over_number`, `ball_number`, `delivery_number`
- `striker_id`, `bowler_id`, `non_striker_id`
- `runs_scored`, `is_wicket`, `wicket_type`, `fielder_id`
- `extra_type`, `extra_runs`
- `score_before`, `score_after`, `wickets_before`, `wickets_after`
- `commentary` (optional)

**This normalized Delivery table is the strongest data foundation for analyst queries.** It allows filtering by player, phase, delivery type, and outcome without parsing JSON.

### Match Access Routes Audit

| Route | Auth | Analyst-relevant |
|---|---|---|
| `GET /games/{id}` | None | Full game state including deliveries |
| `POST /games/{id}/deliveries` | None (scorer) | Scoring only |
| `GET /analytics/games/{id}/phase-map` | None | Phase stats |
| `GET /analytics/games/{id}/pressure-map` | None | Pressure data |
| `GET /predictions/games/{id}/win-probability` | None | Win probability |
| `GET /analytics/games/{id}/innings/{n}/grade` | None | Innings grade |
| `POST /api/analyst/query` | `analyst_pro` / `org_pro` | Players, matches, form, sessions |
| `GET /api/analyst/matches/export` | `analyst_pro` / `org_pro` | Match list CSV/JSON |
| `GET /api/analyst/matches/{id}/ai-summary` | `analyst_pro` / `org_pro` | AI-style match summary (mock) |
| `GET /api/analyst/matches/{id}/context-package` | `analyst_pro` / `org_pro` | Structured match context for LLM |
| `GET /matches/{id}/ai-commentary` | None | Mock AI commentary |
| `GET /analytics/players/{id}/career-summary` | None | Player career data |

**Gap:** There is no `GET /games?status=completed` list endpoint specifically for analysts to browse completed matches. The analyst workspace currently loads matches from an unverified source (audit of the Vue component data loading is required in Phase 4B).

---

## 5. Existing Completed and Live Match Data Availability Audit

- **Live matches:** Available via Socket.IO `state:update` events and `GET /games/{id}`. Phase analysis and pressure-map endpoints work on in-progress games.
- **Completed matches:** `GET /games/{id}` returns completed match state. The analyst query endpoint (`POST /api/analyst/query` with `entity: "matches"`) can list match records. Status filter capability is limited — the current query only lists all games without completed-only filtering.
- **Historical imported matches:** Not yet implemented. Phase 5 (Historical CSV Import) and Phase 6 (OCR/PDF import) are planned. No historical data pipeline currently exists. Analyst features must not depend on historical ingestion that has not been built.

**Risk:** The analyst system blueprint assumes broad historical data availability. Phase 4B must explicitly scope to completed live-scored matches only until historical ingestion is implemented.

---

## 6. Existing Delivery-Level Data Access Audit

Delivery-level data is available via two pathways:

**Pathway A — JSON field on Game:**
- `game.deliveries` is a JSON list on the `Game` table row
- Contains `inning_no`, `over_number`, `ball_number`, `runs_scored`, `is_wicket`, `extra_type`, `extra_runs`, and other delivery fields
- Access: `GET /games/{id}` returns deliveries in game snapshot
- Limitation: This is a flat JSON list; cross-match or player-level delivery queries require Python-side filtering

**Pathway B — Normalized `Delivery` ORM table:**
- Normalized `Delivery` rows created by dual-write pattern in `scorecard_service.py`
- Contains player IDs, innings numbers, runs, wickets, extras, and score progression
- Access: No public REST endpoint currently exposes the normalized Delivery table directly for analyst queries
- This is the stronger foundation for analyst delivery queries

**Gap for analysts:** No dedicated `GET /games/{id}/deliveries` endpoint exists that returns the normalized delivery table. Phase 4B must include this as a core API requirement before building delivery-level analyst visualizations.

---

## 7. Existing Analytics, Dashboard, and Frontend Audit

### Backend Analytics Services Found

| Service | File | Purpose |
|---|---|---|
| Phase analyzer | `backend/services/phase_analyzer.py` | Phase breakdown: powerplay/middle/death |
| Pressure analyzer | `backend/services/pressure_analyzer.py` | Delivery-by-delivery pressure scoring |
| Innings grade service | `backend/services/innings_grade_service.py` | A–D grade for innings performance |
| Prediction service | `backend/services/prediction_service.py` | Win probability and projected score |
| Player career analyzer | `backend/services/player_career_analyzer.py` | Career stats and form |
| Dismissal pattern analyzer | `backend/services/dismissal_pattern_analyzer.py` | Dismissal analysis |
| Match AI service | `backend/services/match_ai_service.py` | Mock AI summaries |
| Match context service | `backend/services/match_context_service.py` | Structured match context package |
| AI player insights | `backend/services/ai_player_insights.py` | Player AI insights |
| Scorecard service | `backend/services/scorecard_service.py` | Dual-write delivery/scorecard |
| Phase analyzer (route-level) | `backend/routes/phase_analysis.py` | Phase map, predictions, trends |

### Frontend Views Found

| View | File | Status |
|---|---|---|
| Analyst Workspace | `frontend/src/views/AnalystWorkspaceView.vue` | Partial — beta, filters work, match data source uncertain |
| Match Case Study | `frontend/src/views/MatchCaseStudyView.vue` | Exists — detailed match view with phase breakdown |
| Phase Analysis View | `frontend/src/views/PhaseAnalysisView.vue` | Exists — per-game phase analysis |
| Analytics View | `frontend/src/views/AnalyticsView.vue` | Exists — general analytics |
| Player Profile View | `frontend/src/views/PlayerProfileView.vue` | Exists — player profiles and stats |
| Multi Player Comparison | `frontend/src/views/MultiPlayerComparisonView.vue` | Exists — player comparisons |
| Tournament Dashboard | `frontend/src/views/TournamentDashboardView.vue` | Exists |

---

## 8. Existing Chart and Visualization Component Audit

All chart components live in `frontend/src/components/analytics/`.

| Component | Description | Backend-wired? |
|---|---|---|
| `ChartBar.vue` | Bar chart wrapper | Requires data prop |
| `ChartLine.vue` | Line chart wrapper | Requires data prop |
| `WinProbabilityChart.vue` | Live win probability bars and score prediction | Yes — calls prediction endpoint |
| `RunRateComparison.vue` | Run rate comparison chart | Requires data prop |
| `PhaseSplits.vue` | Phase comparison breakdown | Requires data prop |
| `WagonWheel.vue` | Shot map / wagon wheel | Requires data prop (likely delivery-level) |
| `PartnershipHeatmap.vue` | Partnership visualization | Requires data prop |

**Additional components used in analyst contexts:**

| Component | File | Notes |
|---|---|---|
| `MiniSparkline.vue` | `frontend/src/components/MiniSparkline.vue` | Win probability trend sparks in analyst workspace |
| `ImpactBar.vue` | `frontend/src/components/ImpactBar.vue` | Net impact indicator in analyst match list |
| `AiCalloutsPanel.vue` | `frontend/src/components/AiCalloutsPanel.vue` | AI insight callouts panel |
| `PhaseAnalysisWidget.vue` | `frontend/src/components/PhaseAnalysisWidget.vue` | Phase widget for dashboards |
| `PhaseTimelineWidget.vue` | `frontend/src/components/PhaseTimelineWidget.vue` | Timeline of phase changes |
| `PressureMapWidget.vue` | `frontend/src/components/PressureMapWidget.vue` | Pressure map widget |
| `WinProbabilityWidget.vue` | `frontend/src/components/WinProbabilityWidget.vue` | Inline win probability |
| `FormTrackerWidget.vue` | `frontend/src/components/FormTrackerWidget.vue` | Player form tracking |
| `PlayerCareerSummaryWidget.vue` | `frontend/src/components/PlayerCareerSummaryWidget.vue` | Career summary display |

**Visualization assessment:** The building blocks (bar, line, wagon wheel, phase splits, pressure map, win probability) already exist as Vue components. The primary gap is wiring them to complete, real backend data for analyst-focused views.

---

## 9. Existing Export and Report Capability Audit

### Backend Export Capabilities

| Capability | File | Format | Auth Required |
|---|---|---|---|
| Player data export | `backend/routes/analyst_pro.py` | CSV / JSON | `analyst_pro` or `org_pro` |
| Match data export | `backend/routes/analyst_pro.py` | CSV / JSON | `analyst_pro` or `org_pro` |
| Player form export | `backend/routes/analyst_pro.py` | CSV / JSON | `analyst_pro` or `org_pro` |
| PDF report (Coach video) | `backend/services/pdf_export_service.py` | PDF (reportlab) | Coach Pro Plus tier |

**Gap:** No analyst-specific PDF export exists. The workflow document explicitly requires a PDF podcast brief as the primary MVP export. This is the most critical export gap.

### Frontend Export Capabilities

**`ExportUI.vue` — CRITICAL FAKE DATA RISK**

The `ExportUI` component at `frontend/src/components/ExportUI.vue` is used in the `AnalystWorkspaceView`. It:

- presents a CSV/JSON download modal with format and filter options
- calls `generateExportData()` (lines 240–269) which returns a hardcoded list of three fake rows: `'Player A'`, `'Player B'`, `'Player C'` with fabricated dates, runs, strike rates, and dismissal types
- does NOT call any backend API
- downloads client-side-generated fake data

**This means that any CSV or JSON export from the analyst workspace currently produces fabricated data, not real match data.** This is a production fake-data risk and must be resolved before any analyst export capability is considered complete.

---

## 10. Existing AI and LLM Capability Audit

### AI Services Found

| Service | File | LLM Status |
|---|---|---|
| AI match summary | `backend/services/match_ai_service.py` | MOCK — deterministic from match data, no LLM |
| Match context package | `backend/services/match_context_service.py` | Data-only, no LLM call |
| AI commentary (delivery) | `backend/services/ai_commentary.py` | MOCK — template-based, no LLM |
| AI player insights | `backend/services/ai_player_insights.py` | MOCK — rule-based, no LLM |
| Coach AI pipeline | `backend/services/coach_ai_pipeline.py` | Exists for video analysis |
| Agent budget service | `backend/services/agent_budget.py` | Exists — AI usage tracking |
| AI usage logging | `backend/services/ai_usage.py` | Exists |

**Current AI status:** All analyst-relevant AI features are mock/deterministic implementations. The comment in `match_ai_service.py` explicitly states: `"TODO: Replace mock implementation with actual LLM call."` No production LLM integration currently exists for match analysis.

**This is both a constraint and an opportunity:** Mock AI summaries grounded in real match data are safer than real LLM calls with hallucination risk, and the mock pattern can be extended for MVP without requiring LLM API keys.

### AI Guardrail Observation

The workflow document already specifies the required guardrails:
- AI must cite the match data it used
- AI must avoid inventing unsupported claims
- Uncertain insights must be labeled tentative
- Coach approval required before publishing

The current mock implementation is inherently safe because it only generates deterministic outputs from real data. When real LLM calls are introduced, these guardrails must be enforced at the service layer.

---

## 11. Existing Role, RBAC, and Tier Capability Audit

### Role Definitions (`backend/config/pricing.py`)

| Role / Plan | Name | Analyst-relevant |
|---|---|---|
| `free` | Free Scoring | No analyst access |
| `player_pro` | Scorers Pro | No analyst access |
| `coach_pro` | Coach Pro | No analyst access |
| `coach_pro_plus` | Coach Pro Plus | No analyst access |
| `coach_live_ai` | Coach Live AI | No analyst access |
| `coach_live_ai_advanced` | Coach Live AI Advanced | No analyst access |
| `analyst_pro` | Analyst Pro | **Analyst access tier** |
| `org_pro` | Org Pro | **Analyst access tier** |

### RBAC Enforcement

- `backend/security.py` provides `require_roles(roles: list[str])` dependency
- `backend/routes/analyst_pro.py` enforces `require_roles(["analyst_pro", "org_pro"])` on all analyst endpoints
- `backend/services/entitlement_service.py` provides feature-level access checks based on tier
- `backend/services/agent_budget.py` provides AI usage tracking and budget limits

### Auth Flow

- JWT-based authentication via `OAuth2PasswordBearer`
- Access token signed with `APP_SECRET_KEY`
- User role stored in `User.role` (enum: `RoleEnum`)
- `security.get_current_user_optional` allows optional auth on public routes

### Analyst Tier Gaps

- `analyst_pro` tier exists in pricing config but no frontend pricing page UI for this tier has been audited as fully wired
- Analytics routes (`/analytics/games/...`) have NO auth enforcement — any user can access phase maps, pressure maps, and innings grades
- No export permission check beyond role — an analyst can export all players/matches regardless of organizational boundary

**Risk: Cross-organization data leakage.** The analyst export endpoints do not filter by organization. An `analyst_pro` user can currently export all player and match data in the system regardless of which organization they belong to. This is a critical isolation requirement for Phase 4B.

---

## 12. Existing Fake and Mock Data Risks Relevant to Analyst Dashboards

All findings from `FAKE_DATA_AUDIT_REPORT.md` remain active. The following are directly relevant to analyst dashboard integrity:

### Risk 1 — `AnalystWorkspaceView.vue` — Unresolved `topBowler` summary
- **File:** `frontend/src/views/AnalystWorkspaceView.vue`
- **Lines:** 129 (display: `{{ summary.topBowler || '—' }}`), 413 (`topBowler: null as string | null`)
- **Current state:** The `topBowler` field defaults to `null` (the audit report's `'J. Smith'` value was removed in a prior commit). The `null` fallback displays `—` in the UI.
- **Risk:** The field is never populated from real backend data — it will always show `—` until a backend endpoint computes the top bowler from real match data.
- **Severity:** Low-medium — shows `—` rather than fake data, but provides no real value. Remains a gap.
- **Fix required before Phase 4B launch:** Compute from real match data via a backend analytics call, or leave as `—` with clear "Not yet available" labelling.

### Risk 2 — `ExportUI.vue` — Hardcoded fake export rows
- **File:** `frontend/src/components/ExportUI.vue`
- **Lines:** 240–269 — `generateExportData()` returns a hardcoded list of three fake rows: `'Player A'`, `'Player B'`, `'Player C'`
- **Risk:** Analyst CSV/JSON downloads contain fabricated data: fake player names, fake run/ball counts, hardcoded dates
- **Severity:** Critical — analyst exports from the workspace are entirely fake
- **Fix required before Phase 4B launch:** Replace with real backend API call to analyst export endpoints; remove `generateExportData()` entirely

### Risk 3 — `DevDashboardWidget.vue` — Celebrity player cards
- **File:** `frontend/src/components/DevDashboardWidget.vue`
- **Risk:** Virat Kohli, MS Dhoni, Jasprit Bumrah hardcoded fallback player cards
- **Severity:** Low for analyst (not in analyst workspace), but must not be introduced to analyst context
- **Fix required:** Do not add DevDashboardWidget to any analyst view

### Risk 4 — `MultiPlayerComparisonWidget.vue` — Celebrity comparison generator
- **File:** `frontend/src/components/MultiPlayerComparisonWidget.vue`
- **Risk:** Celebrity fallback data when no players loaded
- **Severity:** Low for analyst if empty-state is shown instead, but requires guarding in analyst context

### Risk 5 — Match AI summaries are labeled "mock" in code but not in UI
- **File:** `backend/services/match_ai_service.py` — explicit "MOCK" comment, no LLM
- **Risk:** If AI summaries are displayed in analyst workspace without a "tentative" or "system-generated" label, analysts may treat them as authoritative
- **Severity:** Medium — UI must visibly mark AI outputs as tentative/system-generated until real LLM grounding is verified

### Risk 6 — `FanFeedWidget.vue` — hardcoded highlights
- **Severity:** Low — not in analyst workspace, but confirm it is not reused there

---

## 13. Analyst MVP Scope

The MVP must allow one analyst to complete the minimum success test defined in the Workflow document:

> Select one completed match → generate match summary → generate 3 core visuals → create 5 talking points → prepare coach prompts → export a PDF brief → export at least one PNG stat card → save the workspace for later review.

### MVP Scope Items

**Backend (new or hardened):**

1. `GET /api/analyst/matches?status=completed` — List completed matches for analyst selection
2. `GET /api/analyst/matches/{match_id}` — Full match detail for analyst dashboard (real match data, not relying on raw game endpoint)
3. `GET /api/analyst/matches/{match_id}/deliveries` — Ball-by-ball delivery data via normalized `Delivery` table
4. `GET /api/analyst/matches/{match_id}/phase-summary` — Phase-level run rates, wickets, dot balls (may wrap existing phase analyzer)
5. `GET /api/analyst/matches/{match_id}/partnerships` — Partnership breakdown per innings
6. `GET /api/analyst/matches/{match_id}/pdf-brief` — Analyst PDF export (talking points, summary, key stats)
7. Organization-scoped data isolation on all analyst endpoints (filter by organization membership)

**Frontend (new or hardened):**

1. Match selection flow in `AnalystWorkspaceView.vue` — real backend-wired match list, no fake data
2. Match intelligence panel — innings summary, phase breakdown, top performers
3. Core chart wiring — run progression, wickets timeline, phase comparison using real data
4. AI summary display with "Tentative / System-generated" label
5. Podcast prep section — talking points input, workspace notes, coach prompts
6. PDF brief export — calls backend PDF endpoint, not client-side generation
7. Fix `ExportUI.vue` — replace `generateExportData()` with real backend call
8. Fix `topBowler: 'J. Smith'` — compute from real data or show `—`

**Infrastructure/Governance:**

1. Organization isolation enforced on all analyst data endpoints
2. Export permission check (analyst_pro or org_pro)
3. "Tentative" label on all AI/LLM-generated content
4. No fake data introduction

### MVP Non-requirements (must not block MVP)

- Historical match data (Phase 5/6 dependency)
- Wagon wheel / shot maps (delivery placement data not collected in current scorer)
- Real LLM integration (mock AI is acceptable at MVP)
- Podcast recording support view (Day 5 workflow)
- Social media export helper (Day 6 workflow)
- Animated tactical replay
- Multi-sport expansion
- Academy/institute features
- OBS integration
- Video clip timestamps

---

## 14. Non-MVP and Future Scope

These items must not be attempted until the MVP is stable and gated:

| Feature | Phase Gate |
|---|---|
| Real LLM analyst assistant | After MVP + AI guardrail validation |
| Historical match data queries | After Phase 5 (CSV) or Phase 6 (OCR) |
| Wagon wheel (ball placement) | Requires delivery placement data collection |
| Pitch maps | Requires delivery placement data |
| Heatmaps with real delivery zones | Requires delivery placement data |
| Animated tactical replay | Post-MVP visualization phase |
| Social media card generator | After PDF brief MVP is proven |
| OBS / broadcast integration | Long-term media workflow |
| Sports Intelligence Institute | Multi-phase, post-MVP |
| Multi-sport expansion | Post-cricket analyst MVP |
| Conversational AI (natural language queries) | After real LLM integration |
| Podcast episode scheduling/publishing | Media workflow phase |
| Approval workflow with coach sign-off | After workspace foundation |
| Analyst certification modules | Institute phase |
| Opposition scouting profiles | Requires historical data depth |
| Venue analysis | Requires historical multi-match data per venue |

---

## 15. First Analyst Persona and Workflow Target

### Primary MVP Persona: Podcast Analyst / Intelligence Lead

This is the persona described most concretely in `ANALYST_PRODUCTION_WORKFLOW_V1.md`.

**Characteristics:**
- Uses Cricksy weekly to produce one podcast episode
- Works with completed match data
- Needs a match summary, phase breakdown, a few charts, talking points, and a PDF brief
- Does not require live match scoring access during analysis
- Wants to save their workspace and return to it
- Produces content for a coach or on-camera analyst to review

**Primary workflow target:**
> The analyst selects one recently-completed match → reviews innings summary and phase breakdown → identifies the key turning point → builds 3–5 talking points → exports a PDF podcast brief.

This is the safest workflow to implement first because:
- It requires only completed match data (no live dependencies)
- It does not require delivery placement data (no wagon wheels or pitch maps)
- The backend data is already substantially present
- The most critical gaps (PDF export, real match list, data isolation) are well-defined

---

## 16. Recommended First Dashboard and Workspace Slice

### Recommended: Match Intelligence Dashboard

Based on the audit and the workflow document (Priority 1 dashboard), the first buildable analyst dashboard slice is:

**Match Intelligence Dashboard — Single Match View**

Fields required (all from existing `Game` model or existing analytics endpoints):

| Data Element | Source | Status |
|---|---|---|
| Match summary (teams, result, overs) | `GET /games/{id}` | Available |
| Innings scores | `game.batting_scorecard` / deliveries | Available |
| Run progression by over | Delivery data aggregated | Available |
| Wickets timeline | `deliveries` where `is_wicket=True` | Available |
| Partnerships | Delivery data with striker changes | Needs aggregation endpoint |
| Phase run rates | `GET /analytics/games/{id}/phase-map` | Available |
| Top performers | `batting_scorecard`, `bowling_scorecard` | Available |
| Pressure map | `GET /analytics/games/{id}/pressure-map` | Available |
| AI summary (tentative) | `GET /api/analyst/matches/{id}/ai-summary` (mock) | Available (mock) |

**Visualization requirements for this slice:**
- Run progression line chart (use `ChartLine.vue`)
- Phase comparison bar chart (use `ChartBar.vue` or `PhaseSplits.vue`)
- Wickets timeline (new: simple list or overlay on run progression)
- Partnership table (new: table component, no special chart needed)
- Top bowler / top batter cards (use `PlayerSummaryCard.vue` or equivalent)

**This slice deliberately avoids:**
- Delivery placement data (wagon wheel, pitch maps)
- Historical data queries
- Real LLM calls
- Cross-match comparisons (keep to single match first)

---

## 17. Backend API and Data Requirements

### New or Missing Endpoints Required for MVP

| Priority | Endpoint | Method | Description | Auth |
|---|---|---|---|---|
| P0 | `/api/analyst/matches` | GET | List completed matches (scoped by org) | `analyst_pro` / `org_pro` |
| P0 | `/api/analyst/matches/{match_id}` | GET | Full match detail for analyst dashboard | `analyst_pro` / `org_pro` |
| P0 | `/api/analyst/matches/{match_id}/deliveries` | GET | Ball-by-ball from normalized Delivery table | `analyst_pro` / `org_pro` |
| P1 | `/api/analyst/matches/{match_id}/partnerships` | GET | Partnership breakdown per innings | `analyst_pro` / `org_pro` |
| P1 | `/api/analyst/matches/{match_id}/phase-summary` | GET | Phase-level summary (wrapper for phase-map) | `analyst_pro` / `org_pro` |
| P1 | `/api/analyst/matches/{match_id}/pdf-brief` | GET | PDF podcast brief with summary and talking points | `analyst_pro` / `org_pro` |
| P2 | `/api/analyst/workspaces` | GET / POST | List and create analyst workspaces (saved state) | `analyst_pro` / `org_pro` |
| P2 | `/api/analyst/workspaces/{id}` | GET / PATCH | Read and update workspace (notes, status) | `analyst_pro` / `org_pro` |

### Existing Endpoints to Harden for Analyst Use

| Endpoint | Current State | Hardening Required |
|---|---|---|
| `GET /analytics/games/{id}/phase-map` | No auth | Add org-scoping or accept current open state per security review |
| `GET /analytics/games/{id}/pressure-map` | No auth | Same as above |
| `GET /api/analyst/query` | Auth OK | Add completed-only filter; add org-scope filter |
| `GET /api/analyst/matches/export` | Auth OK | Add org-scope filter; hook to real data for frontend |
| `GET /api/analyst/matches/{id}/ai-summary` | Auth OK (mock) | Add "tentative" flag to response; no behavior change |

### Data Isolation Rule

All new analyst endpoints must:

1. Accept the authenticated user's organization context
2. Return only matches belonging to that organization (or public/shared matches if explicit)
3. Never return player or match data from other organizations

---

## 18. Frontend UX Requirements

### Analyst Workspace (`AnalystWorkspaceView.vue`)

**Required changes for MVP:**

1. **Match list:** Wire to `GET /api/analyst/matches?status=completed` (new endpoint). Replace any fake or mock data source.
2. **Top bowler summary:** Remove hardcoded `'J. Smith'`. Compute from first real match data or show `—`.
3. **Export trigger:** Replace `ExportUI.vue`'s `generateExportData()` fake export with a call to backend analyst export endpoints.
4. **Match row click:** Confirm navigation to `MatchCaseStudyView.vue` or a new analyst match detail view.
5. **Loading/error states:** Ensure proper empty, loading, and error states for all data-dependent sections.

### Match Intelligence View (new or extended from MatchCaseStudyView)

**Required elements:**

1. Match header — teams, result, format, date
2. Innings summary cards — runs, wickets, overs for each innings
3. Run progression chart — by over using `ChartLine.vue`
4. Phase breakdown — powerplay/middle/death with run rates using `PhaseSplits.vue`
5. Wickets timeline — list of wickets with over, batter, bowler, dismissal type
6. Partnership summary — table of partnerships with runs and balls
7. Top performers — top batter(s) and top bowler(s)
8. AI summary panel — labeled "System-generated / Tentative" using `AiCalloutsPanel.vue`
9. Talking points input — free-text notes section for analyst-created talking points

### Podcast Prep Section (within or adjacent to Match Intelligence View)

**Required elements:**

1. Episode outline text area
2. Talking points list (add/remove)
3. Coach discussion prompts text area
4. Selected charts panel (tick which charts to include)
5. Export to PDF button (calls backend PDF endpoint)
6. Workspace status indicator (Research Started → Coach Review Ready → etc.)

### AI Summary Display Rules (frontend enforcement)

Any AI-generated content (talking points, summaries, insights) must:
- Display a "Tentative / System-generated" badge or disclaimer
- Show a "Source data" reference or link to match data
- Never appear as a confirmed, authoritative statement
- Be editable by the analyst before saving

---

## 19. Visualization Requirements

### Required for MVP (buildable from existing components)

| Visual | Component | Data Source | Status |
|---|---|---|---|
| Run progression by over | `ChartLine.vue` | Delivery aggregation | Component exists, endpoint needed |
| Phase run rate comparison | `PhaseSplits.vue` or `ChartBar.vue` | `GET /analytics/games/{id}/phase-map` | Component + endpoint exist |
| Wickets timeline | New simple list/overlay | Filtered deliveries | Simple; no complex chart needed |
| Partnership chart | `ChartBar.vue` or table | New partnerships endpoint | Component exists, endpoint needed |
| Pressure map visualization | `PressureMapWidget.vue` | `GET /analytics/games/{id}/pressure-map` | Component + endpoint exist |
| Win probability trend | `WinProbabilityWidget.vue` / `MiniSparkline.vue` | `GET /predictions/games/{id}/win-probability` | Component + endpoint exist |
| Top performer cards | `PlayerSummaryCard.vue` | Scorecard aggregation | Component exists |

### Deferred Visualizations (post-MVP)

| Visual | Blocker |
|---|---|
| Wagon wheel / shot map | Requires delivery placement data (not collected) |
| Pitch map | Requires delivery pitch location data (not collected) |
| Bowling length heatmap | Requires pitch location data |
| Collapse graph (multi-match) | Requires historical data |
| Venue trend charts | Requires historical multi-venue data |
| Player form over time | Partial data via `PlayerForm` — viable post-MVP |

---

## 20. Export Requirements

### MVP Export Formats

| Format | Purpose | Source | Status |
|---|---|---|---|
| PDF podcast brief | Analyst's primary deliverable | New backend endpoint using reportlab | Not built |
| CSV match data | Raw data for further analysis | `GET /api/analyst/matches/export` (existing) | Built but not wired to frontend properly |
| JSON match data | Programmatic use | `GET /api/analyst/matches/export` (existing) | Built but not wired to frontend properly |
| CSV player stats | Player-level export | `GET /api/analyst/players/export` (existing) | Built |

### PDF Brief Requirements

The PDF podcast brief must contain:

1. Episode title (analyst-entered)
2. Match summary (teams, result, date, format)
3. Key match facts (runs, wickets, top performers from real data)
4. 3–5 talking points (analyst-entered or AI-suggested and approved)
5. Top tactical insight (analyst-entered)
6. Coach discussion prompts (analyst-entered)
7. Selected charts (PNG embeds or chart summaries)
8. System-generated AI summary (labeled "Tentative")
9. Export timestamp and analyst name

**Implementation note:** `pdf_export_service.py` already uses `reportlab`. A new function or module for analyst PDF can follow the same pattern without touching video analysis PDF code.

### Post-MVP Export Formats

- PNG stat card exports
- Markdown episode notes
- Presentation slide export
- Social media carousel package
- YouTube description template
- Coach report bundle

---

## 21. AI Guardrails and Grounding Rules

These rules must be enforced at both the backend service layer and the frontend display layer:

### Backend Rules

1. **No invention:** AI summary services must only generate output from verified match data fields. No fabrication of statistics, player names, or match events.
2. **Source citation:** Every AI insight must include a reference to the source data (e.g., `"source": "over 14 pressure data"` or `"source": "innings 2 deliveries"`).
3. **Tentativeness flag:** AI responses must include a `"tentative": true` field in the response schema when the insight is a pattern inference rather than a computed fact.
4. **No cross-organization data:** AI summaries must only use data from the match being analyzed, scoped to the requesting organization.
5. **No player personal data:** AI summaries must not include personal data (player age, private health status, off-field information).
6. **LLM token budget:** When real LLM is introduced, enforce token budget limits per `agent_budget.py` and log usage via `ai_usage.py`.

### Frontend Rules

1. All AI-generated content must display a "Tentative / System-generated" badge.
2. Analysts must be able to edit, approve, or reject any AI suggestion before saving.
3. AI content must not be submitted to any export (PDF, CSV, social) without analyst review.
4. The podcast brief approval status must be explicitly "Approved for Recording" before the PDF export button is enabled for content that includes AI suggestions.

### Future LLM Rules (pre-LLM integration gate)

Before any real LLM call is introduced:

1. A prompt template must be reviewed and approved
2. The LLM response must be post-processed to strip any hallucinated statistics
3. All LLM outputs must be validated against real match data before display
4. A comparison test must show LLM outputs versus deterministic mock outputs

---

## 22. Permission and Isolation Requirements

### Access Control Rules for Analyst System

| Requirement | Rule |
|---|---|
| Analyst endpoints require auth | All `/api/analyst/*` routes must enforce `analyst_pro` or `org_pro` role |
| Data isolation | Analyst endpoints must only return data belonging to the requesting user's organization |
| Cross-org isolation | An analyst in Organization A must never see Organization B's matches, players, or notes |
| Export permission | Only `analyst_pro` or `org_pro` users may trigger exports |
| AI summary access | AI summaries are gated to `analyst_pro` or `org_pro` |
| Workspace isolation | Analyst workspaces must be private to the creating user or explicitly shared within the same organization |
| No scorer-level bypass | Scorers (free tier) must not be able to access analyst routes even if they know the endpoint URLs |

### Organization Isolation Implementation Note

The current `analyst_pro` query endpoint does not apply organization filtering. Before Phase 4B produces any data to analysts, the backend must:

1. Read the requesting user's `org_id` or `organization_id` from the authenticated user record
2. Filter all Game, PlayerProfile, and related queries to that organization
3. Return `403 Forbidden` if the user has no organization association

---

## 23. Data Source and No-Fake-Data Rules

### Hard Rules

1. **No fake data in analyst exports.** All analyst CSV, JSON, and PDF exports must source from real database records. No hardcoded sample rows, celebrity names, or generated data.
2. **No fake data in analyst charts.** Chart data must come from real delivery, scorecard, or analytics endpoint responses. No `Math.random()` or hardcoded chart series.
3. **No placeholder analytics.** Summary cards (top bowler, avg runs per over, wickets in phase) must show real computed values or `—` / "No data" — never a hardcoded name or number.
4. **Mock AI is allowed at MVP** as long as it is generated from real match data using deterministic rules and labeled "System-generated."
5. **The `npm run guard:fake-data` CI check must pass** for any analyst-related component change. New components must comply with whatever rule this guard enforces.
6. **`ExportUI.vue` must be fixed** before any analyst-facing export is considered complete. The `generateExportData()` function must be replaced with a real backend API call.

### Data Source Reference Table

| Data | Allowed Source | Forbidden Source |
|---|---|---|
| Match list | `GET /api/analyst/matches` (backend DB) | Client-side hardcoded arrays |
| Match summary | `GET /games/{id}` or new analyst detail endpoint | Mock objects |
| Innings runs | `game.batting_scorecard` or delivery aggregation | Hardcoded values |
| Player names | `PlayerProfile.player_name` from DB | Celebrity names, placeholder initials |
| Phase stats | `GET /analytics/games/{id}/phase-map` | Client-side calculations from fake data |
| AI summaries | `match_ai_service.py` from real game data | Free-text invention |
| Export rows | Backend analyst export endpoints | `generateExportData()` or similar |

---

## 24. Testing and Gate Requirements

### Gates for Phase 4B Implementation PRs

Every Phase 4B implementation PR must pass:

1. `pre-commit run --all-files` — linting, formatting, type checks
2. `ruff check .` — no new ruff violations
3. `ruff format --check .` — formatting clean
4. `cd backend && mypy --config-file pyproject.toml --explicit-package-bases .` — no new type errors
5. `cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py` — scoring regression protected
6. `cd backend && pytest tests/integration/ -v --tb=short` — integration tests pass
7. `cd backend && pytest tests/test_dls_calculations.py -v --tb=short` — DLS regression protected
8. `cd frontend && npm run guard:fake-data` — no new fake data introduced
9. `cd frontend && npm run type-check` — no TypeScript errors
10. `cd frontend && npm run build-only` — production build succeeds

### Required Tests for Phase 4B New Analyst Endpoints

| Test | Type |
|---|---|
| Analyst match list returns only completed games | Backend integration |
| Analyst match list scoped to user's organization | Backend integration (isolation) |
| Analyst match list returns 403 for non-analyst user | Backend permission |
| Analyst delivery endpoint returns real delivery data | Backend integration |
| Analyst PDF brief export generates valid PDF bytes | Backend unit/integration |
| AI summary response includes `tentative` flag | Backend unit |
| Frontend match list shows real matches (no hardcoded list) | Frontend component test |
| Frontend export calls backend endpoint (not `generateExportData`) | Frontend component test |
| `topBowler` computed from real data or shows `—` | Frontend component test |
| Organization A analyst cannot access Organization B data | Backend integration (isolation) |

---

## 25. Protected Files and Areas

The following must not be modified by any Phase 4B analyst implementation:

| Area | Files / Paths | Reason |
|---|---|---|
| Scoring logic | `backend/services/scoring_service.py` | Cricket truth — must not change |
| DLS logic | `backend/dls.py`, `backend/services/dls/`, `backend/services/dls_service.py` | DLS math is protected |
| Live bus | `backend/services/live_bus.py` | Real-time broadcast — do not break |
| Coach Pro Plus video | `backend/workers/analysis_worker.py`, `backend/services/coach_plus_analysis.py`, `backend/services/pose_service.py` | Video analysis must not be disrupted |
| Migrations | `backend/alembic/versions/` | No migration changes without full review |
| Pricing config | `backend/config/pricing.py` | Do not change tier definitions without explicit approval |
| CI/CD workflows | `.github/workflows/` | Do not modify workflows |
| Infra | `infra/terraform/` | No infra changes in this phase |
| Frontend video store | `frontend/src/stores/coachPlusVideoStore.ts` | Video store must not be changed |
| Frontend video service | `frontend/src/services/coachPlusVideoService.ts` | Video service must not be changed |

---

## 26. Recommended Smallest Safe Phase 4B Implementation Issue

### Recommended Issue: Phase 4B — Analyst Match Intelligence MVP

**Title:** Phase 4B: Analyst Match Intelligence Dashboard — Real Data Wiring

**Scope:**

1. **Backend:**
   - Add `GET /api/analyst/matches?status=completed` — org-scoped completed match list
   - Add `GET /api/analyst/matches/{match_id}` — analyst match detail (teams, innings summary, phase breakdown)
   - Add `GET /api/analyst/matches/{match_id}/deliveries` — delivery-level data from normalized `Delivery` table
   - Add `GET /api/analyst/matches/{match_id}/partnerships` — partnership breakdown
   - Enforce org-scope filter on all new endpoints
   - Add `"tentative": true` flag to AI summary response

2. **Frontend:**
   - Fix `AnalystWorkspaceView.vue` match list to call new `GET /api/analyst/matches` endpoint
   - Fix `topBowler` placeholder — compute from real data or show `—`
   - Fix `ExportUI.vue` — call backend analyst export instead of `generateExportData()`
   - Add "System-generated / Tentative" label to `AiCalloutsPanel` when displaying AI summaries
   - Wire `PhaseSplits.vue` or `ChartBar.vue` to phase-map endpoint for selected match
   - Wire run progression chart to delivery data for selected match

3. **Tests:**
   - Org isolation integration tests
   - Analyst permission tests
   - Frontend no-fake-data guard must pass

**Not in Phase 4B scope:**
- PDF brief export (Phase 4C)
- Analyst workspace persistence (Phase 4D)
- Podcast prep dashboard (Phase 4E)
- Real LLM integration

**Why this is the smallest safe slice:** It fixes the most critical fake-data risks (ExportUI, topBowler), establishes real data wiring for the analyst workspace, and adds org isolation before any real analyst data is exposed — without touching scoring, DLS, Coach Pro Plus, or any other protected system.

---

## 27. Rollback and Containment Plan for Analyst Implementation

### Phase 4B Rollback Strategy

Because Phase 4B adds new routes and does not modify existing routes, the rollback plan is:

1. **Backend rollback:** All new analyst endpoints are in `backend/routes/analyst_pro.py` or a new `backend/routes/analyst_match.py` file. If rollback is required, remove the new file and unregister its router from `backend/app.py`. Existing analyst query, export, and AI summary endpoints remain unchanged.

2. **Frontend rollback:** All analyst view changes are isolated to `frontend/src/views/AnalystWorkspaceView.vue` and `frontend/src/components/ExportUI.vue`. Revert these files via `git revert` without affecting scoring, coach, or video analysis views.

3. **No migration rollback needed:** Phase 4B must not add migrations. If new workspace persistence is added later (Phase 4D), that migration must have a clean `downgrade()` path.

4. **Feature flag option:** If analyst features need to be gated during rollout, the existing `entitlement_service.py` and beta access system can gate the analyst workspace by feature name without removing code.

### Containment Rules

1. Phase 4B must not write to any existing table columns that scoring logic depends on (`Game.total_runs`, `Game.deliveries`, `Game.batting_scorecard`, etc.)
2. Phase 4B must not modify the Socket.IO broadcast on scoring events
3. Phase 4B new endpoints must be additive only — no modification of existing game or player routes
4. Phase 4B frontend changes must not modify `gameStore.ts`, `authStore.ts`, `coachPlusVideoStore.ts`, or the scoring view components

---

## Appendix A: Files Changed in Phase 4A

- Created: `docs/PHASE_4A_ANALYST_SYSTEM_ARCHITECTURE_AUDIT_AND_SPEC_LOCK.md` (this document)
- Updated: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` — minimal update to reference Phase 4A as complete

## Appendix B: Confirmation — Only Docs Changed

Phase 4A modifies only documentation files. No backend app code, frontend app code, scoring logic, DLS logic, live bus, Coach Pro Plus code, migrations, dependencies, infra, or workflows were changed.

## Appendix C: Audit Sources Reviewed

1. `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md` ✅
2. `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md` ✅
3. `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` ✅
4. `docs/PHASE_1D_OPEN_PR_TRIAGE_AND_CHECKLIST_NUMBERING.md` ✅
5. `backend/routes/analyst_pro.py` ✅
6. `backend/routes/analytics.py` ✅
7. `backend/routes/phase_analysis.py` ✅
8. `backend/routes/prediction.py` ✅
9. `backend/routes/player_analytics.py` ✅
10. `backend/routes/players.py` ✅
11. `backend/routes/matches.py` ✅
12. `backend/routes/ai.py` ✅
13. `backend/routes/gameplay.py` ✅
14. `backend/routes/games.py` ✅
15. `backend/sql_app/models.py` ✅
16. `backend/services/match_ai_service.py` ✅
17. `backend/services/match_context_service.py` ✅
18. `backend/services/pdf_export_service.py` ✅
19. `backend/services/scorecard_service.py` ✅
20. `backend/services/entitlement_service.py` ✅
21. `backend/config/pricing.py` ✅
22. `backend/security.py` ✅
23. `frontend/src/views/AnalystWorkspaceView.vue` ✅
24. `frontend/src/views/MatchCaseStudyView.vue` ✅
25. `frontend/src/components/ExportUI.vue` ✅
26. `frontend/src/components/WinProbabilityChart.vue` ✅
27. `frontend/src/components/analytics/` (all files) ✅
28. `frontend/src/components/AiCalloutsPanel.vue` ✅
29. `frontend/src/components/MiniSparkline.vue` ✅
30. `frontend/src/components/ImpactBar.vue` ✅
31. `FAKE_DATA_AUDIT_REPORT.md` ✅

## Appendix D: Validation Status

Phase 4A is a docs-only phase. CI is expected to be skipped by the path-ignore rules defined in `.github/workflows/ci.yml` (markdown and docs-only changes are ignored per the checklist). No app code was changed, so no test runs are required. The next code implementation phase (Phase 4B) must pass the full CI gate as defined in Section 24.

---

*Phase 4A Complete. Proceed to Phase 4B only after this document has been reviewed and approved.*
