# Markdown Outline Indexer

Fix a Markdown indexer so it creates GitHub-style heading anchors and link records while ignoring code examples.

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
