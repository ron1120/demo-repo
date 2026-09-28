#!/usr/bin/env bash
# Dispatch demo CI runs so there are real failed runs to triage.
# Usage: scripts/generate_runs.sh [runs_per_case]   (default 3 -> 12 failing + 3 passing)
# Do not re-run failed case_b runs afterwards: a passing re-run overwrites the failed conclusion.
set -euo pipefail

COUNT="${1:-3}"
command -v gh >/dev/null || { echo "gh CLI is required (https://cli.github.com)"; exit 1; }

for case in case_a case_b case_c case_d none; do
  for _ in $(seq "$COUNT"); do
    gh workflow run ci.yml -f case="$case"
  done
done

echo "Dispatched. Watch progress with: gh run list --workflow ci.yml"
