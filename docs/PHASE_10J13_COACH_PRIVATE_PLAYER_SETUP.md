# Phase 10J.13 — Coach-Private Player Setup & Match Setup Decoupling

Issue #501 is implemented as an additive Coach Pro Plus workflow. Match Setup remains a separate, unchanged match-scoring workflow.

## Audit and reuse decisions

- The Coach Pro Plus player selector loaded `CoachPlayerAssignment` records, then fetched each `PlayerProfile`, but sent coaches to `/setup` to create a player. That link was the Match Setup coupling.
- `PlayerProfile` is already the canonical identity used by Video Sessions, Player Development, coaching assignments, and longitudinal progress. `CoachPlayerAssignment` already supplies coach ownership and has a unique coach/player index. No parallel identity or CRUD model was added.
- The only existing DOB field belongs to a competition current-season roster. Reusing it would require competition/team context, so the canonical `PlayerProfile` gained one nullable `date_of_birth` column instead.

## Implemented flow

- `GET /api/coaches/plus/players` returns deduplicated active-assignment profiles scoped to the authenticated coach, organization, or superuser.
- `POST /api/coaches/plus/players` creates a `PlayerProfile` and active `CoachPlayerAssignment` for the authenticated user in one transaction.
- Name and DOB are optional. Blank names receive `Test Player <unique suffix>`; future DOB values are rejected.
- The Video Session modal now contains a small “Add coaching player” form. Successful creation refreshes the selector and automatically selects the new profile.
- No team, club, match, game, player login, email, or parent record is created or required.

## Compatibility and isolation

- Coach Pro Plus sees only direct active assignments. `org_pro` sees active assignments made by users in the same organization. Cross-coach and cross-organization access remains denied by the existing Video Session, Player Development, and longitudinal guards.
- Existing assigned/team-derived `PlayerProfile` records continue through the same selector and APIs.
- V2 result contracts, goals/interventions, camera and discipline prerequisites, legacy playerless Video Sessions, and `/setup` Match Setup code are unchanged.

## Migration and rollback

Migration `20260905103000` adds only nullable `player_profiles.date_of_birth` and descends from the existing single head. Its downgrade removes that column. Application rollback consists of reverting the new Coach Plus player endpoints/UI and downgrading one revision; no existing profile, assignment, Video Session, or Match Setup schema is otherwise changed.
