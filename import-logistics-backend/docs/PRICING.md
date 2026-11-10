# Pricing Recommendations

## 1. What it does

All amounts in requests and responses are exact decimals (the same `Money` type as the rest of the API: up to 4 decimal places, written as JSON numbers). Ratios such as confidence and margins are plain numbers.

For an item, the engine recommends a selling price, a price band (low to high), a confidence (0 to 1),
the expected margin, and plain-language reasons and warnings. A person stays in charge: it advises, it does not set prices.

## 2. Why it is not a simple average

The first version averaged three numbers (cost-plus, market average, last sold). Reviewing it found real problems:

| Problem in the old logic | Effect | Now |
|--------------------------|--------|-----|
| Market prices in NGN, EUR and CZK were averaged as if they were one currency | Nonsense prices | Every comparable is converted to USD first |
| "Last sold" looked at every organisation's sales | Data leak and wrong signal | Only your organisation's sales |
| One bad listing (a 5,000 among 150s) moved the mean | Wild recommendations | Statistical outliers are removed; a weighted **median** is used |
| A 6-month-old listing counted like today's | Stale prices | Weight halves every 30 days; listings older than 180 days are ignored |
| Cost-plus was treated as just another "market" number | Cost logic diluted | Cost-plus is the anchor; the market signal is blended in by a trust score |
| It could recommend below cost | Silent losses | A minimum-margin floor (default 5%) is enforced, with a warning |
| No sense of how reliable the number was | False certainty | Confidence, band and warnings |

## 3. How it works

1. **Cost basis** = landed cost (after cost allocation). If costs are not allocated yet, the purchase price is used and a warning says so.
2. **Cost-plus** = cost x (1 + target margin, default 20%). **Floor** = cost x (1 + minimum margin, default 5%).
3. **Comparables**: recent market prices (converted to USD) plus your own completed sales of similar items (same category and condition).
4. **Outlier removal** (4 or more comparables): drop prices whose modified z-score (median absolute deviation) exceeds 3.5.
5. **Weights**: `recency x source reliability x scraper confidence x (1.5 if your own sale)`, where recency = 0.5 ^ (age / 30 days).
   Source reliability defaults: eBay, mobile.de, AutoScout24 = 1.0; Jiji = 0.8; Bazos = 0.7.
6. **Market reference** = weighted median; the band comes from the weighted 25th and 75th percentiles.
7. **Trust** in the market = (effective sample size / 6, capped at 1) x 1 / (1 + price spread), capped at 85%. With fewer than 3 comparables it is capped at 50%.
   Effective sample size (Kish) is how many equally-weighted prices the weights are worth.
8. **Blend**: `recommended = trust x market median + (1 - trust) x cost-plus`, then **raised to the floor** if lower.
9. **Output**: recommended price, band, confidence (= trust), expected margin, number of comparables, warnings, explanation.

## 4. Reading the result

| Signal | Meaning | What to do |
|--------|---------|------------|
| High confidence, narrow band | Many consistent, recent comparables | Use the recommendation |
| Low confidence | Few or scattered comparables | Treat as cost-plus; check the market manually |
| Warning: market below landed cost | Selling at market loses money | Hold, negotiate, or accept a loss knowingly |
| Warning: raised to the floor | Market supports less than your minimum margin | Same as above |
| Warning: no market data | Cost-plus only | Run `POST /pricing/refresh-market/{item_id}` |

## 5. Measuring accuracy

`GET /api/v1/pricing/accuracy` (manager+) compares each sold item's last recommendation with its actual sale price:

| Metric | Meaning | Healthy |
|--------|---------|---------|
| `mape` | Mean absolute percentage error | Under about 0.15 |
| `bias` | Positive = recommending too high, negative = too low | Close to 0 |
| `within_10pct` | Share of sales within 10% of the recommendation | Above about 0.6 |

Caveat: the stored recommendation is the most recent one, which may have been generated after the sale. For a rigorous backtest, store each recommendation with a timestamp and compare only those made before the sale.

## 6. Tuning

| Setting | Default | Effect |
|---------|---------|--------|
| `DEFAULT_PROFIT_MARGIN` | 0.20 | Target margin (per request you can pass `profit_margin`, 0.05 to 1.0) |
| `PRICING_MIN_MARGIN` | 0.05 | The floor |
| `PRICING_HALF_LIFE_DAYS` | 30 | Raise for slow-moving goods (vehicles), lower for fast-moving ones (phones) |
| `PRICING_MAX_COMP_AGE_DAYS` | 180 | Ignore older market prices |

Source weights and trust caps live in `app/utils/pricing_math.py` (`SOURCE_WEIGHTS`, `PricingPolicy`). Change them only with the accuracy report in hand.

## 7. Limits and next steps

* Comparables are matched by item name search on each site; poor matches add noise (the outlier filter and confidence help, they do not fix it).
* Condition is only used for your own sales. Scraped listings are not condition-adjusted.
* Landing time, seasonality and demand are not modelled; `demand_analytics` is the place to add them.
* The next real upgrade is learning from your own sales: with a few hundred sold items per category, fit a regression of sale price on cost, market median, condition and age, and compare it against this engine using the accuracy metrics.
* All price maths is in `app/utils/pricing_math.py` (standard library only) with 14 unit tests (`app/tests/test_pricing_math.py`).
