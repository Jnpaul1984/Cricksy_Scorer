# Anonymous public leaderboards

The public community leaderboard endpoint is a deliberately narrow projection of
final, explicitly public organization competition evidence. It has no persisted
leaderboard setting or player-publication setting.

## Eligibility and revocation

- The organization must be active and its community homepage published.
- A competition must belong to that organization and be explicitly published.
- A fixture must link the game to that competition.
- The game must be completed and `published_final`.
- Only participants from a frozen match side that explicitly declares the current
  organization are included; a fixture link does not authorize cross-tenant data.
- If the organization or competition is unpublished, rows disappear on the next
  request. Responses use `Cache-Control: no-store`.

## Response limits

- Only `rank`, a position-only `Participant N` label, and one integer total are
  emitted.
- Runs and wickets are capped at ten positive rows each, ordered by total then a
  hidden internal tie-breaker. Equal totals share a rank.
- No profile, roster, membership, team, fixture, competition, scorecard, or
  organization-private identifier is returned. Labels are not profile links or
  durable public handles.

## Privacy limit

This is pseudonymous display, not a claim that the underlying statistic is
anonymous in every context. A small community may still infer a participant from
an unusual exact result and outside knowledge. The endpoint minimizes metadata and
does not publish names, avatars, identifiers, or profile discovery; a future
governed naming policy is required before any junior or school name can appear.
