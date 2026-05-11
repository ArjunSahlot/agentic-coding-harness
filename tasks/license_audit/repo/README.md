# License Audit

Fix transitive dependency license auditing with normalized SPDX expressions and package exceptions.

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


            The audit receives a package graph dictionary. Each package has
            `license` and `deps`. The root package should be audited along
            with all transitive dependencies reachable from it.

            Policy has `allow`, `deny`, and optional `exceptions`. License
            names should be normalized for common aliases (`Apache 2` to
            `Apache-2.0`, `BSD 3-Clause` to `BSD-3-Clause`, etc.).

            SPDX expressions using `OR` are allowed if any option is
            allowed. Expressions using `AND` are allowed only if all parts
            are allowed. Denied licenses always fail unless an exception
            exists for the specific package and normalized license. Return
            violations as dictionaries with package, license, and reason.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
