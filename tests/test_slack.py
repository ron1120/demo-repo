import json
from types import SimpleNamespace

import pytest

from triage import cli, slack
from triage.models import Diagnosis

RUN_URL = "https://github.com/o/r/actions/runs/7"


def diagnosis(**overrides):
    fields = dict(category="flaky_test", confidence="medium", summary="A timing-dependent test timed out.",
                  evidence=["E   TimeoutError: delivery not acknowledged within 0.25s"],
                  next_step="Re-run the job.", source="llm")
    return Diagnosis(**{**fields, **overrides})


def all_text(payload):
    return json.dumps(payload)


def test_message_carries_the_diagnosis_and_links_to_the_run():
    payload = slack.build_message(diagnosis(), {"workflow": "CI", "branch": "main", "run_attempt": 1}, RUN_URL)
    text = all_text(payload)
    assert "Flaky test" in text and "medium" in text and "TimeoutError" in text and "Re-run the job." in text
    assert "attempt 1" in text and "Check it against the log before acting" in text
    assert payload["blocks"][-1]["elements"][0]["url"] == RUN_URL
    assert payload["text"].startswith("CI failure:")


def test_log_derived_text_cannot_create_mentions_or_links():
    hostile = "<!channel> <https://evil.example|click me> & more"
    payload = slack.build_message(
        diagnosis(summary=hostile, evidence=[hostile], next_step=hostile),
        {"workflow": hostile, "branch": hostile},
        RUN_URL,
    )
    text = all_text(payload)
    assert "<!channel>" not in text and "<https://evil.example" not in text
    assert "&lt;!channel&gt;" in text and "&amp; more" in text


def test_evidence_cannot_break_out_of_the_code_block():
    payload = slack.build_message(diagnosis(evidence=["``` *injected* ```"]), {}, RUN_URL)
    evidence_block = next(b for b in payload["blocks"] if "Evidence" in b.get("text", {}).get("text", ""))
    body = evidence_block["text"]["text"]
    assert body.count("```") == 2


def test_long_text_is_clipped_under_slacks_limit():
    payload = slack.build_message(diagnosis(summary="x" * 10_000), {}, RUN_URL)
    assert all(len(b["text"]["text"]) <= 3000 for b in payload["blocks"] if b["type"] == "section")


def test_missing_meta_still_renders():
    assert slack.build_message(diagnosis(evidence=[]), None, RUN_URL)["blocks"]


class FakeWebhook:
    def __init__(self, status=200, body="ok"):
        self.calls = []
        self.status, self.body = status, body

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        return SimpleNamespace(status_code=self.status, text=self.body)


def test_post_sends_json_to_the_webhook():
    hook = FakeWebhook()
    slack.post("https://hooks.slack.com/services/T/B/x", {"text": "hi"}, session=hook)
    assert hook.calls == [("https://hooks.slack.com/services/T/B/x", {"text": "hi"})]


def test_post_raises_when_slack_rejects():
    with pytest.raises(RuntimeError, match="invalid_payload"):
        slack.post("https://hooks.slack.com/x", {}, session=FakeWebhook(400, "invalid_payload"))


@pytest.fixture
def notify_env(monkeypatch):
    meta = {"workflow": "CI", "branch": "main", "run_attempt": 1}
    monkeypatch.setattr(cli, "diagnose_run", lambda repo, run_id, **kw: (diagnosis(), meta))
    posted = []
    monkeypatch.setattr(cli, "post", lambda url, payload: posted.append((url, payload)))
    return posted


def test_notify_posts_when_a_webhook_is_configured(notify_env, monkeypatch, capsys):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/x")
    assert cli.main(["notify", "--repo", "o/r", "--run-id", "7"]) == 0
    url, payload = notify_env[0]
    assert url.startswith("https://hooks.slack.com/") and payload["blocks"][-1]["elements"][0]["url"] == RUN_URL
    assert "Posted diagnosis" in capsys.readouterr().out


def test_notify_dry_run_prints_and_never_posts(notify_env, monkeypatch, capsys):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/x")
    assert cli.main(["notify", "--repo", "o/r", "--run-id", "7", "--dry-run"]) == 0
    assert notify_env == [] and '"blocks"' in capsys.readouterr().out


def test_notify_without_a_webhook_prints_instead_of_posting(notify_env, monkeypatch, capsys):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert cli.main(["notify", "--repo", "o/r", "--run-id", "7"]) == 0
    captured = capsys.readouterr()
    assert notify_env == [] and "SLACK_WEBHOOK_URL is not set" in captured.err
