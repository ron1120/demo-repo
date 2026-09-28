from __future__ import annotations

import re

_SECRET_KEY = r"[A-Za-z0-9_.-]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)[A-Za-z0-9_.-]*"

# Order matters: multi-line and structural patterns first, generic key=value last.
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)(authorization:\s*(?:bearer|basic|token)\s+)\S+"), r"\1[REDACTED]"),
    (
        re.compile(rf"(?i)\b({_SECRET_KEY})(\s*[=:]\s*)(?!\[REDACTED|\*{{3}})(\"[^\"]*\"|'[^']*'|[^\s,;]+)"),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"\b(?!git@)[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[REDACTED_EMAIL]"),
]


def redact(text: str) -> tuple[str, int]:
    total = 0
    for pattern, replacement in _PATTERNS:
        text, count = pattern.subn(replacement, text)
        total += count
    return text, total
