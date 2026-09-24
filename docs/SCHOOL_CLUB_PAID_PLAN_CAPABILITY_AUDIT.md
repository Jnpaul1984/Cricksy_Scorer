# School & Club Paid Plan Capability Audit

## 1. Executive Summary

This audit is based on repository commit `99337250d671d21b68742278eab9df6fc7e44eea` (current `main` at audit time). It does not treat historical planning documents as runtime truth.

Cricksy has a strong shared Free organization foundation and substantial premium personal tooling, but it does **not** yet have paid School/Club plans. `Organization`, `OrganizationMembership`, and `OrganizationEntitlement` provide the correct contextual tenancy direction; however, the entitlement schema accepts only `school_free` and `club_free`. The Free plans deliberately share the same capability objects. The end-to-end Club Free PostgreSQL acceptance test proves that the School implementation is being reused for Clubs rather than forked.

The strongest premium reuse candidates are deterministic analytics and exports, coach assignments/sessions/notes, player-development plans and reports, the Analyst workspace, and the Coach Pro Plus video-session/upload/analysis/report pipeline. Most are readiness **B**, not **A**, because their authorization and ownership depend on global `RoleEnum`, a personal plan, `User.org_id`, coach/user ownership, or legacy organization assumptions. They must be adapted to the current Organization + OrganizationMembership + organization-capability model before School/Club use.

The largest gaps are team operations (availability, attendance, pre-match order planning, communications, and season planning), organization-scoped paid entitlements and seats, enforceable organization AI quotas, clip extraction/library semantics, organization-safe branding, automated reporting, and organization benchmarking/opposition intelligence.

Recommended product boundary:

- **Free = run cricket:** preserve every currently delivered Free organization workflow.
- **Performance = manage and improve cricket:** team operations, coaching/development, deterministic advanced analytics, comparisons, dashboards, and exports; bounded non-video AI only after quotas and privacy are governed.
- **Elite = analyze, automate, and optimize cricket:** video, AI video/session reports, richer organization intelligence, and automation, all with explicit storage, processing, retention, and seat controls.

The audit classifies 45 capabilities: **A 7, B 20, C 7, D 5, E 6**. These counts describe repository readiness, not a release commitment.

## 2. Audit Method and Sources

Readiness classifications are:

- **A — Production-ready and directly reusable:** working end-to-end with current organization tenancy or no material new business logic.
- **B — Implemented but requires organization-context adaptation:** meaningful backend/frontend/persistence exists, but ownership or authorization is personal/legacy.
- **C — Partial/incomplete:** real pieces exist, but the user workflow, persistence, enforcement, or production boundary is incomplete.
- **D — Entitlement/UI/config only:** a plan/config/UI claim exists without meaningful end-to-end enforcement.
- **E — Not implemented:** repository search found no reliable implementation for the proposed capability.

Primary sources:

- Canonical pricing: `backend/config/pricing.py::{IndividualPlan, INDIVIDUAL_PRICES, INDIVIDUAL_ENTITLEMENTS, VenuePlan, VENUE_PRICES, VENUE_ENTITLEMENTS, get_complete_plan_details}`.
- Pricing enforcement tests: `backend/tests/test_pricing_contract.py::TestPricingContract` and `backend/tests/test_pricing_consistency.py`.
- Organization data and roles: `backend/sql_app/models.py::{Organization, OrganizationMembership, OrganizationEntitlement, SchoolPlayerMembership, SchoolTeamPlayerMembership, Team, PlayerProfile}`.
- Shared Free plans: `backend/services/organization_entitlement_service.py::{FREE_ORGANIZATION_CAPABILITIES, FREE_ORGANIZATION_EXCLUDED_CAPABILITIES, PLAN_CAPABILITIES, require_organization_capability}`.
- Organization APIs: `backend/routes/organizations.py`, `backend/routes/school_matches.py`, `backend/routes/school_statistics.py`, and `backend/routes/school_competitions.py`.
- Shared School/Club UI: `frontend/src/router/index.ts::organizationChildren`, `frontend/src/views/school/*`, `frontend/src/composables/useSchoolContext.ts`, and `frontend/src/composables/useOrganizationTerminology.ts`.
- Shared Club proof: `backend/tests/test_club_free.py::test_club_free_shared_cricket_workflow_on_postgresql` and `frontend/tests/unit/ClubFreeViews.spec.ts`.
- Premium surfaces: `backend/routes/{coach_pro,coach_pro_plus,coach_notes,player_development,player_analytics,analyst_pro,analytics,prediction,ai,branding}.py`, corresponding services/models, and `frontend/src/views/{CoachesDashboardView,CoachProPlusVideoSessionsView,AnalystWorkspaceView,AnalyticsView}.vue`.
- Governance context only: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`. It is not modified by this issue.

Repository searches covered routes, services, models, migrations, frontend views/components/services, tests, pricing/billing configuration, and terms for availability, attendance, selection planning, ordering, communications, scheduling, reporting, automation, opponent analysis, and benchmarking. Absence findings below mean no reliable current implementation was found in those searched runtime surfaces; they are not legal or market assertions.

## 3. Current Free Organization Baseline

### 3.1 Data and authorization baseline

`backend/sql_app/models.py::Organization` supports `school` and `club`. `OrganizationMembership` supplies contextual `owner`, `admin`, `coach`, `scorer`, and `viewer` roles without adding School/Club roles to global `RoleEnum`. `OrganizationEntitlement` is organization-owned and separate from `User.role`, `User.subscription_plan`, and `User.org_id`.

Current organization entitlements accept only `school_free` and `club_free` (`OrganizationEntitlement.ck_organization_entitlements_plan_key`). `backend/services/organization_entitlement_service.py::FREE_ORGANIZATION_PLAN_BY_TYPE` maps organization type to the appropriate plan, while both entries in `PLAN_CAPABILITIES` reference the exact same `FREE_ORGANIZATION_CAPABILITIES` object. `backend/tests/test_club_free.py::test_school_and_club_use_type_correct_shared_free_entitlements` protects that equivalence.

### 3.2 Exact shared Free capabilities

| Capability constant | Delivered behavior | Evidence |
|---|---|---|
| `school_matches_unlimited` | Organization match creation is not limited by a per-organization match counter. | `backend/services/organization_entitlement_service.py`; `backend/services/school_match_service.py::create_school_match`; `backend/tests/test_school_match_setup.py` |
| `school_master_roster` | Canonical `PlayerProfile` plus retained organization membership and lifecycle. | `backend/sql_app/models.py::{PlayerProfile, SchoolPlayerMembership}`; `backend/services/organization_roster_service.py`; `backend/tests/test_school_roster.py` |
| `school_persistent_teams` | Reusable organization-owned teams. | `backend/sql_app/models.py::Team`; `backend/services/organization_team_service.py`; `backend/tests/test_school_teams.py` |
| `school_team_rosters` | Reusable many-team assignment without duplicating `PlayerProfile`. | `backend/sql_app/models.py::SchoolTeamPlayerMembership`; `backend/services/organization_team_roster_service.py`; `backend/tests/test_school_team_roster.py` |
| `school_match_playing_xi` | Match-local XI, captain, keeper, and internal/external-opponent setup from persistent teams. | `backend/api/schemas/school_matches.py`; `backend/services/school_match_service.py`; `frontend/src/views/school/SchoolMatchSetupView.vue`; `backend/tests/test_school_match_setup.py` |
| `school_basic_statistics` | Organization-scoped player/team aggregate statistics. | `backend/services/school_statistics_service.py`; `backend/routes/school_statistics.py`; `frontend/src/views/school/SchoolStatisticsView.vue`; `backend/tests/test_school_statistics.py` |
| `school_fixtures_results` | Organization fixtures/results derived from tenant-scoped matches. | `backend/routes/school_statistics.py`; `frontend/src/views/school/SchoolFixturesResultsView.vue`; `backend/tests/test_school_statistics.py` |
| `school_live_scorecards` | Membership-scoped live state plus controlled public publication. | `backend/routes/school_competitions.py::{get_publication, update_publication, public_school_scorecard}`; `frontend/src/views/school/SchoolPublicScorecardView.vue`; `backend/tests/test_school_competition_publication.py` |
| `school_competitions` | Organization-scoped competitions, entrants, fixtures, game linking, and standings. | `backend/services/school_competition_service.py`; `backend/routes/school_competitions.py`; `frontend/src/views/school/SchoolCompetitionsView.vue`; `backend/tests/test_school_competition_publication.py` |

Bulk CSV/XLSX player import is also part of the delivered Free experience, but there is no separate `school_player_import` capability constant. `backend/services/school_player_import_service.py::create_preview` and `apply_import` require the master-roster capability (and team-roster capability for optional team assignment). Preview/apply, duplicate resolution, explicit apply, tenant isolation, and non-mutating preview are tested in `backend/tests/test_school_player_imports.py`; Club reuse is exercised by `test_club_free_shared_cricket_workflow_on_postgresql`.

The backend explicitly excludes `advanced_ai`, `video_analysis`, `advanced_analytics`, `analyst_tooling`, `premium_coaching`, and `premium_broadcast_video` from both Free plans. Free is therefore broad operational cricket, not premium analysis.

### 3.3 What must remain Free

The following are current architecture and must not be removed to manufacture upgrade pressure: organization creation/membership, unlimited organization scoring, master roster, persistent teams, team rosters, XI/captain/keeper selection, internal and external-opponent match setup, CSV/XLSX roster import, basic player/team statistics, fixtures/results, competitions/standings, live member scorecards, and controlled public scorecards. Any later reduction is an explicit owner/product decision and cannot be inferred from this audit.

## 4. Canonical Current Individual/Venue Pricing

`backend/config/pricing.py` is the canonical source. `backend/services/billing_service.py::PLAN_FEATURES` is derived from it for backward compatibility, although the billing service identifies itself as mocked/placeholder. `backend/tests/test_pricing_contract.py::test_pricing_snapshot` and `test_entitlements_snapshot`, plus `backend/tests/test_pricing_consistency.py`, enforce the code contract.

### 4.1 Individual plans

| Plan | Current monthly USD | Implemented entitlement highlights |
|---|---:|---|
| Free Scoring (`free`) | $0.00 | scoring/live scoring; 5 AI reports; 10,000 tokens; 10 games; 1 tournament; no export/advanced analytics/team management |
| Scorers Pro (`player_pro`) | $1.99 | PDF/CSV export; advanced analytics; 15 AI reports; 30,000 tokens; unlimited games/tournaments |
| Coach Pro (`coach_pro`) | $19.99 | coach dashboard, notes, team management, advanced analytics, exports; 100 reports/100,000 tokens; no coaching sessions entitlement |
| Coach Pro Plus (`coach_pro_plus`) | $29.99 | Coach Pro plus assignments, sessions, video/upload/analysis/session reports; 25 GB; 7,200-second upload limit; 100 reports/100,000 tokens |
| Coach Live AI (`coach_live_ai`) | $59.99 | video/coaching feature flags; 50 GB; 10,800-second limit; 200 reports/250,000 tokens |
| Coach Live AI Advanced (`coach_live_ai_advanced`) | $99.99 | same broad flags; 100 GB; unlimited duration/reports/tokens |
| Analyst Pro (`analyst_pro`) | $29.99 | advanced analytics, PDF/CSV, team management; 200 reports/100,000 tokens |
| Organization Pro (`org_pro`) | $99.99 | broad coaching/video/analysis flags; unlimited reports/tokens/storage/duration with documented fair-use caveat |

There is a real contract mismatch that future work must resolve rather than inherit: `RoleEnum` contains `free`, `player_pro`, `coach_pro`, `coach_pro_plus`, `analyst_pro`, `org_pro`, and `venue_admin`, but not the two `coach_live_ai*` pricing plans. Pricing definitions therefore do not by themselves prove purchasable/authenticated runtime access.

### 4.2 Venue plans

| Plan | Current monthly USD | Canonical entitlements |
|---|---:|---|
| Venue Scoring Pro | $39.00 | branding removal, custom logo, fullscreen scoreboard; no broadcast layouts/multi-camera/LED |
| Venue Broadcast Plus | $99.00 | Venue Scoring Pro plus broadcast layouts, multi-camera, LED, custom overlays |
| League License | Contact | all listed venue/broadcast flags, contract-defined pricing |

Historical documentation differs from current canonical pricing configuration. Old planning/audit documents are useful provenance, but this audit does not silently reconcile them with `pricing.py` and does not modify either source.

## 5. Premium Capability Inventory

The inventory includes the shared Free foundation because it determines what can be safely composed into paid tiers. “Owner” below means the present authorization/ownership boundary, not the recommended future one.

| Capability | Current owner/plan | Backend | Frontend | Persistence | Entitlement | Tests | Readiness | Organization adaptation / key risk |
|---|---|---|---|---|---|---|---|---|
| Organization lifecycle, membership and tenant isolation | School/Club Free membership | `routes/organizations.py`; `organization_service.py` | School/Club shared admin shell | Organization + membership | Free plans | `test_school_organizations.py`, `test_club_free.py` | **A** | Reuse unchanged as paid-plan authority root. |
| Master roster and canonical player reuse | Organization | `organization_roster_service.py` | `SchoolPlayersView.vue` | PlayerProfile + SchoolPlayerMembership | Free | `test_school_roster.py` | **A** | Keep canonical profile; paid private metadata needs separate ownership. |
| Persistent teams and team rosters | Organization | organization team/roster services | team and roster views | Team + SchoolTeamPlayerMembership | Free | `test_school_teams.py`, `test_school_team_roster.py` | **A** | Keep in Free; terminology remains UI-level. |
| CSV/XLSX roster import | Organization | `school_player_import_service.py` | `SchoolImportView.vue` | SchoolPlayerImportSession/Row | Master/team-roster capabilities | `test_school_player_imports.py` | **A** | Keep in Free; do not couple to historical import. |
| Match setup and playing XI | Organization/member role | `school_match_service.py` | `SchoolMatchSetupView.vue` | Game match-local snapshots | Free capability conjunction | `test_school_match_setup.py` | **A** | Keep XI separate from team membership. |
| Basic statistics, fixtures and results | Organization | `school_statistics_service.py` | statistics/fixtures views | Game/delivery truth | Free | `test_school_statistics.py` | **A** | Paid analytics must add depth, not remove these aggregates. |
| Competitions and public/live scorecards | Organization/publication state | `school_competition_service.py` and routes | competitions/public scorecard views | Tournament/Fixture/Game publication fields | Free | `test_school_competition_publication.py`, `test_club_free.py` | **A** | Preserve tenant-private/public boundary. |
| Career, year, dismissal, form, consistency analytics | Public/personal player routes | `routes/player_analytics.py` | `PlayerProfileView.vue`, leaderboard | PlayerProfile/PlayerForm | `advanced_analytics` claim | `test_player_pro_features.py`, `test_player_profiles.py` | **B** | Scope eligible match history to organization/context; avoid exposing another tenant's private identity data. |
| Phase, pressure, heatmap and clustering analytics | Analyst/global role patterns | analytics/phase/heatmap/clustering routes/services | `AnalyticsView.vue`, analytics panels | Derived Game/delivery data | advanced analytics | phase/heatmap/clustering tests | **B** | Add organization-owned query scope and deterministic-data provenance. |
| Analyst filtered query workspace | `analyst_pro`/`org_pro` global role | `analyst_pro.py::run_analytics_query` | `AnalystWorkspaceView.vue` | Game, PlayerForm, CoachingSession | analyst/advanced flags | `test_analyst_pro_features.py` | **B** | Replace `User.org_id`/created-by scoping with membership + resource predicates. |
| Analyst CSV/JSON exports | global Analyst roles | `analyst_pro.py::{export_players, export_matches, export_player_form, get_analyst_export_data}` | `ExportUI.vue` | generated response, no export record | export flags | `test_analyst_pro_features.py`, `ExportUI.spec.ts` | **B** | Apply tenant filters, minor-data field policy, audit log, row limits. |
| Video-analysis PDF report | Coach Pro Plus owner | `coach_pro_plus.py::export_analysis_pdf`; `pdf_export_service.py` | video sessions view | PDF key/status on job | `export_pdf` + video | `test_pdf_export_restrictions.py` | **B** | Organization membership, report audience, retention, and download audit required. |
| Coach dashboard | personal Coach role | coach/player-development routes | `CoachesDashboardView.vue` | assignments/sessions/plans | `coach_dashboard` | `test_coach_pro_features.py` | **B** | Resolve role/seat in current organization; no global upgrade. |
| Coach-player assignment | Org Pro or superuser creates; coach owns | `coach_pro.py::assign_player` | coach dashboard/video player selector | CoachPlayerAssignment | `player_assignments` | `test_coach_pro_features.py` | **B** | Add organization/membership ownership and lifecycle; current FK deletes with coach. |
| Coaching sessions | coach/user-owned | coach-pro CRUD | coach dashboard | CoachingSession | plan flags inconsistent: route permits coach_pro while canonical Coach Pro flag is false | `test_coach_pro_features.py` | **B** | Reconcile code/config intentionally; tenant and minor visibility rules required. |
| Coaching notes | coach-owned; global premium roles | `coach_notes.py` | `coachingApi.ts`, notebook surfaces | CoachNote | `coaching_notes` | `test_coach_notes_contract.py` | **B** | Current update/delete is creator-centric; define private-to-coach vs organization visibility. |
| Player-development plans/goals | coach or legacy Org Pro | `player_development.py` and services | development cards/review UI | PlayerDevelopmentPlan and goal/intervention tables | coaching/AI flags | player-development test suite | **B** | Replace free-form `org_id`/global role assumptions with Organization FK/context and membership snapshots. |
| Development reports and team dashboard | coach/legacy org | report/dashboard services and routes | development insight/team overview cards | persisted plan plus derived report | no distinct organization entitlement | development dashboard/report tests | **B** | Organization-safe aggregation, audience, approval, and minor-facing policy. |
| Longitudinal progress and session comparison | Coach Pro Plus/Org Pro owner | `coach_pro_plus.py::{compare_session_jobs, get_player_longitudinal_progress}` | `PlayerLongitudinalProgress.vue`, video view | video jobs/goals/outcomes | video analysis | longitudinal/video tests | **B** | Decide portable cricket history versus organization-private coaching history. |
| Video-session CRUD | Coach Pro Plus/legacy Org Pro | `coach_pro_plus.py` session endpoints | video sessions view/store/service | VideoSession | video sessions | video session history tests | **B** | Current `OwnerTypeEnum` + `User.org_id` is not OrganizationMembership authorization. |
| Video upload, storage and playback | user/legacy org owner | presigned upload/complete/stream endpoints; quota service | video service/view | S3 key, file size, session/job | upload/storage/duration flags | upload, stream, quota tests | **B** | Organization quota ledger, malware/content validation, retention and membership-loss behavior. |
| Async video analysis pipeline | Coach Pro Plus/legacy Org Pro | analysis-job APIs, SQS service, worker, recovery | polling/results UI | VideoAnalysisJob/Chunk | video analysis | AI/video integration and recovery tests | **B** | Cost admission, tenant-safe worker payloads, cancellation, and organization billing required. |
| Goals, interventions, compliance and job comparison | video owner/coach | Coach Pro Plus goal/outcome endpoints | video results UI | fields/models around VideoAnalysisJob | video analysis | coach suggestions/report tests | **B** | Model organization/coaching relationship and immutable historical access snapshots. |
| Match AI summary/context package | Analyst roles | `analyst_pro.py::{get_match_ai_summary,get_match_context_package}`; `match_ai_service.py` | match case-study/analyst surfaces | Game AI summary fields/context | AI predictions/report claims | `test_match_ai_summary.py`, analyst tests | **B** | Separate deterministic context from generated prose; org scope and quota accounting. |
| ML win predictions | match access/current user | `prediction.py::get_game_win_probability`; prediction/model services | win-probability widget | prediction model/result metadata | `ai_predictions` | `test_prediction_service.py` | **B** | Confirm model availability/SLA and membership/public exposure rules. |
| Tournament intelligence and season aggregates | legacy tournament/analyst context | `routes/tournament_intelligence.py`; `tournament_intelligence_service.py` | `TournamentIntelligencePanel.vue` | Tournament/Fixture/Game-derived output | no distinct paid organization capability | `test_tournament_intelligence.py` | **B** | Reuse calculations only after current Organization ownership, competition scope and data-completeness policy are enforced. |
| Custom live overlays | game/broadcast routes, not current organization membership | overlay/event/sponsor routes/services | `EventOverlay.vue`, embed/viewer surfaces | game/event/sponsor data | venue `custom_overlays` | overlay/sponsor tests | **B** | Bind templates/assets to organization and enforce public output sanitization. |
| AI corrective guidance | premium global role | `coach_notes.py::get_ai_corrective_guidance` | `coachingApi.ts` | response not a governed org record | coaching/AI implied | coach notes tests | **C** | Provider/cost/provenance and persisted review workflow are not a complete organization product. |
| Moment markers, clip tagging and clip library | video-session owner | marker routes/models | coaching API/video UI pieces | VideoMomentMarker | video flags | marker/video tests | **C** | Markers exist; durable extracted clips, library lifecycle, sharing, quotas, and org policy are incomplete. |
| AI coaching suggestions/session report generation | video-job owner | suggestion/report services and endpoints | video results UI | JSON on VideoAnalysisJob and governed plan links | AI session reports | coach suggestion/report/V2 tests | **C** | Valuable implementation exists, but provider/cost enforcement and organization audit/seat policy are incomplete. |
| Ball tracking, pitch calibration/map and target-zone reports | personal video owner | Coach Pro Plus endpoints | video analysis UI | job JSON, TargetZone | video analysis | ball tracking/video tests | **C** | Mixed ownership (`TargetZone.owner_id` user) and production model limitations require hardening. |
| Live AI commentary | optional user | `ai.py::generate_ai_commentary`; `ai_commentary.py` | live commentary surfaces | usage log only | `ai_predictions` | AI route/service tests | **C** | Current usage records approximate 50 tokens and labels model `rule-based`; it is not proof of paid LLM commentary. |
| AI usage accounting and quotas | personal role, optional `org_id` | `ai_usage.py`, `billing_service.py`, billing routes | usage dashboard | AiUsageLog | token/report limits | AI usage/billing tests | **C** | Logging exists, but billing service is mocked and quota fields are not a paid OrganizationEntitlement contract. |
| Organization branding/theme editor | arbitrary `org_id` string | `branding.py`, `branding_service.py` | `useBranding.ts` | in-process `_org_themes`, not authoritative DB | venue logo/branding flags | `test_branding_service.py` | **C** | Routes lack current membership authority and persistence; unsafe as a paid tenant feature without redesign. |
| Premium fullscreen scoreboard/branding removal | venue config claim | no distinct paid organization enforcement found | viewer/embed scoreboards exist | no paid org grant | venue flags | general scoreboard tests | **D** | Working scoreboards do not prove paid fullscreen/branding-removal enforcement. |
| Broadcast layouts | Venue Broadcast Plus | meaningful paid layout implementation not established | generic scoreboard/overlay surfaces only | none identified | flag only | no end-to-end paid gate found | **D** | Requires explicit product and implementation scope. |
| Multi-camera support | Venue Broadcast Plus | no reliable orchestration found | none established | none identified | flag only | none found | **D** | Do not promise for School/Club Elite from configuration alone. |
| LED integration | Venue Broadcast Plus | no reliable integration found | none established | none identified | flag only | none found | **D** | Hardware/protocol/support surface is unscoped. |
| Priority support | multiple paid plans | no support workflow/SLA implementation found | no complete support surface | none identified | flag only | none found | **D** | Commercial/operational promise, not software entitlement alone. |
| Player availability | none | no organization availability domain found | no organization UI found | new model required | none | none | **E** | Requires dated event/match availability and privacy rules. |
| Attendance | none | no organization attendance domain found | no organization UI found | new model required | none | none | **E** | Schools need minor/teacher access and correction/audit semantics. |
| Advanced squad, batting-order and bowling-order planning | only match-local XI/captain/keeper exists | no persistent pre-match plan found | no planning UI found | new snapshot/version model required | none | none | **E** | Keep current XI Free; paid planning must be additive. |
| Training schedule, communications, announcements and season planning | none | no reliable shared org workflow found | no complete UI found | new models required | none | none | **E** | Notifications/consent/retention become separate risks. |
| Organization opponent analysis and benchmarking | isolated match/tournament intelligence exists | no tenant-wide paid comparison product | no complete org UI | new scoped aggregates/snapshots likely | none | no organization E2E | **E** | Requires minimum cohort/privacy rules and deterministic-vs-AI separation. |
| Scheduled reports, automation and organization-wide intelligence | none | no organization scheduler/report-delivery workflow | none | new schedule/run/audit models | none | none | **E** | Requires cost admission, delivery security, idempotency and failure handling. |

## 6. Team Operations Audit

| Operation | Current state | Organization-ready? | Persistence implication |
|---|---|---|---|
| Availability | Not implemented as a player/member response workflow. | No | New match/event-scoped response plus status/audit model. |
| Attendance | Not implemented as organization training/match attendance. | No | New event, attendance record, recorder and correction audit. |
| Squad/match selection | Free playing XI, captain and keeper are implemented at match creation. No versioned pre-match planning workflow was found. | Core selection yes; advanced planning no | Preserve Game snapshots; add versioned plan only if approved. |
| Batting/bowling order | Live scorer state and striker/bowler selection exist; no persistent pre-match order plan was found. | No paid planning surface | New ordered plan/snapshot; never replace scoring truth. |
| Captain/keeper | Implemented in Free match setup. | Yes, Free | No new persistence needed for existing behavior. |
| Match preparation | Team roster/XI setup exists; tasks/checklists/opposition pack do not. | Partial | Likely preparation record linked to fixture/team. |
| Training scheduling | CoachingSession schedules one coach-player session; no organization/team training calendar. | No | New organization/team event domain. |
| Communications/announcements | No reliable organization announcement workflow found. | No | New audience, delivery, read-state, consent and retention model. |
| Season planning | `Team.season` is metadata, not a planning workflow. | No | New season/calendar/goal model if approved. |

Team Operations is therefore a legitimate first paid slice, but captain/keeper/XI and roster operations remain Free.

## 7. Coaching & Development Audit

`CoachPlayerAssignment`, `CoachingSession`, `CoachNote`, `PlayerDevelopmentPlan`, development goals/interventions/checkpoints, and video jobs provide a substantial base. The frontend has coach dashboards, note APIs, development cards, recommendation review, video history, comparison, and PDF access. Tests cover assignments/sessions, note contracts, development approval, dashboards/reports, longitudinal history, video evidence, and V2 reports.

Current ownership is fragmented:

- Assignment and coaching session rows are keyed to `coach_user_id` and `player_profile_id`; deletion/visibility follows the coach relationship, not current OrganizationMembership.
- Coach notes are created by a coach and updates/deletes are creator/superuser centric. Note visibility includes `private_to_coach` and `org_only`, but “org” is not yet the current Organization FK/membership contract throughout.
- Player-development plans contain `org_id` as a string and authorize `org_pro` through `User.org_id`; this predates current organization membership.
- Video sessions use `owner_type`/`owner_id` and treat global `org_pro` + `User.org_id` as organization authority.
- `PlayerProfile` is global cricket identity/statistics, while SchoolPlayerMembership is organization-local roster status/metadata. Students do not require user accounts.

For School/Club reuse, coaching access should require: active organization membership, an organization-provided coaching seat/capability, active organization-player membership, and an explicit coaching relationship or administrator policy. Private coach notes must not automatically become organization-wide. When a membership ends, future access should cease, while immutable audit/history retention follows an owner-approved policy.

Minor-player requirements include least-privilege coach access, explicit player/guardian-facing publication policy, export restrictions, sensitive note categorization, video consent/visibility, access audit, and retention/deletion decisions. This audit does not claim legal compliance.

## 8. Analytics & Export Audit

### 8.1 Deterministic analytics

Implemented deterministic surfaces include player career/year/dismissal/form/consistency endpoints, organization basic statistics, innings grades and pressure maps, phase analysis, heatmaps, clustering, analyst delivery/match/player queries, tournament standings and intelligence, and player-development aggregation. Evidence includes `backend/routes/{player_analytics,analytics,analyst_pro}.py`, specialized analysis routes/services, `frontend/src/views/{AnalyticsView,AnalystWorkspaceView}.vue`, and corresponding analytics/analyst tests.

These must remain distinct from AI-generated interpretation. A calculation from Game/delivery truth can be Performance-tier analytics even when no model call is involved. Generated summaries require provider, quota, provenance, and review controls.

### 8.2 Exports

- Analyst CSV/JSON: implemented backend routes and `ExportUI.vue`; current access uses global Analyst/Org Pro roles and legacy game scoping.
- Video analysis PDF: implemented generation, readiness checks, persisted artifact metadata, UI download, and authorization tests.
- Player/scorecard data: response APIs exist, but no evidence supports an unrestricted organization bulk-export product.

Future organization exports require tenant predicates on every source, column allowlists, minor/student-identifier suppression by audience, row/file limits, audit logging, short-lived downloads, and membership revalidation. Public scorecards already demonstrate suppression of `student_identifier` and internal organization identifiers in `test_club_free_shared_cricket_workflow_on_postgresql`; paid exports must not reuse the public contract blindly or bypass it.

## 9. AI Audit

| AI/ML capability | Actual implementation | Inputs/outputs and persistence | Cost/quota state | Organization reuse assessment |
|---|---|---|---|---|
| Win probability | Prediction route/service and model manager; deterministic model result plus source metadata. | Game state -> probability/grounding response. | Entitlement flag exists; no organization usage ledger tied to current entitlement. | B; require org match access, model availability policy and public/private output rule. |
| Match AI summary | Match context service + match AI service + Analyst endpoints. | Game/delivery/roster context -> persisted/retrieved summary/context. | Individual AI report/token claims; enforcement not current-org based. | B; good context reuse after tenancy, provenance and quota adaptation. |
| Live commentary | Rule-based generator logs approximate token use as model `rule-based`. | Live match context -> transient commentary; usage row when authenticated. | Fixed approximate token record, not provider metering. | C; do not market as paid LLM automation from current evidence. |
| Corrective guidance | Coach-notes endpoint and training-drill/guidance services. | Coach/player observations -> guidance response. | No complete organization cost/admission contract. | C; provider/review/persistence/privacy need definition. |
| Video/session analysis | Async SQS worker, pose/metric/findings/report pipeline. | S3 video -> persisted jobs/chunks/metrics/findings/V2 reports. | Storage and duration limits exist by personal plan; compute quota is not an org entitlement. | B/C by subfeature; core pipeline reusable, commercial org operation incomplete. |
| Coaching suggestions/development drafts | Findings/report services and governed recommendation/approval workflow. | Video/match/coaching evidence -> persisted suggestions/plans/reports. | No complete organization report quota or seat model. | C for paid org product; preserve human approval before player-facing use. |
| Usage accounting | AiUsageLog can record user and optional `org_id`; reporting endpoints aggregate usage. | Feature/context/model/token metadata -> database rows. | `billing_service.py` is explicitly mocked; organization entitlement has no quota columns. | C; useful base, not enforceable paid organization metering. |

No repository evidence establishes complete organization products for scheduled player reports, team reports, season summaries, opponent reports, or automated report delivery. Existing report/context components may be reused, but those use cases remain E until scoped.

AI cost drivers are provider tokens/calls, model inference, video frame/pose processing, retries, report regeneration, polling/background jobs, and retained artifacts. Required controls include per-organization and per-seat counters, idempotent request keys, admission before enqueue, hard/soft limits, model/version records, failure charging policy, abuse/rate limits, and owner-visible usage. “Unlimited” personal Org Pro configuration is not a safe default for new organization tiers.

## 10. Video Audit

Current video capability is substantial:

- Persistence: `VideoSession`, `VideoAnalysisJob`, `VideoAnalysisChunk`, `VideoMomentMarker`, and `TargetZone` in `backend/sql_app/models.py`.
- Upload/storage: presigned S3 initiate/complete, file-size persistence, duration validation, quota service, and S3 object verification in `backend/routes/coach_pro_plus.py`.
- Playback: presigned stream URL endpoint and frontend playback.
- Relationships: player-centered session fields and JSON player IDs; owner is coach or legacy org. A direct current Organization/Team FK is not consistently present.
- Processing: queued jobs/chunks, SQS service, long-poll worker, recovery, quick/deep stages, findings, reports, repetitions and phases.
- Coach workflow: goals, interventions, outcomes/compliance, comparisons, longitudinal progress, suggestions, governed development recommendations, and PDF export.
- Deletion: single/bulk session deletion attempts to remove S3 objects and database analysis data; retention policy is not a paid organization contract.

Reusable for Elite after adaptation: session/upload/playback core, async job state machine, worker recovery, analysis artifacts, reports, and comparison UI. Partial: markers are not a full extracted clip library; target zones are personally owned; organization access relies on global Org Pro/User.org_id; organization storage/compute accounting is absent.

Cost and privacy risks: raw storage, derived artifacts, presigned transfer/bandwidth, long-duration uploads, repeated analysis, GPU/CPU worker time, failed/retried jobs, backups, deletion lag, and video containing minors/bystanders. Owner/legal decisions are required for consent, lawful basis, retention duration, export/share rules, subject requests, provider regions, and deletion guarantees. No cost figures are inferred here.

## 11. Organization Authorization & Seat Model Audit

### 11.1 Current conflict map

| Legacy dependency | Examples | Required adaptation |
|---|---|---|
| Global `RoleEnum` | Coach, Analyst, Org Pro route guards | Resolve active OrganizationMembership role plus organization plan/capability; keep personal role independent. |
| Personal plan feature | billing feature lookups and video `_check_feature_access` | Add organization plan resolution in organization context; define personal fallback explicitly. |
| User-owned object | CoachNote, CoachPlayerAssignment, CoachingSession, TargetZone | Add organization/resource ownership and relationship checks without exposing other organizations. |
| `org_pro` + `User.org_id` | Analyst scoping, video owner access, player development | Replace with current Organization FK and membership; never trust `User.org_id` as paid-organization authority. |
| Superuser | administrative bypasses | Keep explicit, audited operational bypass only; do not use for normal organization flow. |

### 11.2 Proposed contextual authorization rule

For every paid request, authorize all of:

1. Active `Organization` selected by route/context.
2. Active `OrganizationMembership` for the actor.
3. Active organization entitlement and named capability.
4. Resource `organization_id` (or safely migrated owner) equals route organization.
5. Membership role/seat permits the action.
6. Player/team/match relationship belongs to that organization, with tenant-safe 404 for exact foreign IDs.

### 11.3 Seat model

The current membership system can support a future contextual seat assignment, but no paid seat entity/count contract exists. The safest direction is an organization-scoped seat/grant keyed to membership and capability bundle. It must not mutate `User.role`, `subscription_plan`, or permanently grant personal benefits.

Questions requiring owner approval:

- Does Performance include a fixed number of coach seats or all active coaches?
- Does Elite include separate analyst/video seats, pooled seats, or role-based access?
- Can owners/admins consume premium capabilities without a seat?
- Are scorers/viewers ever eligible for analytics read access?
- What happens to authored notes/reports/video when a seat or membership ends?
- Do individually paid users retain their personal workspace outside the organization? Recommended: yes; organization access ends with membership while personal entitlements remain independent.

## 12. Player Identity / History Implications

`PlayerProfile` is the canonical cricket player/statistics record. `SchoolPlayerMembership` links that player into any School or Club and stores organization-local roster status/metadata; `SchoolTeamPlayerMembership` permits multiple teams without duplicate profiles. Coaching, development, analytics, and video currently attach to PlayerProfile but use coach/user/legacy-org ownership inconsistently.

Four possible history contracts:

- **Global PlayerProfile:** strongest continuity when changing organizations, highest privacy/leakage risk for private coaching/video.
- **Organization membership:** safest tenant privacy, but history fragments and may disappear from the player's next organization.
- **Team membership:** too narrow for multi-team and long-term development.
- **Coaching relationship:** supports private notes but is fragile when coach/player relationships end.

Recommended candidate for owner decision is a **hybrid snapshot model**, not a locked persistence decision:

- Global, evidence-backed cricket performance truth follows PlayerProfile.
- Organization-funded notes, development plans, video, reports and AI outputs are organization-owned and relationship-scoped.
- Cross-organization portability requires explicit consent/transfer policy and a bounded snapshot, not implicit access to the source organization's records.
- Historical artifacts retain author, organization, player identity reference, source evidence, visibility, and policy snapshot even after membership changes.

Owner/legal approval is required before schema design, especially for minors, player access, guardian access, portability, deletion, and organization departure.

## 13. Security / Privacy / Tenancy

Required controls for every future slice:

- Tenant-safe route predicates include route organization ID and resource ID; no global-role or `User.org_id` shortcut.
- Membership and paid seat are revalidated on reads, writes, exports, stream URLs, background enqueue and artifact download.
- Minor/player data is private by default; student identifiers never enter public scorecards, broad exports, AI prompts or video metadata unless explicitly required and approved.
- Coach-private and organization-visible records have distinct, enforced visibility semantics.
- Analyst access is read-only unless a separately named role/capability permits mutation.
- Video uses short-lived URLs, validated content/size/duration, access logging, controlled sharing, retention and deletion jobs.
- Exports are scoped, field-limited, size-limited, auditable and protected after generation.
- AI provider data flow records purpose, input categories, model/provider, organization, output, provenance, review state and retention; secrets/raw prompts are not exposed to clients.
- Public/private publication remains explicit and reversible without leaking internal IDs or roster metadata.
- Administrative/superuser access is logged; organization owners cannot grant capabilities the plan does not contain.
- Membership removal, seat removal, organization suspension and entitlement expiry have defined effects on sessions, jobs, reports, downloads and scheduled work.

This document does not assert compliance with child protection, education, privacy, biometric, employment, copyright, or AI law. Those are owner/legal decisions by jurisdiction.

## 14. Free Capability Protection

Protected in both School Free and Club Free:

- Core scoring and unlimited organization match creation.
- Master roster and canonical player reuse.
- Persistent Team creation and maintenance.
- Team rosters and multi-team player membership.
- Match-local playing XI, captain and wicketkeeper selection.
- CSV/XLSX import with preview/validation/duplicate resolution/explicit apply.
- Basic player/team statistics.
- Fixtures and results.
- Competitions, entrants, fixtures and standings.
- Live member scorecards and controlled public scorecards.
- Current organization administration and contextual membership roles.

Performance and Elite must add management, development, analysis, automation and resource-intensive capabilities. They must not introduce artificial match limits or move current operational cricket behind a paywall without a separately approved product decision.

## 15. Proposed School/Club Free–Performance–Elite Matrix

The same capability bundles should serve both organization types; School/Club labels and carefully identified privacy rules vary by context.

| Capability | Free | Performance | Elite | Current readiness | Notes |
|---|---:|---:|---:|---|---|
| Scoring, rosters, teams, XI, fixtures/results, competitions, public scorecards, import, basic stats | Yes | Yes | Yes | A | Protected Free baseline. |
| Availability and attendance | — | Candidate | Yes | E | First operations slice; privacy/audit needed. |
| Versioned squad and batting/bowling order planning | Core XI remains Free | Candidate advanced planning | Yes | E | Must not alter scoring truth. |
| Coaching assignments, sessions and notes | — | Candidate | Yes | B | Contextual seats and visibility required. |
| Development goals/plans/history/comparison | — | Candidate | Yes | B | Hybrid history decision required. |
| Deterministic advanced analytics and organization dashboards | Basic only | Candidate | Yes | B | Separate from AI interpretation. |
| CSV/JSON/PDF exports | — | Candidate bounded export | Yes | B | Minor-data policy and audit required. |
| Bounded non-video AI reports | — | Optional candidate | Higher quota | B/C | Only after organization metering and review policy. |
| Video upload/playback/session analysis | — | — | Candidate | B/C | Storage, compute, privacy and seats dominate cost. |
| Clip library/tags | — | — | Candidate | C | Markers exist; library/extraction incomplete. |
| Automated reports and organization intelligence | — | — | Candidate | E | Requires scheduler, quota, delivery and audit. |
| Opponent analysis/benchmarking | — | Limited deterministic candidate | Candidate advanced | E | No current organization-wide product; cohort privacy matters. |
| Branding/broadcast | Public scorecards remain Free | Optional branding only after hardening | Evaluate separately | C/D | Venue value is not automatically School/Club value. |

School and Club use the same implementation. Genuine differences:

- School: minors/student privacy, teacher/coach context, year-group and academic-year terminology.
- Club: adult/youth mix, team-manager terminology, season/member operations.
- UI-only differences: “School”/“Club”, “student/player”, “year group/age group” where approved.
- Data/authorization differences: minor consent/visibility and potentially guardian/teacher authority. These require explicit policy; they are not justification for duplicating core capability code.

## 16. Individual Plan Overlap / Cannibalization Risks

| Existing plan | Organization-tier overlap | Risk/question |
|---|---|---|
| Player Pro / Scorers Pro | advanced stats and exports | Organization access must not grant permanent personal export/analytics outside membership; define player-facing access. |
| Coach Pro | dashboard, notes, team management, analytics, exports | Performance could substitute for individual Coach Pro for staff. Decide included seat count and personal-workspace separation. |
| Coach Pro Plus | assignments, sessions, video, AI reports | Elite directly overlaps. Define video/coach seats and whether individually owned history remains accessible outside organization. |
| Coach Live AI tiers | high AI/video quotas | These plans exist in pricing but not global RoleEnum. Resolve product/runtime status before using them as an anchor. |
| Analyst Pro | workspace, advanced analytics, exports, AI summaries | Performance/Elite analyst seats may cannibalize individual Analyst Pro; constrain access to organization data. |
| Org Pro | broad “unlimited” coaching/video/analysis claim | Legacy Org Pro authorization uses global role/User.org_id and conflicts with current contextual tenancy. Decide migration/coexistence; do not map automatically. |
| Venue Scoring/Broadcast | branding, fullscreen, overlays, broadcast hardware | Avoid bundling niche venue value into School/Club tiers unless demand and implementation justify it. |

Recommended licensing principle: an organization subscription grants contextual capabilities to selected active memberships. Personal subscriptions remain personal; membership loss removes organization access but does not downgrade the user's personal account. Authored organization records remain governed by the organization's retention/access policy.

## 17. Cost / Quota / Fair-Use Considerations

| Tier | Value driver | Expensive capabilities | Needed controls/questions |
|---|---|---|---|
| Free | run cricket and onboard organizations | database/storage/traffic for matches, imports and public live views | Abuse/rate limits and reasonable operational safeguards, but no artificial match cap. |
| Performance | save staff time and improve players through operations, coaching and deterministic analysis | exports, aggregate queries, limited AI reports | coach/analyst seats, export limits, report quota, refresh cadence, monthly vs annual, fair-use language. |
| Elite | video intelligence and automation | raw/derived video storage, bandwidth, worker compute, AI inference, retries, scheduled generation | video seats, GB and duration limits, compute minutes/jobs, retention tiers, report/token quotas, overage/stop behavior, annual commitment. |

Do not copy Org Pro's configured unlimited storage/tokens into new tiers without cost evidence. Required decisions include pooled versus per-seat quotas, unused quota rollover, failed job charging, re-analysis charging, export limits, archival pricing, support scope, and abuse response. Current code contains no approved School/Club prices.

## 18. Open Product Decisions

1. Final capability names and whether Performance contains bounded AI or remains deterministic/coaching only.
2. Staff seat counts, seat types, assignment authority and owner/admin consumption.
3. Coexistence/migration for personal Org Pro and `User.org_id`.
4. Whether Player/Coach/Analyst individual subscribers receive any organization seat benefit or discount.
5. Player/guardian access to organization-funded development history.
6. Hybrid-history portability, transfer consent, revocation and snapshot semantics.
7. Coach-private versus organization-visible note defaults and administrator access.
8. Minor video consent, AI-provider usage, retention, deletion and geographic requirements.
9. Organization export fields, audit, retention and student-identifier policy.
10. AI provider/model approval, human-review requirements and quota/overage behavior.
11. Video storage, duration, processing, retention and bandwidth limits.
12. Whether branding/fullscreen/overlays belong in organization tiers or remain venue products.
13. Monthly/annual billing, trials, grace periods, entitlement expiry and grandfathering.
14. Availability/attendance scope and whether guardian/player accounts are required.
15. School academic-year semantics versus Club season semantics.
16. Support level/SLA; the current `priority_support` flag is not an implemented workflow.

## 19. Recommended Incremental Implementation Slices

### Slice 1 — Organization Team Operations

- Reuse: OrganizationMembership, Team, roster, fixture and XI services/UI.
- New: availability, attendance, preparation and versioned selection/order planning only as approved.
- Likely schema: organization event, availability response, attendance record, selection-plan/version; migrations required.
- Authorization: membership role + Performance capability + exact org/team/fixture predicates.
- Frontend: shared School/Club operations screens using terminology composable.
- Tests: role matrix, cross-tenant exact-ID 404, minor fields, optimistic/concurrent updates, XI/scoring regressions.
- Risk: confusing planned orders with authoritative live scoring.
- Prerequisite: paid organization plan/seat contract.

### Slice 2 — Organization Coaching & Development

- Reuse: CoachPlayerAssignment, CoachingSession, CoachNote, development plan/report/dashboard/approval workflows.
- New/adapt: Organization FKs, membership/seat authority, note visibility, relationship lifecycle, history snapshots.
- Likely migrations: organization ownership and retained-author/audience fields; exact shape awaits history decision.
- Frontend: contextual coach dashboard and player development workspace.
- Tests: coach/admin/analyst matrices, private-note isolation, membership/seat removal, minor visibility, player multi-org history.
- Risk: leaking sensitive notes or transferring history without authority.
- Prerequisites: Slice 1 identity/event decisions; owner/legal history policy.

### Slice 3 — Performance Analytics & Exports

- Reuse: deterministic analytics, Analyst query workspace, organization basic stats, CSV/JSON and PDF patterns.
- New/adapt: organization query scopes, dashboards, export audit/field policies and bounded jobs for large exports.
- Likely schema: saved filter/view only if product approves; export job/audit may be required.
- Frontend: organization/team/season dashboards and scoped export controls.
- Tests: data-truth fixtures, tenant isolation, public/private/minor redaction, large-query limits, deterministic calculations.
- Risk: expensive queries and cross-tenant joins.
- Prerequisite: organization analyst seat/capability.

### Slice 4 — Organization AI Reports

- Reuse: match context, report/presentation services, AiUsageLog, governed recommendation review.
- New: organization quota ledger, request/admission/idempotency, provider metadata, report ownership/audience and review state.
- Likely migrations: organization AI usage/allocation and report-run records.
- Frontend: bounded player/team/match report requests, usage and review.
- Tests: quota concurrency, retry idempotency, provider failure, prompt input redaction, evidence/provenance, human approval.
- Risk: variable cost, hallucination and minor-data provider exposure.
- Prerequisites: Slice 2/3 evidence and visibility contracts.

### Slice 5 — Video Performance

- Reuse: upload/playback, sessions/jobs/chunks, SQS worker, recovery, analysis reports, comparisons and PDF.
- New/adapt: current Organization ownership, video seats, compute/storage accounting, retention/deletion, consent/access audit, clip library if approved.
- Likely migrations: organization ownership, quota/usage, policy snapshot and clip entities.
- Frontend: contextual Elite video workspace, usage/retention controls.
- Tests: tenant-safe URLs/jobs, upload validation, quota concurrency, worker tenant payload, delete/recovery, membership loss, minor privacy.
- Risk: highest storage/bandwidth/compute and privacy exposure.
- Prerequisites: Slice 2 identity/history and Slice 4 usage accounting.

### Slice 6 — Elite Automation & Intelligence

- Reuse: reports, analytics context packages, job/idempotency patterns.
- New: schedule/delivery engine, organization intelligence aggregation, benchmarking/opponent policy, run audit and cancellation.
- Likely migrations: schedule, run, delivery, cohort/version records.
- Frontend: schedule management, report history, usage and failures.
- Tests: duplicate prevention, timezone/calendar, entitlement expiry, quota reservation, tenant-safe delivery, cohort privacy, cancellation/retry.
- Risk: unattended cost, stale/wrong recipients, invalid benchmarking claims.
- Prerequisites: all relevant earlier slices; this should be last.

Each slice should be a separately governed issue with a real-PostgreSQL migration gate where schema changes occur, one Alembic head, explicit rollback, security/tenant tests, Free regressions, and protected scoring/DLS/result/video/AI boundaries appropriate to the slice.

## 20. Future Governance Recommendation

Do not add a new master phase in Issue #559. After owner decisions on seats, history, privacy, quotas and tier boundaries, the roadmap should become **multiple governed phases or small phase groups**, not one large implementation phase. The six slices have different schemas, risk profiles and rollback needs; each should begin with an audit/spec lock or an implementation-ready issue and independently protect Free functionality.

Recommended governance follow-up:

1. Owner decision record for product tiers, seats, history, minors/privacy, quotas and legacy Org Pro.
2. A narrowly scoped master-checklist governance PR, if the owner elects to create formal phases.
3. Separate implementation issues per slice, starting with organization plan/seat authority and Team Operations.
4. No implementation issue may implicitly broaden organization capabilities or change canonical pricing.

## 21. Explicit Non-Goals

This audit does not:

- Implement School/Club Performance or Elite.
- Change pricing, billing, entitlements, roles, memberships or authorization.
- Add migrations, dependencies, workflows or runtime code.
- Modify scoring truth, DLS, result logic, match state, historical import, AI execution, video processing or public publication.
- Establish final prices, quotas, fair-use terms, seat counts, support SLAs or legal compliance.
- Lock a player-history persistence contract.
- Promise entitlement/config-only venue features as implemented organization products.
- Add a phase to `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`.

## 22. Final Recommendation

Proceed toward one shared organization capability architecture for Schools and Clubs. First approve the contextual paid-plan/seat contract and hybrid-history/privacy decisions. Then implement Team Operations, Coaching & Development, and deterministic Analytics/Exports before introducing organization AI or video. Video and automation belong in Elite only after enforceable usage accounting, retention, provider, consent and tenant controls exist.

The repository can reuse substantial Coach Pro, Coach Pro Plus and Analyst Pro functionality, but reuse means adapting authorization and ownership—not granting global roles to organization members and not treating legacy `User.org_id` or personal Org Pro as the new tenancy model. Free must remain the complete “run cricket” product already proven for both Schools and Clubs.

