#!/usr/bin/env bash
# Poll and collect every ECR scan page before applying the vulnerability policy.
set -euo pipefail
: "${ECR_REPOSITORY:?ECR_REPOSITORY is required}"
: "${AWS_REGION:?AWS_REGION is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
aws_bin="${AWS_BIN:-aws}"
poll_seconds="${SCAN_POLL_SECONDS:-10}"
max_pages="${MAX_SCAN_PAGES:-100}"
max_findings_bytes="${MAX_FINDINGS_BYTES:-10485760}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

for attempt in $(seq 1 30); do
  status_json="$("$aws_bin" ecr describe-image-scan-findings --repository-name "$ECR_REPOSITORY" --image-id "imageTag=$IMAGE_TAG" --region "$AWS_REGION" --no-paginate --output json)"
  status="$(jq -er '.imageScanStatus.status | if type == "string" then . else error("missing scan status") end' <<<"$status_json")" || { echo "::error::Unable to parse ECR image scan status" >&2; exit 1; }
  echo "Attempt $attempt: Scan status is $status"
  case "$status" in
    COMPLETE) break ;;
    FAILED) echo "::error::ECR image scan failed" >&2; exit 1 ;;
    IN_PROGRESS|PENDING) ;;
    *) echo "::error::Unexpected ECR image scan status: $status" >&2; exit 1 ;;
  esac
  if [ "$attempt" -eq 30 ]; then echo "::error::ECR image scan did not complete in time" >&2; exit 1; fi
  sleep "$poll_seconds"
done

all_findings='[]'
next_token=''
page_count=0
declare -A seen_tokens=()
while :; do
  page_count=$((page_count + 1))
  if [ "$page_count" -gt "$max_pages" ]; then echo "::error::ECR findings exceeded page limit" >&2; exit 1; fi
  if [ -n "$next_token" ]; then
    if [[ -v "seen_tokens[$next_token]" ]]; then
      echo "::error::ECR findings pagination repeated a nextToken" >&2
      exit 1
    fi
    seen_tokens["$next_token"]=1
  fi
  args=(ecr describe-image-scan-findings --repository-name "$ECR_REPOSITORY" --image-id "imageTag=$IMAGE_TAG" --region "$AWS_REGION" --no-paginate --output json)
  if [ -n "$next_token" ]; then args+=(--next-token "$next_token"); fi
  page_json="$("$aws_bin" "${args[@]}")"
  page_findings="$(jq -ce '.imageScanFindings.findings | if type == "array" then . else error("missing findings array") end' <<<"$page_json")" || { echo "::error::Unable to parse ECR findings page" >&2; exit 1; }
  # Keep pages out of argv: valid ECR pages can exceed the OS argument limit.
  all_findings="$(jq -ce -s '.[0] + .[1]' <(printf '%s\n' "$all_findings") <(printf '%s\n' "$page_findings"))" || exit 1
  if [ "$(printf '%s' "$all_findings" | wc -c)" -gt "$max_findings_bytes" ]; then echo "::error::ECR findings exceeded size limit" >&2; exit 1; fi
  next_token="$(jq -er 'if .nextToken == null then "" elif (.nextToken | type) == "string" and (.nextToken | length) > 0 then .nextToken else error("invalid nextToken") end' <<<"$page_json")" || { echo "::error::Unable to parse ECR findings pagination token" >&2; exit 1; }
  [ -n "$next_token" ] || break
done
echo "Full scan findings (all pages):"
printf '%s\n' "$all_findings"
printf '%s\n' "$all_findings" | "$script_dir/check-ecr-scan-findings.sh"
