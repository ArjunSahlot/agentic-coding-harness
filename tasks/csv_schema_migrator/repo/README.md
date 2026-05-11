# CSV Schema Migrator

Fix a legacy CSV row migrator with aliases, typed coercion, and row-level error reporting.

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


            The migration pipeline receives rows from old CSV exports after
            csv.DictReader has converted them to dictionaries. The schema
            maps canonical field names to aliases, type information, and
            whether the field is required.

            The migrator returns `(records, errors)`. Valid rows become
            dictionaries containing only canonical fields. Unknown source
            columns are ignored. Invalid rows are omitted from records and
            reported with a 1-based row number plus a readable message.

            Supported types are `str`, `int`, `bool`, and `date`. Strings
            are stripped. Booleans accept yes/no, true/false, y/n, and 1/0.
            Dates are emitted in ISO `YYYY-MM-DD` form and accept
            `YYYY-MM-DD`, `MM/DD/YYYY`, and `DD Mon YYYY`.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
