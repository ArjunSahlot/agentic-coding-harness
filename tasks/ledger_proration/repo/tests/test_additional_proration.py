from __future__ import annotations

import unittest
from decimal import Decimal

from billing import LineItem, Payment, allocate_payments, money, summarize_by_item


class AdditionalProrationTests(unittest.TestCase):
    def test_remainder_ties_are_awarded_by_lexical_item_id(self):
        items = [
            LineItem("b", "sales", money("1.00")),
            LineItem("a", "sales", money("1.00")),
            LineItem("c", "sales", money("1.00")),
        ]

        totals = summarize_by_item(allocate_payments(items, [Payment("penny", money("0.01"))]))

        self.assertEqual(totals, {"a": money("0.01"), "b": money("0.00"), "c": money("0.00")})

    def test_all_non_positive_items_receive_zero_allocations(self):
        items = [
            LineItem("fee-waiver", "discounts", money("-3.00")),
            LineItem("note", "sales", money("0.00")),
        ]

        totals = summarize_by_item(allocate_payments(items, [Payment("cash", money("5.00"))]))

        self.assertEqual(totals, {"fee-waiver": money("0.00"), "note": money("0.00")})
        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("0.00"))

    def test_cash_and_equal_credit_net_to_zero_by_item(self):
        items = [
            LineItem("seat", "sales", money("30.00")),
            LineItem("storage", "sales", money("10.00")),
        ]
        payments = [
            Payment("cash", money("8.00")),
            Payment("credit", money("8.00"), kind="credit"),
        ]

        totals = summarize_by_item(allocate_payments(items, payments))

        self.assertEqual(totals["seat"], money("0.00"))
        self.assertEqual(totals["storage"], money("0.00"))


if __name__ == "__main__":
    unittest.main()
