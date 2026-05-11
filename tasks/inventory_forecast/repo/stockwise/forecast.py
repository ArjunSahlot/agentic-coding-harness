from __future__ import annotations

import math
from datetime import date, timedelta


def _recent(entries: list[dict], today: date, days: int) -> list[dict]:
    start = today - timedelta(days=days)
    return [entry for entry in entries if start <= date.fromisoformat(entry["date"]) < today]


def recommend(skus: list[dict], history: list[dict], today: date) -> list[dict]:
    results = []
    by_sku: dict[str, list[dict]] = {}
    for entry in history:
        by_sku.setdefault(entry["sku"], []).append(entry)

    for sku in skus:
        rows = _recent(by_sku.get(sku["sku"], []), today, sku.get("lookback_days", 14))
        avg = sum(row.get("units_sold", 0) for row in rows) / max(1, len(rows))
        target = math.ceil(avg * sku.get("lead_time_days", 0))
        qty = max(0, target - sku.get("on_hand", 0))
        results.append({"sku": sku["sku"], "avg_daily_demand": avg, "target_stock": target, "recommended_qty": qty})
    return results
