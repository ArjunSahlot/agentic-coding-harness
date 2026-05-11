from __future__ import annotations

from decimal import Decimal


def render_item_summary(totals: dict[str, Decimal]) -> str:
    lines = ["item_id,allocated"]
    for item_id in sorted(totals):
        lines.append(f"{item_id},{totals[item_id]:.2f}")
    return "\n".join(lines)
