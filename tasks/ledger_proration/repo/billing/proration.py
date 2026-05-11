from __future__ import annotations

from decimal import Decimal

from .models import CENT, LineItem, Payment, money


def allocate_payments(items: list[LineItem], payments: list[Payment]) -> list[dict]:
    # BUG: This uses floats and rounded dollars directly. It also
    # includes adjustment lines in the denominator and treats
    # credits as positive cash.
    total = sum(float(item.amount) for item in items)
    allocations: list[dict] = []
    if not items or total == 0:
        return allocations

    for payment in payments:
        for item in items:
            raw = float(item.amount) / total * float(payment.amount)
            allocations.append(
                {
                    "payment_id": payment.id,
                    "item_id": item.id,
                    "account": item.account,
                    "amount": money(round(raw, 2)),
                }
            )
    return allocations


def summarize_by_item(allocations: list[dict]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for allocation in allocations:
        item_id = allocation["item_id"]
        totals[item_id] = totals.get(item_id, Decimal("0.00")) + allocation["amount"]
    return {key: value.quantize(CENT) for key, value in totals.items()}
