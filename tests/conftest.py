import json
from types import SimpleNamespace

import pytest


class FakeClient:
    """Stands in for anthropic.Anthropic: records requests and returns a canned response."""

    def __init__(self, answer=None, stop_reason="end_turn", raw_text=None, error=None):
        self.calls = []
        self.messages = self
        self._error = error
        self._stop_reason = stop_reason
        self._text = raw_text if raw_text is not None else json.dumps(answer or {})

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(stop_reason=self._stop_reason, content=[SimpleNamespace(type="text", text=self._text)])


ANSWER = {
    "category": "flaky_test",
    "confidence": "medium",
    "summary": "A timing-dependent test timed out.",
    "evidence": ["E   TimeoutError: delivery not acknowledged within 0.25s"],
    "next_step": "Re-run the job.",
}


@pytest.fixture
def fake():
    return FakeClient(ANSWER)
