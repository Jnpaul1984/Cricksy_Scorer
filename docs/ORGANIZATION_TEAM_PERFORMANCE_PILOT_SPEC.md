# Organization Team Performance Staff Pilot — Locked Scope

This document locks the bounded scope for issue #626 before implementation. It authorizes a private, read-only School/Club Team Performance pilot surface only. It does not authorize enabling access for any real organization, changing existing permissions or Free entitlements, billing, credential creation, deployment, or any later product expansion.

## Product contract

- Add one private Team Performance view inside the existing organization workspace. It applies equally to School and Club organizations.
- An authorized staff member selects one Team owned by the current organization (including an archived Team, clearly labelled) and one exact overs limit from 1 through 120.
- Analyze all matching recorded history: official, completed, limited-overs games with the selected format and exact overs limit. DLS-marked and shortened recorded innings remain eligible; no result or missing delivery is inferred.
- Display aggregate batting and bowling cards plus a coverage panel. Batting includes team and bat runs, wickets lost, legal balls/overs, run rate, legal dots, extras, and recorded fours/sixes. Bowling includes opposition team runs conceded, bowler-charged runs, team concession rate, bowling economy, team wickets, and bowler-credited wickets. Use aggregate ratios; undefined denominators display a dash. Eleven legal balls display as 1.5 overs.
- Team runs per wicket is not a player batting average. Do not expose player-level rows, identities, contact data, notes, deliveries, public projections, or exports.
- Always show: **“Based on recorded delivery data. Historical completeness has not been verified.”**

## Access and default-off authority

- Keep `school_free`/`club_free` entitlement records, capability sets, and their current resolver/API unchanged. `school_basic_statistics` is not authorization for this pilot.
- Add an independent `organization_team_performance` grant, default absent. A grant records its organization, validity start/end, granting operator, reason, and lifecycle status; revocation records its operator, time, and reason. Grant/revoke domain operations are idempotent and audit-ready. There is no public grant-management endpoint and no self-upgrade path.
- Do not seed, bootstrap, or create a production grant. Operational grant authority and actual pilot organizations remain owner decisions.
- On every read request, verify the active authenticated user, active organization, active organization membership, approved contextual role (`owner`, `admin`, or `coach`), current active grant and its validity, and exact Team ownership before calculation. Scorers and viewers are excluded. Personal subscriptions, `User.org_id`, creator/global roles, and superuser status never substitute for these checks.
- A user without active organization membership receives the existing non-disclosing organization 404. An authorized member with an unapproved role or no active pilot grant receives 403. An authorized member supplying a foreign/nonexistent Team receives a non-disclosing 404. A missing, future, expired, or revoked grant denies access.
- Revalidate membership, role, organization, grant, and Team for every request; client-side route hiding is not authorization.

## Analysis and response boundary

- Preserve the existing atomic malformed-game/innings exclusions, frozen-side and same-organization boundaries, dismissal validation, DLS/shortened-innings behavior, weighted aggregate rates, and 3/99-innings regression coverage.
- Keep ordinary cohort exclusions distinct from invalid/missing-data warnings. Coverage reports eligible/included game counts, usable batting/bowling innings, used rows, and distinct excluded game/innings counts. Never infer a completeness percentage; usable bowling does not imply usable batting.
- The API response is a typed allowlist of aggregate metrics, selected scope, and safe coverage only. Do not return source game IDs, innings attribution IDs, exclusion game/innings identifiers, raw deliveries, player identity/contact data, notes, public projections, or export links.
- Bound query/response workload. If the eligible cohort exceeds a configured hard limit, reject explicitly with a scope-too-large response; never silently truncate history.
- Distinguish unavailable access, loading, no eligible games, no usable ledger, usable data with exclusions, usable recorded data, request failure, and explicit scope-too-large states. Do not allow stale organization/team/format results to replace current state; clear protected data on organization/team/format changes, logout, or access loss.

## Explicit non-goals

No changes to scoring, DLS, results, personal plans, billing, existing Free statistics, public surfaces, or existing permissions. No recent-form chronology, phases, comparisons, AI, exports, checkout, real-organization grant, or deployment is in this slice.

## Verification gate

Test School/Club parity; owner/admin/coach versus scorer/viewer; missing/future/active/expired/revoked grant lifecycle; inactive/removed memberships and organizations; direct API access; cross-organization Team/player/opponent isolation; idempotent audited grant/revoke; existing 3/99-innings and unknown-dismissal regressions; weighted rates, zero denominators, and 11-ball overs; safe response serialization; UI switching, stale responses, access loss, coverage and error states; and PostgreSQL migration/security behavior. Run repository-configured lint, type, build, unit, and E2E gates where available. Parent review and exact-head CI are required before any approved merge/deployment.
