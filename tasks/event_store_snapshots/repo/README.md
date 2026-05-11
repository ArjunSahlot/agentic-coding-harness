# Event Store Snapshots

Fix ledger replay so account snapshots are ordered, idempotent, and reject overdrafts.

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


            The event store rebuilds account balances from immutable events.
            Input order is not guaranteed, so events must be applied by
            `(timestamp, sequence)` order. Duplicate event ids are ignored.

            Supported types are `deposit`, `withdrawal`, and `transfer`.
            Withdrawals and transfers must not make the source account
            negative. Rejected events are recorded with their id and reason
            and are not included in applied ids.

            The replay function may receive an opening snapshot with
            balances and already-applied ids. This allows incremental
            rebuilds; duplicate ids from the snapshot should not be applied
            again.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
