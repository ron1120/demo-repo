# demo-app

A tiny app the `CI` workflow tests. The workflow can be told which kind of failure to produce (see the
scenario table in the root README), which gives the triage agent real failed runs to diagnose.

Locally: `SCENARIO=real_bug pytest` (and `GITHUB_RUN_ATTEMPT=1 SCENARIO=flaky pytest` for the flaky one).
