from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .diagnose import diagnose_text
from .models import CATEGORIES, NEEDS_REVIEW

LABELLED = tuple(c for c in CATEGORIES if c != NEEDS_REVIEW)


def load_labels(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(labels_path: Path, mode: str = "hybrid", known_flaky: tuple[str, ...] = (), client=None) -> dict:
    entries = load_labels(labels_path)
    rows = []
    for entry in entries:
        log = (labels_path.parent / entry["log"]).read_text(encoding="utf-8")
        d = diagnose_text(log, meta=entry.get("meta"), mode=mode, known_flaky=known_flaky, client=client)
        rows.append({"id": entry["id"], "label": entry["label"], "predicted": d.category, "source": d.source,
                     "confidence": d.confidence})

    confusion = {label: Counter() for label in LABELLED}
    for r in rows:
        confusion[r["label"]][r["predicted"]] += 1

    per_class = {}
    for c in LABELLED:
        tp = confusion[c][c]
        predicted = sum(confusion[label][c] for label in LABELLED)
        actual = sum(confusion[c].values())
        per_class[c] = {
            "precision": tp / predicted if predicted else None,
            "recall": tp / actual if actual else None,
            "support": actual,
        }

    total = len(rows)
    return {
        "mode": mode,
        "total": total,
        "accuracy": sum(r["label"] == r["predicted"] for r in rows) / total if total else None,
        "abstained": sum(r["predicted"] == NEEDS_REVIEW for r in rows),
        "errors": sum(r["source"] == "error" for r in rows),
        "per_class": per_class,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "rows": rows,
    }


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:4.0f}%"


def format_report(result: dict) -> str:
    lines = [
        f"Mode: {result['mode']}    Samples: {result['total']}",
        f"Accuracy: {_pct(result['accuracy']).strip()}    "
        f"Abstained (needs_human_review): {result['abstained']}    LLM errors: {result['errors']}",
        "",
        f"{'category':<16}{'precision':>10}{'recall':>9}{'support':>9}",
    ]
    for c, m in result["per_class"].items():
        lines.append(f"{c:<16}{_pct(m['precision']):>10}{_pct(m['recall']):>9}{m['support']:>9}")
    lines += ["", "Confusion (rows = true label, columns = predicted):"]
    for label, predicted in result["confusion"].items():
        cells = ", ".join(f"{p}={n}" for p, n in sorted(predicted.items())) or "-"
        lines.append(f"  {label:<16}{cells}")
    wrong = [r for r in result["rows"] if r["label"] != r["predicted"]]
    if wrong:
        lines += ["", "Misses:"]
        lines += [f"  {r['id']}: labelled {r['label']}, predicted {r['predicted']} ({r['source']}, {r['confidence']})"
                  for r in wrong]
    return "\n".join(lines)
