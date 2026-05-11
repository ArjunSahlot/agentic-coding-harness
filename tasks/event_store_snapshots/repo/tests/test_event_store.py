from __future__ import annotations

import unittest
from decimal import Decimal

from events import LedgerState, replay


class EventStoreTests(unittest.TestCase):
    def test_replay_sorts_by_timestamp_then_sequence(self):
        events = [
            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "99.00"},
            {"id": "w1", "timestamp": "2026-01-02T00:00:00Z", "sequence": 3, "type": "withdrawal", "account": "cash", "amount": "4.00"},
            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "10.00"},
        ]

        state = replay(events)

        self.assertEqual(state.balances["cash"], Decimal("6.00"))
        self.assertEqual(state.rejected, [])

    def test_duplicate_event_ids_are_ignored(self):
        events = [
            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "10.00"},
            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "10.00"},
        ]

        state = replay(events)

        self.assertEqual(state.balances["cash"], Decimal("10.00"))
        self.assertEqual(state.applied_ids, {"d1"})

    def test_overdrafts_are_rejected_without_mutating_balance(self):
        events = [
            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "5.00"},
            {"id": "w1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "withdrawal", "account": "cash", "amount": "7.00"},
        ]

        state = replay(events)

        self.assertEqual(state.balances["cash"], Decimal("5.00"))
        self.assertEqual(state.applied_ids, {"d1"})
        self.assertEqual(state.rejected[0]["id"], "w1")

    def test_opening_snapshot_applied_ids_are_respected(self):
        opening = LedgerState(balances={"cash": Decimal("3.00")}, applied_ids={"d0"})
        events = [
            {"id": "d0", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "3.00"},
            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "2.00"},
        ]

        state = replay(events, opening)

        self.assertEqual(state.balances["cash"], Decimal("5.00"))
        self.assertEqual(state.applied_ids, {"d0", "d1"})


if __name__ == "__main__":
    unittest.main()
