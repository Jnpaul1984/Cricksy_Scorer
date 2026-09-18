# Phase 7K — School Free End-to-End Hardening + Rollout Gate

Status: implementation and evidence record for GitHub Issue #543. This document is a deployment runbook, not authority to add capabilities beyond Phase 7.

## 1. Gate decision

School Free may be reported **READY FOR ROLLOUT** only after every command in section 12 is green in CI and the staged-rollout owner completes the go/no-go checklist in section 10. A failed security, tenancy, integrity, migration, cricket-truth, entitlement, acceptance, rollback, or protected-system gate changes the decision to **BLOCKED**.

The implementation intentionally has no new database migration, dependency, pricing rule, billing behavior, School capability, or scoring algorithm. Phase 7K adds automated acceptance gates, a School-specific CI gate, narrow read-side compatibility for the scorer's already-authoritative structured result, publication audit events, and this runbook.

## 2. Phase 7A–7J reconciliation

| Phase | Merged contract | Current implementation evidence | Phase 7K conclusion |
|---|---|---|---|
| 7A | Architecture audit/spec lock | `docs/PHASE_7A_SCHOOL_ARCHITECTURE_AUDIT_AND_SPEC_LOCK.md` (PR #520) | School is an `Organization`; active `OrganizationMembership` is authority; `PlayerProfile` remains canonical; playing XI is a frozen match snapshot. |
| 7B | Organization and memberships | `Organization`, `OrganizationMembership`, `organization_service.py`, migration `20260916020000` (PR #522) | Owner row lock protects final-owner mutations on PostgreSQL. No global School roles were added. |
| 7C | School Free entitlement | `OrganizationEntitlement`, `organization_entitlement_service.py`, migration `20260916030000` (PR #524) | Entitlement belongs to the organization and is independent of personal subscription and `RoleEnum`. |
| 7D | Persistent School Teams | `Team.organization_id`, nullable `Team.owner_user_id`, `organization_team_service.py`, migration `20260916040000` (PR #526) | Organization is authoritative. Creator deletion uses `ON DELETE SET NULL`; `Team.players` remains legacy/non-authoritative. |
| 7E | Master roster | `SchoolPlayerMembership`, `organization_roster_service.py`, migration `20260916050000` (PR #528) | One retained organization/profile association; active/inactive reuses the same membership and profile. Students require no `User`. |
| 7F | Team rosters | `SchoolTeamPlayerMembership`, `organization_team_roster_service.py`, migration `20260916060000` (PR #530) | Canonical School memberships may be reused across Teams. Persistent Team membership is not playing-XI selection. |
| 7G | Bulk roster import | `SchoolPlayerImport`, `school_player_import_service.py`, migration `20260916070000`, `openpyxl==3.1.5` (PR #532) | CSV/XLSX only; preview is immutable; resolution/apply is explicit, bound, locked, single-use, and tenant-scoped. |
| 7H | Administration UI | `frontend/src/views/school/*`, `schoolAdminApi.ts`, `useSchoolContext.ts` (PR #536) | UI uses organization role plus capability context. Backend remains authoritative. |
| 7I | Saved-Team match setup | `school_match_service.py`, `SchoolMatchSetupView.vue` (PR #538) | Two distinct active saved Teams, exactly 11 eligible members each, explicit captain/keeper, frozen canonical IDs. Generic `POST /games` remains unchanged. |
| 7J | Competitions/publication/statistics | `school_competition_service.py`, `school_statistics_service.py`, migration `20260918010000` (PRs #541/#542) | Tenant-scoped stable Team IDs, validated fixture/Game linkage, query-time statistics and standings, private-by-default Games, explicit sanitized publication. |

Merged migration order is:

1. `20260916020000` — organizations and memberships
2. `20260916030000` — organization entitlements
3. `20260916040000` — organization-owned Teams and creator-retention FK
4. `20260916050000` — School master roster
5. `20260916060000` — Team roster memberships
6. `20260916070000` — import sessions
7. `20260918010000` — competition tenancy and match publication

There is exactly one expected head: `20260918010000`.

## 3. Locked School Free contract

The exact included capabilities are:

- `school_matches_unlimited`
- `school_master_roster`
- `school_persistent_teams`
- `school_team_rosters`
- `school_match_playing_xi`
- `school_basic_statistics`
- `school_fixtures_results`
- `school_live_scorecards`
- `school_competitions`

The exact explicit exclusions are:

- `advanced_ai`
- `video_analysis`
- `advanced_analytics`
- `analyst_tooling`
- `premium_coaching`
- `premium_broadcast_video`

`org_pro`, superuser, `User.org_id`, a global `RoleEnum`, or a personal paid subscription does not grant School authority. An active membership in the exact organization and its active `school_free` entitlement are both required. School membership does not upgrade a member's personal account.

## 4. Authority matrix

| Operation | owner | admin | coach | scorer | viewer |
|---|---:|---:|---:|---:|---:|
| Read School context, Teams, rosters, fixtures, results, statistics | yes | yes | yes | yes | yes |
| Manage membership roles/status | yes | governed admin subset | no | no | no |
| Create/update Team and roster metadata | yes | yes | yes | no | no |
| Archive Team or change master-roster lifecycle | yes | yes | no | no | no |
| Assign/deactivate Team roster membership | yes | yes | yes | no | no |
| Preview/apply ordinary import | yes | yes | yes | no | no |
| Reactivate retained membership during import | yes | yes | no | no | no |
| Create match from saved Teams | yes | yes | yes | yes | no |
| Create/update competition or fixture | yes | yes | yes | no | no |
| Link fixture to validated Game | yes | yes | yes | yes | no |
| Publish live/final or return to private | yes | yes | yes | yes | no |
| Delete competition/fixture | yes | yes | no | no | no |

This table summarizes merged service constants and tests; it does not replace server checks. Foreign exact IDs are resolved with organization predicates and return tenant-safe not-found responses without names, counts, metadata, or existence details.

## 5. Acceptance and hardening evidence

`backend/tests/test_school_phase7k_acceptance.py` is the production-like PostgreSQL acceptance gate. It proves:

1. owner registration and School creation;
2. exact `school_free` capabilities and premium exclusions;
3. three persistent Teams;
4. an inactive retained player and an XLSX upload with explicit column mapping;
5. preview classification and zero `PlayerProfile`, master-roster, Team-roster, or `User` mutation;
6. exact duplicate reactivation plus explicit apply;
7. 22 canonical players, no student accounts, and single-use apply conflict;
8. reuse of one canonical profile in another Team without a clone;
9. exactly 11 Team-roster memberships selected per side;
10. the existing scorer completing a one-over match and producing the official result;
11. query-time player/Team statistics and organization results;
12. competition entrants, fixture linkage, and standings from the completed official Game;
13. explicit final publication, sanitized anonymous projection, and return to private;
14. a second match reusing the exact Teams and canonical players;
15. unchanged raw match snapshots after current Team, Team-roster, and master-roster lifecycle changes; and
16. `Team.players == []` throughout School workflows.

The same file exercises exact foreign IDs across organizations, entitlements, memberships, Teams, master roster, Team roster, import sessions, player/Team statistics, competition, fixture, publication, private Game, private snapshot, and match setup. Responses remain tenant-safe and contain none of the foreign School, Team, competition, or player names.

Existing Phase suites remain the authoritative detailed regressions for:

- final-owner locking, owner transfer, membership roles, and tenant isolation;
- Team creator deletion/FK retention;
- roster reactivation and same-name distinct players;
- Team-roster uniqueness and concurrency;
- CSV/XLSX parsing, file/archive/formula limits, binding, expiry, duplicate resolution, concurrent apply, and raw-file non-retention;
- 11-player eligibility and snapshot immutability;
- competition roles, stable IDs, legacy isolation, fixture/Game uniqueness, publication sanitization, and corrections;
- canonical statistics, inactive/archive history, name-only exclusion, and correction-on-next-read.

## 6. Scorer-result compatibility correction

The Phase 7K acceptance path found one concrete Phase 7J read-side defect. The existing scorer stores the official `Game.result` as JSON text containing `result_text`, while School results, Team statistics, fixtures, public scorecards, and standings previously treated every value as legacy plain text. A scorer-completed Game could therefore expose serialized JSON and be unresolved in standings.

`school_statistics_service.py` and `school_competition_service.py` now normalize either representation at read time. The change does not calculate, rewrite, or persist a result and does not modify scoring truth. Legacy plain-text Games behave identically; scorer-produced structured results expose the same authoritative `result_text` and drive the same deterministic winner mapping.

## 7. Import and performance boundaries

Governed import flow remains:

`upload -> parse -> map -> validate -> preview -> duplicate resolution -> explicit apply`

Limits remain 2 MiB uploaded content, 1,000 data rows, 32 columns, 255 characters per cell, 512 ZIP entries, 20 MiB expanded ZIP content, and a 200:1 expansion ratio. Only CSV and non-macro XLSX are accepted. Formula cells, macros, external links, encrypted/malformed workbooks, legacy XLS, oversized files, and archive bombs are rejected. Formula values are never evaluated or trusted. Raw workbook bytes are not retained in the import session.

Preview/apply is bound to organization, actor, content hash, parsed preview, and expiry. Apply locks the authoritative import row with `SELECT ... FOR UPDATE`, is single-use, uses row savepoints, validates exact candidates/Teams again, and creates no `User`.

Local PostgreSQL baseline on 2026-09-18:

| Gate | Data size | Observed evidence | Bound enforced by test |
|---|---:|---:|---:|
| CSV preview + apply + roster read | 1,000 rows | 10.65 seconds total pytest wall time on the validation workstation | preview <60 s, apply <120 s, roster read <30 s |
| End-to-end XLSX acceptance | 22 players, 23 Team memberships, 2 Games | passes on migrated PostgreSQL | all API operations controlled and finite |
| Player/Team statistics | frozen canonical Game ledgers | fixed organization-filtered Game query plus in-process deterministic aggregation | no cross-tenant/unfiltered query and no materialized counter |
| Teams/rosters/match setup | 11-player sides | joined organization predicates; no per-player API loop in match validation | exact 11, bounded selected IDs |
| Competitions/fixtures | organization-scoped rows | SQL organization/competition filters and fixed standings query shape | no automatic fixture conversion |

The 1,000-row apply intentionally performs governed per-row validation/savepoint work. No Redis, materialized statistic, cache, or new infrastructure is justified by the measured gate. Re-baseline before materially increasing the governed limits.

## 8. Browser and accessibility gate

`npm run test:e2e:school` runs the School administration, saved-Team match setup, and statistics/competition/publication Cypress specifications as one CI gate.

Coverage includes:

- desktop owner navigation, Team creation, retained-player reactivation, CSV preview/resolution/apply;
- tablet scorer read-only behavior;
- labeled required controls, ARIA-labelled School context/navigation, keyboard submit/action activation, status messaging, and a required destructive Team-archive confirmation;
- explicit selection of 11 eligible players per side, captain/keeper, and transition to the existing scoring route;
- statistics, competition, fixtures/results, final publication confirmation, and anonymous sanitized scorecard.

The browser suite uses API intercepts to validate UI contracts. It complements rather than replaces the migrated-PostgreSQL API acceptance journey.

## 9. Observability and operator monitoring

Existing structured events cover organization create/access denial/membership change, entitlement provisioning, Team/roster/Team-roster mutations and conflicts, import preview rejection/create/apply start/row failure/conflict/completion, and School match creation/failure.

Phase 7K adds:

- `organization.school_competition_authorization_denied` with organization, actor, membership role, and requested capability;
- `organization.school_match_publication_changed` with organization, Game, actor, previous state, and new state.

No student metadata, uploaded spreadsheet content, raw player rows, or access tokens are logged by these events.

During rollout, monitor:

- HTTP 401/403/404/409/422 and 5xx rates for `/api/organizations/*` and `/public/school-scorecards/*`;
- authorization-denied events for unexpected role/capability patterns;
- import preview rejections, row failures, conflicts, elapsed request time, and completion counts;
- School match creation failures;
- publication transition volume and unexpected repeated state changes;
- PostgreSQL constraint/deadlock/lock-timeout errors;
- scorer, innings-transition, result, and DLS regression dashboards already used by the product.

Security/operations owns tenant or entitlement incidents. Cricket/scoring ownership investigates scorer/result/DLS regressions. School product ownership handles workflow/support issues. Database ownership approves migration or entitlement-row operations.

## 10. Staged rollout and smoke test

There is **no feature flag** in the repository. Do not claim one. The existing rollout control is the exact organization entitlement row plus active organization status. New School creation provisions `school_free`; no public endpoint mutates an entitlement.

### Prerequisites

1. Back up the production database and record restore verification.
2. Confirm the deployed revision contains all Phase 7 migrations and this Phase 7K gate.
3. Confirm CI is green, including `Backend (School Free PostgreSQL gate)` and `Frontend (School Free E2E gate)`.
4. Confirm `alembic heads` has exactly `20260918010000` and production `alembic current` matches it.
5. Confirm the cohort's owner/admin contacts and support escalation channel.
6. Confirm no unresolved critical/high incident or security advisory affects the release.

### Cohort procedure

1. Start with internal/test Schools, then one named pilot School, then a small named cohort.
2. Provision only exact School organizations. For new Schools, use the ordinary organization creation contract. For a pre-Phase-7C School, database/application operations may call the existing idempotent `provision_existing_school_free_entitlement` service through an approved one-off operational task; do not expose it as an ad hoc public endpoint.
3. Verify `GET /api/organizations/{id}/entitlements` as an active member returns `plan_key=school_free`, `status=active`, exactly nine included capabilities, and exactly six exclusions.
4. Run the smoke journey: create Team; create one player; preview a two-row CSV/XLSX and confirm zero roster mutation; apply; assign Team roster; create a saved-Team match with 11 per side; score a short test match; confirm result/statistics; create/link fixture; publish and return private.
5. Confirm an outsider receives 404 for the private Game/snapshot and the anonymous public route receives 404 after return to private.
6. Hold the cohort at least one operational observation window before expanding.

### Go/no-go checkpoint

Proceed only when migrations, smoke, tenant denial, entitlement exactness, import immutability/apply, scoring/result/statistics, publication/private reversal, logs, and support readiness are confirmed. Stop expansion for any unexplained 5xx increase, cross-tenant symptom, duplicate/corrupt identity, unresolved fixture, wrong official result, premium leakage, import replay, or rollback uncertainty.

## 11. Rollback and rehearsal

Rollback prioritizes write isolation and data preservation. It does not delete canonical players, retained memberships, Teams, Team rosters, import audit/result metadata, Games, deliveries, fixtures, competitions, statistics inputs, or historical snapshots.

### Dependency-safe rollback sequence

1. Stop cohort expansion and announce the incident owner.
2. Block new School writes for the affected exact organization(s) by changing their `organization_entitlements.status` from `active` to `disabled` in one reviewed PostgreSQL transaction. Use exact organization IDs, capture affected-row counts, and have database ownership approve the operation. This makes capability checks fail closed. There is currently no first-class entitlement-disable API.
3. Verify School write endpoints return controlled capability errors and anonymous scorecards return 404 because public capability resolution is disabled.
4. Leave generic legacy scoring and non-School products online unless their own incident evidence requires separate action.
5. Export affected organization, entitlement, roster, Team, import, Game, fixture, and competition identifiers for incident analysis. Do not export raw uploaded files; they are not retained.
6. Roll application code back only to a revision compatible with the current additive schema. Do not downgrade populated Phase 7 schema during an incident.
7. Restore service only after the correction passes the PostgreSQL School gate and the exact cohort entitlement is reviewed and re-enabled.

### Schema downgrade constraints

The migration round-trip is rehearsed only on an empty disposable PostgreSQL database. Phase 7 migrations remove additive data on downgrade. In addition, `20260916040000` deliberately refuses downgrade when retained Teams have `owner_user_id IS NULL`, because recreating the legacy non-null/CASCADE FK would destroy or invalidate retained Teams. Production rollback therefore keeps the additive schema in place.

### Rollback rehearsal checks

- Disable one disposable School entitlement and prove Team/roster/import/match writes fail closed.
- Prove stored canonical and historical rows remain unchanged.
- Prove a previously public scorecard becomes unavailable while the capability is disabled.
- Re-enable the exact entitlement only after owner approval and re-run smoke.
- Record timestamps, operator, organization IDs, row counts, and validation responses in the incident/change ticket.

## 12. Release validation commands

Run from repository root with repository-supported Python/Node versions.

```text
python backend/scripts/check_alembic_single_head.py
python -m alembic -c backend/alembic.ini upgrade head
pytest -q backend/tests/test_school_*.py
pytest -q backend/tests/test_auth*.py backend/tests/test_rbac*.py
pytest -q backend/tests/test_core_scoring.py backend/tests/test_scoring_integration.py
pytest -q backend/tests/test_dls_calculations.py backend/tests/test_results_endpoint.py
pytest -q backend/tests/integration
pytest -q backend/tests/test_analyst*.py backend/tests/test_historical_import*.py
pre-commit run ruff --all-files
pre-commit run ruff-format --all-files
mypy --config-file backend/pyproject.toml --explicit-package-bases backend
pre-commit run --all-files
git diff --check

cd frontend
npm run test:unit
npm run type-check
npm run build
npm run test:e2e:school
```

Use a disposable real PostgreSQL database for School and migration gates. Validate clean upgrade, catalog constraints/FKs, safe empty-database downgrade through the Phase 7 chain, re-upgrade, one head, owner/import/Team-roster/fixture concurrency, and creator-deletion retention.

Known unchanged-main frontend unit baseline on 2026-09-18: 603 passed and 5 failed (four `GameScoringView` cases caused by `WinProbabilityChart` test setup, one video-session narrative case). A rollout candidate must reproduce the exact same failure identity on unchanged `main`; no new failure is acceptable. The School Cypress gate, typecheck, production build, and relevant component suites must be green. This baseline is not permission to ignore a changed or new failure.

Known unchanged-main static-analysis baseline on 2026-09-18: the repository's full ESLint command reports 53 errors and 89 warnings, and a newer-than-repository Ruff reports 46 diagnostics. Phase 7K reproduces those exact counts on `fa385689`, adds no diagnostic in a changed file, and passes the repository-pinned Ruff/Ruff-format hooks across all files. These baseline findings remain repository debt; they are not silently treated as Phase 7K regressions.

## 13. Deferred/non-goals

- Fielding statistics remain omitted because canonical fielder identity is not reliably persisted in existing delivery truth.
- There is no automatic fixture-to-match conversion.
- There is no first-class rollout feature flag or public entitlement-disable endpoint; controlled exact entitlement status is the current mechanism.
- No Redis, materialized statistics, cache, or infrastructure was added.
- No advanced AI, video, analyst, advanced analytics, premium coaching, or billing capability is part of School Free.
- No Phase 8 or later work is authorized by this document.
