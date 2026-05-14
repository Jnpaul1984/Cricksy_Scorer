# Frontend E2E Coverage Matrix

This document defines the browser-level E2E validation gate status for every major Cricksy UI workspace.

Maintained as part of the frontend testing standard introduced in Phase 5O.1 and expanded in the Frontend E2E Validation Expansion issue.

---

## Coverage Matrix

| Workspace / Area | Route(s) | Current E2E Coverage | Required Smoke Test | Required Regression Tests | CI Gate Name | Priority |
|---|---|---|---|---|---|---|
| **Analyst Workspace** | `/analyst/workspace`, `/analyst/match/:matchId` | ✅ `analyst_workspace_data_library.cy.ts` — covers Data Library search, filter, sort, detail navigation, empty state, error state | ✅ In place | Add: deep session filter, AI tab, registry panel | `test:e2e:analyst` | **P0 — Done** |
| **Scoring / Game Scoring** | `/game/:gameId/scoring`, `/setup`, `/game/:gameId/select-xi` | ⚠️ Partial — `match_creation_flow.cy.ts`, `scoring_gate_smoke.cy.ts`, `wicket_new_batter_flow.cy.ts`, `next_over_flow.cy.ts`, `innings_flip_flow.cy.ts`, `weather_interruption_flow.cy.ts` require a live backend | Add intercept-only smoke: page load, scoring console disabled when game over | Add: delivery submission, extras, wickets, DLS interruption | `test:e2e:scoring` | **P1** |
| **Live Scoreboard / Viewer** | `/view/:gameId`, `/embed/:gameId` | ⚠️ Partial — `ci_match_simulator.cy.ts` exercises viewer but requires a live backend | Add intercept-only smoke: scoreboard renders result banner, score, overs | Add: live update, embed iframe render | `test:e2e:viewer` | **P1** |
| **Coach Workspace / Coach Dashboard** | `/coaches`, `/coach/dashboard` | ✅ `coach_workspace_smoke.cy.ts` — covers page load, header, no-match state, quick links | ✅ In place | Add: active match card render, video sessions link | `test:e2e:coach` | **P1 — Done** |
| **Coach Pro Plus Video Sessions** | `/coaches/video-sessions` | ❌ No E2E coverage | Add intercept-only smoke: page loads, session list renders | Add: session detail, playback controls | `test:e2e:coach` | **P2** |
| **Historical Import / Upload flows** | Via `HistoricalImportPanel.vue` component (embedded in Analyst Workspace) | ❌ No dedicated E2E coverage | Add intercept-only smoke: upload panel opens, dry-run response renders | Add: apply flow, rollback, error states | `test:e2e:import` | **P2** |
| **Match Case Study / Analyst Detail** | `/analyst/match/:matchId` | ⚠️ Partial — covered via analyst workspace Data Library "View" navigation in `analyst_workspace_data_library.cy.ts` | Full standalone smoke: page load with stubbed case study data | Add: phase breakdown, key players, AI summary panel | `test:e2e:analyst` | **P2** |
| **Player Profile** | `/player/:playerId`, `/players/:playerId/profile` | ❌ No E2E coverage | Add intercept-only smoke: page loads, player header renders | Add: batting/bowling stats, career summary | `test:e2e:admin` | **P2** |
| **Admin / Org / Team Management** | `/admin/beta-users`, `/org-management`, `/teams` | ❌ No E2E coverage | Add intercept-only smoke: admin page loads, user list renders | Add: add/remove user, team CRUD | `test:e2e:admin` | **P2** |
| **Auth / Login** | `/login` | ❌ No dedicated E2E coverage (auth is stubbed in all other specs via `visitWithAuth`) | Add smoke: login form renders, email/password fields present, submit redirects | Add: failed login, remember me, redirect-after-login | `test:e2e:smoke` | **P1** |

---

## Coverage Summary

| Status | Count |
|--------|-------|
| ✅ In place | 2 (Analyst Workspace, Coach Dashboard) |
| ⚠️ Partial / requires live backend | 3 (Scoring, Viewer, Match Case Study) |
| ❌ No coverage | 5 (Video Sessions, Import, Player Profile, Admin, Auth/Login) |

---

## Suite Definitions

Suites map to `npm run test:e2e:<suite>` or `node ./scripts/run-e2e.mjs --suite <suite>`.

| Suite name | Specs included | Requires live backend? | Used in CI? |
|---|---|---|---|
| `analyst` | `analyst_workspace_data_library.cy.ts` | No — intercepts only | ✅ Yes (`frontend-analyst-e2e` job) |
| `coach` | `coach_workspace_smoke.cy.ts` | No — intercepts only | ✅ Yes (`frontend-coach-e2e` job) |
| `smoke` | `analyst_workspace_data_library.cy.ts`, `coach_workspace_smoke.cy.ts` | No — intercepts only | ✅ Yes (runs both gates) |
| `scoring` | `scoring_gate_smoke.cy.ts`, `match_creation_flow.cy.ts`, `next_over_flow.cy.ts`, `wicket_new_batter_flow.cy.ts`, `innings_flip_flow.cy.ts`, `weather_interruption_flow.cy.ts` | **Yes** — requires seeded backend | Run on demand / full-stack CI only |
| `import` | _(not yet implemented)_ | No — intercepts only | Follow-up |
| `admin` | _(not yet implemented)_ | No — intercepts only | Follow-up |

---

## Future Feature Rule

For any PR that changes frontend behavior in a major workspace, the PR **must** either:

1. Add or update the relevant E2E spec for that workspace, **or**
2. Explain in the PR description why unit/component tests are sufficient for that specific change, **or**
3. Document why E2E coverage is intentionally deferred with a follow-up issue linked in the PR.

This rule applies to all workspaces listed above.

---

## Follow-up Issues Required

The following areas have no E2E coverage and should each have a dedicated follow-up issue:

- [ ] **FE-E2E-001** — Auth/Login smoke E2E gate (`/login` form renders, submit behaviour)
- [ ] **FE-E2E-002** — Coach Pro Plus Video Sessions smoke E2E gate (`/coaches/video-sessions`)
- [ ] **FE-E2E-003** — Historical Import / Upload flow smoke E2E gate (via `HistoricalImportPanel.vue`)
- [ ] **FE-E2E-004** — Player Profile smoke E2E gate (`/player/:playerId`)
- [ ] **FE-E2E-005** — Admin / Org / Team Management smoke E2E gate (`/admin/beta-users`, `/org-management`, `/teams`)
- [ ] **FE-E2E-006** — Convert scoring and viewer specs to use intercept-only mode so they can run without a live backend in CI

---

## Data Strategy

All CI-eligible E2E specs must:

- Use **Cypress `cy.intercept()`** to stub API responses — never call a real backend in CI.
- Store fixture data only in `frontend/cypress/fixtures/` or inline in the spec file.
- Never introduce mock/fake data into production services, stores, or API paths.
- Use `cy.visitWithAuth()` (defined in `frontend/cypress/support/commands.ts`) to fake authentication.

Specs that require a live backend (e.g., scoring flows) should be run in a separate full-stack CI job or on demand locally.
