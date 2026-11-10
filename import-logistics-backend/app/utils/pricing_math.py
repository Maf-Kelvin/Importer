# app/utils/pricing_math.py
"""Price recommendation engine (standard library only, so it is fully unit-tested).

Why not a simple average?
  * A mean is wrecked by one bad scrape (a 5,000 listing among 100s). We use a
    weighted MEDIAN after removing statistical outliers.
  * Old listings say little about today. Each comparable's weight decays with age.
  * Sources differ in reliability, and your OWN completed sales are the best evidence.
  * Few or widely scattered comparables should not override your cost logic. The
    market signal is blended with cost-plus by a trust score built from the
    effective sample size and the spread of prices.
  * The result must never silently fall below your minimum margin, and it should come
    with a price band, a confidence and plain-language reasons, so a human can decide.

All prices are USD Decimals. Weights/statistics are floats (they are not money).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Sequence

from app.utils.money import quantize, to_decimal

# Reliability of each source (0..1). Starting points; tune them with the backtest.
SOURCE_WEIGHTS = {
    "ebay": 1.0, "mobile_de": 1.0, "autoscout24": 1.0,
    "jiji": 0.8, "bazos_cz": 0.7,
    "own_sale": 1.0,
}


@dataclass(frozen=True)
class Comparable:
    price_usd: Decimal
    age_days: float
    source: str = "unknown"
    confidence: float = 0.5          # scraper's own confidence, 0..1
    own_sale: bool = False           # a completed sale of yours (strongest evidence)


@dataclass(frozen=True)
class PricingPolicy:
    target_margin: Decimal = Decimal("0.20")
    min_margin: Decimal = Decimal("0.05")
    half_life_days: float = 30.0         # a comparable loses half its weight every 30 days
    outlier_threshold: float = 3.5       # modified z-score (Iglewicz-Hoaglin)
    min_comps: int = 3                   # fewer than this caps the market trust
    saturating_n: float = 6.0            # effective sample size at which sample size stops mattering
    max_market_trust: float = 0.85       # cost-plus always keeps at least 15% say
    own_sale_boost: float = 1.5
    low_data_trust_cap: float = 0.5


@dataclass
class Recommendation:
    recommended: Decimal
    low: Decimal
    high: Decimal
    confidence: float
    expected_margin: float
    cost_plus: Decimal
    floor: Decimal
    market_median: Optional[Decimal] = None
    comps_used: int = 0
    outliers_removed: int = 0
    effective_n: float = 0.0
    market_trust: float = 0.0
    warnings: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)


# ------------------------------------------------------------------------------
# statistics
# ------------------------------------------------------------------------------
def _median(values: Sequence[Decimal]) -> Decimal:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def remove_outliers(comps: Sequence[Comparable], threshold: float) -> tuple[list[Comparable], int]:
    """Drop comparables whose modified z-score exceeds `threshold` (needs >= 4 points)."""
    if len(comps) < 4:
        return list(comps), 0
    prices = [c.price_usd for c in comps]
    med = _median(prices)
    mad = _median([abs(p - med) for p in prices])
    if mad == 0:
        return list(comps), 0
    limit = Decimal(str(threshold)) * mad / Decimal("0.6745")
    kept = [c for c in comps if abs(c.price_usd - med) <= limit]
    return kept, len(comps) - len(kept)


def weighted_quantile(pairs: Sequence[tuple[Decimal, float]], q: float) -> Decimal:
    """Weighted quantile; at an exact boundary it averages the two neighbours."""
    ordered = sorted(pairs, key=lambda p: p[0])
    total = sum(w for _, w in ordered)
    target = q * total
    cum = 0.0
    for i, (value, weight) in enumerate(ordered):
        cum += weight
        if abs(cum - target) < 1e-12 and i + 1 < len(ordered):
            return (value + ordered[i + 1][0]) / 2
        if cum > target:
            return value
    return ordered[-1][0]


def comparable_weight(c: Comparable, policy: PricingPolicy) -> float:
    age = max(c.age_days, 0.0)
    recency = 0.5 ** (age / policy.half_life_days)
    source = SOURCE_WEIGHTS.get("own_sale" if c.own_sale else c.source, 0.6)
    conf = min(max(c.confidence, 0.05), 1.0)
    boost = policy.own_sale_boost if c.own_sale else 1.0
    return recency * source * conf * boost


def effective_sample_size(weights: Sequence[float]) -> float:
    """Kish effective sample size: how many equally-weighted comparables the weights are worth."""
    total = sum(weights)
    squares = sum(w * w for w in weights)
    return (total * total / squares) if squares > 0 else 0.0


# ------------------------------------------------------------------------------
# the engine
# ------------------------------------------------------------------------------
def recommend_price(
    landed_cost: object,
    comps: Sequence[Comparable],
    policy: PricingPolicy = PricingPolicy(),
) -> Recommendation:
    cost = to_decimal(landed_cost)
    if cost <= 0:
        raise ValueError("landed cost must be positive")

    cost_plus = quantize(cost * (1 + policy.target_margin), 2)
    floor = quantize(cost * (1 + policy.min_margin), 2)
    warnings: list[str] = []
    why: list[str] = []

    usable, removed = remove_outliers(list(comps), policy.outlier_threshold)
    if removed:
        why.append(f"Ignored {removed} price(s) that were statistical outliers.")

    weighted = [(c.price_usd, comparable_weight(c, policy)) for c in usable]
    weighted = [(p, w) for p, w in weighted if w > 0]

    if not weighted:
        warnings.append("No market data: this price is cost-plus only. Add or refresh market prices.")
        why.append(f"Cost-plus: landed cost x (1 + {policy.target_margin:.0%} target margin).")
        return Recommendation(
            recommended=cost_plus, low=floor, high=cost_plus, confidence=0.3,
            expected_margin=float(quantize((cost_plus - cost) / cost, 6)),
            cost_plus=cost_plus, floor=floor, warnings=warnings, explanation=why,
        )

    weights = [w for _, w in weighted]
    n_eff = effective_sample_size(weights)
    median = quantize(weighted_quantile(weighted, 0.5), 2)
    q1 = weighted_quantile(weighted, 0.25)
    q3 = weighted_quantile(weighted, 0.75)
    spread = float((q3 - q1) / median) if median > 0 else 1.0

    trust = min(1.0, n_eff / policy.saturating_n) * (1.0 / (1.0 + spread))
    trust = min(trust, policy.max_market_trust)
    if len(weighted) < policy.min_comps:
        trust = min(trust, policy.low_data_trust_cap)
        warnings.append(f"Only {len(weighted)} comparable price(s): treat the market signal as weak.")

    blended = quantize(Decimal(str(trust)) * median + Decimal(str(1 - trust)) * cost_plus, 2)
    recommended = blended

    why.append(
        f"Market median {median} from {len(weighted)} comparable(s) "
        f"(effective sample {n_eff:.1f}, price spread {spread:.0%})."
    )
    why.append(f"Blended {trust:.0%} market / {1 - trust:.0%} cost-plus ({cost_plus}).")

    if median < cost:
        warnings.append("Market price is below your landed cost: selling at market would lose money.")
    if recommended < floor:
        recommended = floor
        warnings.append(
            f"Raised to your minimum-margin floor ({floor}); the market supports less. "
            "Consider holding the item or negotiating cost."
        )
        why.append(f"Floor applied: landed cost x (1 + {policy.min_margin:.0%} minimum margin).")

    low = max(floor, quantize(q1, 2))
    high = max(low, quantize(q3, 2))
    if recommended > high:
        high = recommended
    if recommended < low:
        low = recommended

    return Recommendation(
        recommended=recommended, low=low, high=high, confidence=round(trust, 3),
        expected_margin=float(quantize((recommended - cost) / cost, 6)),
        cost_plus=cost_plus, floor=floor, market_median=median,
        comps_used=len(weighted), outliers_removed=removed,
        effective_n=round(n_eff, 2), market_trust=round(trust, 3),
        warnings=warnings, explanation=why,
    )


# ------------------------------------------------------------------------------
# measuring accuracy against what actually sold
# ------------------------------------------------------------------------------
def error_metrics(pairs: Sequence[tuple[object, object]]) -> dict[str, float]:
    """pairs = [(recommended, actual_sold_price)].

    mape  : mean absolute percentage error (lower is better)
    bias  : average signed error as % of actual (positive = we recommend too high)
    within_10pct : share of sales that landed within 10% of the recommendation
    """
    errors = []
    for rec, actual in pairs:
        r, a = to_decimal(rec), to_decimal(actual)
        if a > 0:
            errors.append(float((r - a) / a))
    if not errors:
        return {"n": 0, "mape": 0.0, "bias": 0.0, "within_10pct": 0.0}
    n = len(errors)
    return {
        "n": n,
        "mape": round(sum(abs(e) for e in errors) / n, 4),
        "bias": round(sum(errors) / n, 4),
        "within_10pct": round(sum(1 for e in errors if abs(e) <= 0.10) / n, 4),
    }
