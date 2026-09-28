import pytest

from app.notifier import deliver


def test_delivery_acknowledged():
    assert deliver("order shipped", timeout=0.25) is True


def test_empty_message_rejected():
    with pytest.raises(ValueError):
        deliver("")
