# Phase 10J.18A Performance Baseline Runbook

This runbook captures deployed Coach Pro Plus latency evidence. It is a measurement procedure,
not an instruction to optimize or change production behavior.

## Before the test

1. Use a deployed production-like environment and a Coach Pro Plus account with one completed
   video-analysis session, a reviewable plan, and PDF export enabled.
2. Open browser developer tools, preserve the Console and Network logs, and filter the Console for
   `[coach-performance]`.
3. Open the backend structured-log viewer and filter for `event=coach_performance` (or the JSON
   event value `coach_performance`).
4. Record the deployment/commit, browser, device class, connection type, region, date, and UTC time.

## Test sequence

Perform each action once for a cold observation, then three times for warm observations:

1. Open the Coach Pro Plus video sessions landing page and wait for the session list to render.
2. Open a completed session and wait for its analysis history to render.
3. Open **Analysis Results** and wait for the V2 report to render. The completed-session history
   response already carries the V2 report, so its request timing is shared and the modal emits one
   separate `analysis_results` render timing.
4. Submit one permitted coach review/approval action.
5. Request the PDF and allow the browser to hand the returned URL to its download/open behavior.

Do not upload a video or repeatedly trigger actions merely to create more samples.

## Evidence and correlation

Frontend Console events contain the operation, phase, duration in milliseconds, outcome/status,
safe response byte size when `Content-Length` is present, item count for measured renders, and the
response `request_id`. Backend events contain the same operation, total handler duration,
outcome/status, list item count where applicable, and exact generated PDF bytes for export.

To correlate one action, copy `request_id` from the frontend request event and find the backend
`coach_performance` event with the same request ID. The existing request middleware creates and
echoes this identifier. It is opaque and contains no player or report data. If a proxy removes the
response header, correlate the operation and UTC timestamp window and record that limitation.

The `pdf_download` frontend event measures only the browser download handoff. Browser/object-store
transfer completion is not claimed because that boundary is not reliably observable here.

## Phase 10J.18B capture sheet

For every sample, record:

- operation and cold/warm label;
- frontend request duration and backend handler duration;
- frontend render or download-handoff duration when emitted;
- HTTP status/outcome and request ID;
- response bytes or item count when emitted;
- environment metadata listed above;
- median, minimum, maximum, and sample count for each operation;
- any reproducible gap between frontend and backend time.

Do not include player names, session/job/plan IDs, report text, URLs, tokens, video data, or request
and response bodies in the capture sheet.

## Interpretation guardrails

Do not classify a single outlier, cold start, developer-tools overhead, slow client render, network
delay, or object-storage download time as an application defect without repeated measurements that
isolate the relevant layer. A large frontend/backend gap is evidence to investigate the network or
client boundary; it does not by itself identify a backend defect. Missing payload bytes means the
response did not expose a safe size header, not that the payload was empty.
