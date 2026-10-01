# Block 4C sponsor governance

The first slice has exactly one eligible surface: the published public organization homepage. School and Club organization staff with an active contextual `owner` or `admin` membership may propose a sponsor. They cannot approve it.

Only a Cricksy platform administrator (`User.is_superuser`) may approve, and the proposing account cannot approve its own proposal. A platform administrator may immediately take down any approved placement. Every proposal, approval and takedown creates a durable audit record; takedown never deletes prior evidence and ends public display immediately.

There is no ad-network, payment, revenue share, impression reporting, private-data targeting, junior/private-space placement, or private-data sponsor access. The organization must itself be publicly published for its approved placement to be returned.

Jason approved exactly four initial sponsor categories: `sports-equipment`, `education`, `ordinary-food-businesses`, and `local-services`. Every individual sponsor in one of those categories still requires mandatory Cricksy platform approval; organization staff can only propose. All other categories are denied by default. `ordinary-food-businesses` and `local-services` do not imply approval for regulated, age-restricted, financial, medical, gambling, alcohol, tobacco, political, or other legally sensitive businesses; those remain denied unless the owner explicitly makes a future policy decision.

`CRICKSY_SPONSOR_PLACEMENTS_ENABLED` remains `false` by default, so this approved category policy does not itself enable public placement. The public endpoint sends `Cache-Control: no-store, max-age=0`; server-side takedown excludes every new request immediately, while an already open public page checks again within 30 seconds. Jason explicitly accepted that bounded first-release takedown behavior; it is not an instantaneous-client-display claim and does not authorize production release.

Visibility is also a persisted, platform-superuser-only three-gate control: global, School/Club organization, and individual sponsor placement. Each gate defaults off and each mutation is audited. Re-enabling a gate does not approve a proposal, publish an organization, override category policy or the environment emergency backstop, or revive a placement that was taken down.

## Block 4D pilot reporting boundary

`CRICKSY_SPONSOR_AGGREGATE_REPORTING_ENABLED` is a separate default-`false` gate and does not enable placement display. When it is explicitly enabled for a pilot, public clients may submit only a random one-event UUID, the approved placement id, and `display` or `click`. The service never accepts or stores a viewer account, player/child data, IP address, user agent, cookie, device id, location, referrer, targeting data, payment data, or revenue data.

Events count only while the placement is currently approved, visible through all three gates, category-allowed, feature-enabled, and on a published public organization homepage. A per-placement in-memory 60/minute limit, one-event UUID de-duplication, a 20-day? No: UUID nonces are retained for **two days only** solely to reject replay; the durable data is one School/Club + approved placement + UTC date aggregate with display and click totals. This is reporting, not ad targeting or monetization.

Current Owner/Admin staff may read only their own organization’s still-approved placement aggregates in a bounded 31-day date range. Platform superusers have aggregate oversight. Takedown, unpublish, a visibility-gate closure, policy disablement, or removal of approval blocks new events immediately and removes that placement from reports. This slice does not determine any legal consent requirement; pilot legal/privacy review remains a release blocker.
