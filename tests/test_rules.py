from triage import rules
from triage.models import DEPENDENCY_ENV, FLAKY_TEST, INFRA_FAILURE


def test_curl_timeout_is_infra():
    d = rules.match("curl: (28) Failed to connect to 10.255.255.1 port 443 after 5002 ms: Timeout was reached")
    assert d.category == INFRA_FAILURE and d.confidence == "high"
    assert d.evidence[0].startswith("curl: (28)")


def test_disk_full_is_infra():
    assert rules.match("ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device").category == INFRA_FAILURE


def test_unresolvable_version_is_dependency():
    d = rules.match("ERROR: No matching distribution found for requests==99.0.0")
    assert d.category == DEPENDENCY_ENV and d.confidence == "high"


def test_network_failure_during_install_stays_infra():
    log = "WARNING: Connection timed out while fetching\nERROR: No matching distribution found for requests"
    assert rules.match(log).category == INFRA_FAILURE


def test_missing_module_is_medium_confidence():
    d = rules.match("E   ModuleNotFoundError: No module named 'yaml'")
    assert d.category == DEPENDENCY_ENV and d.confidence == "medium"


def test_plain_assertion_failure_has_no_rule():
    assert rules.match("FAILED tests/test_orders.py::test_apply_discount - assert 240.0 == 225.0") is None


def test_known_flaky_only_when_every_failure_is_listed():
    log = "FAILED tests/test_notifier.py::test_delivery_acknowledged - TimeoutError"
    known = ("test_delivery_acknowledged",)
    assert rules.match(log, known).category == FLAKY_TEST
    assert rules.match(log + "\nFAILED tests/test_orders.py::test_apply_discount - assert", known) is None
    assert rules.match(log) is None
