# app/tests/test_money.py
from decimal import Decimal

import pytest

from app.utils.money import (
    allocate_proportionally, convert, quantize, to_decimal,
)

D = Decimal


def test_float_conversion_is_not_binary_noise():
    assert to_decimal(0.1) == D("0.1")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "abc", True])
def test_rejects_invalid_values(bad):
    with pytest.raises((ValueError, TypeError)):
        to_decimal(bad)


def test_quantize_uses_bankers_rounding():
    assert quantize("2.00005", 4) == D("2.0000")
    assert quantize("2.00015", 4) == D("2.0002")


def test_convert_applies_rate_and_rounds():
    assert convert("100", "0.00065") == D("0.0650")


def test_split_100_three_ways_sums_exactly():
    parts = allocate_proportionally("100.00", [1, 1, 1], places=2)
    assert parts == [D("33.34"), D("33.33"), D("33.33")]
    assert sum(parts) == D("100.00")


def test_split_is_proportional():
    parts = allocate_proportionally("1000", [1, 3], places=2)
    assert parts == [D("250.00"), D("750.00")]


def test_parts_always_sum_to_total_even_for_awkward_weights():
    weights = ["0.333", "7.1", "12.007", "0.001", "99.9"]
    total = "12345.6789"
    parts = allocate_proportionally(total, weights)
    assert sum(parts) == D("12345.6789")
    assert all(p >= 0 for p in parts)


def test_zero_weight_item_gets_nothing():
    parts = allocate_proportionally("10.00", [0, 5, 5], places=2)
    assert parts[0] == D("0.00")
    assert sum(parts) == D("10.00")


def test_is_deterministic():
    a = allocate_proportionally("10", [1, 1, 1], places=2)
    b = allocate_proportionally("10", [1, 1, 1], places=2)
    assert a == b


@pytest.mark.parametrize(
    "total,weights",
    [("10", []), ("10", [0, 0]), ("10", [-1, 2]), ("-5", [1, 1])],
)
def test_invalid_allocations_raise(total, weights):
    with pytest.raises(ValueError):
        allocate_proportionally(total, weights)
