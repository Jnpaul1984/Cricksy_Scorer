# School & Club Free + Performance Product Checklist

## 1. Product strategy and audit basis

This Issue #561 audit is grounded in repository commit `58f41d8ebf15d82c28624f6f9b85cfdb6547aad1` (the latest `main` inspected on 2026-09-24). Runtime code and tests are treated as truth; entitlement names and earlier roadmap prose are not treated as proof of implementation.

- **Free — Run your cricket.** School and Club share one organization capability architecture. The current operating baseline is protected and must not be weakened to manufacture upgrade pressure.
- **Performance — Manage, coach, improve and understand your cricket.** It adds organization-safe workflows, deterministic analysis, coaching and presentation. Deterministic cricket evidence precedes bounded AI explanation.
- **Elite — future boundary only.** This checklist neither promises nor plans a public Elite product.
- **Private Video Analysis — controlled operated service.** Existing video technology may support an internal service after hardening; it is not a public organization self-service entitlement.

No row authorizes implementation, pricing, billing, entitlements, migrations, roles, public routing, AI execution, video processing, or use of private message content as performance-model input. Nothing here authorizes sale of identifiable children's personal information.

## 2. Status, cost and control legend

Each capability row has exactly one primary status and one cost class.

- **BUILT:** organization-native and end-to-end now.
- **ADAPT:** meaningful code exists, but tenancy, authorization, terminology, persistence, privacy, or packaging must change.
- **NEW:** no reliable implementation was found.
- **DEFER:** intentionally outside current Free/Performance/private-video scope.
- **OWNER DECISION:** product, privacy, legal, or economic behavior must be locked first.
- **LOW:** ordinary DB/API/UI work; **USAGE-SENSITIVE:** volume, traffic, jobs, export, storage, email or push drives cost; **HIGH:** AI/video/large storage/bandwidth/paid services; **UNKNOWN:** repository evidence is insufficient.

Every row's control profile records the Issue #561 economic fields in this order: `driver; hard quota; rate limit; retention; paid third party; worker`.

| Profile | Driver; hard quota; rate limit; retention; paid third party; worker |
|---|---|
| C-DB | DB/API/UI; no; normal abuse limit; normal records; no; no |
| C-PUBLIC | public traffic; traffic ceiling if abused; yes; normal records/cache; hosting/CDN possible; no |
| C-MSG | notification volume; channel quota; yes; message/notification policy required; push/email/SMS possible; delivery worker likely |
| C-EXPORT | query/output size; row/file quota; yes; generated-artifact policy; object storage possible; large exports likely |
| C-AI | inference/tokens; yes; yes; prompt/output policy; AI provider likely; yes |
| C-VIDEO | storage/bandwidth/compute; yes; yes; explicit media/artifact lifecycle; S3/AI/compute; yes |
| C-PAY | transaction/provider volume; provider/economic limits; yes; financial/legal schedule; payment provider; webhooks/reconciliation likely |
| C-DATA | aggregation/query/export; cohort/export limits; yes; governed dataset policy; possible; batch work likely |

### 2.1 Evidence registry

Checklist cells cite these exact current-code anchors. A citation is evidence of existing technology, not proof that the requested organization product is already safe.

- **E-ORG:** `backend/sql_app/models.py::{Organization,OrganizationMembership,OrganizationEntitlement}`; `backend/services/organization_service.py::{create_organization,list_organizations_for_user,require_membership_manager,update_membership,disable_membership}`; `backend/routes/organizations.py`; tests `backend/tests/{test_school_organizations,test_school_memberships,test_school_tenant_isolation,test_club_free}.py`.
- **E-ENT:** `backend/services/organization_entitlement_service.py::{FREE_ORGANIZATION_CAPABILITIES,PLAN_CAPABILITIES,require_organization_capability}`; tests `backend/tests/{test_school_entitlements,test_club_free}.py`.
- **E-ROSTER:** `backend/sql_app/models.py::{PlayerProfile,SchoolPlayerMembership}`; `backend/services/organization_roster_service.py`; `frontend/src/views/school/SchoolPlayersView.vue`; tests `backend/tests/test_school_roster.py`, `frontend/tests/unit/SchoolAdminViews.spec.ts`.
- **E-TEAM:** `backend/sql_app/models.py::{Team,SchoolTeamPlayerMembership}`; organization team/roster services; `SchoolTeamsView.vue`, `SchoolTeamRosterView.vue`; tests `test_school_teams.py`, `test_school_team_roster.py`.
- **E-IMPORT:** `backend/services/school_player_import_service.py::{create_preview,apply_import,_parse_csv,_parse_xlsx}`; `SchoolImportView.vue`; `backend/tests/test_school_player_imports.py`.
- **E-MATCH:** `backend/services/school_match_service.py::{_eligible_side,_team_snapshot,_external_snapshot,create_school_match}`; `backend/api/schemas/school_matches.py`; `SchoolMatchSetupView.vue`; `backend/tests/test_school_match_setup.py`.
- **E-STATS:** `backend/services/school_statistics_service.py::{player_statistics,team_statistics,match_results,fixture_summaries}`; `SchoolStatisticsView.vue`, `SchoolFixturesResultsView.vue`; `backend/tests/test_school_statistics.py`.
- **E-COMP:** `backend/services/school_competition_service.py::{create_competition,create_fixture,link_fixture_game,standings,publication,public_scorecard}`; corresponding routes/views; tests `test_school_competition_publication.py`, `test_club_free.py`.
- **E-EVENT:** `backend/sql_app/models.py::{OrganizationEvent,OrganizationEventTeam,OrganizationEventRosterPlayer}`; `backend/services/organization_event_service.py::{create_event,list_events,update_event,cancel_event,calendar}`; `backend/routes/organization_events.py`; `frontend/src/views/school/OrganizationEventsView.vue`; tests `backend/tests/test_organization_events.py`, `frontend/tests/unit/OrganizationEventsView.spec.ts`.
- **E-TERMS:** `frontend/src/router/index.ts::organizationChildren`; `frontend/src/composables/{useSchoolContext,useOrganizationTerminology}.ts`; `frontend/tests/unit/ClubFreeViews.spec.ts`.
- **E-PLAYER:** `backend/sql_app/models.py::{PlayerProfile,PlayerAchievement,PlayerForm}`; `backend/routes/player_analytics.py::{get_player_career_summary_endpoint,get_player_yearly_stats,get_player_dismissals,get_player_form_analysis,get_player_consistency_score,get_batting_leaderboard}`; `PlayerProfileView.vue`; tests `test_player_profiles.py`, `test_player_pro_features.py`, `PlayerProfileView.spec.ts`.
- **E-FAN:** `backend/sql_app/models.py::FanFavorite`; `backend/routes/fan_mode.py::{create_favorite,list_favorites,delete_favorite}`; `frontend/src/views/PlayerProfileView.vue::{loadFavorites,toggleFavorite}`; `frontend/src/services/api.ts::{getFanFavorites,createFanFavorite,deleteFanFavorite}`.
- **E-ANALYTICS:** `backend/routes/{analytics,player_analytics,analyst_pro,prediction}.py`; `backend/services/analyst_access.py`; `AnalyticsView.vue`, `AnalystWorkspaceView.vue`, `MultiPlayerComparisonView.vue`; phase/pressure/heatmap/clustering/prediction and analyst tests.
- **E-COACH:** `backend/sql_app/models.py::{CoachPlayerAssignment,CoachingSession,CoachNote}`; `backend/routes/{coach_pro,coach_notes}.py`; `CoachesDashboardView.vue`; tests `test_coach_pro_features.py`, `test_coach_notes_contract.py`.
- **E-DEV:** `backend/sql_app/models.py::{PlayerDevelopmentPlan,PlayerDevelopmentGoal,PlayerProgressCheckpoint,PlayerDevelopmentIntervention}`; `backend/routes/player_development.py`; development plan/dashboard/report/longitudinal services; associated backend and frontend tests.
- **E-EXPORT:** `backend/routes/analyst_pro.py::{export_players,export_matches,export_player_form,get_analyst_export_data}`; `backend/services/pdf_export_service.py`; `ExportUI.vue`; tests `test_analyst_pro_features.py`, `test_pdf_export_restrictions.py`, `ExportUI.spec.ts`.
- **E-AI:** `backend/sql_app/models.py::{AiUsageLog,AiInsightReview}`; `backend/services/{ai_usage,ai_match_summary,ai_player_insights,ai_insight_review_service,coach_ai_pipeline}.py`; routes `ai.py`, `ai_usage.py`, `ai_insight_review.py`; Phase 8/AI/report tests.
- **E-SPONSOR:** `backend/sql_app/models.py::{Sponsor,SponsorImpression}`; `backend/routes/{sponsors,sponsor_rotation}.py`; `backend/services/sponsor_rotation_engine.py`; `SponsorsBar.vue`; tests `test_sponsor_rotation_engine.py`.
- **E-BRAND:** `backend/routes/branding.py`; `backend/services/branding_service.py`; `BrandingPanel.vue`, `EventOverlay.vue`, `useBranding.ts`; `backend/tests/test_branding_service.py`. Current themes are in-memory and routes are not current OrganizationMembership enforcement.
- **E-BILL:** `backend/config/pricing.py`; `backend/routes/billing.py`; `backend/services/billing_service.py`; pricing contract/consistency tests. The billing module explicitly says it is mocked pending Stripe and is not organization transaction processing.
- **E-VIDEO:** `backend/sql_app/models.py::{VideoSession,VideoAnalysisJob,VideoAnalysisChunk,VideoMomentMarker,TargetZone}`; `backend/routes/coach_pro_plus.py`; `CoachProPlusVideoSessionsView.vue`; upload/stream/quota/history/PDF tests. Ownership is personal/global-role or legacy `User.org_id`, not current membership tenancy.
- **E-VIDEO-JOB:** `backend/services/{s3_service,sqs_service,video_job_recovery,video_quota_service,video_chunking}.py`; `backend/scripts/run_video_analysis_worker.py`; tests `test_video_job_recovery.py`, `test_video_quota.py`, `test_video_upload_s3_key_persistence.py`, `test_video_stream_url_presign.py`.
- **E-VIDEO-RESULT:** `backend/services/{coach_plus_analysis,coach_report_v2,coach_report_presentation,coach_strength_consistency}.py`; analysis/repetition/phase/report/longitudinal endpoints in `coach_pro_plus.py`; report/V2/integration tests.
- **E-ABSENT:** repository-wide model/route/service/view/test filename and symbol searches found no organization availability, attendance, announcement, chat, guardian, organization-payment, donation, or fundraising runtime surface. `backend/core/live_bus.py` and Socket.IO carry scoring state, not private/team messaging.

## 3. Current shared Free baseline — protected

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-BASE-001 | Organization creation | Free | BUILT | LOW | E-ORG | Preserve shared School/Club creation. | None | No | C-DB |
| FREE-BASE-002 | Contextual memberships | Free | BUILT | LOW | E-ORG | Preserve membership authority. | Organization | No | C-DB |
| FREE-BASE-003 | Owner/admin/coach/scorer/viewer roles | Free | BUILT | LOW | E-ORG | Preserve contextual matrix; no global school roles. | Membership | No | C-DB |
| FREE-BASE-004 | Shared School Free / Club Free capability source | Free | BUILT | LOW | E-ENT; same frozen set is asserted by `test_club_free.py`. | Keep one capability vocabulary. | Entitlement | No | C-DB |
| FREE-BASE-005 | Master roster | Free | BUILT | LOW | E-ROSTER | Preserve lifecycle and tenant scope. | Organization | No | C-DB |
| FREE-BASE-006 | Canonical PlayerProfile | Free | BUILT | LOW | E-ROSTER | Preserve canonical identity. | None | No | C-DB |
| FREE-BASE-007 | Persistent Teams | Free | BUILT | LOW | E-TEAM | Preserve organization ownership. | Organization | No | C-DB |
| FREE-BASE-008 | Team rosters | Free | BUILT | LOW | E-TEAM | Preserve reusable multi-Team membership. | Roster, Team | No | C-DB |
| FREE-BASE-009 | CSV/XLSX roster import | Free | BUILT | USAGE-SENSITIVE | E-IMPORT | Preserve preview/apply and limits. | Master roster | No | C-DB |
| FREE-BASE-010 | Saved-Team match setup | Free | BUILT | LOW | E-MATCH | Preserve snapshot boundary. | Team roster | No | C-DB |
| FREE-BASE-011 | External-opponent match setup | Free | BUILT | LOW | E-MATCH | Preserve match-local opponent data. | Match setup | No | C-DB |
| FREE-BASE-012 | Playing XI | Free | BUILT | LOW | E-MATCH | Preserve exactly-11 validation. | Match setup | No | C-DB |
| FREE-BASE-013 | Captain and wicketkeeper | Free | BUILT | LOW | E-MATCH | Preserve XI-contained role validation. | Playing XI | No | C-DB |
| FREE-BASE-014 | Organization scoring | Free | BUILT | USAGE-SENSITIVE | `school_competition_service.py::{school_game_scoring_authorization,require_school_game_scorer}`; `test_school_phase7k_acceptance.py`. | Do not change scoring truth. | Match setup | No | C-DB |
| FREE-BASE-015 | Fixtures and results | Free | BUILT | LOW | E-STATS | Preserve organization attribution. | Scored Game | No | C-DB |
| FREE-BASE-016 | Competitions | Free | BUILT | LOW | E-COMP | Preserve entrants/fixtures/standings. | Teams, Games | No | C-DB |
| FREE-BASE-017 | Basic player statistics | Free | BUILT | LOW | E-STATS | Preserve evidence-backed aggregates. | Scoring truth | No | C-DB |
| FREE-BASE-018 | Basic Team statistics | Free | BUILT | LOW | E-STATS | Preserve evidence-backed aggregates. | Scoring truth | No | C-DB |
| FREE-BASE-019 | Live/member scorecards | Free | BUILT | USAGE-SENSITIVE | E-COMP; member game authorization and scoring routes. | Keep membership scope. | Game | No | C-PUBLIC |
| FREE-BASE-020 | Controlled public scorecards | Free | BUILT | USAGE-SENSITIVE | E-COMP | Preserve explicit reversible publication. | Publication state | No | C-PUBLIC |
| FREE-BASE-021 | School/Club terminology and routes | Free | BUILT | LOW | E-TERMS | Continue UI terminology over shared services. | Organization type | No | C-DB |
| FREE-BASE-022 | Tenant isolation | Free | BUILT | LOW | E-ORG/E-ROSTER/E-TEAM; `test_school_tenant_isolation.py`, `test_club_free.py`. | Preserve route-org plus resource predicates. | Membership | No | C-DB |

## 4. Free expansion — Run your cricket

### 4.1 Availability

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-AVL-001 | Available / Unavailable / Maybe response | Free | NEW | LOW | E-ABSENT | Add tenant-scoped response model/API/UI. | Events, player subject | No | C-DB |
| FREE-AVL-002 | Fixture-linked availability | Free | NEW | LOW | Fixtures exist (E-COMP); no response link (E-ABSENT). | Link response to fixture/event. | FREE-AVL-001 | No | C-DB |
| FREE-AVL-003 | Training/event-linked availability | Free | NEW | LOW | E-ABSENT | Link response to event. | Event foundation | No | C-DB |
| FREE-AVL-004 | Player/guardian response path | Free | OWNER DECISION | UNKNOWN | No guardian relationship (E-ABSENT). | Lock minor identity, consent and proxy rules. | Guardian policy | Yes — respondent authority | C-DB |
| FREE-AVL-005 | Coach/team-manager overview | Free | NEW | LOW | E-ABSENT | Add role-scoped Team summary. | FREE-AVL-001 | No | C-DB |
| FREE-AVL-006 | Response deadline | Free | NEW | LOW | E-ABSENT | Add deadline/time-zone semantics. | Events | No | C-DB |
| FREE-AVL-007 | Response/change history | Free | NEW | LOW | E-ABSENT | Add immutable actor/time audit. | FREE-AVL-001 | No | C-DB |
| FREE-AVL-008 | Optional reason/comment privacy | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock audiences, sensitive-data and retention rules. | Privacy policy | Yes — visibility | C-DB |
| FREE-AVL-009 | Filter by availability | Free | NEW | LOW | E-ABSENT | Add scoped filters/indexes/UI. | FREE-AVL-001 | No | C-DB |
| FREE-AVL-010 | Availability visible in selection | Free | NEW | LOW | XI exists (E-MATCH); no availability. | Read-only signal in selection; no auto-choice. | FREE-AVL-001, selection workspace | No | C-DB |
| FREE-AVL-011 | Low-cost reminder path | Free | NEW | USAGE-SENSITIVE | No notification service (E-ABSENT). | Start in-app; meter external delivery. | Notifications, deadlines | No | C-MSG |

### 4.2 Events and calendar

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-EVT-001 | Organization calendar | Free | BUILT | LOW | E-EVENT. | Preserve tenant-scoped CRUD, cancellation history and bounded calendar queries. | Organization | No | C-DB |
| FREE-EVT-002 | Team calendar | Free | BUILT | LOW | E-EVENT `calendar(..., team_id=...)`; Team-scoped backend tests and shared Team-audience selector. | Preserve whole-organization visibility plus exact Team audience/fixture filtering. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-003 | Training sessions | Free | BUILT | LOW | E-EVENT `OrganizationEventCreate.event_type`; training CRUD tests. | Preserve training as a scheduled event, separate from drill generation. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-004 | Matches represented as events | Free | BUILT | LOW | E-EVENT `calendar` projects authoritative `Fixture` rows; fixture projection regression. | Preserve reference/projection only; never copy or mutate scoring truth. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-005 | Other events | Free | BUILT | LOW | E-EVENT supports the bounded `other` type. | Extend API validation for future types without a database enum/schema rewrite. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-006 | Date/time/location | Free | BUILT | LOW | E-EVENT requires timezone-aware inputs, stores timezone-aware timestamps and returns UTC; timezone tests. | Preserve explicit offsets and UTC response semantics. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-007 | Recurring sessions | Free | NEW | LOW | E-EVENT intentionally persists single occurrences only. | Deferred from 1A: specify a separate series/template plus materialized-occurrence/exception contract, idempotent generation window and series-edit semantics before adding recurrence; reject unsupported recurrence fields meanwhile. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-008 | Participant scope | Free | BUILT | LOW | E-EVENT uses DB-enforced organization-matching Team/roster references; tenant/no-login tests. | Preserve mutually exclusive organization, Teams and selected-roster-player scopes. | Membership, Team | No | C-DB |
| FREE-EVT-009 | RSVP | Free | NEW | LOW | E-ABSENT | Add event response distinct from attendance. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-010 | Upcoming-events dashboard | Free | BUILT | LOW | E-EVENT provides upcoming filtering, deterministic ordering and bounded limits; shared calendar UI. | Preserve start-time/ID ordering and bounded pagination. | FREE-EVT-001 | No | C-DB |
| FREE-EVT-011 | Cancellation/update notifications | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Persist changes; in-app first; bounded delivery. | Events, notifications | No | C-MSG |
| FREE-EVT-012 | School/Club terminology | Free | BUILT | LOW | E-EVENT reuses E-TERMS in one shared view/route factory. | Preserve presentation-only terminology over the shared backend domain. | Event UI | No | C-DB |

### 4.3 Attendance

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-ATT-001 | Training attendance | Free | NEW | LOW | E-ABSENT | Add event participant attendance. | Training events | No | C-DB |
| FREE-ATT-002 | Event attendance | Free | NEW | LOW | E-ABSENT | Generalize attendance across event types. | Events | No | C-DB |
| FREE-ATT-003 | Coach/admin marking | Free | NEW | LOW | Membership roles exist (E-ORG); no attendance mutation. | Define role matrix and audit. | FREE-ATT-001 | No | C-DB |
| FREE-ATT-004 | Present / Absent / Excused | Free | NEW | LOW | E-ABSENT | Add constrained states. | FREE-ATT-001 | No | C-DB |
| FREE-ATT-005 | Attendance history | Free | NEW | LOW | E-ABSENT | Retain event/member history and actor. | FREE-ATT-001 | No | C-DB |
| FREE-ATT-006 | Player attendance percentage | Free | NEW | LOW | E-ABSENT | Deterministic denominator/status rules. | Attendance history | No | C-DB |
| FREE-ATT-007 | Team participation metrics | Free | NEW | LOW | E-ABSENT | Add deterministic Team aggregates. | Attendance history | No | C-DB |
| FREE-ATT-008 | Season attendance summary | Free | NEW | LOW | E-ABSENT | Define season/calendar bounds and summary. | Events, attendance | No | C-DB |
| FREE-ATT-009 | Junior/minor privacy | Free | OWNER DECISION | UNKNOWN | No guardian/minor policy layer (E-ABSENT). | Lock visibility, correction, retention and exports. | Privacy/legal policy | Yes — minor handling | C-DB |

### 4.4 Selection and match preparation

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-SEL-001 | Squad selection from roster | Free | BUILT | LOW | E-TEAM/E-MATCH | Preserve saved-Team roster eligibility. | Team roster | No | C-DB |
| FREE-SEL-002 | Current playing XI | Free | BUILT | LOW | E-MATCH | Preserve match-local XI. | Match setup | No | C-DB |
| FREE-SEL-003 | Captain | Free | BUILT | LOW | E-MATCH | Preserve XI validation. | Playing XI | No | C-DB |
| FREE-SEL-004 | Wicketkeeper | Free | BUILT | LOW | E-MATCH | Preserve XI validation. | Playing XI | No | C-DB |
| FREE-SEL-005 | Availability integrated into selection | Free | NEW | LOW | E-MATCH has no availability input. | Add advisory signal only. | FREE-AVL-001 | No | C-DB |
| FREE-SEL-006 | Reserves/substitutes | Free | NEW | LOW | E-MATCH persists XI only. | Add pre-match reserve semantics. | Selection plan | No | C-DB |
| FREE-SEL-007 | Basic batting-order planning | Free | NEW | LOW | Scoring scorecards are live truth; no draft order. | Add separate planned order. | Selection plan | No | C-DB |
| FREE-SEL-008 | Basic bowling-role/order planning | Free | NEW | LOW | No pre-match bowling plan. | Add separate planned role/order. | Selection plan | No | C-DB |
| FREE-SEL-009 | Save draft | Free | NEW | LOW | Match creation is immediate (E-MATCH). | Add versioned draft persistence. | Selection plan | No | C-DB |
| FREE-SEL-010 | Publish Team | Free | NEW | LOW | E-ABSENT | Add explicit publication state/time/actor. | Draft | No | C-DB |
| FREE-SEL-011 | Notify selected players | Free | NEW | USAGE-SENSITIVE | E-ABSENT | In-app first; external channel bounded. | Published selection, notifications | No | C-MSG |
| FREE-SEL-012 | Notify reserves | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Same controlled delivery. | Reserves, notifications | No | C-MSG |
| FREE-SEL-013 | Selection history | Free | NEW | LOW | Game snapshots retain final XI, not draft/publication history. | Add immutable versions. | Selection plan | No | C-DB |
| FREE-SEL-014 | Planned order separate from live scoring truth | Free | ADAPT | LOW | E-MATCH snapshots and Game scorecards are distinct; scoring protected by master checklist Rule 5. | Enforce one-way handoff and no mutation of scoring truth. | Selection plan, scoring contract | No | C-DB |

### 4.5 Messaging and communication

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-MSG-001 | Organization announcements | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Add tenant-scoped announcement/feed. | Membership | No | C-MSG |
| FREE-MSG-002 | Team announcements | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Add Team audience. | Teams, FREE-MSG-001 | No | C-MSG |
| FREE-MSG-003 | Team/group messaging | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Add membership-derived rooms and delivery. | Safeguarding policy | No | C-MSG |
| FREE-MSG-004 | Staff-only groups | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Resolve contextual staff membership. | Messaging, roles | No | C-MSG |
| FREE-MSG-005 | Selected-squad group | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Build audience from published selection snapshot. | Selection publication | No | C-MSG |
| FREE-MSG-006 | Training/event participant group | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Build audience from event scope. | Events | No | C-MSG |
| FREE-MSG-007 | Direct messaging | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock who may contact whom, especially minors. | Safeguarding/legal | Yes — policy permits | C-MSG |
| FREE-MSG-008 | Parent/guardian-aware junior communication | Free | OWNER DECISION | UNKNOWN | No guardian relation (E-ABSENT). | Lock guardian identity, consent and visibility. | Guardian model/policy | Yes — authority | C-MSG |
| FREE-MSG-009 | Read status | Free | NEW | LOW | E-ABSENT | Add per-recipient receipt state. | Messaging | No | C-DB |
| FREE-MSG-010 | Notification preferences | Free | NEW | LOW | E-ABSENT | Add channel/event preference model. | Notifications | No | C-DB |
| FREE-MSG-011 | In-app notifications | Free | NEW | USAGE-SENSITIVE | E-ABSENT | Persist bounded notification inbox. | Event sources | No | C-MSG |
| FREE-MSG-012 | Push notifications | Free | NEW | HIGH | E-ABSENT | Provider integration, device tokens, metering. | Preferences, provider | No | C-MSG |
| FREE-MSG-013 | Report/moderation controls | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock moderation authority, appeal and evidence. | Safeguarding policy | Yes — policy | C-MSG |
| FREE-MSG-014 | Safeguarding/traceability | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock audit access, escalation and jurisdiction. | Legal/privacy review | Yes — policy | C-MSG |
| FREE-MSG-015 | Membership removal revokes access | Free | NEW | LOW | Membership disable exists (E-ORG), but no message ACL. | Revalidate access and terminate subscriptions. | Messaging, membership | No | C-DB |
| FREE-MSG-016 | Message retention policy | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock retention/deletion/legal-hold rules. Private contents are prohibited from performance-model inputs/training. | Privacy/legal | Yes — retention | C-MSG |

### 4.6 Player cricket identity

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-ID-001 | Canonical PlayerProfile | Free | BUILT | LOW | E-ROSTER/E-PLAYER | Preserve one canonical cricket record. | None | No | C-DB |
| FREE-ID-002 | Organization roster membership | Free | BUILT | LOW | E-ROSTER | Preserve organization-local metadata. | PlayerProfile | No | C-DB |
| FREE-ID-003 | Multi-Team membership | Free | BUILT | LOW | E-TEAM | Preserve one profile across Teams. | Organization roster | No | C-DB |
| FREE-ID-004 | Improved player-facing cricket profile | Free | ADAPT | LOW | E-PLAYER; `PlayerProfileView.vue`. | Add organization-context/privacy presentation. | Identity policy | No | C-DB |
| FREE-ID-005 | Career history | Free | BUILT | LOW | E-PLAYER career-summary endpoint/tests. | Keep basic cricket truth Free. | PlayerProfile | No | C-DB |
| FREE-ID-006 | Season history | Free | ADAPT | LOW | E-PLAYER year-stats exists, not organization-season history. | Add season/org filters without hiding truth. | Season semantics | No | C-DB |
| FREE-ID-007 | Team history | Free | NEW | LOW | Current Team membership is lifecycle state, not retained history. | Define retained membership/match history. | History policy | No | C-DB |
| FREE-ID-008 | Basic batting stats | Free | BUILT | LOW | E-STATS/E-PLAYER | Preserve. | Scoring truth | No | C-DB |
| FREE-ID-009 | Basic bowling stats | Free | BUILT | LOW | E-STATS/E-PLAYER | Preserve. | Scoring truth | No | C-DB |
| FREE-ID-010 | Fielding stats where truth supports | Free | OWNER DECISION | UNKNOWN | `SchoolStatisticsView.vue` states fielder identity is not retained reliably. | Define evidence threshold; do not invent fielding truth. | Scoring evidence audit | Yes — supported metrics | C-DB |
| FREE-ID-011 | Achievements | Free | BUILT | LOW | E-PLAYER `PlayerAchievement`; player profile tests. | Add org-safe display where needed. | PlayerProfile | No | C-DB |
| FREE-ID-012 | Public/private controls | Free | OWNER DECISION | UNKNOWN | Profile/favorite UI exists (E-PLAYER/E-FAN), no comprehensive publication policy. | Lock field-level visibility and actor authority. | Privacy policy | Yes — visibility | C-DB |
| FREE-ID-013 | Junior privacy defaults | Free | OWNER DECISION | UNKNOWN | No minor/guardian policy layer. | Define private-by-default fields and audiences. | Legal/privacy | Yes — defaults | C-DB |
| FREE-ID-014 | Organization-departure/history rules | Free | OWNER DECISION | UNKNOWN | Issue #559 hybrid-history question remains open. | Lock portable cricket truth vs organization-private records. | History policy | Yes — ownership/portability | C-DB |
| FREE-ID-015 | Future guardian relationship | Free | OWNER DECISION | UNKNOWN | E-ABSENT | Lock identity, consent, multiple guardians and revocation before schema. | Legal/privacy | Yes — relationship | C-DB |

### 4.7 Organization/community pages

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-PUB-001 | School/Club cricket homepage | Free | NEW | USAGE-SENSITIVE | School overview is authenticated; no organization public homepage. | Add controlled public page. | Publication/privacy | No | C-PUBLIC |
| FREE-PUB-002 | Basic organization logo/branding | Free | ADAPT | USAGE-SENSITIVE | E-BRAND exists but in-memory/legacy authorization. | Persist and membership-scope basic logo. | Organization auth | No | C-PUBLIC |
| FREE-PUB-003 | Teams | Free | BUILT | LOW | E-TEAM | Decide only public projection, not core Team storage. | Privacy | No | C-DB |
| FREE-PUB-004 | Fixtures | Free | BUILT | USAGE-SENSITIVE | E-STATS/E-COMP | Expose only explicitly public data. | Publication | No | C-PUBLIC |
| FREE-PUB-005 | Results | Free | BUILT | USAGE-SENSITIVE | E-STATS/E-COMP | Expose only explicitly public data. | Publication | No | C-PUBLIC |
| FREE-PUB-006 | Competitions | Free | BUILT | LOW | E-COMP | Public page projection may be adapted. | Publication | No | C-PUBLIC |
| FREE-PUB-007 | Public scorecards | Free | BUILT | USAGE-SENSITIVE | E-COMP | Preserve explicit publication. | Game publication | No | C-PUBLIC |
| FREE-PUB-008 | Standings | Free | BUILT | LOW | E-COMP | Add public projection if approved. | Competition | No | C-PUBLIC |
| FREE-PUB-009 | Basic leaderboards | Free | ADAPT | LOW | E-PLAYER batting leaderboard; `LeaderboardView.vue` and tests. | Organization/competition scope and privacy. | Stats, privacy | No | C-DB |
| FREE-PUB-010 | Public player profiles where permitted | Free | OWNER DECISION | UNKNOWN | E-PLAYER has profile UI; no organization publication contract. | Lock minor/field publication and consent. | Identity privacy | Yes — permission | C-PUBLIC |
| FREE-PUB-011 | Follows/favorites | Free | ADAPT | LOW | E-FAN supports player/team favorite records but is not organization-page integrated. | Add tenant/public subject validation. | Public subjects | No | C-DB |
| FREE-PUB-012 | Shareable match/Team links | Free | ADAPT | USAGE-SENSITIVE | Public scorecard route exists (E-COMP); no governed Team share route. | Stable public identifiers/revocation. | Publication | No | C-PUBLIC |
| FREE-PUB-013 | Privacy controls | Free | OWNER DECISION | UNKNOWN | Publication is match-specific (E-COMP), not page/profile-wide. | Lock audiences, defaults and reversibility. | Privacy policy | Yes — publication scope | C-PUBLIC |

### 4.8 Basic reporting

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| FREE-RPT-001 | Printable/basic scorecard | Free | ADAPT | USAGE-SENSITIVE | Scorecard views/data exist (E-COMP); PDF service is premium/video-oriented (E-EXPORT). | Add bounded basic print presentation. | Scorecard | No | C-EXPORT |
| FREE-RPT-002 | Basic season summary | Free | ADAPT | LOW | Year statistics exist (E-PLAYER), but no organization season report. | Add deterministic season scope/presentation. | Season semantics | No | C-DB |
| FREE-RPT-003 | Basic Team statistics | Free | BUILT | LOW | E-STATS | Preserve. | Scoring truth | No | C-DB |
| FREE-RPT-004 | Participation report | Free | NEW | LOW | E-ABSENT | Define participation denominator from events/matches. | Events/attendance | No | C-DB |
| FREE-RPT-005 | Attendance summary | Free | NEW | LOW | E-ABSENT | Build after attendance truth. | Attendance | No | C-DB |
| FREE-RPT-006 | Basic player cricket record | Free | BUILT | LOW | E-PLAYER/E-STATS | Preserve access to underlying cricket history. | PlayerProfile | No | C-DB |

## 5. Free monetization foundations

These rows describe future architecture only. They do not authorize prices, advertising, transactions, data sale, or entitlement changes.

### 5.1 Individual conversion

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| MON-IND-001 | Player individual upgrade path | Free monetization | ADAPT | LOW | E-BILL; `PricingPageView.vue`; Player Pro routes/tests. | Connect real purchase flow without org leakage. | Billing decision | No | C-DB |
| MON-IND-002 | Coach individual upgrade path | Free monetization | ADAPT | LOW | E-BILL/E-COACH; Coach Pro UI/tests. | Preserve personal workspace and real purchase flow. | Billing decision | No | C-DB |
| MON-IND-003 | Analyst individual upgrade path | Free monetization | ADAPT | LOW | E-BILL/E-ANALYTICS; Analyst workspace/tests. | Preserve personal workspace and real purchase flow. | Billing decision | No | C-DB |
| MON-IND-004 | Personal vs organization entitlement separation | Free monetization | BUILT | LOW | E-ORG/E-ENT separate `OrganizationEntitlement` from `User.role/subscription_plan`. | Preserve boundary in paid design. | None | No | C-DB |
| MON-IND-005 | Membership never permanently grants personal premium | Free monetization | BUILT | LOW | E-ORG/E-ENT; organization checks use active membership/capability. | Keep contextual grant only. | Membership | No | C-DB |
| MON-IND-006 | Personal premium persists independently | Free monetization | BUILT | LOW | User subscription fields and org entitlements are separate (E-ORG/E-BILL). | Add explicit regression when paid org seats exist. | Paid-seat design | No | C-DB |
| MON-IND-007 | Personal / School / Club context switching | Free monetization | NEW | LOW | School/Club routing exists (E-TERMS); no unified context switcher. | Add explicit active-context UX/security. | Entitlement separation | No | C-DB |

### 5.2 Sponsorship and advertising

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| MON-SPONSOR-001 | Sponsor slot on public scorecards | Free monetization | ADAPT | USAGE-SENSITIVE | E-SPONSOR game sponsors/impressions and `SponsorsBar.vue`; E-COMP public scorecard. | Organization authorization, placement and privacy. | Public scorecard | No | C-PUBLIC |
| MON-SPONSOR-002 | Sponsor slot on fixtures/results pages | Free monetization | ADAPT | USAGE-SENSITIVE | E-SPONSOR plus fixtures/results UI (E-STATS). | Add governed placement and reporting. | Public pages | No | C-PUBLIC |
| MON-SPONSOR-003 | Sponsor slot on competition pages | Free monetization | ADAPT | USAGE-SENSITIVE | E-SPONSOR plus competition UI (E-COMP). | Add governed placement. | Public competition | No | C-PUBLIC |
| MON-SPONSOR-004 | Sponsor slot on organization homepage | Free monetization | NEW | USAGE-SENSITIVE | Public homepage absent; sponsor tech exists (E-SPONSOR). | Build homepage first. | FREE-PUB-001 | No | C-PUBLIC |
| MON-SPONSOR-005 | Advertising/sponsorship policy | Free monetization | OWNER DECISION | UNKNOWN | Runtime has sponsor objects but no organization policy contract. | Lock prohibited categories, minors, approval and takedown. | Legal/product | Yes — policy | C-PUBLIC |
| MON-SPONSOR-006 | No advertising in private junior messaging | Free monetization | OWNER DECISION | UNKNOWN | Messaging absent (E-ABSENT). | Codify prohibition before messaging/ads. | Safeguarding policy | Yes — prohibition | C-MSG |
| MON-SPONSOR-007 | No behavioral targeting from children's private data | Free monetization | OWNER DECISION | UNKNOWN | No targeting implementation found. | Codify prohibition and audit data flow. | Privacy/legal | Yes — prohibition | C-DATA |
| MON-SPONSOR-008 | Performance ad-removal option | Free monetization | ADAPT | LOW | Canonical pricing has branding-removal flags (E-BILL), not org Performance enforcement. | Organization capability and placement enforcement. | Performance entitlement | No | C-DB |
| MON-SPONSOR-009 | Organization-managed sponsor placement | Free monetization | ADAPT | USAGE-SENSITIVE | E-SPONSOR rotation schedules/metrics accept organization IDs but lack current membership tenancy. | Adapt authorization/persistence/public surfaces. | Sponsor policy, org auth | No | C-PUBLIC |
| MON-SPONSOR-010 | Sponsor reporting | Free monetization | ADAPT | USAGE-SENSITIVE | E-SPONSOR impressions/exposure metrics. | Organization-safe verified metrics/export. | Sponsor placement | No | C-DATA |
| MON-SPONSOR-011 | Revenue share | Free monetization | DEFER | UNKNOWN | No revenue-share ledger or contract. | Revisit only after policy/economics/payments. | Payments, legal | Yes — economics | C-PAY |

### 5.3 Payments and transactions

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| MON-PAY-001 | Membership fees | Free monetization | NEW | USAGE-SENSITIVE | E-BILL is mocked subscription lookup, not transaction processing. | Build organization ledger/provider flow. | Payment policy | No | C-PAY |
| MON-PAY-002 | Match fees | Free monetization | NEW | USAGE-SENSITIVE | E-BILL | Add fee objects, payers and allocation. | Payment foundation | No | C-PAY |
| MON-PAY-003 | Tournament registration | Free monetization | NEW | USAGE-SENSITIVE | Competitions exist (E-COMP); no payments. | Link registration transaction without altering entrants truth. | Payment foundation | No | C-PAY |
| MON-PAY-004 | Camps/coaching-event payments | Free monetization | NEW | USAGE-SENSITIVE | Events/payment processing absent. | Add after events and payment foundation. | Events, payments | No | C-PAY |
| MON-PAY-005 | Fundraising | Free monetization | NEW | USAGE-SENSITIVE | E-ABSENT | Define campaign/ledger/provider model. | Payments | No | C-PAY |
| MON-PAY-006 | Donations | Free monetization | NEW | USAGE-SENSITIVE | E-ABSENT | Define donor, receipt and privacy flow. | Payments | No | C-PAY |
| MON-PAY-007 | Provider integration | Free monetization | NEW | HIGH | Billing says mocked pending Stripe (E-BILL). | Select provider; implement webhooks/idempotency/security. | Owner selection | Yes — provider | C-PAY |
| MON-PAY-008 | Platform/transaction fee economics | Free monetization | OWNER DECISION | UNKNOWN | No organization transaction economics. | Lock fees, taxes, chargebacks and jurisdictions. | Finance/legal | Yes — economics | C-PAY |
| MON-PAY-009 | Refunds | Free monetization | NEW | USAGE-SENSITIVE | E-BILL | Add provider-backed refund state/audit. | Provider, ledger | No | C-PAY |
| MON-PAY-010 | Reconciliation and financial controls | Free monetization | OWNER DECISION | UNKNOWN | E-BILL | Lock roles, approvals, reports, retention and audit. | Finance/legal/provider | Yes — controls | C-PAY |

### 5.4 Aggregated intelligence and data products

Data categories must remain distinct: organization/player operational data; private personal data; derived analytics; anonymized/aggregated data; public cricket data; and AI-generated artifacts. Private messages are excluded from performance-model and monetization inputs. This checklist does not authorize external data sale or API access.

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| MON-DATA-001 | Data-governance policy | Free monetization | OWNER DECISION | UNKNOWN | No product-wide ownership/portability contract; Issue #559 leaves decisions open. | Lock categories, purposes, owners, access, deletion and portability. | Legal/privacy | Yes — policy | C-DATA |
| MON-DATA-002 | Aggregation/anonymization thresholds | Free monetization | OWNER DECISION | UNKNOWN | No cohort-threshold service. | Define k-threshold/suppression/re-identification tests. | MON-DATA-001 | Yes — thresholds | C-DATA |
| MON-DATA-003 | Prohibit sale of identifiable children's information | Free monetization | OWNER DECISION | UNKNOWN | No sale path found. | Codify absolute product/legal prohibition and audit. | Legal/privacy | Yes — prohibition | C-DATA |
| MON-DATA-004 | Prohibit monetizing private message content | Free monetization | OWNER DECISION | UNKNOWN | Messaging absent (E-ABSENT). | Codify exclusion from analytics, AI and data products. | Messaging/data policy | Yes — prohibition | C-DATA |
| MON-DATA-005 | Competition/league aggregate reports | Free monetization | ADAPT | USAGE-SENSITIVE | E-COMP standings plus E-ANALYTICS aggregation technology. | Cohort privacy, organization/league authority and provenance. | Data policy | No | C-DATA |
| MON-DATA-006 | Participation trends | Free monetization | NEW | USAGE-SENSITIVE | Participation/attendance truth absent. | Build only from governed operational data. | Events/attendance | No | C-DATA |
| MON-DATA-007 | Cricket-development trends | Free monetization | ADAPT | USAGE-SENSITIVE | E-DEV has development evidence, but is private/legacy-owned. | Aggregate only after private-data and cohort policy. | Data policy, org adaptation | No | C-DATA |
| MON-DATA-008 | Research/board data products | Free monetization | DEFER | UNKNOWN | No approved product/API. | Revisit after legal approval and proven anonymization. | Governance/thresholds | Yes — purpose/market | C-DATA |
| MON-DATA-009 | Consent/legal review | Free monetization | OWNER DECISION | UNKNOWN | No consent framework for this use. | Obtain jurisdiction-specific approval; do not infer consent. | Legal/privacy | Yes — lawful basis | C-DATA |
| MON-DATA-010 | Provenance/sample-size requirements | Free monetization | OWNER DECISION | UNKNOWN | Analytics evidence exists but no product-wide disclosure standard. | Lock source/version/window/cohort display and suppression. | MON-DATA-001/002 | Yes — standard | C-DATA |

## 6. Performance — manage, coach, improve and understand

Performance is one shared School/Club bundle architecture. Access must resolve active `OrganizationMembership`, organization capability, contextual seat (when approved), and exact resource tenant. It must never permanently upgrade personal accounts. No final price is set here.

### 6.1 Advanced deterministic analytics

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-AN-001 | Advanced batting analytics | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS player/phase/heatmap services/tests. | Organization filters, seat and privacy. | Performance authority | No | C-DATA |
| PERF-AN-002 | Advanced bowling analytics | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS phase/pressure/dismissal services/tests. | Organization filters and evidence labels. | Performance authority | No | C-DATA |
| PERF-AN-003 | Fielding analytics | Performance | OWNER DECISION | UNKNOWN | Current School UI states fielder identity is incomplete; V2 video fielding is separate. | Approve only evidence-backed metrics. | Scoring evidence audit | Yes — truth boundary | C-DATA |
| PERF-AN-004 | Current form | Performance | ADAPT | LOW | E-PLAYER form-analysis/PlayerForm tests. | Organization-season scope. | Org query scope | No | C-DB |
| PERF-AN-005 | Career trends | Performance | ADAPT | LOW | E-PLAYER career/year/form endpoints. | Separate global cricket truth from private org views. | History policy | No | C-DATA |
| PERF-AN-006 | Season trends | Performance | ADAPT | LOW | E-PLAYER year stats; E-STATS. | Define org season semantics. | Season model | No | C-DATA |
| PERF-AN-007 | Phase analysis | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS phase routes/services/tests. | Tenant-scope queries. | Org query scope | No | C-DATA |
| PERF-AN-008 | Pressure analysis | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS pressure models/routes/tests. | Tenant scope and provenance. | Org query scope | No | C-DATA |
| PERF-AN-009 | Dismissal analysis | Performance | ADAPT | LOW | E-PLAYER dismissal endpoint/recommendations. | Tenant/season filters; deterministic evidence. | Org query scope | No | C-DATA |
| PERF-AN-010 | Heatmaps | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS heatmap routes/components/tests. | Tenant scope and query limits. | Org query scope | No | C-DATA |
| PERF-AN-011 | Clustering | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS clustering routes/services/tests. | Tenant scope, explain clusters, bounded compute. | Org query scope | No | C-DATA |
| PERF-AN-012 | Player comparison | Performance | ADAPT | USAGE-SENSITIVE | `player_analytics.py::get_player_comparison`; `MultiPlayerComparisonView.vue`; tests. | Organization-safe eligible-player scope. | Org query scope | No | C-DATA |
| PERF-AN-013 | Team comparison | Performance | NEW | USAGE-SENSITIVE | Basic Team stats exist (E-STATS), no comparison product. | Deterministic comparable Team metrics. | Team stats | No | C-DATA |
| PERF-AN-014 | Opposition analysis | Performance | NEW | USAGE-SENSITIVE | No organization opposition workspace. | Define lawful data scope and filters. | Analytics foundation | No | C-DATA |
| PERF-AN-015 | Venue analysis | Performance | ADAPT | USAGE-SENSITIVE | Historical venue intelligence models/services exist, but belong to historical-import/Analyst track. | Read-only adapter; protect historical import. | Org scope, provenance | No | C-DATA |
| PERF-AN-016 | Matchup analysis | Performance | NEW | USAGE-SENSITIVE | No organization matchup product. | Define batter/bowler evidence and sample rules. | Analytics foundation | No | C-DATA |
| PERF-AN-017 | Organization/Team/season filters and safe Analyst workspace | Performance | ADAPT | USAGE-SENSITIVE | `analyst_pro.py::run_analytics_query`; `analyst_access.py` uses `User.org_id`/created-by; Analyst tests/UI. | Replace legacy scope with membership/resource predicates; add seat/read-only limits. | Performance authority | No | C-DATA |

### 6.2 Performance dashboards

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-DASH-001 | Coach dashboard | Performance | ADAPT | LOW | E-COACH; `CoachesDashboardView.vue`; coach tests. | Membership/seat and organization ownership. | Performance authority | No | C-DB |
| PERF-DASH-002 | Team dashboard | Performance | ADAPT | LOW | E-DEV `get_team_development_overview`; Team overview component/tests. | Current organization and audience. | Coaching adaptation | No | C-DATA |
| PERF-DASH-003 | Season dashboard | Performance | NEW | USAGE-SENSITIVE | No organization season dashboard. | Define season/filter aggregates. | Season semantics | No | C-DATA |
| PERF-DASH-004 | Player-development dashboard | Performance | ADAPT | LOW | E-DEV dashboard routes/services/components/tests. | Membership/seat/privacy adaptation. | Coaching adaptation | No | C-DATA |
| PERF-DASH-005 | Organization cricket dashboard | Performance | ADAPT | USAGE-SENSITIVE | Legacy `OrgManagementView.vue` and Analyst aggregates exist; not current membership-native. | Compose tenant-safe operational/performance metrics. | Org query scope | No | C-DATA |
| PERF-DASH-006 | Participation trends | Performance | NEW | USAGE-SENSITIVE | No participation truth. | Build after event/attendance foundation. | Free events/attendance | No | C-DATA |
| PERF-DASH-007 | Attendance trends | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Build deterministic trends. | Attendance | No | C-DATA |
| PERF-DASH-008 | Availability trends | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Build deterministic trends. | Availability | No | C-DATA |
| PERF-DASH-009 | Selection/playing-opportunity trends | Performance | NEW | USAGE-SENSITIVE | Final XI snapshots exist; selection history does not. | Define opportunity metrics and fairness caveats. | Selection history | No | C-DATA |
| PERF-DASH-010 | Performance trends | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS/E-DEV longitudinal services. | Organization/season scope. | Analytics adaptation | No | C-DATA |
| PERF-DASH-011 | Multi-Team overview | Performance | NEW | USAGE-SENSITIVE | Team list/basic stats exist, no combined performance view. | Aggregate safely across organization Teams. | Team dashboards | No | C-DATA |
| PERF-DASH-012 | School age-group overview | Performance | NEW | LOW | `year_group` exists on roster, no dashboard. | Privacy-safe grouping and terminology. | School policy | No | C-DATA |
| PERF-DASH-013 | Club squad overview | Performance | NEW | LOW | Shared Teams exist, no squad overview. | Shared dashboard with Club terminology. | Team dashboard | No | C-DATA |

### 6.3 Coaching

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-COACH-001 | Organization-scoped coach assignments | Performance | ADAPT | LOW | E-COACH assignments are coach/global-role owned. | Add organization/membership lifecycle. | Performance authority | No | C-DB |
| PERF-COACH-002 | Coaching sessions | Performance | ADAPT | LOW | E-COACH session CRUD/tests. | Organization ownership and reconciled entitlement. | Coach assignment | No | C-DB |
| PERF-COACH-003 | Coaching notes | Performance | ADAPT | LOW | E-COACH note CRUD/tests. | Tenant scope and audience fields. | Coach assignment | No | C-DB |
| PERF-COACH-004 | Coach-private notes | Performance | OWNER DECISION | UNKNOWN | `CoachNote` has creator access patterns but no locked org-private policy. | Lock administrator/player/guardian access. | Privacy/legal | Yes — visibility | C-DB |
| PERF-COACH-005 | Organization-visible notes | Performance | OWNER DECISION | UNKNOWN | E-COACH lacks governed shared audience semantics. | Lock audiences and immutable author. | Privacy/legal | Yes — visibility | C-DB |
| PERF-COACH-006 | Note visibility policy | Performance | OWNER DECISION | UNKNOWN | Issue #559 leaves it open. | Define states, transitions, exports and audit. | PERF-COACH-004/005 | Yes — policy | C-DB |
| PERF-COACH-007 | Development observations | Performance | ADAPT | LOW | E-DEV observations/evidence/plans. | Organization ownership and visibility. | Coaching adaptation | No | C-DB |
| PERF-COACH-008 | Session history | Performance | ADAPT | LOW | E-COACH/E-VIDEO session history endpoints/tests. | Separate non-video/video and organization scope. | Coaching adaptation | No | C-DB |
| PERF-COACH-009 | Coach/player relationship lifecycle | Performance | OWNER DECISION | UNKNOWN | Assignment activation exists; departure/history semantics open. | Lock end, transfer, access and retention. | History policy | Yes — lifecycle | C-DB |
| PERF-COACH-010 | Contextual staff-seat authorization | Performance | OWNER DECISION | UNKNOWN | No paid seat entity; current checks use global roles. | Lock seat types/counts/assignment before schema. | Product/economics | Yes — seat model | C-DB |
| PERF-COACH-011 | Membership removal behavior | Performance | OWNER DECISION | UNKNOWN | Membership disable exists; premium artifact behavior undefined. | Lock read/write/download/history effects. | Seat/history policy | Yes — retention/access | C-DB |
| PERF-COACH-012 | Multi-organization privacy | Performance | OWNER DECISION | UNKNOWN | Canonical PlayerProfile is shared; coaching data ownership is not. | Lock organization-private boundary and portability. | Data ownership | Yes — boundary | C-DB |

### 6.4 Player development

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-DEV-001 | Development goals | Performance | ADAPT | LOW | E-DEV goals/services/tests. | Organization ownership/seat/audience. | Coaching adaptation | No | C-DB |
| PERF-DEV-002 | Development plans | Performance | ADAPT | LOW | E-DEV draft/review/list/report routes/tests. | Organization scope and approval policy. | Coaching adaptation | No | C-DB |
| PERF-DEV-003 | Progress tracking | Performance | ADAPT | LOW | E-DEV checkpoints/longitudinal tests. | Tenant and season scope. | Development plan | No | C-DATA |
| PERF-DEV-004 | Milestones | Performance | ADAPT | LOW | E-DEV goals/checkpoints/interventions. | Define organization-safe milestone semantics. | Development plan | No | C-DB |
| PERF-DEV-005 | Coach observations | Performance | ADAPT | LOW | E-COACH/E-DEV. | Visibility and organization ownership. | Note policy | No | C-DB |
| PERF-DEV-006 | Player progress history | Performance | ADAPT | USAGE-SENSITIVE | E-DEV longitudinal service/components/tests. | Hybrid history and tenant-safe filters. | History decision | No | C-DATA |
| PERF-DEV-007 | Season development summary | Performance | ADAPT | USAGE-SENSITIVE | E-DEV report services; no current org-season package. | Add organization/season scope. | Season semantics | No | C-DATA |
| PERF-DEV-008 | Player comparisons | Performance | ADAPT | USAGE-SENSITIVE | E-ANALYTICS comparison plus E-DEV evidence. | Eligible cohort/privacy and provenance. | Analytics adaptation | No | C-DATA |
| PERF-DEV-009 | Evidence linked to matches/statistics | Performance | ADAPT | LOW | E-DEV report evidence refs and approval tests. | Organization resource validation. | Analytics scope | No | C-DB |
| PERF-DEV-010 | Player/guardian access policy | Performance | OWNER DECISION | UNKNOWN | No guardian relation; player approval exists only in development flow. | Lock read/comment/approve/download rights. | Legal/privacy | Yes — access | C-DB |
| PERF-DEV-011 | Organization-owned private development data | Performance | OWNER DECISION | UNKNOWN | Current records are coach/user/legacy-org owned. | Lock ownership, administrator access and retention. | Data policy | Yes — ownership | C-DB |
| PERF-DEV-012 | Career-vs-private-history boundary | Performance | OWNER DECISION | UNKNOWN | E-PLAYER and E-DEV coexist; portability unresolved. | Approve hybrid snapshot/transfer contract. | Issue #559 decision | Yes — portability | C-DB |

### 6.5 Advanced selection intelligence

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-SEL-001 | Advanced squad planning | Performance | NEW | LOW | E-MATCH is final match setup, not planning. | Add versioned workspace above Free selection. | Free selection history | No | C-DB |
| PERF-SEL-002 | Form in selection workspace | Performance | ADAPT | LOW | Form exists (E-PLAYER); no selection integration. | Tenant-safe advisory display. | PERF-SEL-001 | No | C-DATA |
| PERF-SEL-003 | Availability + attendance + performance view | Performance | NEW | USAGE-SENSITIVE | Availability/attendance absent. | Compose governed signals. | Free availability/attendance, analytics | No | C-DATA |
| PERF-SEL-004 | Role/balance view | Performance | NEW | LOW | No planning role model. | Define deterministic role taxonomy. | PERF-SEL-001 | No | C-DB |
| PERF-SEL-005 | Batting depth | Performance | NEW | LOW | Stats exist; no selection metric. | Define transparent deterministic calculation. | Analytics | No | C-DATA |
| PERF-SEL-006 | Bowling options | Performance | NEW | LOW | Stats exist; no selection metric. | Define transparent deterministic calculation. | Analytics | No | C-DATA |
| PERF-SEL-007 | Recent workload | Performance | NEW | USAGE-SENSITIVE | No workload model. | Define event/match workload evidence. | Events/history | No | C-DATA |
| PERF-SEL-008 | Opposition performance | Performance | NEW | USAGE-SENSITIVE | No org opposition workspace. | Add lawful deterministic opponent scope. | PERF-AN-014 | No | C-DATA |
| PERF-SEL-009 | Venue/context evidence | Performance | ADAPT | USAGE-SENSITIVE | Historical venue and match context technology exists (E-ANALYTICS). | Organization-safe read adapter/provenance. | PERF-AN-015 | No | C-DATA |
| PERF-SEL-010 | Previous XI comparison | Performance | ADAPT | LOW | E-MATCH stores XI snapshots; no comparison UI. | Query prior organization games. | Match history | No | C-DATA |
| PERF-SEL-011 | Selection history | Performance | NEW | LOW | Free draft/publication history absent. | Reuse immutable Free history. | FREE-SEL-013 | No | C-DB |
| PERF-SEL-012 | Selection rationale/coach notes | Performance | OWNER DECISION | UNKNOWN | Coach notes exist (E-COACH), not selection/audience policy. | Lock confidentiality, subject access and retention. | Note policy | Yes — visibility | C-DB |
| PERF-SEL-013 | Deterministic evidence first | Performance | ADAPT | LOW | Master checklist Rule 5; E-ANALYTICS/E-DEV evidence contracts. | Enforce provenance before any explanation. | Analytics | No | C-DB |
| PERF-SEL-014 | No automatic override of coach decisions | Performance | OWNER DECISION | UNKNOWN | No automated selector exists. | Codify human-decision boundary and audit. | Product/safety | Yes — guardrail | C-DB |

### 6.6 Advanced reports and exports

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-RPT-001 | PDF performance reports | Performance | ADAPT | USAGE-SENSITIVE | E-EXPORT/E-VIDEO-RESULT. | Organization ownership, audience, bounded jobs. | Analytics/coach adaptation | No | C-EXPORT |
| PERF-RPT-002 | CSV export | Performance | ADAPT | USAGE-SENSITIVE | E-EXPORT analyst CSV routes/tests. | Membership/seat scope and field policy. | Performance authority | No | C-EXPORT |
| PERF-RPT-003 | JSON where appropriate | Performance | ADAPT | USAGE-SENSITIVE | `analyst_pro.py::_format_export/get_analyst_export_data`. | Tenant scope and versioned schema. | Performance authority | No | C-EXPORT |
| PERF-RPT-004 | Player development report | Performance | ADAPT | USAGE-SENSITIVE | E-DEV player/plan report routes/tests. | Organization ownership/audience. | Development adaptation | No | C-EXPORT |
| PERF-RPT-005 | Team report | Performance | ADAPT | USAGE-SENSITIVE | E-DEV Team summary report. | Current organization and season scope. | Development adaptation | No | C-EXPORT |
| PERF-RPT-006 | Season report | Performance | NEW | USAGE-SENSITIVE | No organization season report. | Define deterministic package. | Season dashboard | No | C-EXPORT |
| PERF-RPT-007 | Coach report | Performance | ADAPT | USAGE-SENSITIVE | E-VIDEO-RESULT coach report service/V2/tests. | Non-video/org packaging, review and audience. | Coaching adaptation | No | C-EXPORT |
| PERF-RPT-008 | Organization report | Performance | ADAPT | USAGE-SENSITIVE | Legacy organization PDF patterns and Analyst exports exist, not current tenancy. | Compose tenant-safe report. | Dashboards | No | C-EXPORT |
| PERF-RPT-009 | Participation report | Performance | NEW | USAGE-SENSITIVE | Participation truth absent. | Build after Free events/attendance. | FREE-RPT-004 | No | C-EXPORT |
| PERF-RPT-010 | Export audit | Performance | NEW | LOW | No organization export-job/audit record. | Log requester/scope/fields/artifact/download. | Export foundation | No | C-DB |
| PERF-RPT-011 | Junior-data restrictions | Performance | OWNER DECISION | UNKNOWN | No approved export field policy. | Lock redaction, consent and permitted audiences. | Legal/privacy | Yes — fields | C-EXPORT |
| PERF-RPT-012 | Tenant-safe generation/download | Performance | ADAPT | USAGE-SENSITIVE | E-EXPORT/E-VIDEO presigned patterns; current access is legacy. | Recheck membership/seat on job and download. | Performance authority | No | C-EXPORT |
| PERF-RPT-013 | Size/rate limits | Performance | NEW | USAGE-SENSITIVE | No organization export quota/admission ledger. | Add row/file/concurrency/rate limits. | Export job design | No | C-EXPORT |

### 6.7 Cricksy Benchmarks

Current leaderboards/comparisons are not privacy-preserving benchmark products.

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-BENCH-001 | Age-group benchmarks | Performance | NEW | USAGE-SENSITIVE | E-PLAYER leaderboards lack cohort governance. | Build governed cohorts. | Data policy | No | C-DATA |
| PERF-BENCH-002 | Role benchmarks | Performance | NEW | USAGE-SENSITIVE | No benchmark service. | Define role taxonomy/cohorts. | Data policy | No | C-DATA |
| PERF-BENCH-003 | Competition-level benchmarks | Performance | NEW | USAGE-SENSITIVE | Standings exist (E-COMP), not player benchmarks. | Govern comparable cohorts. | Data policy | No | C-DATA |
| PERF-BENCH-004 | Regional benchmarks | Performance | OWNER DECISION | UNKNOWN | No reliable region/cohort consent contract. | Approve geography/sample rules. | Legal/product | Yes — regions | C-DATA |
| PERF-BENCH-005 | Progression benchmarks | Performance | NEW | USAGE-SENSITIVE | Longitudinal tooling exists (E-DEV), not pooled benchmarks. | Build privacy-safe cohort deltas. | Data policy | No | C-DATA |
| PERF-BENCH-006 | Team benchmarks | Performance | NEW | USAGE-SENSITIVE | E-STATS lacks cross-org comparison product. | Build governed aggregates. | Data policy | No | C-DATA |
| PERF-BENCH-007 | Percentiles/ranges | Performance | NEW | USAGE-SENSITIVE | No benchmark computation/versioning. | Implement deterministic distribution contract. | Cohort datasets | No | C-DATA |
| PERF-BENCH-008 | Minimum cohort sizes | Performance | OWNER DECISION | UNKNOWN | No threshold standard. | Lock suppression threshold. | Privacy/statistics | Yes — threshold | C-DATA |
| PERF-BENCH-009 | Privacy-preserving aggregation | Performance | OWNER DECISION | UNKNOWN | No anonymization service. | Lock method and re-identification tests. | Legal/privacy | Yes — method | C-DATA |
| PERF-BENCH-010 | No identification of comparison organizations/children | Performance | OWNER DECISION | UNKNOWN | No benchmark product. | Codify suppression and disclosure prohibition. | Legal/privacy | Yes — prohibition | C-DATA |
| PERF-BENCH-011 | Provenance/sample-size display | Performance | NEW | LOW | Evidence labels exist in Analyst work, not benchmark UI. | Display cohort/window/version/sample/suppression. | Benchmark engine | No | C-DB |

### 6.8 Controlled AI

Required flow: **cricket data → deterministic Cricksy analysis → bounded AI explanation**.

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-AI-001 | Organization AI quota | Performance | ADAPT | HIGH | E-AI has usage logging/org summary but no current organization admission ledger. | Add concurrency-safe organization quota. | Performance entitlement/seat | No | C-AI |
| PERF-AI-002 | Usage accounting | Performance | ADAPT | HIGH | `AiUsageLog`, `log_ai_usage`, usage routes (E-AI). | Record actual provider/model/tokens/cost/org. | PERF-AI-001 | No | C-AI |
| PERF-AI-003 | Performance reports | Performance | ADAPT | HIGH | E-AI/E-DEV/E-VIDEO-RESULT report pipelines. | Organization evidence package and bounded generation. | Deterministic analytics | No | C-AI |
| PERF-AI-004 | Match summaries | Performance | ADAPT | HIGH | `analyst_pro.py::get_match_ai_summary`; `match_ai_service.py`; tests. | Organization access/quota/review. | PERF-AI-001 | No | C-AI |
| PERF-AI-005 | Player development summaries | Performance | ADAPT | HIGH | E-AI/E-DEV player insight/recommendation review. | Org privacy/quota/audience. | Development adaptation | No | C-AI |
| PERF-AI-006 | Team analysis | Performance | ADAPT | HIGH | Analyst context/Team development summaries exist. | Bounded organization evidence package. | Analytics adaptation | No | C-AI |
| PERF-AI-007 | Selection-support explanation | Performance | NEW | HIGH | No selection intelligence or explanation route. | Build only above approved deterministic evidence. | Selection intelligence | No | C-AI |
| PERF-AI-008 | Evidence/provenance | Performance | ADAPT | LOW | AI review/evidence contracts and Phase 8 tests (E-AI). | Enforce source/version/citations for org artifacts. | Deterministic metrics | No | C-DB |
| PERF-AI-009 | Human review | Performance | ADAPT | LOW | `AiInsightReview` and review routes/tests (E-AI). | Organization reviewer role/audit. | Performance authority | No | C-DB |
| PERF-AI-010 | Minor-data policy | Performance | OWNER DECISION | UNKNOWN | No approved organization AI minor policy. | Lock allowed inputs/providers/audiences/retention. | Legal/privacy | Yes — policy | C-AI |
| PERF-AI-011 | Provider-data policy | Performance | OWNER DECISION | UNKNOWN | Provider governance not locked. | Approve providers, training exclusion, region and retention. | Security/legal | Yes — provider | C-AI |
| PERF-AI-012 | Idempotency/retry | Performance | ADAPT | HIGH | Video jobs/recovery and review flows provide patterns, not org AI admission. | Add request key/reservation/retry charging. | Quota ledger | No | C-AI |
| PERF-AI-013 | Cost monitoring | Performance | ADAPT | HIGH | AiUsageLog records approximate usage; no reliable cost ledger. | Capture actual provider cost and alerts. | Usage accounting | No | C-AI |
| PERF-AI-014 | Quota/overage policy | Performance | OWNER DECISION | UNKNOWN | Canonical personal limits exist; no org policy. | Lock hard stop/overage/failure charging/renewal. | Economics | Yes — policy | C-AI |

### 6.9 Performance communication automation

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-COMM-001 | Scheduled announcements | Performance | NEW | USAGE-SENSITIVE | Messaging absent (E-ABSENT). | Scheduler, cancellation and delivery audit. | Free messaging | No | C-MSG |
| PERF-COMM-002 | Templates | Performance | NEW | LOW | E-ABSENT | Add organization-owned templates with safe variables. | Free messaging | No | C-DB |
| PERF-COMM-003 | Automatic availability reminders | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Event/deadline-driven bounded delivery. | Availability, notifications | No | C-MSG |
| PERF-COMM-004 | Training reminders | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Event-driven bounded delivery. | Events, notifications | No | C-MSG |
| PERF-COMM-005 | Selection notifications | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Publish-triggered delivery. | Selection publication | No | C-MSG |
| PERF-COMM-006 | Missing-response reminders | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Target non-responders without exposing others. | Availability | No | C-MSG |
| PERF-COMM-007 | Attendance follow-up | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Policy-bound follow-up; no performance inference from messages. | Attendance | No | C-MSG |
| PERF-COMM-008 | Structured target groups | Performance | NEW | LOW | E-ABSENT | Resolve audiences from membership/event/selection snapshots. | Free messaging | No | C-DB |
| PERF-COMM-009 | Communication audit/dashboard | Performance | NEW | USAGE-SENSITIVE | E-ABSENT | Delivery metadata only; never analyze private message contents for performance. | Messaging policy | No | C-DATA |

### 6.10 Performance commercial tools

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| PERF-COM-001 | Organization-managed sponsors | Performance | ADAPT | USAGE-SENSITIVE | E-SPONSOR. | Current membership authorization/persistence. | Sponsor policy | No | C-PUBLIC |
| PERF-COM-002 | Sponsor placement | Performance | ADAPT | USAGE-SENSITIVE | E-SPONSOR rotation engine/routes. | Organization-scoped placement surfaces. | PERF-COM-001 | No | C-PUBLIC |
| PERF-COM-003 | Sponsor reporting | Performance | ADAPT | USAGE-SENSITIVE | E-SPONSOR impressions/exposure metrics. | Verified tenant-safe report. | Sponsor placement | No | C-DATA |
| PERF-COM-004 | Remove standard Cricksy advertising | Performance | ADAPT | LOW | Canonical venue `remove_branding` flag exists (E-BILL), not org enforcement. | Define organization capability and public-page behavior. | Product entitlement | No | C-DB |
| PERF-COM-005 | Enhanced branding | Performance | ADAPT | USAGE-SENSITIVE | E-BRAND is real UI/service but in-memory/legacy-auth. | Persist, membership-scope and validate assets. | Performance authority | No | C-PUBLIC |
| PERF-COM-006 | Enhanced public pages | Performance | NEW | USAGE-SENSITIVE | Current public surface is scorecard-only (E-COMP). | Build after Free homepage/privacy. | FREE-PUB-001/013 | No | C-PUBLIC |
| PERF-COM-007 | Embeddable fixtures/results/scorecards | Performance | ADAPT | USAGE-SENSITIVE | Public scorecard and existing embed/viewer patterns exist. | Tenant publication, origin/rate controls. | Public pages | No | C-PUBLIC |
| PERF-COM-008 | Custom domain candidate | Performance | DEFER | UNKNOWN | No domain verification/routing. | Revisit after mature public pages. | Hosting/security | Yes — support/economics | C-PUBLIC |
| PERF-COM-009 | Payment administration/reconciliation | Performance | NEW | USAGE-SENSITIVE | E-BILL is not transaction processing. | Build only after organization payments. | MON-PAY foundation | No | C-PAY |

## 7. Private Cricksy Video Analysis Service

This is a manually controlled service track, not public Elite. Existing Coach Pro Plus technology is substantial, but its user/global-role and legacy `User.org_id` access model is not current OrganizationMembership tenancy.

### 7.1 Existing technology audit

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| VIDEO-TECH-001 | Ingestion/upload | Private video | ADAPT | HIGH | E-VIDEO `initiate_video_upload/complete_video_upload`; upload tests. | Controlled operator/customer intake and org-safe ownership. | Private gate | No | C-VIDEO |
| VIDEO-TECH-002 | Format validation | Private video | ADAPT | HIGH | `coach_pro_plus.py::analyze_video` validates suffix; presigned upload trusts later S3 checks. | Validate MIME/container/codec before admission. | Upload | No | C-VIDEO |
| VIDEO-TECH-003 | Upload recovery | Private video | ADAPT | HIGH | Upload completion idempotency and job retry exist (E-VIDEO/E-VIDEO-JOB); no multipart-resume workflow. | Add expired/partial upload cleanup/retry. | Upload state | No | C-VIDEO |
| VIDEO-TECH-004 | Secure storage | Private video | ADAPT | HIGH | S3 keys and short-lived presigned URLs (E-VIDEO/E-VIDEO-JOB). | Org/service ownership, encryption/audit/policy. | Access policy | No | C-VIDEO |
| VIDEO-TECH-005 | Session management | Private video | ADAPT | HIGH | VideoSession CRUD/history UI/tests (E-VIDEO). | Service-case/org tenancy and lifecycle. | Private gate | No | C-VIDEO |
| VIDEO-TECH-006 | Match/training classification | Private video | ADAPT | HIGH | VideoSession has discipline/session metadata, not match-vs-training service classification. | Add controlled brief/classification. | Intake | No | C-VIDEO |
| VIDEO-TECH-007 | Player linking | Private video | ADAPT | HIGH | `VideoSession.player_ids/primary_player_id`; assignment checks (E-VIDEO). | Canonical PlayerProfile and tenant validation. | Identity policy | No | C-VIDEO |
| VIDEO-TECH-008 | Team linking | Private video | NEW | HIGH | VideoSession has no Team FK/snapshot. | Add only after ownership/spec lock. | Org video model | No | C-VIDEO |
| VIDEO-TECH-009 | Analysis job reliability | Private video | ADAPT | HIGH | VideoAnalysisJob status/progress/idempotent completion (E-VIDEO). | Admission, leases, retry budget and service SLO. | Worker hardening | No | C-VIDEO |
| VIDEO-TECH-010 | Worker reliability | Private video | ADAPT | HIGH | SQS service and worker script (E-VIDEO-JOB). | Tenant payload, observability, dead-letter/runbook. | Queue ops | No | C-VIDEO |
| VIDEO-TECH-011 | Processing state | Private video | ADAPT | HIGH | Job/chunk enums, progress/stage endpoints (E-VIDEO/E-VIDEO-JOB). | Normalize customer/operator state contract. | Job model | No | C-VIDEO |
| VIDEO-TECH-012 | Failed-job recovery | Private video | ADAPT | HIGH | `video_job_recovery.py::{mark_stale_video_analysis_jobs,retry_video_analysis_job}`; tests. | Operational schedule, retry/cost policy. | Worker ops | No | C-VIDEO |
| VIDEO-TECH-013 | Analysis results | Private video | ADAPT | HIGH | E-VIDEO-RESULT plus job result endpoints/tests. | Operator QC and service output contract. | Job completion | No | C-VIDEO |
| VIDEO-TECH-014 | PDF/report generation | Private video | ADAPT | HIGH | `export_analysis_pdf`, PDF S3 artifact, report tests (E-VIDEO-RESULT). | Controlled audience/download/retention. | Results | No | C-VIDEO |
| VIDEO-TECH-015 | Coach review/edit | Private video | ADAPT | HIGH | Goals/interventions/suggestions/review-style flows (E-VIDEO-RESULT). | Explicit operator/coach approval/version contract. | Service workflow | No | C-VIDEO |
| VIDEO-TECH-016 | Evidence/provenance | Private video | ADAPT | HIGH | Repetition/phase/evidence mappings and V2 report tests. | Persist model/version/source/confidence/QC. | Results | No | C-VIDEO |
| VIDEO-TECH-017 | Internal administration | Private video | NEW | HIGH | No operator case/queue/admin surface. | Add least-privilege internal service console. | Service workflow | No | C-VIDEO |
| VIDEO-TECH-018 | Storage monitoring | Private video | ADAPT | HIGH | `video_quota_service.py` computes user bytes and checks plan quota. | Organization/job ledger, alerts and orphan scan. | Cost ledger | No | C-VIDEO |
| VIDEO-TECH-019 | Compute-cost monitoring | Private video | NEW | HIGH | Jobs record state, not compute/vendor cost. | Capture runtime/resource/provider cost per job. | Job telemetry | No | C-VIDEO |
| VIDEO-TECH-020 | Retention/deletion | Private video | ADAPT | HIGH | Session delete/bulk-delete endpoints exist; no approved lifecycle/object-proof policy. | Retention scheduler, object/artifact deletion proof. | Retention decision | No | C-VIDEO |
| VIDEO-TECH-021 | Access control | Private video | ADAPT | HIGH | E-VIDEO uses global roles, owner_id and `User.org_id`. | Current membership/service-case predicates and access audit. | Private gate | No | C-VIDEO |
| VIDEO-TECH-022 | S3/object-storage assumptions | Private video | ADAPT | HIGH | `S3_COACH_VIDEOS_BUCKET`, S3 service, key snapshots/presigned tests. | Document availability, encryption, region, lifecycle and recovery. | Infrastructure decision | No | C-VIDEO |
| VIDEO-TECH-023 | Queue/worker assumptions | Private video | ADAPT | HIGH | `SQS_VIDEO_ANALYSIS_QUEUE_URL`, SQS service, worker/recovery tests. | Document concurrency, DLQ, leases, deployment and cost. | Infrastructure decision | No | C-VIDEO |

### 7.2 Private operated-service workflow

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| VIDEO-SVC-001 | Customer intake | Private video | NEW | HIGH | No service-case intake. | Controlled customer/case record. | Private gate | No | C-VIDEO |
| VIDEO-SVC-002 | Booking/job request | Private video | NEW | HIGH | Analysis job exists only after session/upload. | Add commercial request/approval state. | Intake | No | C-VIDEO |
| VIDEO-SVC-003 | Team/player consent | Private video | OWNER DECISION | UNKNOWN | No minor/video consent framework. | Lock subjects, guardians, revocation and evidence. | Legal/privacy | Yes — consent | C-VIDEO |
| VIDEO-SVC-004 | Footage intake | Private video | ADAPT | HIGH | Upload pipeline (E-VIDEO). | Operator-assisted channel and chain of custody. | Intake/consent | No | C-VIDEO |
| VIDEO-SVC-005 | Analysis brief | Private video | NEW | LOW | Coaching focus exists on VideoSession, not service brief. | Add requested outputs/constraints/subjects. | Booking | No | C-DB |
| VIDEO-SVC-006 | Operator queue | Private video | NEW | HIGH | SQS is compute queue, not human-work queue. | Add assignment/priority/SLA/audit. | Internal admin | No | C-VIDEO |
| VIDEO-SVC-007 | Analysis workflow | Private video | ADAPT | HIGH | E-VIDEO/E-VIDEO-JOB/E-VIDEO-RESULT. | Orchestrate intake→processing→QC→delivery. | Operator queue | No | C-VIDEO |
| VIDEO-SVC-008 | Quality-control review | Private video | NEW | HIGH | No mandatory service QC state. | Add reviewer/checklist/version/reject loop. | Results | No | C-VIDEO |
| VIDEO-SVC-009 | Coach/analyst review | Private video | ADAPT | HIGH | Existing coach findings/reports and AI review patterns. | Add assigned reviewer authority/approval. | QC workflow | No | C-VIDEO |
| VIDEO-SVC-010 | Final report/output | Private video | ADAPT | HIGH | PDF/results exist (E-VIDEO-RESULT). | Freeze approved deliverable/version. | QC approval | No | C-VIDEO |
| VIDEO-SVC-011 | Secure delivery | Private video | ADAPT | HIGH | Presigned stream/PDF URLs and tests. | Case-recipient scope, expiry, download audit. | Access control | No | C-VIDEO |
| VIDEO-SVC-012 | Retention agreement | Private video | OWNER DECISION | UNKNOWN | No customer retention contract. | Lock raw/derived/report periods and deletion. | Legal/economics | Yes — retention | C-VIDEO |
| VIDEO-SVC-013 | Per-job/package pricing support | Private video | OWNER DECISION | UNKNOWN | No service catalog/order model. | Lock units, inclusions, retries and taxes; do not change canonical prices here. | Economics | Yes — pricing | C-PAY |
| VIDEO-SVC-014 | Cost tracking per job | Private video | NEW | HIGH | File size/status exist, no consolidated cost ledger. | Aggregate compute/storage/AI/labor. | Cost telemetry | No | C-VIDEO |
| VIDEO-SVC-015 | Operator time tracking | Private video | NEW | LOW | No operator work log. | Add assignment/time entries with privacy. | Operator queue | No | C-DB |
| VIDEO-SVC-016 | AI cost tracking | Private video | ADAPT | HIGH | AiUsageLog exists (E-AI), not reliably joined to video job/cost. | Record actual per-job provider/model cost. | Usage ledger | No | C-AI |
| VIDEO-SVC-017 | Storage cost tracking | Private video | ADAPT | HIGH | File bytes/quota exist (E-VIDEO-JOB), not billed retention cost. | Track raw/derived/artifact byte-days. | Storage ledger | No | C-VIDEO |
| VIDEO-SVC-018 | Customer feedback | Private video | NEW | LOW | Generic FeedbackSubmission exists, no service/job linkage. | Add controlled post-delivery feedback. | Delivery | No | C-DB |

### 7.3 Private-access guardrails

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| VIDEO-GUARD-001 | No unfinished public video signup | Private video | BUILT | LOW | No public organization video signup/route was found; Coach Pro Plus routes require auth/roles. | Preserve until explicit release gate. | None | No | C-DB |
| VIDEO-GUARD-002 | No unrestricted customer upload | Private video | BUILT | HIGH | Upload endpoints enforce authenticated feature/session ownership and quota (E-VIDEO). | Preserve; harden service-case access. | Access control | No | C-VIDEO |
| VIDEO-GUARD-003 | No public Elite promise | Private video | BUILT | LOW | Current organization plans are free only (E-ENT); no Elite org entitlement. | Keep product claims private/future. | Governance | No | C-DB |
| VIDEO-GUARD-004 | Internal/private feature gate | Private video | ADAPT | LOW | Global premium role/feature checks exist (E-VIDEO/E-BILL), not service-case gate. | Add internal allowlist/case authorization. | Service identity | No | C-DB |
| VIDEO-GUARD-005 | Controlled customer access | Private video | ADAPT | HIGH | Owner checks/presigned URLs exist (E-VIDEO). | Time/case/audience-scoped access and audit. | Private gate | No | C-VIDEO |
| VIDEO-GUARD-006 | Explicit storage limits | Private video | ADAPT | HIGH | Personal-plan GB quotas exist (`video_quota_service.py`). | Service package quota and reservation. | Economics | No | C-VIDEO |
| VIDEO-GUARD-007 | Explicit processing limits | Private video | ADAPT | HIGH | Personal upload-duration flags and job config exist. | Package duration/job/retry/compute limits. | Economics | No | C-VIDEO |
| VIDEO-GUARD-008 | Manual quality gate | Private video | OWNER DECISION | UNKNOWN | No mandatory QC state exists. | Approve mandatory operator/reviewer release gate. | Service policy | Yes — release gate | C-VIDEO |
| VIDEO-GUARD-009 | No organization-wide self-service entitlement yet | Private video | BUILT | LOW | `OrganizationEntitlement` accepts only `school_free`/`club_free`; video is excluded (E-ENT). | Preserve until separate public-readiness governance. | Governance | No | C-DB |

### 7.4 Elite-readiness learning metrics

| ID | Capability | Product | Status | Cost | Existing evidence | Required work | Dependencies | Owner decision? | Controls |
|---|---|---|---|---|---|---|---|---|---|
| VIDEO-LEARN-001 | Average footage size | Private video | ADAPT | LOW | `VideoSession.file_size_bytes` and quota computation. | Service-job aggregation. | Cost ledger | No | C-DATA |
| VIDEO-LEARN-002 | Average processing time | Private video | ADAPT | LOW | Job timestamps/status exist. | Reliable stage timestamps and dashboards. | Job telemetry | No | C-DATA |
| VIDEO-LEARN-003 | Failed-job rate | Private video | ADAPT | LOW | Job statuses/errors and recovery tests. | Service cohort/window/retry definitions. | Job telemetry | No | C-DATA |
| VIDEO-LEARN-004 | AI cost | Private video | NEW | HIGH | No per-video actual AI cost. | Join provider usage to job. | VIDEO-SVC-016 | No | C-AI |
| VIDEO-LEARN-005 | Storage retention cost | Private video | NEW | HIGH | Bytes exist; byte-days/rates do not. | Add retention-cost ledger. | VIDEO-SVC-017 | No | C-VIDEO |
| VIDEO-LEARN-006 | Operator labor | Private video | NEW | LOW | No operator time tracking. | Aggregate controlled time entries. | VIDEO-SVC-015 | No | C-DATA |
| VIDEO-LEARN-007 | Most valuable report outputs | Private video | NEW | LOW | Multiple outputs exist, no service value signal. | Structured feedback/usage outcomes. | Delivery/feedback | No | C-DATA |
| VIDEO-LEARN-008 | Requested coach workflows | Private video | NEW | LOW | No service-request taxonomy. | Capture structured requests, not private messages. | Intake | No | C-DATA |
| VIDEO-LEARN-009 | Willingness to pay and recurring vs one-off use | Private video | OWNER DECISION | UNKNOWN | No order/pricing research records. | Approve research method and data handling. | Product/economics | Yes — research | C-DATA |
| VIDEO-LEARN-010 | Privacy/consent friction | Private video | OWNER DECISION | UNKNOWN | Consent framework absent. | Define non-sensitive operational metric after legal approval. | Consent policy | Yes — measurement | C-DATA |

## 8. Data/privacy ownership decisions

These decisions remain open; this audit does not silently resolve Issue #559/#561 policy.

| Decision | Current evidence and safe boundary | Approval required |
|---|---|---|
| Organization operational data | Current organization resources are tenant-owned through `organization_id`; preserve exact route-org/resource predicates. | Retention/export/departure policy |
| Canonical player/career data | `PlayerProfile` and evidence-backed cricket truth are canonical and reusable. | Portability, correction and public visibility |
| Organization-private development data | Current development records use mixed coach/user/legacy-org ownership. | Ownership, administrator/player/guardian access, departure |
| Coach-private data | Current creator access is not a complete visibility policy. | Private/shared states, exceptional access, retention |
| Messages | No runtime exists. Contents must never enter performance-model training/input or data monetization. | Safeguarding, direct-message, moderation, retention, legal hold |
| Guardian/minor data | No guardian model exists. Private-by-default is the safe design constraint. | Identity, consent, proxy response, exports, jurisdiction |
| Video | S3/session/jobs exist under legacy ownership. | Consent, subjects, access, storage region, retention/deletion |
| AI inputs/outputs | Usage/review infrastructure exists; organization/minor/provider policy does not. | Provider training exclusion, data region/retention, audience, review |
| Public cricket data | Match publication is explicit and reversible; that does not automatically publish Teams/profiles. | Field-level publication and takedown |
| Derived analytics | Deterministic outputs require source/version/window and authorized inputs. | Portability and external reuse |
| Anonymized/aggregated data | No approved threshold/anonymization service exists. | Minimum cohort, suppression, re-identification tests, permitted purpose |

Absolute product boundaries: do not sell identifiable children's personal information; do not monetize private messages; do not infer guardian consent; do not expose one organization's private data to another; do not convert organization membership into permanent personal premium.

## 9. Cost and unit-economics guardrails

- LOW Free work is preferred. Any HIGH-cost Free capability requires a separate owner decision before implementation.
- In-app notification is the first channel. SMS, transactional email, push and WhatsApp-style providers are metered external services, never assumed unlimited/free.
- Exports require row/file/concurrency caps, admission controls and artifact retention. Public pages require traffic/rate/cache monitoring.
- AI requires organization quota reservation, idempotency, actual provider/model/token/cost records, human review where appropriate, and a locked hard-stop/overage policy.
- Video requires per-job storage, bandwidth, compute, AI and operator-time accounting; explicit raw/derived/report retention; retry charging rules; and hard upload/duration/job limits.
- Payments require provider idempotency/webhook verification, reconciled ledger, refunds/chargebacks, financial role separation and jurisdiction review.
- Aggregation requires cohort suppression, provenance, sample size, purpose limitation and re-identification testing.

## 10. Dependency map

```text
Current Organization + Membership + Free entitlement
  ├─ Free events/calendar
  │    ├─ availability ─┬─ Free selection planning ── notifications
  │    └─ attendance ───┘             └────────────── Performance selection
  ├─ Free public/privacy policy ── community pages ── sponsor surfaces
  ├─ Performance plan/seat authority
  │    ├─ coaching visibility/history decisions ── development dashboards/reports
  │    ├─ organization-safe analytics ── dashboards/selection/exports
  │    └─ quota ledger ── controlled AI
  └─ private-video gate + consent/retention
       ├─ org/service ownership + S3/SQS hardening
       ├─ operator/QC/delivery workflow
       └─ real cost/quality metrics ── future Elite decision only
```

Schema-changing work, if later authorized, must follow the master checklist real-PostgreSQL Alembic gate. Scoring, DLS, result logic, innings state, historical import, analyst evidence truth, AI execution and video processing remain protected unless an independently governed issue explicitly scopes them.

## 11. Summary counts

Counts are mechanically derived from the 340 capability rows above. Header, evidence, decision and recommendation tables are not capability rows.

### 11.1 By implementation status

| Status | Count |
|---|---:|
| BUILT | 57 |
| ADAPT | 114 |
| NEW | 113 |
| DEFER | 3 |
| OWNER DECISION | 53 |
| **Total** | **340** |

### 11.2 By cost class

| Cost | Count |
|---|---:|
| LOW | 136 |
| USAGE-SENSITIVE | 96 |
| HIGH | 52 |
| UNKNOWN | 56 |
| **Total** | **340** |

### 11.3 By product group

| Product group | Count |
|---|---:|
| Free | 118 |
| Free monetization | 38 |
| Performance | 124 |
| Private video | 60 |
| **Total** | **340** |

## 12. Already-built summary

The 57 BUILT rows are concentrated in the protected shared Free foundation: organization creation/membership/roles; one School/Club capability source; canonical roster and reusable Teams; import; saved/external match setup; XI/captain/keeper; organization scoring; fixtures/results/competitions/basic statistics; controlled public scorecards; contextual terminology and tenant isolation; and the shared organization/Team calendar, training/other events, scoped participants, fixture projection, timezone contract and upcoming view. Canonical career/batting/bowling/achievement truth and the structural separation of personal versus organization entitlements also exist. Private video is not organization-ready, but four negative public-exposure guardrails are true today: no public signup, no unrestricted unauthenticated upload, no public organization Elite promise and no organization-wide video self-service entitlement.

## 13. Adaptation summary

The 114 ADAPT rows are existing technology, not organization-ready product promises. Major reuse pools are:

- Player/Analyst deterministic analytics, filters, comparisons, exports and match-context packages.
- Coach assignments, sessions, notes, development plans/checkpoints/dashboards/reports and longitudinal progress.
- Sponsor rotation/impressions and branding technology, which need current membership tenancy and durable persistence.
- AI usage/review/report patterns, which need organization admission, quota, privacy and real cost accounting.
- Coach Pro Plus video sessions, S3 upload/playback, SQS jobs/worker/recovery, results, reports and comparisons, which need controlled service/org ownership, consent, retention, cost and operator workflow.

`User.org_id`, global `RoleEnum`, personal plan checks, creator ownership, or an entitlement/config flag are not substitutes for current OrganizationMembership authorization.

## 14. Genuinely-new summary

The 113 NEW rows are led by availability, recurrence/RSVP/notification delivery, attendance, draft selection/order planning, communication/notification, participation history, organization public homepage, organization transaction processing, organization-safe benchmark products, Performance selection workspace/automation, export audit/admission, operator-service workflow, and reliable per-job economics. Existing playing XI does not prove availability, reserves, draft publication, batting/bowling planning or selection intelligence. Mock subscription billing does not prove transaction/payment processing.

## 15. Owner decisions

The 53 OWNER DECISION rows must remain blocked until their named authority approves behavior. Highest-dependency decisions are:

1. Minor/guardian identity, consent, communication, public profile, attendance/availability and export rules.
2. Message safeguarding, direct-message authority, moderation, traceability and retention; private content is excluded from models and monetization.
3. Global cricket history versus organization-private coaching/development/selection/video ownership, portability and departure.
4. Coach-private versus organization-visible notes and exceptional administrator/player/guardian access.
5. Performance plan, contextual staff seats, membership removal and personal-plan coexistence.
6. Sponsor/advertising categories and the prohibition on child-data behavioral targeting.
7. Payment provider, transaction economics, refunds, reconciliation and financial controls.
8. Aggregation thresholds, lawful purpose, consent, provenance and prohibition on identifiable child-data sale.
9. Fielding evidence threshold, benchmark cohorts/disclosure, and automated-selection human-decision boundary.
10. AI providers, minor inputs, training/retention, review and quota/overage behavior.
11. Video consent, storage/processing/retention limits, operated-service pricing and the manual public-readiness gate.

## 16. Recommended dependency-aware build order

This is sequencing guidance, not implementation phases.

1. **Free Events / Availability / Attendance:** establish shared event identity, actor history and minor policy before reminders or analytics.
2. **Free Selection & Match Preparation:** add draft/reserve/order/history above the protected match-local XI and live-scoring truth.
3. **Free Messaging / Notifications:** only after audience sources and safeguarding/retention decisions; in-app first.
4. **Free Community + Monetization Foundations:** public/privacy controls first, then sponsor adaptations; transactions remain separate.
5. **Performance Organization Entitlement/Seat Foundation:** owner-approved contextual seats/capabilities without changing personal accounts.
6. **Performance Coaching & Development adaptation:** organization ownership, visibility and history decisions before UI reuse.
7. **Performance Analytics / Dashboards / Selection Intelligence:** deterministic organization-scoped evidence before AI.
8. **Performance Reports / Exports:** tenant-safe generation, audit, redaction, quotas and download authorization.
9. **Performance Benchmarks / Controlled AI:** only after cohort privacy, provenance, quota and human-review controls.
10. **Private video hardening in parallel:** controlled gate, org/service ownership, S3/SQS reliability, consent, retention and cost telemetry.
11. **Private operated-service workflow in parallel:** intake, operator queue, QC, delivery, package economics and feedback.
12. **Elite only after real video economics and Performance maturity:** no public promise or self-service entitlement before a separate owner/governance decision.

## 17. Future Elite boundary and governance recommendation

Elite remains future scope. Private-service evidence should inform—not pre-commit—its storage, compute, failure, operator, report-value, demand and consent economics. Do not create implementation phases from this audit. First resolve the owner decisions, then create narrowly governed issues with explicit authorization matrices, data ownership, cost controls, PostgreSQL gates where schemas change, Free regressions and rollback.

## 18. Explicit non-goals

This audit does not implement features; change runtime code/tests/migrations/dependencies/workflows; alter pricing, billing, `RoleEnum`, organization entitlements, player identity, scoring, DLS, results, innings state, historical import, AI execution, video processing or public routes; create phases; expose Elite; authorize identifiable child-data sale; or authorize private messages as analytics/model input.
