from __future__ import annotations

import unittest
from decimal import Decimal

from billing import LineItem, Payment, allocate_payments, money, summarize_by_item


class ProrationTests(unittest.TestCase):
    def test_largest_remainder_conserves_payment_cents(self):
        items = [
            LineItem("a", "sales", money("1.00")),
            LineItem("b", "sales", money("1.00")),
            LineItem("c", "sales", money("1.00")),
        ]
        payments = [Payment("p1", money("10.00"))]

        allocations = allocate_payments(items, payments)
        totals = summarize_by_item(allocations)

        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("10.00"))
        self.assertEqual(totals, {"a": money("3.34"), "b": money("3.33"), "c": money("3.33")})

    def test_credit_allocations_are_negative(self):
        items = [
            LineItem("hosting", "revenue", money("20.00")),
            LineItem("support", "revenue", money("10.00")),
        ]
        payments = [Payment("credit-7", money("12.00"), kind="credit")]

        totals = summarize_by_item(allocate_payments(items, payments))

        self.assertEqual(totals["hosting"], money("-8.00"))
        self.assertEqual(totals["support"], money("-4.00"))
        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("-12.00"))

    def test_zero_and_negative_items_are_not_denominator_members(self):
        items = [
            LineItem("base", "sales", money("10.00")),
            LineItem("zero", "sales", money("0.00")),
            LineItem("discount", "discounts", money("-5.00")),
        ]
        payments = [Payment("cash", money("5.00"))]

        totals = summarize_by_item(allocate_payments(items, payments))

        self.assertEqual(totals["base"], money("5.00"))
        self.assertEqual(totals["zero"], money("0.00"))
        self.assertEqual(totals["discount"], money("0.00"))

    def test_multiple_payments_keep_payment_identity_and_order(self):
        items = [
            LineItem("a", "sales", money("6.00")),
            LineItem("b", "sales", money("4.00")),
        ]
        payments = [
            Payment("cash-1", money("10.00")),
            Payment("credit-1", money("2.50"), kind="credit"),
        ]

        allocations = allocate_payments(items, payments)

        self.assertEqual([row["payment_id"] for row in allocations[:2]], ["cash-1", "cash-1"])
        self.assertEqual([row["payment_id"] for row in allocations[2:]], ["credit-1", "credit-1"])
        self.assertEqual([row["amount"] for row in allocations], [money("6.00"), money("4.00"), money("-1.50"), money("-1.00")])


if __name__ == "__main__":
    unittest.main()
