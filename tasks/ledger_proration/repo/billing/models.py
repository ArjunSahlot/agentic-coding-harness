from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

CENT = Decimal("0.01")


def money(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT)


@dataclass(frozen=True)
class LineItem:
    id: str
    account: str
    amount: Decimal
    taxable: bool = True


@dataclass(frozen=True)
class Payment:
    id: str
    amount: Decimal
    kind: str = "cash"
