from __future__ import annotations

import unittest
from datetime import date

from stockwise import recommend


class InventoryForecastTests(unittest.TestCase):
    def test_excludes_stockout_days_from_average(self):
        skus = [{"sku": "A", "on_hand": 0, "on_order": 0, "lead_time_days": 2, "safety_days": 1, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 4}]
        history = [
            {"sku": "A", "date": "2026-01-06", "units_sold": 4, "in_stock": True},
            {"sku": "A", "date": "2026-01-07", "units_sold": 0, "in_stock": False},
            {"sku": "A", "date": "2026-01-08", "units_sold": 6, "in_stock": True},
            {"sku": "A", "date": "2026-01-09", "units_sold": 0, "in_stock": False},
        ]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["avg_daily_demand"], 5.0)
        self.assertEqual(row["target_stock"], 15)
        self.assertEqual(row["recommended_qty"], 15)

    def test_accounts_for_open_orders_and_rounds_to_pack_size(self):
        skus = [{"sku": "B", "on_hand": 3, "on_order": 4, "lead_time_days": 2, "safety_days": 2, "pack_size": 6, "max_stock": 50, "min_order": 1, "lookback_days": 3}]
        history = [
            {"sku": "B", "date": "2026-01-07", "units_sold": 3, "in_stock": True},
            {"sku": "B", "date": "2026-01-08", "units_sold": 3, "in_stock": True},
            {"sku": "B", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
        ]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["target_stock"], 12)
        self.assertEqual(row["recommended_qty"], 6)

    def test_respects_max_stock_cap_and_min_order(self):
        skus = [{"sku": "C", "on_hand": 18, "on_order": 0, "lead_time_days": 5, "safety_days": 1, "pack_size": 5, "max_stock": 21, "min_order": 4, "lookback_days": 2}]
        history = [
            {"sku": "C", "date": "2026-01-08", "units_sold": 4, "in_stock": True},
            {"sku": "C", "date": "2026-01-09", "units_sold": 4, "in_stock": True},
        ]

        [row] = recommend(skus, history, date(2026, 1, 10))

        self.assertEqual(row["recommended_qty"], 3)


if __name__ == "__main__":
    unittest.main()
