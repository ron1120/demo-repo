# demo-app

A tiny app the `CI` workflow tests. The workflow's `case` input switches on a specific failure, which gives
the triage agent real failed runs to diagnose. The case codes are neutral on purpose (see the root README).

Locally: `CASE=case_a pytest` (and `GITHUB_RUN_ATTEMPT=1 CASE=case_b pytest` for case_b).
