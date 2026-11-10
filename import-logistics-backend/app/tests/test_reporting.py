# app/tests/test_reporting.py
from decimal import Decimal

from app.utils.reporting import profit_and_margin, unallocated

D = Decimal


def test_profit_uses_cost_of_sold_items_only():
    profit, margin = profit_and_margin("700", "590")
    assert profit == D("110.0000")
    assert margin == 0.186441


def test_no_sales_means_zero_profit_not_a_loss():
    assert profit_and_margin(0, 0) == (D("0.0000"), 0.0)


def test_a_real_loss_is_negative():
    profit, margin = profit_and_margin("50", "80")
    assert profit == D("-30.0000") and margin < 0


def test_none_values_are_treated_as_zero():
    assert profit_and_margin(None, None) == (D("0.0000"), 0.0)


def test_unallocated_expenses():
    assert unallocated("100.00", "60.0000") == D("40.0000")
    assert unallocated("100", "100") == D("0.0000")
