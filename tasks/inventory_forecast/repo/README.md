# Inventory Forecast

Fix replenishment recommendations that account for stockouts, pack sizes, open orders, and caps.

This is a benchmark fixture for a coding agent. The project is deliberately
small enough to inspect in one sitting, but the relevant behavior is spread
across README notes, implementation modules, fixtures, and tests.

## Ground Rules

- Runtime: Python 3.12 or newer.
- Dependencies: Python standard library only.
- Public APIs used by tests should remain stable.
- Prefer deterministic behavior; benchmark scoring depends on repeatable
  verification.

## Domain Notes


            The recommender estimates average daily demand over a lookback
            window. Days where the product was out of stock should be
            excluded from the denominator because zero sales on those days
            do not mean zero demand.

            Target stock is `ceil(avg_daily_demand * (lead_time_days +
            safety_days))`. Recommended quantity is target minus on-hand and
            already-on-order units. If positive, round up to the SKU pack
            size. Do not recommend more than `max_stock - on_hand -
            on_order`. If the final positive recommendation is below
            `min_order`, use `min_order` rounded to pack size, still
            respecting the cap.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
