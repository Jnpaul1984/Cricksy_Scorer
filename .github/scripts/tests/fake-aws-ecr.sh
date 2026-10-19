#!/usr/bin/env bash
# Simulates a COMPLETE scan whose second findings page contains the reported HIGHs.
set -euo pipefail
: "${FAKE_AWS_STATE_FILE:?FAKE_AWS_STATE_FILE is required}"
call=0
if [ -f "$FAKE_AWS_STATE_FILE" ]; then call="$(cat "$FAKE_AWS_STATE_FILE")"; fi
call=$((call + 1))
printf '%s' "$call" > "$FAKE_AWS_STATE_FILE"

case "$call" in
  1) printf '%s\n' '{"imageScanStatus":{"status":"COMPLETE"}}' ;;
  2) printf '%s\n' '{"imageScanFindings":{"findings":[{"name":"CVE-low","severity":"LOW","attributes":[{"key":"package_name","value":"curl"}]}]},"nextToken":"second-page"}' ;;
  3) if [ "${FAKE_AWS_MODE:-block}" = repeat-token ]; then printf '%s\n' '{"imageScanFindings":{"findings":[]},"nextToken":"second-page"}'; else printf '%s\n' '{"imageScanFindings":{"findings":[{"name":"CVE-2026-85091","severity":"HIGH","attributes":[{"key":"package_name","value":"zlib1g"}]},{"name":"CVE-2026-5435","severity":"HIGH","attributes":[{"key":"package_name","value":"libc6"}]},{"name":"CVE-2026-19499","severity":"HIGH","attributes":[{"key":"package_name","value":"libc6"}]},{"name":"CVE-2026-107161","severity":"HIGH","attributes":[{"key":"package_name","value":"libsasl2-2"}]}]}}'; fi ;;
  *) echo "unexpected fake AWS invocation: $call" >&2; exit 1 ;;
esac
