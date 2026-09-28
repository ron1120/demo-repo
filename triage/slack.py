from __future__ import annotations

import requests

from .models import DEPENDENCY_ENV, FLAKY_TEST, INFRA_FAILURE, NEEDS_REVIEW, REAL_FAILURE, Diagnosis

LABELS = {
    REAL_FAILURE: ":bug: Real failure",
    FLAKY_TEST: ":game_die: Flaky test",
    INFRA_FAILURE: ":cloud: Infra failure",
    DEPENDENCY_ENV: ":package: Dependency / environment",
    NEEDS_REVIEW: ":mag: Needs human review",
}
MAX_TEXT = 2800  # Slack section text limit is 3000


def escape(text: str) -> str:
    """Escape Slack control characters so log-derived text cannot create mentions or links."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


def build_message(d: Diagnosis, meta: dict | None, run_url: str) -> dict:
    meta = meta or {}
    where = f"{escape(str(meta.get('workflow') or 'CI'))} on `{escape(str(meta.get('branch') or 'unknown'))}`"
    if meta.get("run_attempt"):
        where += f" (attempt {meta['run_attempt']})"
    label = LABELS.get(d.category, d.category)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "CI failure diagnosis"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{where}\n*{label}*  |  confidence: *{d.confidence}*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": _clip(escape(d.summary))}},
    ]
    if d.evidence:
        evidence = "\n".join(escape(line).replace("```", "'''") for line in d.evidence)
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": _clip(f"*Evidence*\n```{evidence}```")}})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": _clip(f"*Next step:* {escape(d.next_step)}")}})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Suggested diagnosis from the triage agent (via {d.source}). Check it against the log before acting.",
                }
            ],
        }
    )
    blocks.append(
        {
            "type": "actions",
            "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Open run"}, "url": run_url}],
        }
    )
    return {"text": f"CI failure: {label} ({d.confidence} confidence)", "blocks": blocks}


def post(webhook_url: str, payload: dict, session=None) -> None:
    response = (session or requests).post(webhook_url, json=payload, timeout=15)
    if response.status_code != 200 or response.text.strip() != "ok":
        raise RuntimeError(f"Slack rejected the message: HTTP {response.status_code} {response.text[:200]}")
