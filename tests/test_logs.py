from triage.logs import clean, extract_excerpt


def test_clean_strips_timestamps_and_ansi():
    raw = "2026-09-14T08:12:31.0370000Z \x1b[31mFAILED\x1b[0m tests/a.py::t\n2026-09-14T08:12:32Z plain"
    assert clean(raw) == "FAILED tests/a.py::t\nplain"


def test_short_log_returned_whole():
    text = "line one\nline two"
    assert extract_excerpt(text) == text


def test_long_log_keeps_error_and_stays_within_budget():
    noise = [f"step {i}: doing routine work" for i in range(5000)]
    noise[2500] = "##[error]Something specific broke here"
    text = "\n".join(noise + ["Process completed with exit code 1."])
    excerpt = extract_excerpt(text, max_chars=3000)
    assert "Something specific broke here" in excerpt
    assert "Process completed with exit code 1." in excerpt
    assert "lines omitted" in excerpt
    assert len(excerpt) < 3500


def test_long_log_without_signals_keeps_the_tail():
    text = "\n".join(f"quiet line {i}" for i in range(4000))
    excerpt = extract_excerpt(text, max_chars=2000)
    assert "quiet line 3999" in excerpt
    assert "quiet line 5\n" not in excerpt
