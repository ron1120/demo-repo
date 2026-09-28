from __future__ import annotations

from dataclasses import asdict, dataclass, field

REAL_FAILURE = "real_failure"
FLAKY_TEST = "flaky_test"
INFRA_FAILURE = "infra_failure"
DEPENDENCY_ENV = "dependency_env"
NEEDS_REVIEW = "needs_human_review"

CATEGORIES = (REAL_FAILURE, FLAKY_TEST, INFRA_FAILURE, DEPENDENCY_ENV, NEEDS_REVIEW)
CONFIDENCES = ("high", "medium", "low")


@dataclass
class Diagnosis:
    category: str
    confidence: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    next_step: str = ""
    source: str = "llm"  # "rules" | "llm" | "error"
    redactions: int = 0
    model: str = ""  # the model that answered (a fallback model if the first one declined); empty for rules
    usage: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
