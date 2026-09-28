# CI Triage Agent

Diagnoses failed GitHub Actions runs and posts the result to Slack. Given a failed run, it says whether
the cause is a real code failure, a flaky test, an infra failure, or a dependency/environment issue,
with a confidence level, verbatim log evidence and a suggested next step. Read-only: it never reruns,
edits or deploys anything.

```
.github/workflows/ci.yml      The pipeline being triaged. A `case` input switches on each failure type.
.github/workflows/triage.yml  Fires when CI fails: runs the agent and posts to Slack.
demo-app/                     Small app the CI workflow tests.
triage/                       The agent: log cleanup, redaction, excerpting, rules, model call, GitHub, Slack, eval.
samples/                      8 synthetic labelled logs (2 per category).
scripts/generate_runs.sh      Dispatches demo runs to produce real failed runs.
tests/                        Offline tests (fake model client, fake GitHub session, fake webhook).
```

## How a diagnosis works

1. `CI` fails. GitHub fires `triage.yml` (`workflow_run`, only when the conclusion is `failure`).
2. The agent fetches the failed jobs' logs through the API. It does **not** check out the failed run's code.
3. Timestamps and ANSI codes are stripped, then **secrets are redacted** on the full text.
4. **Rules** catch unambiguous cases (network timeout, disk full, unresolvable package, ...). A
   high-confidence rule answers directly, with no model call.
5. Otherwise an **excerpt** (error lines with context plus the tail, at most 12k chars) goes to the
   model with run metadata and any rule hint. The model returns structured JSON.
6. Anything unclear, refused, truncated or unparseable becomes `needs_human_review`.
7. The result is posted to Slack with the evidence, next step and a link to the run.
8. The full record (run metadata plus the diagnosis, and for model answers the model name and token
   counts) is printed to the triage run's log and saved as an artifact named `diagnosis-<run id>` on
   that run. It is saved before posting, so it survives a Slack failure.

Log text is treated as untrusted input, and so is anything derived from it. The system prompt tells the
model never to follow instructions found in a log, and Slack output is escaped so a log cannot inject
mentions (`<!channel>`) or links.

## Set it up on GitHub

1. Push this directory as the root of a GitHub repo.
2. **Slack webhook.** At api.slack.com/apps create an app, enable **Incoming Webhooks**, add a webhook to
   the channel you want, and copy its URL. You do not need to connect Slack to anything else.
3. **Repo secrets** (Settings, Secrets and variables, Actions):
   - `SLACK_WEBHOOK_URL`: the webhook URL from step 2.
   - `ANTHROPIC_API_KEY`: your API key. (`GITHUB_TOKEN` is provided automatically.)
4. Generate failures: `scripts/generate_runs.sh 1` (needs the `gh` CLI), or Actions tab, CI, Run workflow.
   Each failing run should produce a Slack message within about a minute of the run ending.

Only the `triage.yml` workflow on the default branch is used; a `workflow_run` workflow must exist there.
Rules-only failures (network, disk, dependency) need no API key; the model is called only for the rest.

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                     # 75 offline tests

python -m triage diagnose --log-file samples/logs/synthetic-flaky-notifier.log
python -m triage diagnose --repo OWNER/REPO --run-id 123456789
python -m triage notify --repo OWNER/REPO --run-id 123456789 --dry-run   # prints the Slack payload
python -m triage eval --mode rules         # no API key needed
python -m triage eval --mode hybrid
```

Credentials: `ANTHROPIC_API_KEY` for model calls, `GITHUB_TOKEN` (or `gh auth login`) for fetching runs.
Modes: `hybrid` (default), `rules` (no model), `llm` (model only). Settings: `TRIAGE_MODEL` (default
`claude-opus-5-5`), `TRIAGE_EFFORT` (default `medium`), `TRIAGE_FALLBACKS=0` to turn off the
server-side refusal fallback (needed off the Claude API, e.g. on Bedrock).

## Build a real evaluation set

1. Run `scripts/generate_runs.sh 3`: 3 runs of each case (12 failing, 3 passing). Do not re-run failed
   `case_b` runs afterwards; a passing re-run overwrites the failed conclusion.
2. When they finish: `python -m triage build-dataset --repo OWNER/REPO` downloads the redacted logs and
   labels each from the case code in its run title (`CI (case_b)` becomes `flaky_test`, and so on).
3. `python -m triage eval` scores against them.

| Case | What happens | Label |
|---|---|---|
| `none` | Everything passes | (passing run) |
| `case_a` | `apply_discount` subtracts the percentage instead of applying it; fails on every attempt | `real_failure` |
| `case_b` | `test_delivery_acknowledged` times out on attempt 1, passes on a re-run | `flaky_test` |
| `case_c` | Fixtures download times out (unroutable address) | `infra_failure` |
| `case_d` | `pip install requests==99.0.0` cannot resolve | `dependency_env` |

**Why the codes are neutral.** The workflow file, the run title and the job log are all input to the
model. When the cases had descriptive names, the log printed `SCENARIO: flaky` and the run title was
`CI (flaky)`, so the model could read the answer instead of diagnosing it. The code-to-label key now lives
only in `triage/dataset.py`, and `tests/test_demo_repo.py` fails if a label word appears in the workflow,
the demo source, the demo test output or the sample logs. Runs made before this change are skipped by
`build-dataset` because their logs contain the answer.

The failures are still planted, which makes the labels certain, but real failures are messier. Treat
accuracy on this set as an upper bound.

## What has and has not been tested

Tested (offline): redaction, excerpting, rules, request shape, error handling, eval maths, GitHub client
against a fake session, Slack payload and escaping, the notify command, demo app behaviour per case,
the structure and safety properties of both workflows, and that no label word leaks into the model's input.

**Not yet tested:** a live model call, a live GitHub fetch, a real Slack post, and the workflows actually
running on GitHub. The first live run is the real test of the prompt, the structured-output request and
the `workflow_run` wiring.

## Known limits (v1)

- Model confidence is self-reported and not calibrated; check it against the eval before trusting it.
- Redaction is pattern-based and will miss secrets with no recognisable shape.
- Only the latest attempt of a run is analysed; earlier attempts are not compared.
- Every failure posts a new Slack message; there is no threading or de-duplication of repeat failures.
- `workflow_run` fires only for workflows in the same repo.

## Next steps

1. Push, add the two secrets, generate runs, build the dataset, run the first live `eval`.
2. Record the on-call's real classification (a reaction or button in Slack) to grow the labelled set.
3. Track repeat failures per test so known-flaky tests are recognised automatically.
