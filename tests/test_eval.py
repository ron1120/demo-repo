from pathlib import Path

from triage.evaluate import evaluate, format_report

LABELS = Path(__file__).resolve().parent.parent / "samples" / "labels.json"


def test_rules_only_scores_the_rule_covered_samples():
    result = evaluate(LABELS, mode="rules")
    assert result["total"] == 8
    # Rules cover infra and dependency; real bugs and flaky tests have no rule and abstain.
    assert result["per_class"]["infra_failure"]["recall"] == 1.0
    assert result["per_class"]["dependency_env"]["recall"] == 1.0
    assert result["per_class"]["real_failure"]["recall"] == 0.0
    assert result["abstained"] == 4
    assert result["errors"] == 0


def test_known_flaky_list_lifts_flaky_recall_only_for_listed_tests():
    known = ("tests/test_notifier.py::test_delivery_acknowledged",)
    result = evaluate(LABELS, mode="rules", known_flaky=known)
    assert result["per_class"]["flaky_test"]["recall"] == 0.5


def test_report_is_readable():
    text = format_report(evaluate(LABELS, mode="rules"))
    assert "precision" in text and "Confusion" in text and "Misses:" in text
