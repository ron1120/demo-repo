import os


def order_total(items):
    return round(sum(price * qty for price, qty in items), 2)


def apply_discount(total, percent):
    if os.environ.get("SCENARIO") == "real_bug":
        # Simulated regression: subtracts the percentage points instead of applying the percentage.
        return max(total - percent, 0.0)
    return round(max(total * (1 - percent / 100), 0.0), 2)
