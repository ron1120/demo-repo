from __future__ import annotations

import os
import shutil
import subprocess

import requests

API = "https://api.github.com"
FAILED_CONCLUSIONS = ("failure", "timed_out")


def find_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    if shutil.which("gh"):
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


class GitHubClient:
    def __init__(self, token: str | None = None, session=None):
        self.session = session or requests.Session()
        token = token or find_token()
        if not token:
            raise RuntimeError("No GitHub token: set GITHUB_TOKEN, or log in with 'gh auth login'.")
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get(self, path: str, **params):
        response = self.session.get(f"{API}{path}", params=params or None, timeout=60)
        response.raise_for_status()
        return response

    def list_jobs(self, repo: str, run_id: int) -> list[dict]:
        jobs, page = [], 1
        while True:
            batch = self._get(f"/repos/{repo}/actions/runs/{run_id}/jobs", per_page=100, page=page).json()["jobs"]
            jobs.extend(batch)
            if len(batch) < 100:
                return jobs
            page += 1

    def job_log(self, repo: str, job_id: int) -> str:
        return self._get(f"/repos/{repo}/actions/jobs/{job_id}/logs").text

    def list_failed_runs(self, repo: str, workflow: str) -> list[dict]:
        data = self._get(f"/repos/{repo}/actions/workflows/{workflow}/runs", status="failure", per_page=100).json()
        return data["workflow_runs"]

    def fetch_failure(self, repo: str, run_id: int) -> tuple[dict, str]:
        """Return (metadata, combined log of the failed jobs) for a run."""
        run = self._get(f"/repos/{repo}/actions/runs/{run_id}").json()
        failed_jobs = [j for j in self.list_jobs(repo, run_id) if j.get("conclusion") in FAILED_CONCLUSIONS]
        if not failed_jobs:
            raise ValueError(f"Run {run_id} has no failed jobs (conclusion: {run.get('conclusion')}).")

        parts, failed_steps = [], []
        for job in failed_jobs:
            steps = [s["name"] for s in job.get("steps", []) if s.get("conclusion") in FAILED_CONCLUSIONS]
            failed_steps.extend(steps)
            header = f"##### JOB: {job['name']} | failed step(s): {', '.join(steps) or 'unknown'} #####"
            parts.append(f"{header}\n{self.job_log(repo, job['id'])}")

        meta = {
            "repository": repo,
            "workflow": run.get("name"),
            "event": run.get("event"),
            "branch": run.get("head_branch"),
            "run_attempt": run.get("run_attempt"),
            "run_conclusion": run.get("conclusion"),
            "failed_jobs": [j["name"] for j in failed_jobs],
            "failed_steps": failed_steps,
        }
        return meta, "\n".join(parts)
