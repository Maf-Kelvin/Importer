# app/schemas/types.py
"""Shared Pydantic types for money, FX rates and weights.

Values are validated and handled as Decimal. In JSON they are written as
numbers (not strings) so existing clients keep working; precision is limited
by the validators (4 decimal places for money, 8 for rates, 3 for weights).
"""
from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer


def _to_number(value: Decimal) -> float:
    return float(value)


_json_number = PlainSerializer(_to_number, return_type=float, when_used="json")

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=4), _json_number]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4), _json_number]
Rate = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8), _json_number]
Weight = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3), _json_number]
