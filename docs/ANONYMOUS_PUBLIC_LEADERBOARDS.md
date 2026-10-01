# Anonymous public leaderboards

The public leaderboard is a narrow projection of completed, explicitly public
organization competition evidence. It has no player-publication setting.

- The organization homepage and competition must both be published.
- The game must be completed and `published_final`.
- Frozen match sides must explicitly claim the organization; a fixture link alone
  never authorizes cross-tenant data.
- Revocation removes rows on the next request; responses use `Cache-Control: no-store`.
- Only rank, a position-only `Participant N` label, and an integer total are emitted.
  Runs and wickets each have at most ten positive rows.

No names, profiles, roster memberships, identifiers, or navigation links are returned.
Small communities may still infer a participant from an unusual result and outside
knowledge; this is a minimized pseudonymous display, not a naming-policy approval.
