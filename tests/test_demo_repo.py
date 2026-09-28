import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo-app"
WORKFLOWS = ROOT / ".github" / "workflows"
PYTEST_BIN = Path(sys.executable).parent / "pytest"


def run_demo_tests(scenario, attempt="1"):
    # Use the pytest executable, as the workflow does: `python -m pytest` would put the cwd on sys.path
    # and hide a missing `pythonpath` setting.
    if not PYTEST_BIN.exists():
        pytest.skip("pytest executable not found next to the interpreter")
    env = {**os.environ, "SCENARIO": scenario, "GITHUB_RUN_ATTEMPT": attempt}
    return subprocess.run([str(PYTEST_BIN), "-q", "-p", "no:cacheprovider"],
                          cwd=DEMO, env=env, capture_output=True, text=True)


def load(name):
    workflow = yaml.safe_load((WORKFLOWS / name).read_text())
    workflow["_on"] = workflow.get("on", workflow.get(True))  # YAML 1.1 parses the key `on` as True
    return workflow


def test_demo_passes_with_no_scenario():
    result = run_demo_tests("none")
    assert result.returncode == 0, result.stdout


def test_real_bug_fails_deterministically():
    for attempt in ("1", "2"):
        result = run_demo_tests("real_bug", attempt)
        assert result.returncode != 0 and "test_apply_discount" in result.stdout


def test_flaky_fails_on_first_attempt_and_passes_on_rerun():
    first = run_demo_tests("flaky", "1")
    assert first.returncode != 0 and "TimeoutError" in first.stdout
    assert run_demo_tests("flaky", "2").returncode == 0


def test_ci_workflow_offers_every_scenario():
    workflow = load("ci.yml")
    options = workflow["_on"]["workflow_dispatch"]["inputs"]["scenario"]["options"]
    assert {"none", "real_bug", "flaky", "infra_timeout", "dependency_missing"} == set(options)
    assert workflow["run-name"].startswith("CI (")
    assert workflow["jobs"]["test"]["defaults"]["run"]["working-directory"] == "demo-app"


def test_triage_workflow_watches_ci_and_only_reacts_to_failures():
    workflow = load("triage.yml")
    trigger = workflow["_on"]["workflow_run"]
    assert trigger["workflows"] == [load("ci.yml")["name"]]
    assert trigger["types"] == ["completed"]
    job = workflow["jobs"]["triage"]
    assert job["if"] == "github.event.workflow_run.conclusion == 'failure'"
    assert workflow["permissions"] == {"actions": "read", "contents": "read"}


def test_triage_workflow_never_checks_out_the_failed_runs_code():
    text = (WORKFLOWS / "triage.yml").read_text()
    assert "head_sha" not in text and "head_branch" not in text and "pull_request" not in text
    steps = load("triage.yml")["jobs"]["triage"]["steps"]
    checkouts = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")]
    assert len(checkouts) == 1 and "with" not in checkouts[0]
