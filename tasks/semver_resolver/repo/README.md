# Semver Resolver

Repair version comparison and constraint resolution for a tiny package resolver.

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


            The resolver chooses the highest available version that satisfies
            a constraint string. Available versions are dictionaries with a
            `version` string and optional `yanked` boolean.

            Supported constraints are comma-separated comparisons using
            `>`, `>=`, `<`, `<=`, and `==`. A caret constraint such as
            `^1.2.3` means `>=1.2.3,<2.0.0`; `^0.2.3` means
            `>=0.2.3,<0.3.0`; and `^0.0.3` means `>=0.0.3,<0.0.4`.

            Versions use SemVer precedence. Numeric major, minor, and patch
            components compare numerically, not lexically. A pre-release
            version like `1.4.0-rc.1` sorts below `1.4.0`. Pre-release
            versions should not be selected unless at least one constraint
            operand itself names a pre-release.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
