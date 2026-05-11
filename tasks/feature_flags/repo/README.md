# Feature Flag Evaluator

Fix a deterministic feature flag evaluator with environments, overrides, rules, and percentage rollout.

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


            Feature configuration is a dictionary keyed by flag name. Each
            flag can have environment-specific settings under `environments`.
            Evaluation order is: environment default, percentage rollout,
            first matching rule, and finally explicit user override. The
            later entries in that sentence win over earlier ones.

            Rules may match a segment (`segment`) or required user
            attributes (`attributes`). A user has `key`, optional `segments`,
            and optional `attributes`. Percentage rollout is deterministic:
            compute SHA-256 of `flag_key:user_key`, take the first 8 hex
            characters as an integer, and modulo 100.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
