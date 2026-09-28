from app.orders import apply_discount, order_total


def test_order_total():
    assert order_total([(10.0, 2), (5.5, 1)]) == 25.5


def test_apply_discount():
    assert apply_discount(250.0, 10) == 225.0


def test_discount_never_negative():
    assert apply_discount(5.0, 200) == 0.0


def test_empty_order():
    assert order_total([]) == 0.0
