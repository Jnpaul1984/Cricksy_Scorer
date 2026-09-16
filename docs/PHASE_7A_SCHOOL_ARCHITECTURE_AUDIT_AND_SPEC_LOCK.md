# Phase 7A — School Architecture Audit + Spec Lock

**Issue:** #519

**Phase:** Phase 7A — School Architecture Audit + Spec Lock

**Audit baseline:** `origin/main` at `bed0570e87411b0cb5c7011e292f5bbd00ed13e3`

**Status:** Specification only; no School Free runtime behavior is implemented by this document.

## 1. Executive decision

The School Free foundation is feasible through additive, organization-scoped models. It must not be implemented by extending the current global user-role mechanism, treating `User.org_id` as tenancy, or continuing to embed mutable rosters in JSON.

The locked direction is:

```text
School Organization
  -> Organization Memberships (people who can administer/use the school)
  -> School Master Roster (canonical PlayerProfile associations; login optional)
  -> Persistent Teams (organization-owned)
  -> Team Rosters (many-to-many membership)
  -> Match Playing XI (match-specific selection and snapshot)
```

The following product decisions are locked:

1. A school is an organization.
2. A user keeps one independent Cricksy identity and may hold different membership roles in multiple organizations.
3. School authority comes from an active organization membership, not from a new global `RoleEnum` value. `school_player` and equivalent global roles are forbidden.
4. `PlayerProfile` remains the canonical cricket-player record. A school-roster entry associates an organization with a `PlayerProfile`; it does not duplicate the player.
5. A rostered student is not required to be a `User`. A later verified link from a `PlayerProfile` to a `User` is optional and separate from membership.
6. One canonical player may be associated with multiple teams in the same school without duplicate profiles.
7. Persistent team membership and a match's playing XI are different records. The XI is selected for one match from eligible players and is preserved in the match snapshot.
8. School Free entitlement belongs to the organization. It never rewrites every member's personal `role` or `subscription_plan`.
9. Existing match JSON remains the backward-compatible scoring snapshot. Later stable references must be additive and nullable for historical rows.
10. Every organization-owned query and mutation must prove active membership for the organization derived from the server-side resource/path. Client-supplied tenant identifiers are not authority.

Phase 7B is **READY** under the implementation contract in section 17.

### Architecture decision register

| # | Required decision | Locked answer |
|---:|---|---|
| 1 | School representation | A school is one `Organization` with `organization_type = school`. |
| 2 | Roles | School roles live only on `OrganizationMembership`. No global school role is added. |
| 3 | Independent identity | `User` remains independent and may have multiple organization memberships. |
| 4 | Canonical player | `PlayerProfile` remains canonical; current alternative IDs become source/snapshot mappings, not new truth. |
| 5 | Students without login | A roster association requires `PlayerProfile`, not `User` or membership. |
| 6 | Future account link | A separate, verified, optional player-to-user link may be added later; it never grants organization membership implicitly. |
| 7 | Persistent teams | Existing `Team` is evolved additively into an organization-owned persistent team. |
| 8 | Master roster | An organization-to-`PlayerProfile` association is the School master roster. |
| 9 | Team roster | A normalized team-to-organization-roster association supports reuse and multi-team membership. |
| 10 | Playing XI | The XI is a per-match selection, not a mutation of persistent team membership. |
| 11 | Match compatibility | Existing match team JSON remains the scoring snapshot; stable source references are additive and nullable. |
| 12 | School Free entitlement | Entitlement belongs to the organization and is resolved in organization context; personal plans are unchanged. |
| 13 | Tenant isolation | Every organization-owned read/write is membership-authorized and filtered by stored organization ID. |
| 14 | File import | School-specific staged CSV/XLSX workflow uses upload, parse, map, validate, preview, explicit duplicate resolution, then explicit apply. |
| 15 | Migration sequence | 7B organization/membership precedes entitlement, teams, roster, team membership, import, UI, match integration, and competitions/statistics. |

## 2. Audit method and evidence standard

This audit read the governing checklist and Issue #519, then inspected the current models, schemas, routes, services, frontend stores/views, migrations, tests, and CI definitions at the baseline commit above. Claims below cite repository paths and the relevant symbol or route. Line numbers are intentionally secondary to symbols because later formatting may move them.

No runtime file, migration, dependency, workflow, pricing rule, billing behavior, scoring rule, DLS rule, result calculation, historical import, analyst feature, or video-analysis feature is changed by Phase 7A.

## 3. Current-state architecture map

### 3.1 Identity, roles, subscription, and tenancy

| Concern | Current repo evidence | Finding |
|---|---|---|
| User identity | `backend/sql_app/models.py` — `User` | A user has a string UUID, email, password hash, active/superuser flags, one global `role`, one `subscription_plan`, and a nullable string `org_id`. |
| Global roles | `backend/sql_app/models.py` — `RoleEnum` | The enum contains `free`, player/coach/analyst plans, `org_pro`, and `venue_admin`. It is both authorization vocabulary and plan vocabulary. There are no school membership roles. |
| Authentication | `backend/security.py` — `get_current_user` | JWT `sub` resolves one `User`; no organization context or membership is loaded. |
| Authorization | `backend/security.py` — `require_roles`, `COACH_ROLES`, `ORG_ROLES`, `ANALYST_ROLES` | Authorization tests only the global user role. |
| Subscription response | `backend/routes/auth_router.py` — `_get_subscription_info`, `GET /auth/me` | Subscription information is derived from the user's global role; `org_id` is returned as a scalar. |
| User administration | `backend/routes/users_router.py` — `list_users`, `update_user_role` | An `org_pro` user can list users and update a target user's global role without an organization filter. This is not tenant-safe organization administration. |
| Schema origin | `backend/alembic/versions/j0e1f2g3h4i5_add_beta_user_fields.py` | The migration added user-level `subscription_plan` and `org_id`; it did not create an organization or membership table. |

There is no `Organization` model and no organization-membership table in the current model/migration graph. `User.org_id` permits only one opaque value and has no foreign key, so it cannot represent independent identity across multiple organizations or enforce tenant integrity.

### 3.2 Player identity

| Representation | Current repo evidence | Finding |
|---|---|---|
| Canonical development/profile record | `backend/sql_app/models.py` — `PlayerProfile`; `backend/routes/players.py` — player-profile routes | `PlayerProfile.player_id` is a string primary key with identity details, date of birth, aggregates, and development relationships. It has no required `User` link and no organization ownership. This is compatible with students who do not log in. |
| Normalized scorecard player | `backend/sql_app/models.py` — `Player`, `BattingScorecard`, `BowlingScorecard`, `Delivery` | A second `players` table uses an integer key and is referenced by normalized scorecard/delivery rows. It is a distinct identity domain from `PlayerProfile`. |
| Match-local player | `backend/services/game_service.py` — `_make_players`, `create_new_game`; `backend/sql_app/crud.py` — `create_game` | Match creation generates new UUIDs from submitted names and stores them in team JSON. It does not resolve `PlayerProfile`. |
| Persistent-team player | `backend/sql_app/models.py` — `Team.players`; `backend/routes/teams.py` — `create_team`, `update_team` | A persistent team embeds `{id, name}` objects in JSON. There is no foreign key or join table to `PlayerProfile`. |
| User link | `backend/sql_app/models.py` — `User`, `PlayerProfile` | No explicit user-to-player-profile link exists. |

Identity is therefore fragmented across `PlayerProfile`, the separate integer-keyed `Player`, persistent-team JSON, and match JSON. School Free must not create a fifth canonical player. `PlayerProfile` remains canonical; later phases will add associations and snapshot references without rewriting historical scoring identities.

### 3.3 Persistent teams and player/team relationships

`backend/sql_app/models.py::Team` is a persistent record, but it is owned by `owner_user_id`, optionally references a coach user, and stores `players` and `competitions` as JSON. `backend/routes/teams.py` scopes CRUD by owner/coach user IDs. There is no `organization_id`, no normalized roster membership, no validity period, and no enforcement that embedded IDs refer to a canonical player.

`backend/services/org_stats.py::get_organization_statistics` treats the supplied `org_id` as `Team.owner_user_id`. It also queries attributes that do not exist on the current `Game`/`Delivery` models, including team foreign keys and differently named state/delivery fields. This service is stale and must not be treated as a School Free statistics foundation.

The routes `GET /api/teams/organizations/{org_id}/stats` and `GET /api/teams/organizations/{org_id}/teams` in `backend/routes/teams.py` do not apply an authentication dependency and rely on that user-ID interpretation. They are not proof of organization tenancy.

### 3.4 Match creation, match-local JSON, and playing XI

`backend/sql_app/models.py::Game` stores `team_a` and `team_b` as JSON, including player IDs/names and later `playing_xi`. It also stores captain/keeper IDs, DLS state, deliveries JSON, scorecard JSON, and result text. It has `created_by_user_id` but no organization or persistent-team foreign keys.

`backend/sql_app/schemas.py::GameCreate` accepts team names and arrays of player names. `backend/routes/games_core.py::create_game` delegates to `backend/services/game_service.py::create_new_game`, which generates new player UUIDs. The create route has no current-user dependency.

`backend/routes/games_router.py::set_playing_xi` validates that submitted IDs are a subset of the embedded match-team player IDs, then writes the XI into the match JSON. This is correctly separate from the initial squad snapshot, but the route currently has no tenant authorization. `backend/routes/roles.py` validates captain/keeper against the embedded team players, not necessarily the selected XI.

`frontend/src/views/MatchSetupView.vue` and `frontend/src/components/PlayersEditor.vue` collect free-form team/player names. `frontend/src/views/TeamSelectionView.vue` selects exactly eleven players and captain/keeper, saves selection in local storage, and posts the XI without a bearer token. Its global-role checks are client-side UX checks, not an authorization boundary.

Locked compatibility rule: later match integration will add nullable organization/team/player source references and versioned snapshot metadata, while retaining `Game.team_a`/`team_b` as the scoring-time snapshot. Historical match JSON must not be rewritten.

### 3.5 Fixtures, tournaments, and competitions

`backend/sql_app/models.py::Tournament`, `TournamentTeam`, and `Fixture` have no organization foreign key. Tournament teams store team data as JSON, and fixtures identify opponents by team names plus an optional `game_id`.

In `backend/routes/tournaments.py`, tournament and fixture creation use the global `org_only_required` dependency, but several list/read/update/delete/add-team paths lack tenant authorization. `backend/sql_app/tournament_crud.py` does not apply organization filters. Existing tests in `backend/tests/test_tournament_api.py` assert global-role behavior, not cross-organization isolation.

These records require an additive tenant migration in Phase 7J. They must not be silently adopted as tenant-safe simply because a create route checks `org_pro`.

### 3.6 Scoring, result, and DLS boundaries

The scoring truth lives in and around `backend/sql_app/models.py::Game`, `backend/routes/gameplay.py`, `backend/routes/games_dls.py`, `backend/dls.py`, delivery/scorecard services, and result calculation code. Phase 7 introduces selection/source metadata only; it does not alter cricket calculations.

Required boundary for all later phases:

- resolve organization/team/roster eligibility before a match starts;
- copy the selected names and stable source identifiers into the existing match snapshot;
- let current scoring, DLS, interruption, result, scorecard, and WebSocket flows consume their existing match representation;
- project completed outcomes back to school statistics asynchronously or in a separate service without becoming scoring truth;
- never recompute or mutate historical scoring data as part of a roster migration.

### 3.7 Statistics

Current statistics are split among match scorecards, player-profile aggregate/development fields, tournament intelligence, historical statistics, analyst features, and the stale `org_stats` service. There is no organization-scoped basic-statistics projection keyed to canonical school roster members.

Phase 7J must define a narrow, reproducible school-statistics projection from completed match snapshots and stable player references. Advanced analytics, analyst systems, AI, coaching intelligence, and video data are separate products and are not School Free dependencies.

### 3.8 Pricing, billing, and feature gating

`backend/config/pricing.py` defines user-oriented `IndividualPlan` records. `backend/services/entitlement_service.py::EntitlementService.get_user_entitlements` resolves entitlements from the user's global role, with superuser/beta logic. `backend/services/billing_service.py` and `backend/routes/billing.py` are likewise user/subscription oriented. `frontend/src/stores/authStore.ts` derives feature access from one global role; `frontend/src/types/auth.ts` exposes one `org_id`.

`org_pro` is not a safe alias for School Free: its current entitlements include capabilities that the School Free contract excludes. Changing a school member's global role would also alter that person's independent account outside the school.

Phase 7C must therefore add an organization-owned, context-aware entitlement source. Personal and organization entitlements remain separate. A request in school context may use only the capabilities granted to that organization plus any explicitly permitted personal capability; it must never promote every member or leak a personal premium capability into the organization's shared access.

### 3.9 CSV, XLSX, and import patterns

`backend/requirements.txt` includes `pandas` and `python-multipart`, but no explicit XLSX engine such as `openpyxl` or `xlrd`. No current School roster CSV/XLSX parser exists. XLSX dependency approval belongs to Phase 7G, not Phase 7A or 7B.

Two current systems provide process patterns only:

- Historical import routes/services use uploads, preview/dry-run/apply behavior, hashes, and duplicate detection. They are protected and must remain separate.
- `backend/routes/cpl_roster.py`, `backend/api/schemas/cpl_roster.py`, and `backend/services/cpl_roster_service.py` implement a competition-season-specific preview/apply workflow with warnings, blockers, duplicate handling, confirmation, and idempotency.

The CPL model is not the School master roster and must not be reused as canonical storage. Only its validation/preview/apply concepts may inform a new isolated implementation.

### 3.10 Frontend organization, auth, team, and match setup

- `frontend/src/views/OrgManagementView.vue` treats global-role users as seats and grants/revokes access by changing `User.role`. It is not membership administration.
- `frontend/src/stores/authStore.ts` and `frontend/src/router/index.ts` gate UI/routes by global role. They have no active-organization membership context.
- `frontend/src/views/TeamManagementView.vue` manages user-owned JSON teams and attempts to fetch a player list; the current `backend/routes/players.py` exposes profile-specific routes, not a School master-roster list contract.
- `frontend/src/components/TeamFormModal.vue` submits embedded player objects.
- `frontend/src/views/MatchSetupView.vue`, `PlayersEditor.vue`, and `TeamSelectionView.vue` use transient names/IDs rather than persistent School teams and canonical players.

Phase 7H must introduce an explicit active-organization context sourced from server memberships, not from a user-editable `org_id` or local storage alone. Frontend checks remain UX only; all enforcement is server-side.

### 3.11 Alembic and database state

The baseline contains 75 Alembic revisions and one head: `20260905103000` (`backend/alembic/versions/20260905103000_add_player_profile_date_of_birth.py`). Relevant earlier revisions include:

- `j0e1f2g3h4i5_add_beta_user_fields.py` — user-level plan and `org_id`;
- `d4e5f6a7b8c9_add_teams_table.py` — user-owned teams with JSON players/competitions;
- `e1a2b3c4d5e6_add_player_profiles_and_achievements.py` — `PlayerProfile`;
- `e1f7a8b2c9d3_add_tournament_tables.py` — tournaments, JSON tournament teams, and fixtures.

`backend/alembic/env.py` enables type/default comparison and supports the Postgres path. `backend/sql_app/database.py` can use in-memory SQLite for tests, so SQLite-only success is insufficient for any Phase 7 schema change.

`.github/workflows/ci.yml` already runs a single-head check and `alembic upgrade head` against PostgreSQL 14 in migration/deploy-parity jobs. The governing checklist additionally requires upgrade, downgrade, and clean re-upgrade evidence on real PostgreSQL for every later migration PR.

### 3.12 Existing tests and CI gates

Relevant current coverage includes:

- `backend/tests/test_auth_basic.py` and `backend/tests/test_rbac_roles.py` for authentication/global roles;
- `backend/tests/test_player_profiles.py` and `backend/tests/test_players_routes.py` for player-profile behavior;
- `backend/tests/test_tournament_api.py` and `test_tournament_crud.py` for current tournament behavior;
- `frontend/cypress/e2e/match_creation_flow.cy.ts` for free-form match creation, XI selection, and scoring;
- `frontend/tests/unit/gameStore.spec.ts` for scoring state.

There are no organization-membership, multi-tenant isolation, School master-roster, or persistent-team-to-XI tests. `backend/tests/EXAMPLE_test_organization.py` is a generic test-layout example, not an organization-domain implementation.

Current CI gates include Python lint/format/type checks, backend pytest suites, real-Postgres migration checks, frontend fake-data guard/type-check/build, and selected Cypress suites. `.github/workflows/docs-check.yml` enforces documentation-only scope for this Phase 7A PR.

## 4. Reusable components and non-reusable assumptions

### Safe to reuse or extend

- `User` identity and JWT authentication.
- `PlayerProfile` as canonical player identity.
- The persistent `Team` concept, after additive organization ownership and normalized roster work.
- Match team JSON as an immutable/backward-compatible snapshot.
- The existing playing-XI endpoint's basic subset-validation concept, after tenant and canonical-eligibility enforcement.
- Tournament/fixture concepts after organization scoping.
- Preview/validation/explicit-apply workflow patterns from imports, in new School-specific code and storage.
- Existing Alembic and real-Postgres CI infrastructure.

### Must not be treated as foundations

- `User.org_id` as authoritative tenancy.
- `RoleEnum.org_pro` as a school membership or School Free entitlement.
- Global role mutation as organization administration.
- `Team.players` JSON as the School master roster.
- Match-generated UUIDs as canonical player identity.
- `TournamentTeam.team_data` as a persistent School team.
- `org_stats` as a correct statistics implementation.
- CPL or historical-import tables as School roster storage.
- Client-side role checks as authorization.

## 5. Conflict and risk register

| ID | Conflict or risk | Required response |
|---|---|---|
| R1 | No organization/membership model; `User.org_id` is single-valued and unconstrained. | Add organization and membership tables first; leave the legacy column non-authoritative. |
| R2 | `org_pro` can list users and mutate global roles without tenant filtering. | New organization APIs must never reuse this behavior. Existing behavior is a separate security debt; do not expand it. |
| R3 | Player identity is fragmented across four representations. | Keep `PlayerProfile` canonical; add explicit associations and snapshot source IDs. Do not destructive-merge identities. |
| R4 | Teams are user-owned JSON documents. | Add organization ownership before School use; add normalized team-roster rows later while retaining JSON for compatibility until migration is proven. |
| R5 | Match creation/XI routes lack server-side organization authorization. | Add authorization and stable references only in Phase 7I; keep scoring internals unchanged. |
| R6 | Tournament tenancy is incomplete and inconsistent. | Add organization scope and denial tests in Phase 7J before School competitions are enabled. |
| R7 | `org_stats` targets nonexistent model attributes. | Quarantine from School work; design a tested projection in Phase 7J. |
| R8 | User-plan entitlements cannot express School Free and `org_pro` includes excluded premium features. | Add organization entitlements in Phase 7C; do not change pricing/billing or user plans. |
| R9 | No verified XLSX engine is declared. | Phase 7G must obtain dependency approval or select an already-approved parser, then test real XLSX files. |
| R10 | Existing frontend “organization” UX changes global roles. | Replace with membership-based School UI in Phase 7H; do not silently relabel the current page. |
| R11 | Minors' roster data creates privacy and retention obligations. | Minimize fields, prohibit public roster browsing, log admin mutations, and obtain policy approval before Phase 7E/7G rollout. |
| R12 | SQLite tests can mask PostgreSQL enum/constraint/index behavior. | Require the checklist's real-Postgres round trip for every schema PR. |

## 6. Target data model — specification only

All identifiers below are server-generated UUID strings unless a later migration review standardizes native Postgres UUID columns. Timestamps are timezone-aware and server-maintained.

### 6.1 Phase 7B foundation

#### `organizations`

| Column | Contract |
|---|---|
| `id` | Primary key. |
| `name` | Required display name, normalized non-empty validation. |
| `organization_type` | Required constrained string; Phase 7 supports `school`. |
| `status` | `active`, `suspended`, or `archived`; default `active`. |
| `created_by_user_id` | Nullable FK to `users.id`, `ON DELETE SET NULL`, for provenance only. |
| `created_at`, `updated_at` | Required timestamps. |

No billing or entitlement fields belong on this table in Phase 7B.

#### `organization_memberships`

| Column | Contract |
|---|---|
| `id` | Primary key. |
| `organization_id` | Required FK to `organizations.id`, indexed, `ON DELETE CASCADE`. |
| `user_id` | Required FK to `users.id`, indexed, `ON DELETE CASCADE`. |
| `role` | `owner`, `admin`, `coach`, `scorer`, or `viewer`. No player role. |
| `status` | `active` or `disabled`; default `active`. Invitations are not part of 7B. |
| `created_by_user_id` | Nullable FK to `users.id`, `ON DELETE SET NULL`. |
| `created_at`, `updated_at` | Required timestamps. |

Constraints: unique `(organization_id, user_id)`; checks for allowed role/status; supporting index `(user_id, status)`. Service rules prevent removal/demotion of the final active owner. A user may have memberships in many organizations.

### 6.2 Later additive models

- **Phase 7C — `organization_entitlements`:** organization FK, entitlement/plan key, status, effective dates, provenance. School Free is an organization grant, not a `User.role` value.
- **Phase 7D — persistent teams:** add nullable `organization_id` and lifecycle state to the existing `teams` table, then make organization ownership mandatory for School-created teams. Preserve legacy owner fields during compatibility rollout.
- **Phase 7E — `organization_roster_players`:** organization FK, `PlayerProfile.player_id` FK, roster status and school-local administrative metadata; unique `(organization_id, player_profile_id)`. Avoid duplicating core identity fields. An optional separately verified `player_user_links` association may connect one `PlayerProfile` to a `User`; it is not required for roster existence.
- **Phase 7F — `team_roster_memberships`:** team FK, organization-roster-player FK, status, join/leave timestamps; enforce same-organization membership in service logic and PostgreSQL-safe constraints/triggers only if justified by migration review.
- **Phase 7G — import staging:** organization-scoped import session, uploaded-file metadata/hash, column map, parsed row results, duplicate candidates, decisions, preview version, expiry, and apply audit. Staging is never canonical roster storage.
- **Phase 7I — match sources:** nullable organization and persistent-team references plus versioned source IDs in snapshots. Existing `team_a`/`team_b` JSON remains present for scoring/history.
- **Phase 7J — competitions:** organization scope on tournaments/fixtures and stable team references while retaining snapshot names for history.

## 7. Future API contracts — specification only

All organization resources are under `/api/organizations/{organization_id}`. The server resolves `organization_id` from the path/resource and authorizes the current JWT user against `organization_memberships`; a body/header value is never accepted as proof of tenancy.

### 7.1 Phase 7B contracts

| Method/path | Contract |
|---|---|
| `POST /api/organizations` | An active authenticated user creates a `school` organization and becomes its `owner` in one transaction. No personal role/plan change. |
| `GET /api/organizations` | List only organizations for which the current user has an active membership. |
| `GET /api/organizations/{id}` | Return organization summary to an active member. Non-members receive tenant-safe not-found behavior. |
| `GET /api/organizations/{id}/me` | Return the caller's active membership and effective organization role. |
| `GET /api/organizations/{id}/memberships` | Owner/admin list of memberships in that organization only. |
| `POST /api/organizations/{id}/memberships` | Owner/admin adds an existing user by exact user ID. No global user search and no email invitation in 7B. |
| `PATCH /api/organizations/{id}/memberships/{membership_id}` | Change role/status under owner-protection rules. |
| `DELETE /api/organizations/{id}/memberships/{membership_id}` | Disable rather than hard-delete through the API; final active owner cannot be disabled. |

Creation, role change, disablement, and failed cross-tenant mutations must emit structured security/audit events without logging secrets or unnecessary student data.

### 7.2 Later contracts

- **7C:** `GET /api/organizations/{id}/entitlements`; server-side capability dependency for School context. No public mutation endpoint until billing/provisioning ownership is approved.
- **7D/7F:** organization-scoped team CRUD and `/teams/{team_id}/roster` membership operations.
- **7E:** organization-scoped master-roster list/create/update/archive and exact canonical-player association endpoints.
- **7G:** `/roster-imports` upload, parse/map, preview, duplicate-decision, and apply endpoints using opaque session/version tokens.
- **7I:** create a match from saved team IDs, return eligible squad, submit a match-specific XI, and persist stable source IDs in the snapshot.
- **7J:** organization-scoped fixtures, results, competitions, and basic-statistics reads.

## 8. Tenant and authorization matrix

`owner`, `admin`, `coach`, `scorer`, and `viewer` are organization-membership roles only.

| Capability | Non-member | Viewer | Scorer | Coach | Admin | Owner |
|---|---:|---:|---:|---:|---:|---:|
| Read school summary | No | Yes | Yes | Yes | Yes | Yes |
| Read master roster/team list | No | Yes | Yes | Yes | Yes | Yes |
| Create/edit players and teams | No | No | No | Yes | Yes | Yes |
| Create match from saved team | No | No | Yes | Yes | Yes | Yes |
| Select XI / score assigned match | No | No | Yes | Yes | Yes | Yes |
| View basic stats/fixtures/results | No | Yes | Yes | Yes | Yes | Yes |
| Manage memberships | No | No | No | No | Yes, except owners | Yes |
| Assign/remove owner | No | No | No | No | No | Yes, never last owner |
| Manage organization status | No | No | No | No | No | Yes |
| Upload/apply roster import | No | No | No | Yes | Yes | Yes |

Authorization invariants:

1. Membership must be active and its organization must be active.
2. A resource's stored `organization_id`, not a client body field, is authoritative.
3. Queries include `organization_id` in the database predicate; authorization is not a post-query filter.
4. Cross-organization object IDs return tenant-safe not-found behavior and no object metadata.
5. Superuser bypass, where retained for operations, must be explicit, tested, and audit logged. Global `org_pro` is not a bypass.
6. Roster players are not members and receive no application access unless independently linked to a user who also has a membership.
7. Public live scorecard access, when enabled, is a separately published match projection; it never implies access to private roster or administration APIs.

## 9. School Free entitlement boundary

School Free grants these capabilities only within an entitled active school organization:

- unlimited school matches;
- reusable master-roster players and persistent teams;
- team-roster and match-XI selection;
- basic player/team statistics derived from school matches;
- fixtures and results;
- published live scorecards;
- school competitions.

It does not grant advanced AI, video analysis, advanced analytics, analyst tooling, premium coaching, or any other premium capability unless separately approved and entitled. It does not change `User.role`, `User.subscription_plan`, personal billing, or personal feature access.

Phase 7C must implement named organization capabilities rather than reuse `org_pro` wholesale. Every gated request supplies an organization context and verifies both membership authorization and organization entitlement. Personal entitlement checks remain valid for personal workflows but cannot make a school-wide premium feature available to other members.

## 10. Future roster import architecture

The required state machine is:

```text
upload -> parse -> map -> validate -> preview -> duplicate resolution -> explicit apply
```

1. **Upload:** authenticated coach/admin/owner uploads CSV or XLSX to an organization-scoped, short-lived session. Enforce extension, MIME/signature, byte/row limits, safe filenames, malware/storage policy, and a content hash.
2. **Parse:** a dedicated School importer reads data without formulas/macros/external links and records parser/version metadata. No canonical writes occur.
3. **Map:** user explicitly maps source columns to allowed fields; required names and optional identifiers/demographics are visible before validation.
4. **Validate:** normalize safely, reject malformed/oversized values, classify blockers/warnings, and detect duplicates within the file and against the organization's roster/canonical profiles.
5. **Preview:** return row-level proposed action (`create profile`, `associate existing`, `skip`, or `blocked`), errors, warnings, candidate matches, and aggregate counts. Preview has an opaque version/hash.
6. **Duplicate resolution:** the administrator explicitly selects an existing canonical player, confirms creation, or skips each ambiguous row. Similar names alone never auto-merge, especially for minors.
7. **Explicit apply:** require confirmation plus the unchanged session/version/hash. Apply once in an organization-scoped transaction, is idempotent, and returns created/associated/skipped counts with audit identifiers.

The importer never calls or mutates historical-import, CPL, analyst, scoring, or video tables. Failed/expired sessions cannot apply. Cross-organization duplicate search exposes only safe match hints from profiles the caller is authorized to use; broader canonical linking requires a separately approved privacy policy.

## 11. Migration dependency ordering

| Order | Phase | Dependency and schema intent |
|---:|---|---|
| 1 | 7B | Add organizations and memberships; establish tenant authorization. |
| 2 | 7C | Add organization entitlements keyed to a real organization. |
| 3 | 7D | Add organization ownership/lifecycle to persistent teams. |
| 4 | 7E | Add organization master-roster associations to canonical `PlayerProfile`. |
| 5 | 7F | Add normalized many-to-many team-roster memberships. |
| 6 | 7G | Add isolated import staging/decision/apply audit after canonical targets exist. |
| 7 | 7H | Add UI/context; no schema change expected. |
| 8 | 7I | Add nullable match source references and versioned snapshots after teams/rosters exist. |
| 9 | 7J | Add organization scope to competitions/fixtures and school-stat projection. |
| 10 | 7K | Hardening/rollout gate; schema changes only for a separately reviewed defect. |

Every migration is additive first, has one verified parent revision, preserves legacy reads, and uses staged backfill/constraint tightening. No Phase 7B migration may backfill `User.org_id` into memberships automatically: current values have no referential source and could create false tenant authority. Legacy reconciliation requires an audited mapping and a separate approved migration/operations plan.

## 12. PostgreSQL migration gate for Phases 7B onward

For every schema-changing PR, record commands and results against real PostgreSQL, not SQLite:

```bash
cd backend
alembic heads
alembic current
alembic upgrade head
alembic downgrade <previous_revision>
alembic upgrade head
pytest -q <focused Phase 7 tests>
```

Also validate a clean database from base to head, the application's current production-to-head path, constraints/indexes/FKs through PostgreSQL catalog inspection, transaction rollback on failure, and one Alembic head. Downgrade must remove only objects introduced by that revision and must not destroy pre-existing data. CI's PostgreSQL migration jobs remain mandatory even when focused local tests pass.

## 13. Testing strategy and CI expectations

Later implementation phases require:

- unit tests for role/capability decisions and invariant helpers;
- API contract tests for success and every denied role;
- cross-organization isolation tests for list/read/create/update/delete using two organizations and overlapping user/team/player identifiers;
- repository/service tests proving organization predicates are present;
- real-Postgres migration round trips and uniqueness/FK behavior;
- compatibility tests for legacy users, teams, games, snapshots, tournaments, and personal plans;
- frontend tests for organization switching and denial UX when UI work begins;
- E2E for the final acceptance journey without stubbing tenant authorization.

Phase 7B CI commands are locked in section 17.11. Later phases add their focused suites and must continue to pass the existing protected scoring/DLS/result tests when touching match integration boundaries.

## 14. Rollout and rollback principles

- Ship additive tables/nullable references behind server-side capability gates.
- Keep legacy data paths readable until backfill and parity are proven.
- Never derive memberships automatically from unverified `User.org_id` values.
- Roll back application use before rolling back schema. Preserve organization data for forward repair unless the exact migration is still pre-production and empty.
- Disable School routes/entitlements to stop rollout; do not downgrade user personal plans.
- Treat cross-tenant leakage as a stop-ship/rollback event.
- Import apply is idempotent and audited; rollback uses recorded associations/rows, not deletion of shared `PlayerProfile` records.
- Match-source rollback removes new selection UX while existing JSON snapshots continue to score and render.

## 15. Protected systems and forbidden changes

All Phase 7 work must protect:

- scoring truth, delivery processing, scorecards, WebSockets, and match-state transitions;
- DLS tables, resource calculations, interruption workflows, and target calculation;
- result computation and historical match snapshots;
- historical import routes/services/models/data;
- analyst and tournament-intelligence systems outside the explicit School basic-stat boundary;
- video-analysis, video-upload, and video-owner systems;
- canonical pricing and billing behavior unless a separately governed phase explicitly authorizes a change;
- personal user roles/subscriptions and existing `PlayerProfile` records.

Forbidden approaches include a global `school_player` role, requiring students to create logins, copying a player profile per team, using `org_pro` as School Free, trusting a client `org_id`, joining tenant data without an organization predicate, changing match calculations to fit the new model, coupling School imports to historical/CPL imports, or editing historical JSON to retrofit references.

## 16. Final Phase 7 acceptance trace

The target flow is supported by the ordered model without collapsing concerns:

1. an authenticated user creates a school organization and becomes owner (7B);
2. School Free entitlement is attached to that organization (7C);
3. the administrator uploads CSV/XLSX, previews and resolves duplicates, then explicitly applies to the master roster (7E/7G);
4. multiple persistent organization teams are created and populated from the same roster without duplicating `PlayerProfile` (7D/7F/7H);
5. a saved team supplies an eligible squad for match creation and a separate playing XI is selected (7I);
6. the existing scoring/DLS/result stack scores the snapshot unchanged (7I/7K);
7. basic school player/team statistics, fixtures/results, live scorecards, and competitions retain stable source associations (7J);
8. the same canonical players and teams are reused in later matches without re-entry (7K).

## 17. Phase 7B — implementation-ready definition

### 17.1 Exact objective

Introduce the minimum authoritative organization and organization-membership foundation for schools, with server-enforced multi-tenant authorization and no change to personal identities, global roles, subscriptions, entitlements, teams, players, matches, or frontend behavior.

### 17.2 Strict scope

Phase 7B may:

- add `Organization` and `OrganizationMembership` persistence models;
- add one Alembic revision for their tables, constraints, foreign keys, and indexes;
- add request/response schemas and an organization service/repository;
- add organization/membership API routes listed in section 7.1;
- add reusable server-side membership/role dependencies;
- register the new router;
- add focused tests, including real-Postgres migration/isolation evidence;
- emit structured security/audit log events using existing logging infrastructure.

Phase 7B does not add roster, team, import, entitlement, billing, competition, match, scoring, or frontend behavior. It does not migrate legacy `User.org_id`.

### 17.3 Likely files allowed to change

Exact placement should follow current package conventions; the PR should remain within this allowlist unless a pre-change audit documents a necessary equivalent:

- `backend/sql_app/models.py`
- `backend/api/schemas/organizations.py` (new; prefer isolated schemas over expanding unrelated contracts)
- `backend/routes/organizations.py` (new)
- `backend/services/organization_service.py` (new)
- `backend/security.py` or a new narrowly scoped `backend/security/organization.py` if package layout permits
- `backend/app.py` (router registration only)
- one new file under `backend/alembic/versions/`
- new focused files under `backend/tests/` for organizations, memberships, authorization, tenant isolation, and migration behavior
- narrowly necessary test fixtures under existing test-support files

No frontend file is required for 7B.

### 17.4 Protected files/systems

Do not change:

- `backend/config/pricing.py`, billing routes/services, or existing entitlement behavior;
- `RoleEnum`, personal role-assignment semantics, or `User.subscription_plan`;
- `User.org_id` behavior or values;
- `PlayerProfile`, `Player`, teams, tournaments, fixtures, games, deliveries, scorecards, or match schemas;
- scoring, DLS, result, historical-import, CPL roster, analyst, coaching intelligence, or video systems;
- frontend source;
- dependencies or workflows.

If implementation proves one of these changes unavoidable, stop Phase 7B and return to governance review.

### 17.5 Proposed schema changes

Implement exactly the `organizations` and `organization_memberships` contracts in section 6.1.

Additional locked behavior:

- organization creation and its owner membership are one transaction;
- IDs are generated server-side;
- duplicate membership returns conflict without revealing data from another organization;
- database checks enforce enumerated strings and uniqueness;
- application logic prevents disabling/demoting the last active owner;
- no seed/backfill from `User.org_id`;
- no organization deletion API in 7B; status change is reserved for a later governed operation;
- no global Postgres enum is required; constrained strings avoid coupling membership roles to `RoleEnum` and make rollback safer.

### 17.6 Proposed API changes

Implement only the seven Phase 7B endpoints in section 7.1. Use explicit Pydantic response models; never serialize password/billing fields. Pagination is required for membership listing. Do not add global user-search, invitation email, entitlement, roster, or team endpoints.

Membership creation accepts an exact existing `user_id`. A missing user returns validation/not-found without exposing the global user directory. The response contains membership identity, organization ID, user ID, role, status, and timestamps only.

### 17.7 Authorization rules

- `POST /api/organizations`: active authenticated user; creator becomes owner.
- list/read/me: current active membership only.
- list memberships: owner/admin.
- add viewer/scorer/coach/admin: owner/admin; an admin cannot create or modify an owner.
- assign, transfer, demote, disable an owner: owner only, with at least one other active owner when removing owner authority.
- modify own membership: the same role constraints apply; no self-removal as last owner.
- non-member/cross-tenant resource: tenant-safe not found.
- superuser bypass: explicit branch, tested and security logged; never inferred from `org_pro`.
- every service query includes the organization key; route-only checks are insufficient.

### 17.8 Required migration

Create one revision whose `down_revision` is the single head current when implementation begins. `upgrade()` creates the two tables, checks, unique constraint, FKs, and indexes. `downgrade()` drops only those new tables/indexes in dependency-safe order. The PR must fail its own preflight if another head appeared and must rebase/re-parent rather than create a merge head casually.

No data migration or backfill is permitted in 7B.

### 17.9 Required tests

At minimum:

1. create school atomically creates owner membership and does not alter the user's global role/plan/legacy `org_id`;
2. one user can own/member multiple schools with different membership roles;
3. unique `(organization_id, user_id)` is enforced on PostgreSQL;
4. non-member cannot list/read members or mutate the organization;
5. a member of School A cannot access a School B object even with its exact ID;
6. viewer/scorer/coach cannot manage memberships;
7. admin can manage non-owner roles but cannot grant/change/remove owner;
8. owner can manage roles, but final active owner cannot be demoted, disabled, or self-removed;
9. disabled membership has no access;
10. suspended/archived organization grants no normal access;
11. exact-user membership creation does not expose global user lists;
12. superuser behavior is explicit and audit logged;
13. transaction rollback leaves neither organization nor orphan membership when owner creation fails;
14. migration upgrade/downgrade/re-upgrade succeeds on real PostgreSQL and leaves one head;
15. existing auth/RBAC tests pass unchanged;
16. negative tests assert response bodies do not leak cross-tenant names, users, counts, or role data.

### 17.10 PostgreSQL validation requirements

Use an empty PostgreSQL database and a production-shaped database at the pre-7B head. Record:

- `alembic heads` shows one head before and after;
- upgrade to the new head succeeds;
- catalog inspection confirms FK delete actions, checks, unique constraint, and indexes;
- concurrent duplicate membership attempts yield one membership and one controlled conflict;
- downgrade to the prior revision succeeds without touching existing tables/data;
- clean re-upgrade succeeds;
- focused API/isolation tests pass against PostgreSQL, not an in-memory SQLite substitute.

### 17.11 CI commands

Run from repository root unless shown otherwise, using the repository's pinned environment:

```bash
pre-commit run --all-files
ruff check backend
ruff format --check backend
mypy backend

cd backend
alembic heads
alembic upgrade head
pytest -q tests/test_school_organizations.py tests/test_school_memberships.py tests/test_school_tenant_isolation.py tests/test_auth_basic.py tests/test_rbac_roles.py
alembic downgrade <pre_7b_revision>
alembic upgrade head
```

Also run the repository's existing CI workflow unchanged. If actual test filenames differ, the PR description must map each command to the required cases above. Do not weaken or skip CI to land the phase.

### 17.12 Rollout plan

1. Deploy additive migration with no legacy backfill.
2. Deploy API behind a server-controlled School foundation flag/default-off exposure if the existing deployment environment supports it; otherwise keep routes unlinked from UI until owner verification.
3. Create internal test organizations and verify audit/security telemetry.
4. Confirm two-tenant denial tests in the deployed environment.
5. Enable only for approved pilot users; no School Free entitlement is granted until 7C.

### 17.13 Rollback plan

- Disable/hide the new organization routes first.
- Roll back application code while leaving additive tables intact if any organization data exists.
- Downgrade the migration only when the tables are confirmed empty or after an approved export/recovery plan; the downgrade must not touch users or `User.org_id`.
- A cross-tenant authorization failure is an immediate disable/rollback condition.

### 17.14 Acceptance criteria

Phase 7B is complete only when:

- an authenticated user can create a school and becomes its owner atomically;
- the same user can belong to multiple organizations with independent roles;
- owners/admins can manage allowed memberships without changing any global role or subscription;
- last-owner, disabled-membership, inactive-organization, and all role boundaries are enforced;
- two-organization negative tests prove no cross-organization data leakage;
- no roster student login or player record is created by membership operations;
- no legacy `User.org_id` value is trusted or backfilled;
- the real-Postgres migration round trip and focused tests pass with one Alembic head;
- only the approved Phase 7B files changed;
- pricing, billing, teams, players, matches, scoring, DLS, results, historical import, analyst, and video systems remain byte-for-byte outside the PR.

### 17.15 Phase 7B readiness and owner decisions

**Readiness: READY.** The safe defaults above make Phase 7B independently implementable without a product decision.

The following approvals are required before their later phases, but do not block 7B:

- privacy/retention and minimum demographic fields for minor players before 7E/7G;
- approved XLSX parser/dependency and upload-size/retention limits before 7G;
- public-live-scorecard publication/privacy policy before 7J;
- controlled reconciliation policy for legacy `User.org_id` values before any backfill;
- provisioning owner for organization entitlements before 7C (administrative grant, billing integration, or another approved source).

## 18. Phase 7A completion criteria

- Current organizations, identity, RBAC, players, teams, match setup/XI, competitions, scoring boundaries, statistics, entitlements, imports, frontend, migrations, tests, and CI have repo evidence above.
- All fifteen architecture decisions required by Issue #519 are answered.
- Target data/API/authorization/entitlement/import contracts are specification-only.
- Migration order and real-Postgres gates are explicit.
- Phase 7B has an independent objective, allowlist, protected list, schema/API/auth contract, migration/test/CI/rollback plan, and acceptance criteria.
- No implementation, migration, dependency, workflow, pricing, billing, scoring, DLS, result, historical, analyst, or video change is part of Phase 7A.
