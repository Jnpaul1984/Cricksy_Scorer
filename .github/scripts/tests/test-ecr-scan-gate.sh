#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
gate="$root/check-ecr-scan-findings.sh"
fixtures="$(dirname -- "${BASH_SOURCE[0]}")/fixtures"
expect_block() { if "$gate" < "$fixtures/$1"; then echo "expected $1 to block" >&2; exit 1; fi; }
expect_pass() { "$gate" < "$fixtures/$1"; }
expect_block four-high.json
expect_block critical.json
expect_pass clean.json
expect_pass kernel-only.json
expect_block malformed.json
expect_block missing-package-name.json
expect_block duplicate-package-name.json
workflow="$root/../workflows/deploy-backend.yml"
grep -Fq 'bash .github/scripts/verify-ecr-image-scan.sh' "$workflow"
! grep -Fq '2>/dev/null || echo 0' "$workflow"
grep -Fq 'bash .github/scripts/tests/test-ecr-scan-gate.sh' "$root/../workflows/ecr-scan-gate.yml"
bash -n "$root/check-ecr-scan-findings.sh" "$root/verify-ecr-image-scan.sh"
state_file="$(mktemp)"
trap 'rm -f "$state_file"' EXIT
if ECR_REPOSITORY=test AWS_REGION=us-east-1 IMAGE_TAG=test SCAN_POLL_SECONDS=0 AWS_BIN="$root/tests/fake-aws-ecr.sh" FAKE_AWS_STATE_FILE="$state_file" "$root/verify-ecr-image-scan.sh"; then
  echo "expected the paginated workflow verifier to block" >&2
  exit 1
fi
test "$(cat "$state_file")" = 3

# A valid low-only ECR findings page larger than Linux's common 128 KiB argv
# floor must still pass: the verifier must not feed it to jq as an argument.
: > "$state_file"
if ! ECR_REPOSITORY=test AWS_REGION=us-east-1 IMAGE_TAG=test SCAN_POLL_SECONDS=0 AWS_BIN="$root/tests/fake-aws-ecr.sh" FAKE_AWS_MODE=large-clean FAKE_AWS_STATE_FILE="$state_file" "$root/verify-ecr-image-scan.sh" >/dev/null; then
  echo "expected the large clean findings page to pass" >&2
  exit 1
fi
test "$(cat "$state_file")" = 2

expect_guard_failure() {
  local mode="$1" expected_error="$2" expected_calls="$3"
  shift 3
  : > "$state_file"
  local output
  if output="$(env "$@" ECR_REPOSITORY=test AWS_REGION=us-east-1 IMAGE_TAG=test SCAN_POLL_SECONDS=0 AWS_BIN="$root/tests/fake-aws-ecr.sh" FAKE_AWS_MODE="$mode" FAKE_AWS_STATE_FILE="$state_file" "$root/verify-ecr-image-scan.sh" 2>&1)"; then
    echo "expected $mode verifier guard to block" >&2
    exit 1
  fi
  grep -Fq "::error::$expected_error" <<<"$output" || { echo "wrong $mode verifier failure: $output" >&2; exit 1; }
  test "$(cat "$state_file")" = "$expected_calls" || { echo "wrong $mode fake AWS call count" >&2; exit 1; }
}

expect_guard_failure repeat-token 'ECR findings pagination repeated a nextToken' 3
expect_guard_failure page-cap 'ECR findings exceeded page limit' 2 MAX_SCAN_PAGES=1
expect_guard_failure byte-cap 'ECR findings exceeded size limit' 2 MAX_FINDINGS_BYTES=1
echo "ECR scan gate fixtures and workflow integration passed"
