# Markdown Outline Indexer

Fix a Markdown indexer so it creates GitHub-style heading anchors and link records while ignoring code examples.

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


            The indexer is used by a documentation site before static
            publishing. It extracts headings and links from markdown files.
            It does not need to parse every markdown extension, but it must
            handle the patterns covered by the tests.

            Heading anchors should match GitHub-style slugs: trim, lowercase,
            remove punctuation other than spaces and hyphens, collapse
            whitespace to hyphens, and append `-1`, `-2`, ... for duplicate
            anchors in the same document.

            Links inside fenced code blocks and inline code spans are
            examples, not real links. Reference definitions like
            `[guide]: ../guide.md#Intro` should be resolved for usages like
            `[Guide][guide]`. Relative links are normalized against the
            directory containing the markdown file. Fragment identifiers are
            slug-normalized with the same anchor logic, but without duplicate
            suffixing.


## Verification

Run:

```bash
python -m unittest discover -s tests -v
```
