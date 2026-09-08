# Phase 10J.18B Completed Session Latency and PDF Responsiveness

## Production evidence

Phase 10J.18A observed completed-session frontend request samples of approximately 422 ms,
1.14 s, 1.20 s, and 4.54 s, with earlier samples of approximately 5.3 s, 6.4 s, and 10.9 s.
Matching AWS handler samples were approximately 15–31 ms and visible Vue rendering was
approximately 1–4 ms. The evidence therefore does not support changing the already-fast backend
handler or render path. The remaining request-versus-handler gap crosses response transfer and JSON
consumption and cannot be attributed more narrowly without post-deploy correlation and payload-size
evidence.

The completed-session UI also awaited player-development plan lookups before clearing its visible
loading gate. Those lookups could return 403 for legacy or unassigned player IDs and were repeated
whenever the session was opened. The plans route correctly enforces active coach/organization
assignment, so the denied response was an incorrectly attempted dependency, not an authorization
defect.

PDF export returned 409 while deep analysis was running. The backend intentionally permits export
only for `done` or `completed` jobs, so this is an availability state and a possible completion race,
not evidence of a PDF generation defect. Successful frontend PDF requests were approximately
1.24–1.57 s while matching backend work was approximately 160–740 ms.

## Minimum fix

- Completed-session history now clears the loading gate and records visible rendering immediately
  after the primary history response; recommendation lookup continues as non-blocking enrichment.
- Recommendation lookups are limited to the active assigned-player list already authorized for the
  current coach or organization. Backend authorization is unchanged, and a failed assignment check
  prevents the optional plan request.
- Both PDF entry points enable export only for `done` or `completed` jobs. An active deep analysis is
  presented as "not ready yet," and an unavoidable 409 completion race receives the same clear
  treatment.
- Phase 10J.18A telemetry and its non-blocking failure behavior are unchanged.

No response-contract, backend-handler, database, worker, model, CV, or PDF architecture change was
required.

## Focused validation

- The Coach Pro Plus view test covers a history render that does not wait for recommendation plans,
  suppression of a plan request for an unassigned player, the deep-running PDF disabled state, and
  the friendly 409 race message.
- Existing backend route tests confirm player-plan authorization remains enforced and PDF export
  remains unavailable for `deep_running` and `quick_done` jobs.
- Existing telemetry tests confirm measurement remains non-blocking.
- Frontend type-check and changed-file checks cover the modified surface.

## Post-deploy comparison

Repeat the Phase 10J.18A cold/warm sequence on the deployed fix. Correlate frontend and backend
events with `X-Request-ID` and record completed-session request/body duration, backend handler
duration, visible render duration, safe response bytes when available, recommendation-plan request
count and 403 count, and PDF status/duration for both a deep-running and a completed job. Compare
the same sample counts and environment metadata with the baseline, and specifically verify that the
history becomes visible before optional recommendation enrichment finishes. Do not infer or record
post-fix production numbers until this deployed comparison is performed.
