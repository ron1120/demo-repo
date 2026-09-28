from __future__ import annotations

import json
import re
from pathlib import Path

from .diagnose import prepare
from .models import DEPENDENCY_ENV, FLAKY_TEST, INFRA_FAILURE, REAL_FAILURE

SCENARIO_LABELS = {
    "real_bug": REAL_FAILURE,
    "flaky": FLAKY_TEST,
    "infra_timeout": INFRA_FAILURE,
    "dependency_missing": DEPENDENCY_ENV,
}
_TITLE = re.compile(r"^CI \((\w+)\)")


def build_dataset(github, repo: str, out_dir: Path, workflow: str = "ci.yml") -> list[dict]:
    """Download redacted logs of the demo repo's failed runs and label them from the scenario in the run title."""
    labels_path = out_dir / "labels.json"
    entries = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else []
    seen = {e["id"] for e in entries}
    added = []

    for run in github.list_failed_runs(repo, workflow):
        match = _TITLE.match(run.get("display_title", ""))
        label = SCENARIO_LABELS.get(match.group(1)) if match else None
        entry_id = f"run-{run['id']}"
        if label is None or entry_id in seen:
            continue
        meta, log_text = github.fetch_failure(repo, run["id"])
        text, _ = prepare(log_text)
        log_file = out_dir / "logs" / f"{entry_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(text, encoding="utf-8")
        added.append({"id": entry_id, "log": f"logs/{entry_id}.log", "label": label, "meta": meta})

    labels_path.write_text(json.dumps(entries + added, indent=2) + "\n", encoding="utf-8")
    return added
