# app/utils/reporting.py
"""Profit arithmetic shared by every report (standard library only).

Definitions - used consistently everywhere:
    revenue            = selling price of items that are SOLD
    cost_of_goods_sold = landed cost of items that are SOLD
    profit             = revenue - cost_of_goods_sold
    margin             = profit / cost_of_goods_sold
    inventory_value    = landed cost of items NOT yet sold (money tied up, not a loss)

The old reports subtracted the cost of ALL items (including unsold stock) from the
revenue of sold items, so every container with unsold stock looked like a loss.
"""
from __future__ import annotations

from decimal import Decimal

from app.utils.money import ZERO, quantize, to_decimal


def profit_and_margin(revenue: object, cogs: object) -> tuple[Decimal, float]:
    rev, cost = to_decimal(revenue or 0), to_decimal(cogs or 0)
    profit = quantize(rev - cost)
    margin = float(quantize(profit / cost, 6)) if cost > 0 else 0.0
    return profit, margin


def unallocated(total_expenses: object, allocated_total: object) -> Decimal:
    """Expenses not yet pushed into item landed costs (run cost allocation)."""
    return quantize(to_decimal(total_expenses or 0) - to_decimal(allocated_total or 0))
