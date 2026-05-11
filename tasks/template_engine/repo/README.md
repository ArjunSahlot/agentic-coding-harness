# Mini Template Engine

Fix a small template renderer with variables, loops, conditionals, filters, and HTML escaping.

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


            The renderer supports a deliberately small template language:
            variables with dotted lookup (`{{ user.name }}`), filters
            separated by pipes, for loops (`{% for item in items %}`), and
            if/else blocks (`{% if user.active %}`).

            Output is HTML-escaped by default. The `safe` filter marks a
            value as already safe. Supported filters are `upper`, `lower`,
            `default:"text"`, and `safe`. Missing values render as an empty
            string unless a default filter is supplied.

            Loop bodies receive the loop variable and a `loop.index` value
            starting at 1. Nested blocks are not required beyond the simple
            combinations covered by tests, but the implementation should be
            deterministic and avoid executing arbitrary Python expressions.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
