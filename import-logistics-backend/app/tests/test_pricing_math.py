# app/tests/test_pricing_math.py
from decimal import Decimal

import pytest

from app.utils.pricing_math import (
    Comparable, PricingPolicy, effective_sample_size, error_metrics,
    recommend_price, remove_outliers, weighted_quantile,
)

D = Decimal


def comps(prices, age=1.0, source="ebay", conf=0.9, own=False):
    return [Comparable(D(str(p)), age, source, conf, own) for p in prices]


def test_no_market_data_falls_back_to_cost_plus_with_a_warning():
    r = recommend_price("100", [])
    assert r.recommended == D("120.00") and r.confidence == 0.3
    assert any("No market data" in w for w in r.warnings)
    assert r.low == D("105.00") and r.high == D("120.00")


def test_strong_market_above_cost_plus_pulls_the_price_up_but_not_all_the_way():
    r = recommend_price("100", comps([200, 205, 195, 210, 198, 202]))
    assert D("120.00") < r.recommended < D("200.00")
    assert r.market_median is not None and r.market_trust <= 0.85


def test_market_below_floor_never_recommends_below_minimum_margin():
    r = recommend_price("100", comps([90, 92, 88, 91, 89, 90]))
    assert r.recommended == D("105.00")                       # the floor
    assert any("below your landed cost" in w for w in r.warnings)
    assert any("minimum-margin floor" in w for w in r.warnings)


def test_one_outlier_does_not_move_the_price():
    clean = recommend_price("100", comps([150, 152, 148, 151, 149]))
    dirty = recommend_price("100", comps([150, 152, 148, 151, 149, 5000]))
    assert dirty.outliers_removed == 1
    assert abs(dirty.recommended - clean.recommended) <= D("1.00")


def test_a_plain_average_would_have_been_wrecked_by_that_outlier():
    prices = [150, 152, 148, 151, 149, 5000]
    mean = sum(prices) / len(prices)
    assert mean > 800                                        # what the old logic would see
    assert recommend_price("100", comps(prices)).recommended < D("200")


def test_old_comparables_count_less_than_recent_ones():
    mixed = comps([100, 101, 99], age=2) + comps([300, 301, 299], age=200)
    r = recommend_price("50", mixed)
    assert r.market_median is not None and r.market_median < D("200")


def test_own_completed_sales_outweigh_scraped_listings():
    scraped = comps([200, 202, 198], source="jiji", conf=0.5)
    own = comps([150, 152, 148], source="own_sale", conf=1.0, own=True)
    r = recommend_price("100", scraped + own)
    assert r.market_median is not None and r.market_median < D("180")


def test_few_comparables_limit_how_much_the_market_can_say():
    r = recommend_price("100", comps([300]))
    assert r.market_trust <= 0.5
    assert any("Only 1 comparable" in w for w in r.warnings)


def test_scattered_prices_lower_confidence():
    tight = recommend_price("100", comps([150, 151, 149, 150, 150, 151]))
    wide = recommend_price("100", comps([60, 250, 90, 300, 120, 220]))
    assert wide.confidence < tight.confidence


def test_price_band_contains_the_recommendation():
    r = recommend_price("100", comps([140, 160, 150, 155, 145, 152]))
    assert r.low <= r.recommended <= r.high


def test_results_are_two_decimal_money_and_deterministic():
    a = recommend_price("123.4567", comps([180, 181, 179, 182, 178]))
    b = recommend_price("123.4567", comps([180, 181, 179, 182, 178]))
    assert a == b
    assert a.recommended == a.recommended.quantize(D("0.01"))


def test_invalid_cost_is_rejected():
    with pytest.raises(ValueError):
        recommend_price("0", [])


def test_weighted_quantile_and_sample_size_helpers():
    assert weighted_quantile([(D(1), 1.0), (D(3), 1.0)], 0.5) == D(2)
    assert weighted_quantile([(D(1), 1.0), (D(2), 1.0), (D(9), 1.0)], 0.5) == D(2)
    assert effective_sample_size([1, 1, 1, 1]) == 4
    assert effective_sample_size([10, 0.01, 0.01]) < 1.1      # one dominant weight = about one sample
    kept, removed = remove_outliers(comps([10, 11, 9, 10, 400]), 3.5)
    assert removed == 1 and len(kept) == 4


def test_error_metrics_measure_recommendation_quality():
    m = error_metrics([("110", "100"), ("90", "100"), ("100", "100")])
    assert m["n"] == 3 and m["mape"] == round((0.1 + 0.1 + 0) / 3, 4)
    assert m["bias"] == 0.0 and m["within_10pct"] == 1.0
    assert error_metrics([])["n"] == 0
