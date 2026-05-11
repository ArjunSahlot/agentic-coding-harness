# Event Store Snapshots

Fix ledger replay so account snapshots are ordered, idempotent, and reject overdrafts.

You are working in a temporary copy of the repository under `repo/`.
Fix the implementation so the verification suite passes.

Constraints:
- Use only the Python standard library.
- Do not download packages or call network services.
- Keep changes focused on the implementation files.
- Preserve the public APIs used by the tests.

Verification command:

```bash
python -m unittest discover -s tests -v
```
