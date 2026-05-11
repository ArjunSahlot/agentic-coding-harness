from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class LedgerState:
    balances: dict[str, Decimal] = field(default_factory=dict)
    applied_ids: set[str] = field(default_factory=set)
    rejected: list[dict] = field(default_factory=list)


def _amount(event: dict) -> Decimal:
    return Decimal(str(event["amount"]))


def replay(events: list[dict], opening: LedgerState | None = None) -> LedgerState:
    state = opening or LedgerState()
    for event in events:
        event_id = event["id"]
        amount = _amount(event)
        kind = event["type"]
        account = event.get("account")
        if kind == "deposit":
            state.balances[account] = state.balances.get(account, Decimal("0")) + amount
        elif kind == "withdrawal":
            state.balances[account] = state.balances.get(account, Decimal("0")) - amount
        elif kind == "transfer":
            target = event["target"]
            state.balances[account] = state.balances.get(account, Decimal("0")) - amount
            state.balances[target] = state.balances.get(target, Decimal("0")) + amount
        state.applied_ids.add(event_id)
    return state
