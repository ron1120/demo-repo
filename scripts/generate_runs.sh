#!/usr/bin/env bash
# Dispatch simulated CI runs so there are real failed runs to triage.
# Usage: scripts/generate_runs.sh [runs_per_scenario]   (default 3 -> 12 failing + 3 passing)
# Do not re-run the flaky runs afterwards: a re-run overwrites the failed conclusion.
set -euo pipefail

COUNT="${1:-3}"
command -v gh >/dev/null || { echo "gh CLI is required (https://cli.github.com)"; exit 1; }

for scenario in real_bug flaky infra_timeout dependency_missing none; do
  for _ in $(seq "$COUNT"); do
    gh workflow run ci.yml -f scenario="$scenario"
  done
done

echo "Dispatched. Watch progress with: gh run list --workflow ci.yml"
