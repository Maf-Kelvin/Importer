# app/utils/money.py
"""
Money helpers (standard library only).

Rules the whole code base follows:
  * Money is ``Decimal`` in Python and ``NUMERIC`` in PostgreSQL, never float.
  * Amounts are stored with 4 decimal places, FX rates with 8.
  * When a total is split across items, the parts MUST add up to the total
    exactly (largest-remainder method), so no cent is created or lost.
"""
from __future__ import annotations

from decimal import (
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    Decimal,
    InvalidOperation,
    localcontext,
)
from typing import Sequence

MONEY_PLACES = 4
RATE_PLACES = 8
DISPLAY_PLACES = 2

ZERO = Decimal("0")


def to_decimal(value: object) -> Decimal:
    """Convert int / float / str / Decimal to a finite Decimal.

    Floats go through ``str()`` so 0.1 becomes Decimal("0.1"), not the
    binary expansion 0.1000000000000000055...
    """
    if isinstance(value, bool):
        raise TypeError("bool is not a valid money value")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(str(value))
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError(f"not a valid number: {value!r}") from exc
    else:
        raise TypeError(f"cannot convert {type(value).__name__} to Decimal")
    if not result.is_finite():
        raise ValueError("NaN and Infinity are not valid money values")
    return result


def quantize(
    value: object, places: int = MONEY_PLACES, rounding: str = ROUND_HALF_EVEN
) -> Decimal:
    """Round to a fixed number of decimal places (banker's rounding)."""
    unit = Decimal(1).scaleb(-places)
    return to_decimal(value).quantize(unit, rounding=rounding)


def convert(amount: object, rate: object) -> Decimal:
    """amount * rate, rounded to storage precision."""
    return quantize(to_decimal(amount) * to_decimal(rate), MONEY_PLACES)


def allocate_proportionally(
    total: object,
    weights: Sequence[object],
    places: int = MONEY_PLACES,
) -> list[Decimal]:
    """Split ``total`` across ``weights`` so the parts sum to ``total`` exactly.

    Largest-remainder method: every share is rounded down to ``places``; the
    few leftover units are handed out to the shares that lost the most.
    Ties are broken by position, so the result is deterministic.
    """
    if not weights:
        raise ValueError("nothing to allocate to")

    parts = [to_decimal(w) for w in weights]
    if any(w < 0 for w in parts):
        raise ValueError("weights must not be negative")
    weight_sum = sum(parts, ZERO)
    if weight_sum == 0:
        raise ValueError("weights add up to zero")

    unit = Decimal(1).scaleb(-places)
    total_q = quantize(total, places)
    if total_q < 0:
        raise ValueError("total must not be negative")

    with localcontext() as ctx:
        ctx.prec = 60
        raw = [total_q * w / weight_sum for w in parts]
        floors = [r.quantize(unit, rounding=ROUND_DOWN) for r in raw]
        remainders = [r - f for r, f in zip(raw, floors)]
        leftover_units = int(
            ((total_q - sum(floors, ZERO)) / unit).to_integral_value()
        )
        order = sorted(range(len(parts)), key=lambda i: (-remainders[i], i))
        result = list(floors)
        for i in order[:leftover_units]:
            result[i] += unit
    return result
