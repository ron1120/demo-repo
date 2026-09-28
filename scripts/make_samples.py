# Regenerates samples/: synthetic GitHub Actions logs with known labels, used by the offline tests and eval.
# The log text must not name the category (tests/test_demo_repo.py checks this).
import json
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "samples"
(OUT / "logs").mkdir(parents=True, exist_ok=True)

SESSION = """============================= test session starts ==============================
platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0 -- /opt/hostedtoolcache/Python/3.12.6/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/demo-ci/demo-ci
collecting ... collected 6 items
"""


def run_step(case):
    return f"""##[group]Run pytest -v
pytest -v
shell: /usr/bin/bash -e {{0}}
env:
  CASE: {case}
  pythonLocation: /opt/hostedtoolcache/Python/3.12.6/x64
##[endgroup]
"""


REAL_DISCOUNT = run_step("case_a") + SESSION + """
tests/test_notifier.py::test_delivery_acknowledged PASSED                [ 16%]
tests/test_notifier.py::test_empty_message_rejected PASSED               [ 33%]
tests/test_orders.py::test_order_total PASSED                            [ 50%]
tests/test_orders.py::test_apply_discount FAILED                         [ 66%]
tests/test_orders.py::test_discount_never_negative PASSED                [ 83%]
tests/test_orders.py::test_empty_order PASSED                            [100%]

=================================== FAILURES ===================================
____________________________ test_apply_discount _______________________________

    def test_apply_discount():
>       assert apply_discount(250.0, 10) == 225.0
E       assert 240.0 == 225.0
E        +  where 240.0 = apply_discount(250.0, 10)

tests/test_orders.py:9: AssertionError
=========================== short test summary info ============================
FAILED tests/test_orders.py::test_apply_discount - assert 240.0 == 225.0
========================= 1 failed, 5 passed in 0.31s ==========================
##[error]Process completed with exit code 1.
"""

REAL_CHECKOUT = run_step("none").replace("tests/", "tests/") + """============================= test session starts ==============================
platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0 -- /opt/hostedtoolcache/Python/3.12.6/x64/bin/python
rootdir: /home/runner/work/shop/shop
collecting ... collected 48 items

tests/test_cart.py::test_add_item PASSED                                 [  2%]
tests/test_cart.py::test_remove_item PASSED                              [  4%]
tests/test_checkout.py::test_checkout_no_coupon PASSED                   [ 60%]
tests/test_checkout.py::test_checkout_applies_coupon FAILED              [ 62%]
tests/test_checkout.py::test_checkout_expired_coupon FAILED              [ 64%]
tests/test_checkout.py::test_checkout_free_shipping PASSED               [ 66%]

=================================== FAILURES ===================================
_________________________ test_checkout_applies_coupon _________________________

cart = <app.cart.Cart object at 0x7f1c2d3a9b50>

    def test_checkout_applies_coupon(cart):
>       result = checkout(cart, coupon="SAVE10")

tests/test_checkout.py:27:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
app/checkout.py:58: in checkout
    rate = coupon_rates.get(coupon.upper())
E   AttributeError: 'NoneType' object has no attribute 'get'
_________________________ test_checkout_expired_coupon _________________________

cart = <app.cart.Cart object at 0x7f1c2d3a9c10>

    def test_checkout_expired_coupon(cart):
>       result = checkout(cart, coupon="OLD5")

tests/test_checkout.py:34:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
app/checkout.py:58: in checkout
    rate = coupon_rates.get(coupon.upper())
E   AttributeError: 'NoneType' object has no attribute 'get'
=========================== short test summary info ============================
FAILED tests/test_checkout.py::test_checkout_applies_coupon - AttributeError: 'NoneType' object has no attribute 'get'
FAILED tests/test_checkout.py::test_checkout_expired_coupon - AttributeError: 'NoneType' object has no attribute 'get'
========================= 2 failed, 46 passed in 3.87s =========================
##[error]Process completed with exit code 1.
"""

FLAKY_NOTIFIER = run_step("case_b") + SESSION + """
tests/test_notifier.py::test_delivery_acknowledged FAILED                [ 16%]
tests/test_notifier.py::test_empty_message_rejected PASSED               [ 33%]
tests/test_orders.py::test_order_total PASSED                            [ 50%]
tests/test_orders.py::test_apply_discount PASSED                         [ 66%]
tests/test_orders.py::test_discount_never_negative PASSED                [ 83%]
tests/test_orders.py::test_empty_order PASSED                            [100%]

=================================== FAILURES ===================================
_________________________ test_delivery_acknowledged ___________________________

    def test_delivery_acknowledged():
>       assert deliver("order shipped", timeout=0.25) is True

tests/test_notifier.py:7:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
app/notifier.py:20: in deliver
    raise TimeoutError(f"delivery not acknowledged within {timeout}s")
E   TimeoutError: delivery not acknowledged within 0.25s
=========================== short test summary info ============================
FAILED tests/test_notifier.py::test_delivery_acknowledged - TimeoutError: delivery not acknowledged within 0.25s
========================= 1 failed, 5 passed in 0.72s ==========================
##[error]Process completed with exit code 1.
"""

FLAKY_LIMITER = run_step("none") + """============================= test session starts ==============================
platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0 -- /opt/hostedtoolcache/Python/3.12.6/x64/bin/python
rootdir: /home/runner/work/api-gateway/api-gateway
collecting ... collected 31 items

tests/test_limiter.py::test_blocks_over_limit PASSED                     [ 74%]
tests/test_limiter.py::test_window_resets_after_one_second FAILED        [ 77%]
tests/test_limiter.py::test_separate_keys_do_not_share_budget PASSED     [ 80%]

=================================== FAILURES ===================================
_____________________ test_window_resets_after_one_second ______________________

limiter = <app.limiter.SlidingWindowLimiter object at 0x7fa0c41d2e10>

    def test_window_resets_after_one_second(limiter):
        for _ in range(5):
            limiter.allow("client-a")
        time.sleep(1.0)
>       assert sum(limiter.allow("client-a") for _ in range(5)) == 5
E       assert 4 == 5
E        +  where 4 = sum(<generator object test_window_resets_after_one_second.<locals>.<genexpr> at 0x7fa0c4210f20>)

tests/test_limiter.py:41: AssertionError
=========================== short test summary info ============================
FAILED tests/test_limiter.py::test_window_resets_after_one_second - assert 4 == 5
======================== 1 failed, 30 passed in 6.02s ==========================
##[error]Process completed with exit code 1.
"""

INFRA_CURL = """##[group]Run if [ "$CASE" = "case_c" ]; then
if [ "$CASE" = "case_c" ]; then
  curl --fail --silent --show-error --max-time 5 https://10.255.255.1/fixtures.tgz -o fixtures.tgz
else
  echo "Fixtures cached, nothing to fetch"
fi
shell: /usr/bin/bash -e {0}
env:
  CASE: case_c
  pythonLocation: /opt/hostedtoolcache/Python/3.12.6/x64
##[endgroup]
curl: (28) Failed to connect to 10.255.255.1 port 443 after 5002 ms: Timeout was reached
##[error]Process completed with exit code 28.
"""

INFRA_DISK = """##[group]Run pip install -r requirements.txt
pip install -r requirements.txt
shell: /usr/bin/bash -e {0}
##[endgroup]
Collecting numpy==2.1.1 (from -r requirements.txt (line 3))
  Downloading numpy-2.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (16.0 MB)
     ---------------------------------------- 16.0/16.0 MB 82.1 MB/s eta 0:00:00
Collecting pandas==2.2.3 (from -r requirements.txt (line 4))
  Downloading pandas-2.2.3-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (12.7 MB)
     ---------------------------------------- 12.7/12.7 MB 91.4 MB/s eta 0:00:00
Installing collected packages: numpy, pandas
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device

##[error]Process completed with exit code 1.
"""

DEP_VERSION = """##[group]Run python -m pip install --upgrade pip
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ "$CASE" = "case_d" ]; then
  pip install "requests==99.0.0"
fi
shell: /usr/bin/bash -e {0}
env:
  CASE: case_d
##[endgroup]
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/site-packages (24.2)
Collecting pytest==8.3.3 (from -r requirements.txt (line 1))
  Downloading pytest-8.3.3-py3-none-any.whl (342 kB)
Installing collected packages: pytest
Successfully installed pytest-8.3.3
ERROR: Could not find a version that satisfies the requirement requests==99.0.0 (from versions: 0.0.1, 0.2.0, 0.2.1, 0.2.2, 0.2.3, 0.2.4, 0.3.0, 0.3.1, 0.3.2, 2.32.0, 2.32.1, 2.32.2, 2.32.3)
ERROR: No matching distribution found for requests==99.0.0
##[error]Process completed with exit code 1.
"""

DEP_MODULE = run_step("none") + """============================= test session starts ==============================
platform linux -- Python 3.12.6, pytest-8.3.3, pluggy-1.5.0
rootdir: /home/runner/work/settings-service/settings-service
collected 0 items / 1 error

==================================== ERRORS ====================================
_______________________ ERROR collecting tests/test_config.py ______________________
ImportError while importing test module '/home/runner/work/settings-service/settings-service/tests/test_config.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.12.6/x64/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_config.py:1: in <module>
    from app.config import load_settings
app/config.py:3: in <module>
    import yaml
E   ModuleNotFoundError: No module named 'yaml'
=========================== short test summary info ============================
ERROR tests/test_config.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
##[error]Process completed with exit code 2.
"""

SAMPLES = [
    ("synthetic-real-discount", REAL_DISCOUNT, "real_failure", 1),
    ("synthetic-real-checkout", REAL_CHECKOUT, "real_failure", 1),
    ("synthetic-flaky-notifier", FLAKY_NOTIFIER, "flaky_test", 1),
    ("synthetic-flaky-limiter", FLAKY_LIMITER, "flaky_test", 1),
    ("synthetic-infra-curl", INFRA_CURL, "infra_failure", 1),
    ("synthetic-infra-disk", INFRA_DISK, "infra_failure", 1),
    ("synthetic-dep-version", DEP_VERSION, "dependency_env", 1),
    ("synthetic-dep-module", DEP_MODULE, "dependency_env", 1),
]

labels = []
base = datetime(2026, 9, 14, 8, 12, 31)
for name, body, label, attempt in SAMPLES:
    lines = body.strip("\n").split("\n")
    stamped = []
    t = base
    for i, line in enumerate(lines):
        t += timedelta(milliseconds=37 * (i % 5 + 1))
        stamped.append(f"{t.strftime('%Y-%m-%dT%H:%M:%S')}.{t.microsecond:06d}0Z {line}")
    (OUT / "logs" / f"{name}.log").write_text("\n".join(stamped) + "\n", encoding="utf-8")
    labels.append({"id": name, "log": f"logs/{name}.log", "label": label,
                   "meta": {"workflow": "CI", "event": "push", "run_attempt": attempt}})

(OUT / "labels.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
print(len(labels), "samples written")
