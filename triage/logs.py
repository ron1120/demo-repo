from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_TIMESTAMP = re.compile(r"^﻿?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ")

_HIGH = re.compile(r"##\[error\]|^FAILED |^E  |Traceback \(most recent call last\)|Process completed with exit code|npm ERR!")
_MEDIUM = re.compile(
    r"^ERROR |timed out|Timeout|Connection (?:refused|reset)|No space left|Killed|No matching distribution|"
    r"Could not (?:find|resolve|install)|ModuleNotFoundError|ImportError|AssertionError|Exception",
)

MAX_LINE = 400


def clean(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = _ANSI.sub("", line)
        line = _TIMESTAMP.sub("", line, count=1)
        lines.append(line.rstrip())
    return "\n".join(lines)


def _merge(windows: list[list[int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end, prio in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
            merged[-1][2] = max(merged[-1][2], prio)
        else:
            merged.append([start, end, prio])
    return merged


def extract_excerpt(text: str, max_chars: int = 12_000, context: int = 8, tail_lines: int = 25) -> str:
    """Keep the parts of a long log most likely to explain a failure: error lines with context, plus the tail."""
    lines = [line[:MAX_LINE] for line in text.split("\n")]
    n = len(lines)
    if sum(len(line) + 1 for line in lines) <= max_chars:
        return "\n".join(lines)

    windows: list[list[int]] = []
    for i, line in enumerate(lines):
        prio = 2 if _HIGH.search(line) else 1 if _MEDIUM.search(line) else 0
        if prio:
            windows.append([max(0, i - context), min(n, i + context + 1), prio])
    windows.append([max(0, n - tail_lines), n, 3])
    merged = _merge(windows)

    def size(w: list[int]) -> int:
        return sum(len(line) + 1 for line in lines[w[0] : w[1]])

    chosen: list[list[int]] = []
    budget = max_chars
    for w in sorted(merged, key=lambda w: (-w[2], -w[0])):
        s = size(w)
        if s <= budget:
            chosen.append(w)
            budget -= s
        elif not chosen:
            start = w[1]
            used = 0
            while start > w[0] and used + len(lines[start - 1]) + 1 <= budget:
                start -= 1
                used += len(lines[start]) + 1
            chosen.append([start, w[1], w[2]])
            budget -= used

    chosen.sort()
    out: list[str] = []
    prev_end = 0
    for start, end, _ in chosen:
        if start > prev_end:
            out.append(f"[... {start - prev_end} lines omitted ...]")
        out.extend(lines[start:end])
        prev_end = end
    if prev_end < n:
        out.append(f"[... {n - prev_end} lines omitted ...]")
    return "\n".join(out)
