from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DEPENDENCY_ENV, FLAKY_TEST, INFRA_FAILURE, Diagnosis


@dataclass(frozen=True)
class Rule:
    name: str
    category: str
    confidence: str
    pattern: re.Pattern
    summary: str
    next_step: str


# Infra rules come before dependency rules on purpose: a network failure during `pip install`
# ends in "No matching distribution found", but the cause is the network, not the package.
RULES = [
    Rule(
        "infra_network",
        INFRA_FAILURE,
        "high",
        re.compile(
            r"curl: \((?:6|7|28|35|56)\)|Connection timed out|Could not resolve host|"
            r"Temporary failure in name resolution|\b50[234] (?:Bad Gateway|Service Unavailable|Gateway Time-?out)"
        ),
        "A network call failed or timed out; this points at connectivity or an upstream service, not the code under test.",
        "Check the status of the endpoint the step calls, then re-run the job. If it repeats, look at runner networking.",
    ),
    Rule(
        "infra_runner",
        INFRA_FAILURE,
        "high",
        re.compile(
            r"The runner has received a shutdown signal|No space left on device|Received request to deprovision|"
            r"The hosted runner encountered an error"
        ),
        "The runner ran out of a resource or was shut down mid-job.",
        "Re-run the job. If it repeats, check runner disk and memory usage and the runner pool health.",
    ),
    Rule(
        "infra_rate_limit",
        INFRA_FAILURE,
        "high",
        re.compile(r"toomanyrequests: You have reached your pull rate limit|API rate limit exceeded"),
        "A registry or API rate limit was hit.",
        "Authenticate the pull or API call, or add caching, then re-run.",
    ),
    Rule(
        "dependency_unresolvable",
        DEPENDENCY_ENV,
        "high",
        re.compile(
            r"Could not find a version that satisfies the requirement|No matching distribution found for|"
            r"npm ERR! code (?:E404|ERESOLVE)|ResolutionImpossible|Could not resolve dependencies"
        ),
        "A dependency could not be resolved or installed.",
        "Check the pinned version or package name in the dependency file and whether the index is reachable.",
    ),
    Rule(
        "dependency_missing_module",
        DEPENDENCY_ENV,
        "medium",
        re.compile(r"ModuleNotFoundError: No module named|Cannot find module '"),
        "A module is missing at import time; usually a dependency that is not declared or not installed.",
        "Confirm the module is listed in the dependency file and installed by the workflow.",
    ),
]

_FAILED_TEST = re.compile(r"^FAILED (\S+)", re.M)


def _line_containing(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start : end if end != -1 else len(text)].strip()[:300]


def match(text: str, known_flaky: tuple[str, ...] = ()) -> Diagnosis | None:
    for rule in RULES:
        m = rule.pattern.search(text)
        if m:
            return Diagnosis(
                category=rule.category,
                confidence=rule.confidence,
                summary=rule.summary,
                evidence=[_line_containing(text, m.start())],
                next_step=rule.next_step,
                source="rules",
            )

    if known_flaky:
        failed = _FAILED_TEST.findall(text)
        if failed and all(any(k in test for k in known_flaky) for test in failed):
            return Diagnosis(
                category=FLAKY_TEST,
                confidence="medium",
                summary="Every failing test is on the known-flaky list.",
                evidence=[f"FAILED {test}" for test in failed[:5]],
                next_step="Re-run the job. If the same test keeps failing, check whether a recent change made it deterministic.",
                source="rules",
            )
    return None
