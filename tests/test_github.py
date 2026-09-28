import json
from types import SimpleNamespace

import pytest

from triage.dataset import build_dataset
from triage.github import GitHubClient


class FakeSession:
    def __init__(self, routes):
        self.headers = {}
        self.routes = routes
        self.requested = []

    def get(self, url, params=None, timeout=None):
        path = url.replace("https://api.github.com", "")
        self.requested.append(path)
        body = self.routes[path]
        if isinstance(body, str):
            return SimpleNamespace(text=body, raise_for_status=lambda: None, json=lambda: None)
        return SimpleNamespace(json=lambda: body, text="", raise_for_status=lambda: None)


ROUTES = {
    "/repos/o/r/actions/runs/7": {"name": "CI", "event": "workflow_dispatch", "head_branch": "main",
                                  "run_attempt": 1, "conclusion": "failure"},
    "/repos/o/r/actions/runs/7/jobs": {"jobs": [
        {"id": 11, "name": "lint", "conclusion": "success", "steps": []},
        {"id": 12, "name": "test", "conclusion": "failure",
         "steps": [{"name": "Run tests", "conclusion": "failure"}, {"name": "Checkout", "conclusion": "success"}]},
    ]},
    "/repos/o/r/actions/jobs/12/logs": "2026-09-14T08:00:00.0000000Z FAILED tests/a.py::t\n",
}


def test_fetch_failure_collects_only_failed_jobs():
    gh = GitHubClient(token="t", session=FakeSession(ROUTES))
    meta, log = gh.fetch_failure("o/r", 7)
    assert meta["failed_jobs"] == ["test"] and meta["failed_steps"] == ["Run tests"]
    assert meta["run_attempt"] == 1
    assert "JOB: test" in log and "FAILED tests/a.py::t" in log
    assert "/repos/o/r/actions/jobs/11/logs" not in gh.session.requested


def test_run_without_failed_jobs_is_an_error():
    routes = {**ROUTES, "/repos/o/r/actions/runs/7/jobs": {"jobs": [{"id": 1, "name": "x", "conclusion": "success"}]}}
    with pytest.raises(ValueError):
        GitHubClient(token="t", session=FakeSession(routes)).fetch_failure("o/r", 7)


def test_build_dataset_labels_from_case_code_and_dedupes(tmp_path):
    routes = {
        **ROUTES,
        "/repos/o/r/actions/workflows/ci.yml/runs": {"workflow_runs": [
            {"id": 7, "display_title": "CI (case_a)"},
            {"id": 8, "display_title": "CI (push)"},
            {"id": 9, "display_title": "CI (real_bug)"},  # old naming: its log names the answer, so skip it
        ]},
    }
    gh = GitHubClient(token="t", session=FakeSession(routes))
    assert len(build_dataset(gh, "o/r", tmp_path)) == 1
    labels = json.loads((tmp_path / "labels.json").read_text())
    assert labels[0]["label"] == "real_failure" and (tmp_path / labels[0]["log"]).exists()
    assert build_dataset(gh, "o/r", tmp_path) == []
    assert len(json.loads((tmp_path / "labels.json").read_text())) == 1
