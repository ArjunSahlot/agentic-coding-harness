from __future__ import annotations

import unittest
from datetime import date

from stockwise import recommend


class AdditionalInventoryForecastTests(unittest.TestCase):
    def test_history_outside_lookback_is_ignored(self):
        skus = [{"sku": "A", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 1, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 2}]
        history = [
            {"sku": "A", "date": "2026-01-01", "units_sold": 100, "in_stock": True},
            {"sku": "A", "date": "2026-01-09", "units_sold": 4, "in_stock": True},
        ]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["avg_daily_demand"], 4.0)
        self.assertEqual(row["target_stock"], 8)
        self.assertEqual(row["recommended_qty"], 8)

    def test_all_stockout_window_recommends_zero(self):
        skus = [{"sku": "B", "on_hand": 0, "on_order": 0, "lead_time_days": 3, "safety_days": 2, "pack_size": 5, "max_stock": 100, "min_order": 5, "lookback_days": 2}]
        history = [
            {"sku": "B", "date": "2026-01-08", "units_sold": 5, "in_stock": False},
            {"sku": "B", "date": "2026-01-09", "units_sold": 0, "in_stock": False},
        ]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["avg_daily_demand"], 0.0)
        self.assertEqual(row["target_stock"], 0)
        self.assertEqual(row["recommended_qty"], 0)

    def test_minimum_order_is_rounded_to_pack_size(self):
        skus = [{"sku": "C", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 0, "pack_size": 4, "max_stock": 100, "min_order": 5, "lookback_days": 1}]
        history = [{"sku": "C", "date": "2026-01-09", "units_sold": 2, "in_stock": True}]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["target_stock"], 2)
        self.assertEqual(row["recommended_qty"], 8)

    def test_multiple_skus_are_forecast_independently(self):
        skus = [
            {"sku": "D", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 0, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 1},
            {"sku": "E", "on_hand": 0, "on_order": 3, "lead_time_days": 1, "safety_days": 0, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 1},
        ]
        history = [
            {"sku": "D", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
            {"sku": "E", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
        ]

        rows = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual([row["sku"] for row in rows], ["D", "E"])
        self.assertEqual([row["recommended_qty"] for row in rows], [3, 0])


if __name__ == "__main__":
    unittest.main()
