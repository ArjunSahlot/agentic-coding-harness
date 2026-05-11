# Line Diff Reporter

Fix a line diff summarizer with whitespace-insensitive mode and merged context windows.

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


            The reporter emits compact hunk dictionaries for review tools.
            Each hunk has 1-based `old_start` and `new_start`, plus
            `old_lines` and `new_lines` lists. Context lines are included on
            both sides. Nearby changes whose context overlaps should be
            merged into one hunk.

            When `ignore_whitespace=True`, lines are compared after
            collapsing all runs of whitespace to a single space and trimming
            edges. The original lines should still be shown in hunks when a
            substantive change remains.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
