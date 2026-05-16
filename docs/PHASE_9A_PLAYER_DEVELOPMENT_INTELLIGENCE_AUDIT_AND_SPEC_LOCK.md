# Phase 9A — Player Development Intelligence Audit and Spec Lock

## 1. Phase title and status

- **Phase:** 9A — Player Development Intelligence Audit and Spec Lock
- **Status:** COMPLETE (documentation/spec-lock only)
- **Repository:** `Jnpaul1984/Cricksy_Scorer`
- **Date:** 2026-05-16
- **Implementation status:** No runtime behavior is added or changed in this phase.

---

## 2. Product doctrine

Cricksy must help teams compete **and** help every player improve.

Locked doctrine for Phase 9 and later:

> Every player should leave the season measurably better than they started.

Phase 9 therefore exists to support schools, academies, coaches, and organizations with:

- coach-approved development plans
- constructive support for weaker or overlooked players
- evidence-based drill assignment and follow-up
- progress checkpoints grounded in real match or video evidence
- clear school/team visibility without mutating official cricket truth

---

## 3. Scope lock

### Allowed in Phase 9A

- Documentation/spec-lock only
- Repo-grounded audit of existing foundations
- Governance rules for future development-plan behavior
- Phase 9 checklist updates after this document is complete

### Explicitly not allowed in Phase 9A

- Backend runtime changes
- Frontend runtime changes
- New APIs, services, schemas, migrations, tests, workers, or package changes
- Video-analysis pipeline/model behavior changes
- Any plan activation, AI orchestration, or coach workflow implementation

### Locked non-goals

- Do **not** replace `backend/routes/coach_pro.py`
- Do **not** replace `backend/services/ai_player_insights.py`
- Do **not** replace existing drill, improvement, dismissal, heatmap, or video-analysis systems
- Do **not** bypass Phase 6B deterministic truth protection
- Do **not** bypass Phase 8C review workflow

---

## 4. Existing repo foundations found

This phase must reuse existing systems instead of inventing a parallel player-development stack.

### 4.1 Player data foundation

| Foundation | Files found | What exists now | Reuse requirement |
|---|---|---|---|
| Official player career profile | `backend/sql_app/models.py` (`PlayerProfile`) and `backend/sql_app/schemas.py` (`PlayerProfileResponse`) | Deterministic batting, bowling, fielding totals and derived averages | Future development plans must reference this as official player truth; never overwrite it |
| Period form snapshots | `backend/sql_app/models.py` (`PlayerForm`) and `backend/sql_app/schemas.py` (`PlayerFormRead`) | Stored period start/end, matches, runs, wickets, averages, form score | Reuse for baseline/progress inputs, not as a separate development-plan truth store |
| Player profile API | `backend/routes/players.py` | `/api/players/{player_id}/profile`, `/form`, `/notes`, `/summary`, `/ai-insights` | Keep player-development features attached to existing player surfaces |
| Player analytics surfaces | `backend/routes/player_analytics.py` | Career summary, yearly stats, comparison, advanced endpoints | Reuse for supporting context, but keep official stats deterministic |
| Monthly improvement tracking | `backend/routes/player_improvement.py`, `backend/services/player_improvement_tracker.py` | Monthly stats, trend periods, improvement score, metric confidence | Reuse as evidence inputs for checkpoints and progress baselines |

### 4.2 Coach-player workflow foundation

| Foundation | Files found | What exists now | Reuse requirement |
|---|---|---|---|
| Coach-player assignment | `backend/sql_app/models.py` (`CoachPlayerAssignment`), `backend/sql_app/schemas.py` (`CoachPlayerAssignmentRead`) | Active assignment between `coach_user_id` and `player_profile_id` | Future plans must be scoped through existing assignment/org boundaries |
| Coaching sessions | `backend/sql_app/models.py` (`CoachingSession`), `backend/sql_app/schemas.py` (`CoachingSessionRead`) | Scheduled sessions with focus area, notes, outcome | Reuse as evidence/history instead of duplicating “intervention session” logic immediately |
| Coach workflow routes | `backend/routes/coach_pro.py` | Assign player, list assigned players, list/create/update sessions | Phase 9 must extend this workflow later, not replace it |
| Coach notes | `backend/routes/players.py` + `PlayerCoachingNotes` | Coach/org notes with visibility control | Reuse as manual evidence source (`source_type=coach_note`) |

### 4.3 AI player insight foundation

| Foundation | Files found | What exists now | Locked interpretation |
|---|---|---|---|
| Player AI insight service | `backend/services/ai_player_insights.py` | Rule-based strengths, weaknesses, recent form, role tags, recommendations | Advisory only; not official truth |
| AI insight route | `backend/routes/players.py` | `/api/players/{player_id}/ai-insights` | Can feed **draft** development recommendations only |
| AI boundary metadata | `backend/domain/ai_boundary.py` | `AiOutputMetadata` with `is_official_truth`, `requires_review`, `confidence_score`, `limitations`, `source_refs`, `grounding_summary` | Phase 9 must reuse this contract for any AI-generated draft output |

Confirmed repo-grounded output fields already present in `PlayerAiInsights`:

- `strengths`
- `weaknesses`
- `recent_form`
- `role_tags`
- `recommendations`
- `ai_metadata`

### 4.4 Drill and recommendation foundation

| Foundation | Files found | What exists now | Reuse requirement |
|---|---|---|---|
| Training drill routes | `backend/routes/training_drills.py` | Player/team suggested drill endpoints | Reuse as draft drill suggestion input only |
| Training drill generator | `backend/services/training_drill_generator.py` | Drill templates, priority/severity, confidence field | Reuse templates/mapping; do not create a second drill library |
| Tactical suggestion engine | `backend/routes/tactical_suggestions.py`, `backend/services/tactical_suggestion_engine.py` | Best bowler, weakness analysis, fielding setup | Reuse as advisory evidence where relevant, not as autonomous coaching |
| Dismissal patterns | `backend/routes/dismissal_patterns.py`, `backend/services/dismissal_pattern_analyzer.py` | Vulnerability profiles, patterns, severity, recommendations | Reuse as weakness evidence when sample size is adequate |
| Heatmaps | `backend/routes/pitch_heatmaps.py`, `backend/services/pitch_heatmap_generator.py` | Scoring, dismissal, release-zone, matchup heatmaps | Reuse as spatial evidence only |

### 4.5 Coach Pro Plus / video-analysis foundation

| Foundation | Files found | What exists now | Locked Phase 9A rule |
|---|---|---|---|
| Video session and analysis APIs | `backend/routes/coach_pro_plus.py` | Session management, upload initiation/completion, analysis jobs, artifact access | Must remain intact; Phase 9A does not alter pipeline behavior |
| Video AI pipeline | `backend/services/coach_ai_pipeline.py` | Pose + ball tracking analysis, non-authoritative findings | Reuse outputs as evidence only |
| Coach findings/report generation | `backend/services/coach_findings.py`, `backend/services/coach_report_service.py` | Structured findings, report text, drills, weekly plan | Reuse report/findings artifacts instead of inventing a separate video evidence pipeline |
| Frontend video surface | `frontend/src/views/CoachProPlusVideoSessionsView.vue`, `frontend/src/stores/coachPlusVideoStore.ts`, `frontend/src/services/coachPlusVideoService.ts` | Coach-facing video session management and analysis result access | Future development evidence must surface through existing Coach Pro Plus UX |

### 4.6 Phase 8 review workflow dependency

| Foundation | Files found | What exists now | Reuse requirement |
|---|---|---|---|
| Review persistence | `backend/sql_app/models.py` (`AiInsightReview`) | Advisory review audit rows with reviewer/org linkage | Reuse review pattern for development-impacting AI outputs |
| Review schemas/routes/services | `backend/api/schemas/ai_insight_review.py`, `backend/routes/ai_insight_review.py`, `backend/services/ai_insight_review_service.py` | GET/POST review state for AI insights; review metadata only | Phase 9 draft outputs must not go active while review is pending/flagged/rejected |
| Review UI | `frontend/src/components/AiInsightReviewCard.vue` | Shared review status card | Reuse for player-development AI review visibility |
| Existing usage | `frontend/src/components/PlayerDevelopmentInsightCard.vue`, `frontend/src/views/AnalystWorkspaceView.vue`, `frontend/src/views/MatchCaseStudyView.vue` | Review state already shown on player/match AI surfaces | Future coach-facing development UI should show review state, not hide it |

### 4.7 Frontend visibility foundation

| Surface | Files found | Current state | Gap relevant to Phase 9 |
|---|---|---|---|
| Player profile | `frontend/src/views/PlayerProfileView.vue` | Official stats, form, notebook, mental panel, AI insights | No persisted development-plan UI, no checkpoints, no drill assignment workflow |
| Player development card | `frontend/src/components/PlayerDevelopmentInsightCard.vue` | Displays AI insights, confidence, limitations, source refs, review card | No active-plan lifecycle; still insight-only |
| Coach dashboard | `frontend/src/views/CoachesDashboardView.vue` | Match snapshot, key players, links, notes, dev dashboard widget | No governed development-plan workflow |
| Dev dashboard widget | `frontend/src/components/DevDashboardWidget.vue` | Uses random recent-match indicators and random development focus selection | Not safe to treat as production player-development truth |
| Analyst workspace | `frontend/src/views/AnalystWorkspaceView.vue` | Match/player intelligence, AI callouts, review cards | No development-plan management; useful only as supporting evidence surface |

### 4.8 Governance foundations already locked elsewhere

- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`
- `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md`
- `docs/PHASE_8_AI_ANALYTICS_MATCH_INTELLIGENCE_AUDIT_AND_SPEC_LOCK.md`

Phase 9 must inherit these rules instead of redefining conflicting ones.

---

## 5. Current gaps

### 5.1 Player data and progress gaps

- `PlayerProfile` is strong for official totals, but there is no dedicated development-plan entity or checkpoint history.
- `PlayerForm` and monthly improvement tracking provide inputs, but there is no governed baseline-vs-goal-vs-checkpoint model.
- Current improvement tracking is batting-heavy and month-based; it is not yet a coach-owned development record.
- No persistent `evidence_refs` model links player growth claims back to form, dismissal patterns, drills, or video artifacts.

### 5.2 Coach workflow gaps

- Coach assignment/session workflows exist, but there is no active development-plan lifecycle (`draft`, `active`, `paused`, `completed`, `archived`).
- Drill suggestions exist, but there is no coach-approved drill assignment record.
- Coaching sessions store notes/outcomes, but outcomes are not tied to structured goals/checkpoints.

### 5.3 AI/governance gaps

- `backend/services/ai_player_insights.py` is advisory-only, but it does not yet populate a governed confidence package, source references, or coach-approval state for development plans.
- Current `weaknesses` wording is useful for internal analysis but is not sufficient on its own for youth-facing plan activation.
- There is no explicit plan-level gate connecting AI review + coach approval + activation.

### 5.4 Evidence quality gaps in drill/recommendation services

- `backend/routes/training_drills.py` currently uses mock/default weakness indicators in the route layer; this cannot be treated as active development-plan truth.
- Tactical suggestions, dismissal patterns, and heatmaps are useful advisory signals, but some route paths use simplified/default values or incomplete delivery context.
- These systems can support evidence, but not autonomous claims of player progress.

### 5.5 Video-analysis integration gaps

- Video artifacts exist, but there is no normalized player-development evidence contract that references session/job/report outputs.
- Phase 9 must reference video evidence by durable IDs/refs instead of copying or mutating video-analysis findings into official stats.

### 5.6 Frontend gaps

- No existing coach-facing UI can create, review, activate, monitor, and close a player development plan.
- `DevDashboardWidget.vue` currently uses random form/focus generation, so it must not be presented as a complete player-development product.
- Player Profile exposes AI insights, but not structured plan status, checkpoints, drill completion, or coach approval state.

---

## 6. Data ownership rules

1. **Official cricket truth stays where it already lives.**
   - Match state, scorecards, DLS, results, and player career totals remain owned by deterministic systems such as `backend/services/scoring_service.py`, `backend/routes/gameplay.py`, `backend/services/dls_service.py`, `backend/sql_app/models.py:PlayerProfile`, and scorecard models.
2. **Development data must be a separate layer.**
   - Future development entities must reference player/profile/org/coach records but may not overwrite them.
3. **Development plans must use real player data only.**
   - Allowed sources: official match/player data, stored form/improvement data, coach notes, coach sessions, governed AI insight drafts, and existing video-analysis artifacts.
4. **No fake performance claims, fake drills, fake progress, or fake data are allowed.**
   - This rule is especially important because `frontend/src/components/DevDashboardWidget.vue` currently generates random display data and therefore cannot be treated as authoritative.
5. **Video evidence remains owned by the video-analysis subsystem.**
   - Future development-plan records may reference video sessions/jobs/reports, not absorb ownership of video artifacts.
6. **Coach approval metadata and AI review metadata are not official cricket truth.**
   - They govern workflow state only.

---

## 7. AI boundary rules

1. **AI can generate draft recommendations only.**
2. **No AI output can overwrite official stats, match results, scorecards, DLS, innings state, or player career totals.**
3. **All Phase 9 AI outputs must reuse `AiOutputMetadata` and keep `is_official_truth = false`.**
4. **`validate_no_official_truth_mutation()` remains mandatory for any AI-adjacent persistence path.**
5. **Low-confidence or insufficient-data recommendations must be blocked or clearly marked.**
   - Phase 6F fallback states such as `insufficient_data`, `sample_size_too_small`, `low_confidence_review_required`, and `blocked_by_youth_safety` should govern future delivery.
6. **AI must be evidence-grounded.**
   - Future development recommendations should include `source_refs`, `grounding_summary`, and explicit limitations when confidence is not high.
7. **No always-running autonomous coaching loop is allowed.**
   - Phase 9 may support on-demand draft generation later, but not background self-triggered plan mutation.
8. **AI does not replace coach judgment.**
   - AI assists with draft insight synthesis only.

---

## 8. Coach approval rules

1. **Coach approval is required before an AI-generated plan becomes active.**
2. **Phase 8C review workflow must be reused, not bypassed.**
   - If a draft plan is based on AI insights, the underlying insight/recommendation review state must be visible and reviewable.
3. **Plan activation requires two separate concepts:**
   - advisory AI review state is acceptable for the source insight
   - explicit coach approval (`coach_approved`) exists for the plan itself
4. **Pending, rejected, flagged, or low-confidence AI content must not auto-activate a plan.**
5. **Youth/player-impacting feedback must always be reviewable.**
6. **Manual coach-created plans may exist later, but AI-sourced sections still require governance metadata where applicable.**

---

## 9. Youth-safe language rules

Locked rules for all future player-development wording:

- Use constructive developmental language.
- Do **not** label a player as a failure, liability, problem, or hopeless case.
- Do **not** surface “weakness” language to youth-facing users without safe reframing such as “development area”, “growth opportunity”, or “current focus area”.
- Do **not** present advisory outputs as certainty or diagnosis.
- Keep feedback specific, coachable, and evidence-based.
- Require review for youth/player-impacting feedback before active use.
- Preserve existing safe patterns already visible in the repo, for example:
  - `frontend/src/components/PlayerDevelopmentInsightCard.vue` → “development guidance”, “main improvement area”, sample warnings, limitations
  - `frontend/src/components/MentalProfilePanel.vue` → coaching disclaimer and “Growth Opportunities” framing

Phase 9 must convert raw analytical weakness signals into safe coaching language before active delivery.

---

## 10. Org/player privacy rules

1. **Backend permissions must enforce coach/org/player boundaries.**
2. Existing route guards must be treated as the baseline:
   - `backend/routes/coach_pro.py` limits coach access to assigned players
   - `backend/routes/players.py` limits form/notes access by role and note visibility
   - `backend/services/ai_insight_review_service.py` stores reviewer org metadata and documents org isolation
   - `backend/routes/coach_pro_plus.py` gates video features by role/feature access
3. Future development entities must include `org_id`, `player_profile_id`, and `coach_user_id` where applicable.
4. Analysts and coaches must only see development data allowed by organization and note visibility policy.
5. Video-derived evidence references must respect existing session ownership and artifact access controls.
6. Player development dashboards must never leak cross-org player progress or coach notes.

---

## 11. Frontend visibility rules

1. **Frontend must not expose backend-only features as complete.**
2. If a feature is intended for coach use, it is not complete until coach-facing UI exists.
3. Future coach/player development UI must display:
   - plan status
   - approval/review state
   - evidence references
   - confidence/limitations where AI is involved
   - insufficient-data/blocked state when recommendations cannot be trusted
4. Existing frontend gaps must be respected:
   - `PlayerProfileView.vue` is insight-aware but not plan-aware
   - `CoachesDashboardView.vue` has no governed development-plan workflow
   - `AnalystWorkspaceView.vue` is evidence/supporting intelligence, not a coach plan manager
5. `DevDashboardWidget.vue` must not be used as proof that a real development dashboard already exists because it currently generates random display values.

---

## 12. Protected files / high-risk areas

These areas are tightly coupled to deterministic truth, AI governance, or Coach Pro Plus artifacts and must not be changed casually in future phases:

### Deterministic truth / boundary protection

- `backend/services/scoring_service.py`
- `backend/routes/gameplay.py`
- `backend/services/dls_service.py`
- `backend/routes/dls.py`
- `backend/domain/ai_boundary.py`
- `backend/sql_app/models.py` (`PlayerProfile`, scorecards, AI review persistence)

### Coach/assignment workflow

- `backend/routes/coach_pro.py`
- `backend/sql_app/models.py` (`CoachPlayerAssignment`, `CoachingSession`, `PlayerCoachingNotes`)
- `backend/sql_app/schemas.py` related coach/player schemas

### Coach Pro Plus / video-analysis pipeline

- `backend/routes/coach_pro_plus.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/services/coach_findings.py`
- `backend/services/coach_report_service.py`
- `backend/services/pose_metrics.py`
- `backend/services/video_job_recovery.py`
- `frontend/src/stores/coachPlusVideoStore.ts`
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/views/CoachProPlusVideoSessionsView.vue`

### Review workflow and governance docs

- `backend/routes/ai_insight_review.py`
- `backend/services/ai_insight_review_service.py`
- `backend/api/schemas/ai_insight_review.py`
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`
- `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md`

---

## 13. Phase 9B recommended smallest safe implementation slice

Phase 9B should be intentionally small:

- **Backend data model only**
- No frontend implementation yet
- No AI orchestration yet
- No autonomous coaching workflows yet
- No video pipeline/model behavior changes
- No migration of existing player/coach/video truth into a second competing system

The purpose of Phase 9B should be to create governed storage for development plans and evidence references so later phases can safely build on it.

---

## 14. Phase 9B data model recommendation

Recommended future entities (not to be implemented in Phase 9A):

- `PlayerDevelopmentPlan`
- `PlayerDevelopmentGoal`
- `PlayerWeaknessTag`
- `PlayerStrengthTag`
- `PlayerDevelopmentIntervention`
- `PlayerDrillAssignment`
- `PlayerProgressCheckpoint`

Recommended future fields/concepts:

- `player_profile_id`
- `coach_user_id`
- `org_id`
- `source_type: match_data | video_analysis | coach_note | ai_insight | manual`
- `weakness_category`
- `severity`
- `confidence_score`
- `coach_approved`
- `status: draft | active | completed | paused | archived`
- `evidence_refs`
- `ai_metadata` where applicable
- `created_at` / `updated_at`

Data-model rules to lock now:

- Separate development tables from official scoring/stat tables
- Preserve one-way references back to evidence sources
- Default AI-sourced records to draft/unapproved
- Keep status transitions auditable
- Store review/approval provenance

---

## 15. Phase 9C service recommendation

Phase 9C should combine existing foundations instead of replacing them:

- reuse `backend/services/ai_player_insights.py` for draft strengths/development areas
- reuse `backend/services/player_improvement_tracker.py` for baseline/progress evidence
- reuse `backend/services/training_drill_generator.py` for candidate drill suggestions
- reuse dismissal/heatmap/tactical services as supporting evidence only
- reuse Phase 8C review state before activation

Locked service rules:

- generate drafts only
- never auto-activate plans
- never auto-claim progress without checkpoint evidence
- never fabricate drills or progress summaries
- include confidence/limitations/evidence references
- block or downgrade outputs when evidence is thin

---

## 16. Phase 9D frontend recommendation

Phase 9D should add a real coach/player development workflow to existing surfaces, not a new disconnected product.

Recommended first UI targets:

- Coach workspace player detail
- Player profile development tab/section
- Review + approval controls for draft recommendations
- Drill assignment and checkpoint status display

Must-have rules:

- show approval/review status inline
- show evidence refs inline
- show confidence/limitations when AI contributes
- do not ship backend-only coach workflow claims
- do not reuse random/mock widget data as production behavior

---

## 17. Phase 9E dashboard recommendation

Phase 9E should provide organization/team visibility using governed development-plan data only.

Recommended dashboard outputs:

- players needing support, framed constructively
- active plan coverage
- goal/checkpoint completion
- players without recent coach intervention
- common team development themes
- drill completion summaries
- school-safe progress rollups

Must not do:

- rank youth players with shaming labels
- claim improvement without evidence
- mix advisory development scores into official league standings or match truth

---

## 18. Phase 9F reports recommendation

Phase 9F should generate coach/shareable development reports from governed plan + evidence data.

Recommended inputs:

- approved development plans
- progress checkpoints
- coach session outcomes
- drill assignment completion
- approved video-analysis evidence refs

Locked report rules:

- no fake progress narratives
- clear advisory labeling where AI contributes
- constructive language for developing players
- visible evidence provenance
- export-safe for school/academy use

---

## 19. Phase 9G skill-contract recommendation

Any Phase 9 intelligence skill must reuse the Phase 6C skill contract rather than inventing a new one.

Recommended future skill categories:

- player development insight synthesis
- weakness-to-drill mapping
- checkpoint summary generation
- team development dashboard summarization
- report narrative support

Mandatory inherited contract rules:

- deterministic-data dependencies declared
- confidence fields declared
- limitations declared
- youth safety rules declared
- organization boundary rules declared
- no-fake-data rule declared
- review requirement declared
- rollback/disable strategy declared

---

## 20. Test and CI gate expectations for future implementation phases

Future implementation phases (9B+) should be gated by existing repo quality standards:

### Backend

- relevant SQLAlchemy/Alembic/schema tests for new plan entities
- permission tests for coach/org/player boundaries
- activation/status-transition tests
- AI boundary tests proving official truth is untouched
- review/approval flow tests

### Frontend

- unit tests for coach/player development UI
- coach workspace E2E or targeted smoke coverage for activation/approval visibility
- no fake-data regressions on visible surfaces

### CI / repository gates to preserve

- checklist verification (`python scripts/checklist.py status`)
- backend lint/type/security gates already defined in CI
- frontend type-check/build/fake-data guard gates already defined in CI
- explicit tests around low-confidence/insufficient-data fallback behavior

---

## 21. Rollback/containment strategy

If a future Phase 9 implementation misbehaves, rollback must be easy because player development is advisory workflow state, not official match truth.

Locked containment approach:

1. Disable new development-plan routes/UI without touching scoring/stat systems.
2. Preserve official truth tables untouched.
3. Keep video-analysis artifacts intact even if plan linkage is rolled back.
4. Revert only Phase 9 plan/intervention/checkpoint entities and related UI.
5. If AI review/approval logic fails, force all AI-derived plans back to `draft`/blocked state.
6. If confidence/evidence requirements fail, fall back to “insufficient data” or review-required states rather than generating speculative guidance.

---

## 22. Acceptance criteria

- [x] Phase 9A audit/spec-lock document exists.
- [x] Existing repo foundations are documented with specific files.
- [x] Current gaps are documented.
- [x] No duplicate player-development system is planned.
- [x] Data ownership rules are clear.
- [x] AI boundary rules are clear.
- [x] Coach approval rules are clear.
- [x] Youth-safe language rules are clear.
- [x] Org/player access boundaries are clear.
- [x] Frontend visibility rules are clear.
- [x] Protected files/high-risk areas are identified.
- [x] Phase 9B is recommended as a smallest safe backend-data-model slice only.
- [x] Phase 9B/9C/9D/9E/9F/9G are recommended but not implemented.
- [x] No runtime behavior changes are part of this phase.

---

## 23. Validation notes

- This phase is documentation/spec-lock only.
- Intended file scope for completion is limited to:
  - `docs/PHASE_9A_PLAYER_DEVELOPMENT_INTELLIGENCE_AUDIT_AND_SPEC_LOCK.md`
  - `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
  - `.mcp/checklist.yaml`
  - `.mcp/checklist.md`
- No backend runtime files were changed.
- No frontend runtime files were changed.
- No migrations were added.
- No tests were changed.
- No CI/workflow or package files were changed.
- Baseline validation attempts before editing showed missing local test/build dependencies in this sandbox (`pytest` unavailable; frontend `vitest`/`sharp` unavailable until dependencies are installed), so Phase 9A validation is limited to documentation/checklist consistency and file-scope verification.
