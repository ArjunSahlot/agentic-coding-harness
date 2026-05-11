# Route Planner

Fix a dispatch route planner so it uses weighted travel times and edge closure intervals.

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


            The planner routes a driver through a directed graph. Each edge
            has a travel time in minutes and optional closure intervals.
            Closure intervals are absolute minute ranges `[start, end)`.

            The planner should find the earliest arrival, not the fewest
            hops. If an edge would overlap a closure interval, the driver may
            wait until the closure ends and then traverse the edge. Waiting
            is part of elapsed travel time. Return the path, the total
            elapsed minutes from requested departure, and the absolute
            arrival minute.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
