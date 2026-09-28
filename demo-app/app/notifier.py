import os
import time


def _ack_delay():
    first_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "2") == "1"
    if os.environ.get("CASE") == "case_b" and first_attempt:
        return 0.35
    return 0.01


def deliver(message, timeout=0.25):
    if not message:
        raise ValueError("message must not be empty")
    time.sleep(_ack_delay())
    if _ack_delay() > timeout:
        raise TimeoutError(f"delivery not acknowledged within {timeout}s")
    return True
