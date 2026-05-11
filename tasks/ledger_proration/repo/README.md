# Ledger Proration

Repair payment allocation logic for a small billing ledger that must conserve cents across cash payments and credits.

This is a benchmark fixture for a coding agent. The project is deliberately
small enough to inspect in one sitting, but the relevant behavior is spread
across README notes, implementation modules, fixtures, and tests.

## Ground Rules

- Runtime: Python 3.12 or newer.
- Dependencies: Python standard library only.
- Public APIs used by tests should remain stable.
- Prefer deterministic behavior; benchmark scoring depends on repeatable
  verification.

## Domain Notes


            The billing service receives positive invoice line items and one
            or more payment records. Each payment must be allocated across
            positive line items in proportion to the line amount.

            Money is represented as Decimal dollars with two fractional
            digits. Allocation is performed in integer cents: compute the
            exact fractional cents for each positive line item, floor each
            share, and distribute leftover cents to the largest fractional
            remainders. If remainders tie, use the line item id in ascending
            lexical order so results are stable.

            Payment kind `cash` produces positive allocations. Payment kind
            `credit` represents a customer credit applied to the invoice; it
            has a positive amount on the input record, but the resulting
            allocations are negative. Zero and negative line items remain
            visible in reports but must receive a 0.00 allocation and must
            not contribute to the allocation denominator.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
