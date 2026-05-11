from __future__ import annotations

import unittest
from decimal import Decimal

from events import LedgerState, replay


class AdditionalEventStoreTests(unittest.TestCase):
    def test_successful_transfer_debits_source_and_credits_target(self):
        events = [
            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "9.00"},
            {"id": "t1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "transfer", "account": "cash", "target": "savings", "amount": "4.50"},
            {"id": "t1", "timestamp": "2026-01-01T00:00:02Z", "sequence": 3, "type": "transfer", "account": "cash", "target": "savings", "amount": "1.00"},
        ]

        state = replay(events)

        self.assertEqual(state.balances["cash"], Decimal("4.50"))
        self.assertEqual(state.balances["savings"], Decimal("4.50"))
        self.assertEqual(state.applied_ids, {"d1", "t1"})

    def test_transfer_overdraft_does_not_credit_target(self):
        events = [
            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "2.00"},
            {"id": "t1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "transfer", "account": "cash", "target": "savings", "amount": "5.00"},
        ]

        state = replay(events)

        self.assertEqual(state.balances["cash"], Decimal("2.00"))
        self.assertNotIn("savings", state.balances)
        self.assertEqual(state.rejected[0]["id"], "t1")

    def test_opening_snapshot_is_not_mutated_by_replay(self):
        opening = LedgerState(balances={"cash": Decimal("1.00")}, applied_ids={"d0"})

        state = replay(
            [{"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "2.00"}],
            opening,
        )

        self.assertEqual(state.balances["cash"], Decimal("3.00"))
        self.assertEqual(opening.balances, {"cash": Decimal("1.00")})
        self.assertEqual(opening.applied_ids, {"d0"})


if __name__ == "__main__":
    unittest.main()
