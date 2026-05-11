# Log Window Rollups

Fix UTC log parsing and window aggregation for service health dashboards.

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


            The dashboard groups plain-text logs into fixed-width UTC time
            windows. Each line starts with an ISO timestamp ending in `Z`,
            then an uppercase level, then key=value fields. At minimum, the
            parser should understand a `service` field.

            Bucket starts are inclusive and bucket ends are exclusive. A log
            at exactly 00:01:00 belongs to the 00:01:00 bucket, not the
            previous one. Rollups should fill empty windows between the
            first and last observed bucket so charts do not skip gaps.

            Severity filtering uses DEBUG < INFO < WARNING < ERROR <
            CRITICAL. Counts are keyed by pipe-joined group values, such as
            `api|ERROR` for group_by=("service", "level").


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
