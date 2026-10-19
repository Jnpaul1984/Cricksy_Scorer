#!/usr/bin/env bash
# Fail closed when the ECR API response is not an array of supported finding objects.
set -euo pipefail

jq -er '
  def valid_finding:
    type == "object"
    and (.severity | type == "string")
    and (.attributes | type == "array")
    and all(.attributes[];
      type == "object"
      and (.key | type == "string")
      and (.value | type == "string"))
    and ([.attributes[] | select(.key == "package_name") | .value] | length == 1)
    and ([.attributes[] | select(.key == "package_name") | .value][0] | length > 0);
  def non_kernel:
    ([.attributes[] | select(.key == "package_name") | .value][0] != "linux");
  if type != "array" then error("ECR findings must be an array")
  elif all(.[]; valid_finding) | not then error("ECR findings contain an unsupported finding shape")
  else
    [ .[] | select(non_kernel) ] as $non_kernel
    | {high: [$non_kernel[] | select(.severity == "HIGH")] | length,
       critical: [$non_kernel[] | select(.severity == "CRITICAL")] | length}
    | "Non-kernel HIGH count: \(.high)\nNon-kernel CRITICAL count: \(.critical)" as $summary
    | if ($summary | test("HIGH count: [1-9]|CRITICAL count: [1-9]")) then
        $summary, "::error::Build failed due to non-kernel HIGH/CRITICAL vulnerabilities.", error("blocking ECR findings")
      else
        $summary, "No blocking non-kernel vulnerabilities found."
      end
  end
'
