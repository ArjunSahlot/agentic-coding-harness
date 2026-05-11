#!/usr/bin/env python3
"""Generate the local SWE benchmark task set.

The generated tasks are intentionally self-contained and use only the Python
standard library. Re-run this script after editing task definitions below.
"""
from __future__ import annotations

import json
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    summary: str
    tags: list[str]
    estimated_context_tokens: int
    files: dict[str, str]


def clean(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean(content), encoding="utf-8")


def task_prompt(task: Task) -> str:
    return f"""
    # {task.title}

    {task.summary}

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
    """


def common_readme(task: Task, domain_notes: str) -> str:
    return f"""
    # {task.title}

    {task.summary}

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

    {domain_notes}

    ## Verification

    Run:

    ```bash
    python -m unittest discover -s tests -v
    ```
    """


CONTEXT_CASES: dict[str, list[dict[str, str]]] = {
    "ledger_proration": [
        {"title": "fractional cents", "detail": "Three equal revenue lines sharing a ten dollar payment create a leftover cent after flooring exact shares. The cent must go to the lexically first line id so nightly invoice exports remain stable."},
        {"title": "credit memo sign", "detail": "Customer credits arrive as positive source amounts because the upstream accounting feed stores the sign in the payment kind. Allocation rows carry the signed effect, so credits are negative allocations."},
        {"title": "adjustment lines", "detail": "Discount and zero-dollar rows stay in invoice reports, but they never earn a share of customer cash and never dilute the denominator used for positive charge lines."},
        {"title": "multiple tenders", "detail": "A card payment, an account credit, and a manual write-off may all touch the same invoice. Allocation rows should preserve payment order and payment ids so reconciliations can be traced."},
        {"title": "decimal safety", "detail": "Binary floats have caused one-cent drift in production exports. All money arithmetic should use Decimal or integer cents until the final Decimal dollar values are built."},
    ],
    "markdown_outline": [
        {"title": "slug compatibility", "detail": "The static site host links directly to GitHub-compatible anchors. Punctuation removal, whitespace collapse, and duplicate suffixes must match the documented behavior closely enough for existing links to keep working."},
        {"title": "example code", "detail": "Documentation authors often include markdown snippets showing intentionally broken links. Fenced code and inline code are instructional examples and should not become link-checker findings."},
        {"title": "reference definitions", "detail": "Long pages prefer reference-style links so repeated URLs are easier to maintain. Definitions are case-insensitive and should resolve before relative path normalization."},
        {"title": "fragment normalization", "detail": "Human-written fragments use spaces and punctuation. The indexer should normalize fragment ids using slug rules, but it should not apply duplicate suffixes across target documents it has not parsed."},
        {"title": "absolute and external targets", "detail": "HTTP, HTTPS, mailto, and root-relative links are already absolute in their own namespace. Only document-relative links should be joined to the current file directory."},
    ],
    "semver_resolver": [
        {"title": "numeric ordering", "detail": "Package feeds are strings, but SemVer components are numbers. Versions like 1.10.0 must sort after 1.9.9 even though lexical ordering says otherwise."},
        {"title": "yanked releases", "detail": "A yanked release can stay visible for lockfile reproducibility, but new resolution should skip it unless a future policy explicitly pins it. The current resolver never pins yanked versions."},
        {"title": "caret ranges", "detail": "Caret ranges are common in ecosystem manifests. The allowed upper bound is sensitive to leading zero components, so 0.2.x and 0.0.x behave differently from 1.x."},
        {"title": "pre-release opt-in", "detail": "Release candidates should not appear in ordinary stable ranges. They become eligible only when a constraint operand itself mentions a pre-release version."},
        {"title": "highest satisfying candidate", "detail": "Resolution should evaluate all constraints first, then choose the maximum SemVer candidate. Early return behavior can pick a lower version by accident."},
    ],
    "csv_schema_migrator": [
        {"title": "aliases from old exports", "detail": "Legacy customer exports used several header names for the same field. The migrator should look up canonical names and aliases without preserving unknown columns in the cleaned output."},
        {"title": "false-like booleans", "detail": "A non-empty string such as 'no' is truthy in Python but false in the data contract. The boolean coercer must map accepted words explicitly and reject ambiguous values."},
        {"title": "date formats", "detail": "Support staff imported files from spreadsheet tools that emitted ISO dates, US slash dates, and day-month-name dates. The canonical record always stores ISO dates."},
        {"title": "row level errors", "detail": "Bad rows should not poison the entire migration. Accumulate errors with one-based row numbers so support can find the source line in the original CSV."},
        {"title": "partial optional data", "detail": "Optional fields may be absent or blank. They should appear in valid records as None so downstream code can rely on a stable canonical key set."},
    ],
    "log_window_rollups": [
        {"title": "UTC buckets", "detail": "The log stream uses Z timestamps. Bucketing should be timezone-aware and then rendered back to a Z suffix so dashboard snapshots are portable across developer machines."},
        {"title": "exclusive ends", "detail": "Window boundaries are start-inclusive and end-exclusive. A record exactly on the minute belongs to that minute's bucket, which avoids double counting during incremental refreshes."},
        {"title": "empty gaps", "detail": "Charts need explicit empty windows between observed buckets. Missing rows make line charts visually compress outages and make alert backtests harder to compare."},
        {"title": "severity threshold", "detail": "Filtering by minimum severity should use the ordering DEBUG, INFO, WARNING, ERROR, CRITICAL. String comparison is not a valid substitute."},
        {"title": "group keys", "detail": "The dashboard flattens group dimensions into pipe-joined strings. Missing dimensions should become empty strings rather than crashing the rollup."},
    ],
    "route_planner": [
        {"title": "earliest arrival", "detail": "Dispatch cares about arrival time, not hop count. A direct road can be slower than two short roads, so the planner needs weighted shortest path behavior."},
        {"title": "closure waits", "detail": "Road closures are intervals. If traversal would overlap a closure, waiting until the closure end is allowed and may still beat an alternate route."},
        {"title": "time dependent state", "detail": "Reaching the same node earlier is better, but reaching it later may still matter if an edge opens after a closure. Visited-state shortcuts must not discard useful timing information too aggressively."},
        {"title": "absolute minutes", "detail": "The benchmark uses integer minutes from an arbitrary epoch. Do not convert to wall-clock datetimes; closure ranges and arrivals are in the same minute coordinate system."},
        {"title": "traceable path", "detail": "The route result is used for explanations, so it must include the ordered path as well as travel and arrival minutes."},
    ],
    "template_engine": [
        {"title": "default escaping", "detail": "Templates render into HTML emails. Variables must be escaped by default so user-provided names and titles cannot inject markup."},
        {"title": "safe values", "detail": "Some snippets are pre-rendered by trusted code. The safe filter is the explicit escape hatch and should not leak to unrelated variables."},
        {"title": "loop context", "detail": "Simple receipt templates need a loop variable and loop.index for numbering. The implementation should create a child context per iteration instead of mutating shared caller state permanently."},
        {"title": "conditionals", "detail": "If/else blocks only need dotted truthy lookup. Avoid eval or arbitrary Python expressions; deterministic lookup is enough for the benchmark."},
        {"title": "filters with arguments", "detail": "The default filter receives a quoted string argument. Missing values and None should use it, while present falsey values such as 0 may still be meaningful."},
    ],
    "event_store_snapshots": [
        {"title": "unordered delivery", "detail": "Event files are merged from shards and may arrive out of order. Replay must sort by timestamp and sequence before applying financial effects."},
        {"title": "idempotent rebuild", "detail": "Retried ingestion can duplicate event ids. A duplicate id should be ignored, not rejected as an overdraft and not counted twice in balances."},
        {"title": "opening snapshots", "detail": "Incremental rebuilds begin from a snapshot with balances and applied ids. The replay should not mutate caller-owned collections in surprising ways if it needs to derive a new state."},
        {"title": "overdraft rejection", "detail": "Withdrawals and transfers cannot make source balances negative. Rejected events should include a reason and must not be added to applied ids."},
        {"title": "decimal amounts", "detail": "Amounts are strings in event payloads. Decimal conversion keeps replay deterministic for currency values."},
    ],
    "feature_flags": [
        {"title": "environment layering", "detail": "Staging and production can have different defaults and rules. The evaluator should read the requested environment and fall back deliberately rather than ignoring environment blocks."},
        {"title": "stable rollout", "detail": "Python's hash is process-randomized and random seeding has cross-flag collisions. Rollout buckets must use the specified SHA-256 flag/user key hash."},
        {"title": "rule matching", "detail": "Rules may target user segments or attribute equality. The first matching rule provides a value, then explicit overrides can still replace it."},
        {"title": "override precedence", "detail": "Support staff use overrides to force-enable or block individual users during incidents. Overrides are the final authority for a flag in an environment."},
        {"title": "unknown flags", "detail": "An unknown flag should evaluate to false rather than raising, which keeps client code resilient during staged config rollouts."},
    ],
    "inventory_forecast": [
        {"title": "stockout demand", "detail": "A zero-sales day while out of stock is missing demand, not low demand. Excluding those days avoids under-ordering popular items."},
        {"title": "lead plus safety", "detail": "Target stock includes both lead time and safety days. Ignoring safety days makes the recommender look good in quiet periods and fail during demand spikes."},
        {"title": "open orders", "detail": "Units already on order should reduce the recommended quantity. Otherwise buyers double-order when a purchase order is already in flight."},
        {"title": "pack rounding", "detail": "Vendors ship fixed pack sizes. Positive recommendations should round up to a pack multiple unless capped by max stock."},
        {"title": "caps and minimums", "detail": "Warehouse max stock is a hard cap. Minimum order quantities apply only when a positive recommendation remains possible under that cap."},
    ],
    "line_diff_reporter": [
        {"title": "whitespace mode", "detail": "Reviewers sometimes ask for semantic diffs that ignore formatting churn. Comparison can normalize whitespace, but displayed hunk lines should remain original text."},
        {"title": "one based starts", "detail": "Editor integrations use one-based line numbers. Raw SequenceMatcher indexes are zero-based, so hunk starts need adjustment after context expansion."},
        {"title": "context expansion", "detail": "Each change should include nearby equal lines on both old and new sides. Context helps reviewers understand a compact hunk without opening the full file."},
        {"title": "merged windows", "detail": "Two changes close together should appear as one hunk when their context overlaps. Separate overlapping hunks duplicate lines and confuse review comments."},
        {"title": "insertions and deletions", "detail": "The same hunk format should support replacements, insertions, and deletions by allowing either side's line list to be empty after context is considered."},
    ],
    "license_audit": [
        {"title": "transitive graph", "detail": "A direct dependency can pull in a problematic transitive package. Auditing only the root package misses the cases policy reviewers care about."},
        {"title": "alias normalization", "detail": "Package metadata often uses human aliases such as Apache 2 or BSD 3-Clause. Normalize common aliases before comparing against SPDX policy names."},
        {"title": "OR expressions", "detail": "A package licensed as MIT OR GPL-3.0 can be consumed under MIT if MIT is allowed. The audit should not fail just because one alternative is denied."},
        {"title": "AND expressions", "detail": "A conjunctive expression requires satisfying every part. If any part is denied, the package is a violation with reason denied."},
        {"title": "package exceptions", "detail": "Legal approvals are package-specific. An exception for one LGPL package should not broadly allow LGPL across the graph."},
    ],
}


def maintainer_context(task: Task) -> str:
    cases = CONTEXT_CASES.get(task.task_id, [])
    case_sections = []
    appendix_sections = []
    for index, case in enumerate(cases, start=1):
        case_sections.append(
            f"""
            ### Scenario {index}: {case['title']}

            {case['detail']}

            When solving the task, treat this scenario as a maintainer note rather
            than a full specification. The visible tests encode the scoring
            contract, while these notes explain why the code is shaped the way it
            is and where previous regressions happened. A strong fix usually
            respects both the test assertions and the operational motivation
            here.

            Suggested inspection path: read the relevant implementation module,
            search for the public API named in the tests, and compare current
            behavior against this scenario. Avoid broad rewrites unless the local
            design is already pointing in that direction.
            """
        )
        appendix_sections.append(
            f"""
            ### Context Slice {index}: {case['title']}

            Background signal: {case['detail']} In previous reviews, this kind
            of scenario was easy to miss when the agent looked only at the first
            failing assertion. The useful context is split between the README,
            the implementation comments, and the unit tests. A context reduction
            strategy should keep the public API, the data shape, and the edge
            case together.

            Input shape: expect compact dictionaries, dataclasses, or strings
            rather than a service container. The benchmark intentionally avoids
            external dependencies so the implementation can be checked by
            reading the local code. If a fix needs configuration, derive it from
            the function arguments or the nearby constants instead of adding a
            new global registry.

            Common false fix: patching only the literal example from one test
            tends to pass the narrow assertion but leaves the domain rule
            inconsistent. Prefer a small helper with a name that describes the
            rule. That gives future tests a clear place to exercise variants of
            `{case['title']}` without growing unrelated code paths.

            Review checklist: preserve ordering where the domain mentions
            traceability, avoid hidden mutation of caller-owned inputs, and make
            error cases explicit. The benchmark scorer can only count tests, but
            a maintainable answer should also make the next edge case easier to
            reason about.

            Context-reduction hint: the high-value tokens for this slice are
            the scenario title, the public API name from the tests, and the
            expected data contract. Lower-value tokens are historical anecdotes
            that do not change the algorithm. Keep the former if you summarize
            or compress this file.

            Verification note: after editing, run the unittest command from the
            task root. When a test fails, compare the actual value to the domain
            phrase above before changing the test or broadening the public API.
            """
        )

    return f"""
    # Maintainer Context

    This reference file exists to make the benchmark more realistic for
    context-management experiments. It contains useful details, historical
    regressions, and non-goals. Not every paragraph maps directly to one test,
    and some information is intentionally redundant with the README and tests.

    ## Task

    - Id: `{task.task_id}`
    - Title: {task.title}
    - Tags: {", ".join(task.tags)}
    - Estimated context target: {task.estimated_context_tokens} tokens

    ## Working Style

    The preferred solution is small, deterministic, and easy to verify with the
    standard-library unittest suite. The benchmark rewards fixes that preserve
    the documented public API and make the implementation easier to reason
    about. It does not reward adding external packages, shelling out to
    platform-specific tools, or changing tests to match the broken behavior.

    ## Historical Scenarios

    {"".join(case_sections)}

    ## Extended Review Notes

    The following slices are intentionally verbose. They provide enough local
    context for large-context and context-reduction experiments without
    requiring package downloads or internet access.

    {"".join(appendix_sections)}

    ## Non-goals

    Do not build a complete production framework for this fixture. The point is
    to repair the local behavior in a way that could plausibly be reviewed by a
    maintainer. Keep compatibility with Python 3.12, avoid network calls, and
    prefer straightforward data structures over clever global state.
    """


def regression_notes(task: Task) -> str:
    payload = {
        "task": task.task_id,
        "title": task.title,
        "cases": CONTEXT_CASES.get(task.task_id, []),
        "notes": [
            "These notes are not executed directly; the unittest suite is the scorer.",
            "They are included so agents can practice selecting relevant context.",
            "A correct implementation should be deterministic across repeated runs.",
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


TASKS: list[Task] = [
    Task(
        task_id="ledger_proration",
        title="Ledger Proration",
        summary="Repair payment allocation logic for a small billing ledger that must conserve cents across cash payments and credits.",
        tags=["finance", "decimal", "rounding", "allocation"],
        estimated_context_tokens=11500,
        files={
            "README.md": common_readme(
                Task("ledger_proration", "Ledger Proration", "Repair payment allocation logic for a small billing ledger that must conserve cents across cash payments and credits.", [], 0, {}),
                """
                The billing service receives positive invoice line items and one
                or more payment records. Each payment must be allocated across
                positive line items in proportion to the line amount.

                Money is represented as Decimal dollars with two fractional
                digits. Allocation is performed in integer cents: compute the
                exact fractional cents for each positive line item, floor each
                share, and distribute leftover cents to the largest fractional
                remainders. If remainders tie, use the line item id in ascending
                lexical order so results are stable.

                Payment kind `cash` produces positive allocations. Payment kind
                `credit` represents a customer credit applied to the invoice; it
                has a positive amount on the input record, but the resulting
                allocations are negative. Zero and negative line items remain
                visible in reports but must receive a 0.00 allocation and must
                not contribute to the allocation denominator.
                """,
            ),
            "billing/__init__.py": """
                from .models import LineItem, Payment, money
                from .proration import allocate_payments, summarize_by_item

                __all__ = [
                    "LineItem",
                    "Payment",
                    "money",
                    "allocate_payments",
                    "summarize_by_item",
                ]
            """,
            "billing/models.py": """
                from __future__ import annotations

                from dataclasses import dataclass
                from decimal import Decimal

                CENT = Decimal("0.01")


                def money(value: str | int | float | Decimal) -> Decimal:
                    return Decimal(str(value)).quantize(CENT)


                @dataclass(frozen=True)
                class LineItem:
                    id: str
                    account: str
                    amount: Decimal
                    taxable: bool = True


                @dataclass(frozen=True)
                class Payment:
                    id: str
                    amount: Decimal
                    kind: str = "cash"
            """,
            "billing/proration.py": """
                from __future__ import annotations

                from decimal import Decimal

                from .models import CENT, LineItem, Payment, money


                def allocate_payments(items: list[LineItem], payments: list[Payment]) -> list[dict]:
                    # BUG: This uses floats and rounded dollars directly. It also
                    # includes adjustment lines in the denominator and treats
                    # credits as positive cash.
                    total = sum(float(item.amount) for item in items)
                    allocations: list[dict] = []
                    if not items or total == 0:
                        return allocations

                    for payment in payments:
                        for item in items:
                            raw = float(item.amount) / total * float(payment.amount)
                            allocations.append(
                                {
                                    "payment_id": payment.id,
                                    "item_id": item.id,
                                    "account": item.account,
                                    "amount": money(round(raw, 2)),
                                }
                            )
                    return allocations


                def summarize_by_item(allocations: list[dict]) -> dict[str, Decimal]:
                    totals: dict[str, Decimal] = {}
                    for allocation in allocations:
                        item_id = allocation["item_id"]
                        totals[item_id] = totals.get(item_id, Decimal("0.00")) + allocation["amount"]
                    return {key: value.quantize(CENT) for key, value in totals.items()}
            """,
            "billing/reports.py": """
                from __future__ import annotations

                from decimal import Decimal


                def render_item_summary(totals: dict[str, Decimal]) -> str:
                    lines = ["item_id,allocated"]
                    for item_id in sorted(totals):
                        lines.append(f"{item_id},{totals[item_id]:.2f}")
                    return "\\n".join(lines)
            """,
            "tests/test_proration.py": """
                from __future__ import annotations

                import unittest
                from decimal import Decimal

                from billing import LineItem, Payment, allocate_payments, money, summarize_by_item


                class ProrationTests(unittest.TestCase):
                    def test_largest_remainder_conserves_payment_cents(self):
                        items = [
                            LineItem("a", "sales", money("1.00")),
                            LineItem("b", "sales", money("1.00")),
                            LineItem("c", "sales", money("1.00")),
                        ]
                        payments = [Payment("p1", money("10.00"))]

                        allocations = allocate_payments(items, payments)
                        totals = summarize_by_item(allocations)

                        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("10.00"))
                        self.assertEqual(totals, {"a": money("3.34"), "b": money("3.33"), "c": money("3.33")})

                    def test_credit_allocations_are_negative(self):
                        items = [
                            LineItem("hosting", "revenue", money("20.00")),
                            LineItem("support", "revenue", money("10.00")),
                        ]
                        payments = [Payment("credit-7", money("12.00"), kind="credit")]

                        totals = summarize_by_item(allocate_payments(items, payments))

                        self.assertEqual(totals["hosting"], money("-8.00"))
                        self.assertEqual(totals["support"], money("-4.00"))
                        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("-12.00"))

                    def test_zero_and_negative_items_are_not_denominator_members(self):
                        items = [
                            LineItem("base", "sales", money("10.00")),
                            LineItem("zero", "sales", money("0.00")),
                            LineItem("discount", "discounts", money("-5.00")),
                        ]
                        payments = [Payment("cash", money("5.00"))]

                        totals = summarize_by_item(allocate_payments(items, payments))

                        self.assertEqual(totals["base"], money("5.00"))
                        self.assertEqual(totals["zero"], money("0.00"))
                        self.assertEqual(totals["discount"], money("0.00"))

                    def test_multiple_payments_keep_payment_identity_and_order(self):
                        items = [
                            LineItem("a", "sales", money("6.00")),
                            LineItem("b", "sales", money("4.00")),
                        ]
                        payments = [
                            Payment("cash-1", money("10.00")),
                            Payment("credit-1", money("2.50"), kind="credit"),
                        ]

                        allocations = allocate_payments(items, payments)

                        self.assertEqual([row["payment_id"] for row in allocations[:2]], ["cash-1", "cash-1"])
                        self.assertEqual([row["payment_id"] for row in allocations[2:]], ["credit-1", "credit-1"])
                        self.assertEqual([row["amount"] for row in allocations], [money("6.00"), money("4.00"), money("-1.50"), money("-1.00")])


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_proration.py": """
                from __future__ import annotations

                import unittest
                from decimal import Decimal

                from billing import LineItem, Payment, allocate_payments, money, summarize_by_item


                class AdditionalProrationTests(unittest.TestCase):
                    def test_remainder_ties_are_awarded_by_lexical_item_id(self):
                        items = [
                            LineItem("b", "sales", money("1.00")),
                            LineItem("a", "sales", money("1.00")),
                            LineItem("c", "sales", money("1.00")),
                        ]

                        totals = summarize_by_item(allocate_payments(items, [Payment("penny", money("0.01"))]))

                        self.assertEqual(totals, {"a": money("0.01"), "b": money("0.00"), "c": money("0.00")})

                    def test_all_non_positive_items_receive_zero_allocations(self):
                        items = [
                            LineItem("fee-waiver", "discounts", money("-3.00")),
                            LineItem("note", "sales", money("0.00")),
                        ]

                        totals = summarize_by_item(allocate_payments(items, [Payment("cash", money("5.00"))]))

                        self.assertEqual(totals, {"fee-waiver": money("0.00"), "note": money("0.00")})
                        self.assertEqual(sum(totals.values(), Decimal("0.00")), money("0.00"))

                    def test_cash_and_equal_credit_net_to_zero_by_item(self):
                        items = [
                            LineItem("seat", "sales", money("30.00")),
                            LineItem("storage", "sales", money("10.00")),
                        ]
                        payments = [
                            Payment("cash", money("8.00")),
                            Payment("credit", money("8.00"), kind="credit"),
                        ]

                        totals = summarize_by_item(allocate_payments(items, payments))

                        self.assertEqual(totals["seat"], money("0.00"))
                        self.assertEqual(totals["storage"], money("0.00"))


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="markdown_outline",
        title="Markdown Outline Indexer",
        summary="Fix a Markdown indexer so it creates GitHub-style heading anchors and link records while ignoring code examples.",
        tags=["markdown", "parser", "normalization"],
        estimated_context_tokens=12200,
        files={
            "README.md": common_readme(
                Task("markdown_outline", "Markdown Outline Indexer", "Fix a Markdown indexer so it creates GitHub-style heading anchors and link records while ignoring code examples.", [], 0, {}),
                """
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
                """,
            ),
            "mdnav/__init__.py": """
                from .parser import collect_outline

                __all__ = ["collect_outline"]
            """,
            "mdnav/normalize.py": """
                from __future__ import annotations

                import posixpath
                import re


                def slugify(title: str) -> str:
                    slug = title.strip().lower().replace(" ", "-")
                    return slug


                def normalize_href(href: str, base_path: str) -> str:
                    if href.startswith(("http://", "https://", "mailto:")):
                        return href
                    base_dir = posixpath.dirname(base_path)
                    return posixpath.normpath(posixpath.join(base_dir, href))
            """,
            "mdnav/parser.py": """
                from __future__ import annotations

                import re

                from .normalize import normalize_href, slugify

                HEADING_RE = re.compile(r"^(#{1,6})\\s+(.+)$", re.MULTILINE)
                INLINE_LINK_RE = re.compile(r"\\[([^\\]]+)\\]\\(([^)]+)\\)")


                def collect_outline(text: str, base_path: str = "README.md") -> dict:
                    headings = []
                    for match in HEADING_RE.finditer(text):
                        headings.append(
                            {
                                "level": len(match.group(1)),
                                "title": match.group(2).strip(),
                                "anchor": slugify(match.group(2)),
                            }
                        )

                    links = []
                    for match in INLINE_LINK_RE.finditer(text):
                        links.append(
                            {
                                "label": match.group(1),
                                "target": normalize_href(match.group(2), base_path),
                                "kind": "inline",
                            }
                        )

                    return {"headings": headings, "links": links}
            """,
            "docs/sample.md": """
                # API Overview

                See [Guide](../guide.md#Intro Section).

                ```markdown
                [Not a link](fake.md)
                ```

                The text `[also ignored](fake.md)` is inline code.

                [Reference][ref]

                [ref]: ../reference.md#API Overview
            """,
            "tests/test_markdown_outline.py": """
                from __future__ import annotations

                import unittest

                from mdnav import collect_outline


                class MarkdownOutlineTests(unittest.TestCase):
                    def test_github_style_heading_anchors_and_duplicates(self):
                        doc = "# Hello, World!\\n## Hello World\\n### Hello   World?\\n"

                        headings = collect_outline(doc)["headings"]

                        self.assertEqual(
                            [h["anchor"] for h in headings],
                            ["hello-world", "hello-world-1", "hello-world-2"],
                        )
                        self.assertEqual([h["level"] for h in headings], [1, 2, 3])

                    def test_ignores_fenced_code_and_inline_code_links(self):
                        doc = '''
                        # Links

                        ```markdown
                        [Fake](bad.md)
                        ```

                        Real [Guide](../guide.md#Intro Section) and `inline [Nope](bad.md)`.
                        '''

                        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

                        self.assertEqual(len(links), 1)
                        self.assertEqual(links[0]["label"], "Guide")
                        self.assertEqual(links[0]["target"], "docs/guide.md#intro-section")

                    def test_reference_links_are_resolved_case_insensitively(self):
                        doc = '''
                        # Reference Test

                        See [Install Guide][GUIDE] and [API][api-ref].

                        [guide]: ../install.md#Install Steps
                        [api-ref]: /api/index.md#HTTP API
                        '''

                        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

                        self.assertEqual([link["target"] for link in links], ["docs/install.md#install-steps", "/api/index.md#http-api"])
                        self.assertEqual([link["kind"] for link in links], ["reference", "reference"])


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_markdown_outline.py": """
                from __future__ import annotations

                import unittest

                from mdnav import collect_outline


                class AdditionalMarkdownOutlineTests(unittest.TestCase):
                    def test_headings_inside_fenced_code_are_ignored(self):
                        doc = "# Real Heading

```markdown
## Fake Heading
```
"

                        headings = collect_outline(doc)["headings"]

                        self.assertEqual([heading["title"] for heading in headings], ["Real Heading"])

                    def test_external_and_mailto_links_are_not_rebased(self):
                        doc = "`[Skip](https://example.com/bad)` [Site](https://example.com/docs#Top) [Mail](mailto:help@example.com)"

                        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

                        self.assertEqual([link["target"] for link in links], ["https://example.com/docs#Top", "mailto:help@example.com"])

                    def test_relative_path_without_fragment_is_normalized(self):
                        doc = "![Logo](../assets/logo.png) and [Sibling](sibling.md#Intro Section)"

                        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

                        self.assertEqual([link["target"] for link in links], ["docs/assets/logo.png", "docs/pages/sibling.md#intro-section"])


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="semver_resolver",
        title="Semver Resolver",
        summary="Repair version comparison and constraint resolution for a tiny package resolver.",
        tags=["semver", "sorting", "constraints"],
        estimated_context_tokens=13100,
        files={
            "README.md": common_readme(
                Task("semver_resolver", "Semver Resolver", "Repair version comparison and constraint resolution for a tiny package resolver.", [], 0, {}),
                """
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
                """,
            ),
            "resolver/__init__.py": """
                from .semver import Version, resolve_versions, sort_versions

                __all__ = ["Version", "resolve_versions", "sort_versions"]
            """,
            "resolver/semver.py": """
                from __future__ import annotations

                from dataclasses import dataclass


                @dataclass(frozen=True)
                class Version:
                    raw: str

                    @classmethod
                    def parse(cls, raw: str) -> "Version":
                        return cls(raw)

                    def __lt__(self, other: "Version") -> bool:
                        return self.raw < other.raw

                    @property
                    def is_prerelease(self) -> bool:
                        return "-" in self.raw


                def sort_versions(versions: list[str]) -> list[str]:
                    return sorted(versions)


                def _matches(version: str, constraint: str) -> bool:
                    if not constraint:
                        return True
                    for part in [p.strip() for p in constraint.split(",") if p.strip()]:
                        if part.startswith(">=") and version < part[2:]:
                            return False
                        if part.startswith("<=") and version > part[2:]:
                            return False
                        if part.startswith(">") and version <= part[1:]:
                            return False
                        if part.startswith("<") and version >= part[1:]:
                            return False
                        if part.startswith("==") and version != part[2:]:
                            return False
                    return True


                def resolve_versions(available: list[dict], constraint: str) -> str | None:
                    candidates = [row["version"] for row in available if not row.get("yanked")]
                    candidates = [version for version in candidates if _matches(version, constraint)]
                    if not candidates:
                        return None
                    return sorted(candidates)[-1]
            """,
            "tests/test_semver_resolver.py": """
                from __future__ import annotations

                import unittest

                from resolver import resolve_versions, sort_versions


                class SemverResolverTests(unittest.TestCase):
                    def test_versions_compare_numerically(self):
                        versions = ["1.9.9", "1.10.0", "1.2.10", "1.2.9"]

                        self.assertEqual(sort_versions(versions), ["1.2.9", "1.2.10", "1.9.9", "1.10.0"])

                    def test_resolves_highest_non_yanked_with_range(self):
                        available = [
                            {"version": "1.2.0"},
                            {"version": "1.10.0"},
                            {"version": "2.0.0"},
                            {"version": "1.11.0", "yanked": True},
                        ]

                        self.assertEqual(resolve_versions(available, ">=1.2.0,<2.0.0"), "1.10.0")

                    def test_caret_constraints_expand_by_semver_rules(self):
                        self.assertEqual(
                            resolve_versions(
                                [{"version": "0.2.3"}, {"version": "0.2.9"}, {"version": "0.3.0"}],
                                "^0.2.3",
                            ),
                            "0.2.9",
                        )
                        self.assertEqual(
                            resolve_versions(
                                [{"version": "0.0.3"}, {"version": "0.0.4"}, {"version": "0.1.0"}],
                                "^0.0.3",
                            ),
                            "0.0.3",
                        )

                    def test_prereleases_require_explicit_prerelease_constraint(self):
                        available = [{"version": "1.4.0-rc.1"}, {"version": "1.3.9"}]

                        self.assertEqual(resolve_versions(available, ">=1.0.0,<1.4.0"), "1.3.9")
                        self.assertEqual(resolve_versions(available, ">=1.4.0-rc.1,<1.4.0"), "1.4.0-rc.1")


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_semver_resolver.py": """
                from __future__ import annotations

                import unittest

                from resolver import resolve_versions, sort_versions


                class AdditionalSemverResolverTests(unittest.TestCase):
                    def test_prerelease_sorting_uses_identifier_precedence(self):
                        versions = ["1.0.0", "1.0.0-alpha.2", "1.0.0-alpha.1", "1.0.1"]

                        self.assertEqual(sort_versions(versions), ["1.0.0-alpha.1", "1.0.0-alpha.2", "1.0.0", "1.0.1"])

                    def test_exact_constraint_selects_matching_version(self):
                        available = [{"version": "2.0.0"}, {"version": "2.1.0"}]

                        self.assertEqual(resolve_versions(available, "==2.0.0"), "2.0.0")

                        available = [{"version": "1.9.0"}, {"version": "1.10.0"}]
                        self.assertEqual(resolve_versions(available, ">=1.0.0,<2.0.0"), "1.10.0")

                    def test_returns_none_when_all_candidates_are_yanked_or_out_of_range(self):
                        self.assertIsNone(resolve_versions([{"version": "1.0.0", "yanked": True}], ">=1.0.0"))
                        self.assertIsNone(resolve_versions([{"version": "3.0.0"}], "<2.0.0"))
                        self.assertIsNone(resolve_versions([{"version": "1.10.0"}], "<1.2.0"))

                    def test_greater_than_and_less_equal_constraints_are_combined(self):
                        available = [{"version": "1.0.0"}, {"version": "1.1.0"}, {"version": "1.2.0"}]

                        self.assertEqual(resolve_versions(available, ">1.0.0,<=1.1.0"), "1.1.0")

                        available = [{"version": "1.9.0"}, {"version": "1.10.0"}, {"version": "1.11.0"}]
                        self.assertEqual(resolve_versions(available, ">1.9.0,<=1.10.0"), "1.10.0")


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="csv_schema_migrator",
        title="CSV Schema Migrator",
        summary="Fix a legacy CSV row migrator with aliases, typed coercion, and row-level error reporting.",
        tags=["csv", "data-cleaning", "validation"],
        estimated_context_tokens=11800,
        files={
            "README.md": common_readme(
                Task("csv_schema_migrator", "CSV Schema Migrator", "Fix a legacy CSV row migrator with aliases, typed coercion, and row-level error reporting.", [], 0, {}),
                """
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
                """,
            ),
            "datamap/__init__.py": """
                from .migrate import migrate_rows

                __all__ = ["migrate_rows"]
            """,
            "datamap/coerce.py": """
                from __future__ import annotations

                from datetime import datetime


                def coerce_value(value: object, kind: str):
                    if value is None:
                        return None
                    text = str(value).strip()
                    if kind == "str":
                        return text
                    if kind == "int":
                        return int(text)
                    if kind == "bool":
                        return bool(text)
                    if kind == "date":
                        return datetime.fromisoformat(text).date().isoformat()
                    return value
            """,
            "datamap/migrate.py": """
                from __future__ import annotations

                from .coerce import coerce_value


                def _first_present(row: dict, names: list[str]):
                    for name in names:
                        if name in row:
                            return row[name]
                    return None


                def migrate_rows(rows: list[dict], schema: dict) -> tuple[list[dict], list[dict]]:
                    records: list[dict] = []
                    errors: list[dict] = []
                    for row_number, row in enumerate(rows):
                        record = {}
                        for field, spec in schema.items():
                            names = [field] + list(spec.get("aliases", []))
                            raw = _first_present(row, names)
                            if spec.get("required") and not raw:
                                errors.append({"row": row_number, "field": field, "message": "missing required value"})
                                continue
                            if raw is None or raw == "":
                                record[field] = None
                            else:
                                record[field] = coerce_value(raw, spec.get("type", "str"))
                        records.append(record)
                    return records, errors
            """,
            "fixtures/legacy_rows.json": """
                [
                  {"Customer ID": " 42 ", "Joined": "01/05/2026", "Active": "yes", "Seat Count": "3"},
                  {"Customer ID": "", "Joined": "5 Feb 2026", "Active": "no", "Seat Count": "1"}
                ]
            """,
            "tests/test_migrator.py": """
                from __future__ import annotations

                import unittest

                from datamap import migrate_rows


                SCHEMA = {
                    "customer_id": {"aliases": ["Customer ID", "customer"], "type": "int", "required": True},
                    "joined_on": {"aliases": ["Joined", "Signup Date"], "type": "date", "required": True},
                    "active": {"aliases": ["Active"], "type": "bool", "required": False},
                    "seats": {"aliases": ["Seat Count"], "type": "int", "required": False},
                }


                class MigratorTests(unittest.TestCase):
                    def test_aliases_and_type_coercion(self):
                        rows = [{"Customer ID": " 42 ", "Joined": "01/05/2026", "Active": "yes", "Seat Count": "3", "Ignored": "x"}]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records, [{"customer_id": 42, "joined_on": "2026-01-05", "active": True, "seats": 3}])

                    def test_boolean_false_strings_are_false(self):
                        rows = [
                            {"Customer ID": "1", "Joined": "2026-02-01", "Active": "no"},
                            {"Customer ID": "2", "Joined": "2026-02-02", "Active": "0"},
                        ]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual([row["active"] for row in records], [False, False])

                    def test_invalid_rows_are_omitted_and_reported_one_based(self):
                        rows = [
                            {"Customer ID": "abc", "Joined": "2026-02-01", "Active": "yes"},
                            {"Customer ID": "", "Joined": "not a date", "Active": "yes"},
                            {"Customer ID": "8", "Joined": "5 Feb 2026", "Active": "false"},
                        ]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(records, [{"customer_id": 8, "joined_on": "2026-02-05", "active": False, "seats": None}])
                        self.assertEqual([err["row"] for err in errors], [1, 2])
                        self.assertTrue(all("message" in err and err["message"] for err in errors))


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_migrator.py": """
                from __future__ import annotations

                import unittest

                from datamap import migrate_rows


                SCHEMA = {
                    "customer_id": {"aliases": ["Customer ID", "customer"], "type": "int", "required": True},
                    "joined_on": {"aliases": ["Joined", "Signup Date"], "type": "date", "required": True},
                    "active": {"aliases": ["Active"], "type": "bool", "required": False},
                    "seats": {"aliases": ["Seat Count"], "type": "int", "required": False},
                }


                class AdditionalMigratorTests(unittest.TestCase):
                    def test_canonical_field_takes_precedence_over_alias(self):
                        rows = [{"customer_id": "7", "Customer ID": "999", "Joined": "2026-03-01", "Active": "y"}]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records[0]["customer_id"], 7)
                        self.assertEqual(records[0]["active"], True)

                        rows = [{"customer_id": "8", "Customer ID": "999", "Joined": "2026-03-01", "Active": "no"}]
                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records[0]["customer_id"], 8)
                        self.assertEqual(records[0]["active"], False)

                    def test_optional_blank_values_are_kept_as_none(self):
                        rows = [{"Customer ID": "11", "Joined": "2026-03-02", "Active": "", "Seat Count": ""}]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records[0]["active"], None)
                        self.assertEqual(records[0]["seats"], None)

                        rows = [{"Customer ID": "12", "Joined": "2026-03-02", "Active": "false", "Seat Count": "0"}]
                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records[0]["active"], False)
                        self.assertEqual(records[0]["seats"], 0)

                    def test_invalid_boolean_omits_row_and_reports_field(self):
                        rows = [{"Customer ID": "12", "Joined": "2026-03-03", "Active": "sometimes"}]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(records, [])
                        self.assertEqual(errors[0]["row"], 1)
                        self.assertEqual(errors[0]["field"], "active")

                    def test_day_month_name_dates_are_accepted(self):
                        rows = [{"Customer ID": "13", "Joined": "17 Mar 2026", "Active": "true"}]

                        records, errors = migrate_rows(rows, SCHEMA)

                        self.assertEqual(errors, [])
                        self.assertEqual(records[0]["joined_on"], "2026-03-17")


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="log_window_rollups",
        title="Log Window Rollups",
        summary="Fix UTC log parsing and window aggregation for service health dashboards.",
        tags=["logs", "datetime", "aggregation"],
        estimated_context_tokens=10900,
        files={
            "README.md": common_readme(
                Task("log_window_rollups", "Log Window Rollups", "Fix UTC log parsing and window aggregation for service health dashboards.", [], 0, {}),
                """
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
                """,
            ),
            "logscan/__init__.py": """
                from .rollup import parse_line, rollup

                __all__ = ["parse_line", "rollup"]
            """,
            "logscan/rollup.py": """
                from __future__ import annotations

                from datetime import datetime

                LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


                def parse_line(line: str) -> dict:
                    parts = line.strip().split()
                    when = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
                    level = parts[1]
                    fields = {"timestamp": when, "level": level}
                    for token in parts[2:]:
                        if "=" in token:
                            key, value = token.split("=", 1)
                            fields[key] = value
                    return fields


                def _bucket_start(epoch: int, window_seconds: int) -> int:
                    return round(epoch / window_seconds) * window_seconds


                def rollup(lines: list[str], window_seconds: int = 60, group_by: tuple[str, ...] = ("service", "level"), min_level: str = "INFO") -> list[dict]:
                    buckets: dict[int, dict[str, int]] = {}
                    min_index = LEVELS.index(min_level)
                    for line in lines:
                        record = parse_line(line)
                        if LEVELS.index(record["level"]) < min_index:
                            continue
                        epoch = int(record["timestamp"].timestamp())
                        bucket = _bucket_start(epoch, window_seconds)
                        key = "|".join(record.get(part, "") for part in group_by)
                        buckets.setdefault(bucket, {})
                        buckets[bucket][key] = buckets[bucket].get(key, 0) + 1
                    return [
                        {"start": datetime.utcfromtimestamp(bucket).isoformat() + "Z", "counts": counts}
                        for bucket, counts in sorted(buckets.items())
                    ]
            """,
            "tests/test_rollups.py": """
                from __future__ import annotations

                import unittest

                from logscan import parse_line, rollup


                class RollupTests(unittest.TestCase):
                    def test_parse_line_extracts_timestamp_level_and_fields(self):
                        record = parse_line("2026-01-01T00:00:05Z ERROR service=api request_id=abc msg=boom")

                        self.assertEqual(record["level"], "ERROR")
                        self.assertEqual(record["service"], "api")
                        self.assertEqual(record["request_id"], "abc")
                        self.assertEqual(record["timestamp"].tzinfo.utcoffset(record["timestamp"]).total_seconds(), 0)

                        result = rollup(["2026-01-01T00:00:31Z ERROR service=api msg=late"], window_seconds=60, min_level="ERROR")
                        self.assertEqual(result[0]["start"], "2026-01-01T00:00:00Z")

                    def test_bucket_boundaries_are_floor_based_and_end_exclusive(self):
                        lines = [
                            "2026-01-01T00:00:59Z INFO service=api msg=late",
                            "2026-01-01T00:01:00Z INFO service=api msg=next",
                        ]

                        result = rollup(lines, window_seconds=60)

                        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])
                        self.assertEqual([row["counts"] for row in result], [{"api|INFO": 1}, {"api|INFO": 1}])

                    def test_fills_empty_windows_and_filters_by_severity(self):
                        lines = [
                            "2026-01-01T00:00:05Z DEBUG service=api msg=debug",
                            "2026-01-01T00:00:05Z ERROR service=api msg=boom",
                            "2026-01-01T00:02:05Z CRITICAL service=worker msg=down",
                        ]

                        result = rollup(lines, window_seconds=60, min_level="WARNING")

                        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-01T00:02:00Z"])
                        self.assertEqual(result[0]["counts"], {"api|ERROR": 1})
                        self.assertEqual(result[1]["counts"], {})
                        self.assertEqual(result[2]["counts"], {"worker|CRITICAL": 1})


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_rollups.py": """
                from __future__ import annotations

                import unittest

                from logscan import rollup


                class AdditionalRollupTests(unittest.TestCase):
                    def test_counts_multiple_records_in_same_bucket(self):
                        lines = [
                            "2026-01-01T00:00:01Z ERROR service=api msg=a",
                            "2026-01-01T00:00:30Z ERROR service=api msg=b",
                            "2026-01-01T00:00:45Z WARNING service=api msg=c",
                        ]

                        result = rollup(lines, window_seconds=60, min_level="WARNING")

                        self.assertEqual(len(result), 1)
                        self.assertEqual(result[0]["counts"], {"api|ERROR": 2, "api|WARNING": 1})

                    def test_custom_group_by_can_group_by_service_only(self):
                        lines = [
                            "2026-01-01T00:00:59Z ERROR service=api msg=a",
                            "2026-01-01T00:01:01Z WARNING service=api msg=b",
                            "2026-01-01T00:01:03Z ERROR service=worker msg=c",
                        ]

                        result = rollup(lines, window_seconds=60, group_by=("service",), min_level="WARNING")

                        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])
                        self.assertEqual(result[0]["counts"], {"api": 1})
                        self.assertEqual(result[1]["counts"], {"api": 1, "worker": 1})

                    def test_non_minute_window_uses_floor_start(self):
                        lines = [
                            "2026-01-01T00:01:14Z INFO service=api msg=a",
                            "2026-01-01T00:01:30Z INFO service=api msg=b",
                        ]

                        result = rollup(lines, window_seconds=45, min_level="INFO")

                        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:45Z", "2026-01-01T00:01:30Z"])


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="route_planner",
        title="Route Planner",
        summary="Fix a dispatch route planner so it uses weighted travel times and edge closure intervals.",
        tags=["graph", "dijkstra", "scheduling"],
        estimated_context_tokens=12600,
        files={
            "README.md": common_readme(
                Task("route_planner", "Route Planner", "Fix a dispatch route planner so it uses weighted travel times and edge closure intervals.", [], 0, {}),
                """
                The planner routes a driver through a directed graph. Each edge
                has a travel time in minutes and optional closure intervals.
                Closure intervals are absolute minute ranges `[start, end)`.

                The planner should find the earliest arrival, not the fewest
                hops. If an edge would overlap a closure interval, the driver may
                wait until the closure ends and then traverse the edge. Waiting
                is part of elapsed travel time. Return the path, the total
                elapsed minutes from requested departure, and the absolute
                arrival minute.
                """,
            ),
            "dispatch/__init__.py": """
                from .planner import Edge, best_route

                __all__ = ["Edge", "best_route"]
            """,
            "dispatch/planner.py": """
                from __future__ import annotations

                from collections import deque
                from dataclasses import dataclass, field


                @dataclass(frozen=True)
                class Edge:
                    to: str
                    minutes: int
                    closed: list[tuple[int, int]] = field(default_factory=list)


                def _can_traverse(edge: Edge, start: int) -> bool:
                    end = start + edge.minutes
                    return all(end <= close_start or start >= close_end for close_start, close_end in edge.closed)


                def best_route(graph: dict[str, list[Edge]], start: str, end: str, depart_minute: int = 0) -> dict:
                    # BUG: This is hop-count BFS and skips closed edges instead of
                    # considering waits. It can miss the earliest arrival.
                    queue = deque([(start, [start], depart_minute)])
                    seen = {start}
                    while queue:
                        node, path, minute = queue.popleft()
                        if node == end:
                            return {"path": path, "travel_minutes": minute - depart_minute, "arrival_minute": minute}
                        for edge in graph.get(node, []):
                            if edge.to in seen or not _can_traverse(edge, minute):
                                continue
                            seen.add(edge.to)
                            queue.append((edge.to, path + [edge.to], minute + edge.minutes))
                    raise ValueError(f"no route from {start} to {end}")
            """,
            "tests/test_route_planner.py": """
                from __future__ import annotations

                import unittest

                from dispatch import Edge, best_route


                class RoutePlannerTests(unittest.TestCase):
                    def test_chooses_fastest_route_not_fewest_hops(self):
                        graph = {
                            "A": [Edge("D", 25), Edge("B", 10), Edge("C", 3)],
                            "B": [Edge("D", 10)],
                            "C": [Edge("D", 30)],
                        }

                        route = best_route(graph, "A", "D", depart_minute=0)

                        self.assertEqual(route, {"path": ["A", "B", "D"], "travel_minutes": 20, "arrival_minute": 20})

                    def test_waits_for_closed_edge_when_it_is_still_best(self):
                        graph = {
                            "A": [Edge("B", 5, closed=[(0, 10)]), Edge("C", 50)],
                            "B": [Edge("D", 5)],
                            "C": [Edge("D", 5)],
                        }

                        route = best_route(graph, "A", "D", depart_minute=0)

                        self.assertEqual(route["path"], ["A", "B", "D"])
                        self.assertEqual(route["travel_minutes"], 20)
                        self.assertEqual(route["arrival_minute"], 20)

                    def test_chooses_alternate_when_closure_makes_direct_path_slower(self):
                        graph = {
                            "A": [Edge("B", 10, closed=[(5, 40)]), Edge("C", 15)],
                            "B": [Edge("D", 5)],
                            "C": [Edge("D", 10)],
                        }

                        route = best_route(graph, "A", "D", depart_minute=0)

                        self.assertEqual(route["path"], ["A", "C", "D"])
                        self.assertEqual(route["arrival_minute"], 25)

                        weighted = {"A": [Edge("D", 30), Edge("B", 5)], "B": [Edge("D", 5)]}
                        route = best_route(weighted, "A", "D", depart_minute=0)
                        self.assertEqual(route["path"], ["A", "B", "D"])
                        self.assertEqual(route["arrival_minute"], 10)


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_route_planner.py": """
                from __future__ import annotations

                import unittest

                from dispatch import Edge, best_route


                class AdditionalRoutePlannerTests(unittest.TestCase):
                    def test_departing_after_closure_does_not_wait(self):
                        graph = {
                            "A": [Edge("D", 25, closed=[(0, 10)]), Edge("B", 5, closed=[(0, 10)])],
                            "B": [Edge("D", 5)],
                        }

                        route = best_route(graph, "A", "D", depart_minute=10)

                        self.assertEqual(route, {"path": ["A", "B", "D"], "travel_minutes": 10, "arrival_minute": 20})

                    def test_waits_when_traversal_would_overlap_closure(self):
                        graph = {
                            "A": [Edge("B", 10, closed=[(5, 8)])],
                            "B": [Edge("D", 1)],
                        }

                        route = best_route(graph, "A", "D", depart_minute=0)

                        self.assertEqual(route["path"], ["A", "B", "D"])
                        self.assertEqual(route["arrival_minute"], 19)

                    def test_raises_when_destination_is_unreachable(self):
                        graph = {"A": [Edge("B", 1)], "C": [Edge("D", 1)]}

                        with self.assertRaises(ValueError):
                            best_route(graph, "A", "D", depart_minute=0)

                        wait_graph = {"A": [Edge("B", 5, closed=[(0, 10)])], "B": [Edge("D", 5)]}
                        route = best_route(wait_graph, "A", "D", depart_minute=0)
                        self.assertEqual(route["arrival_minute"], 20)


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="template_engine",
        title="Mini Template Engine",
        summary="Fix a small template renderer with variables, loops, conditionals, filters, and HTML escaping.",
        tags=["templating", "parser", "escaping"],
        estimated_context_tokens=14400,
        files={
            "README.md": common_readme(
                Task("template_engine", "Mini Template Engine", "Fix a small template renderer with variables, loops, conditionals, filters, and HTML escaping.", [], 0, {}),
                """
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
                """,
            ),
            "minitpl/__init__.py": """
                from .engine import render

                __all__ = ["render"]
            """,
            "minitpl/engine.py": """
                from __future__ import annotations

                import re

                VAR_RE = re.compile(r"{{\\s*(.*?)\\s*}}")


                def _lookup(name: str, context: dict):
                    current = context
                    for part in name.split("."):
                        if isinstance(current, dict):
                            current = current.get(part, "")
                        else:
                            current = getattr(current, part, "")
                    return current


                def render(template: str, context: dict) -> str:
                    # BUG: Only variables work. Blocks, filters, and escaping are
                    # missing.
                    def replace(match: re.Match) -> str:
                        return str(_lookup(match.group(1), context))

                    return VAR_RE.sub(replace, template)
            """,
            "tests/test_template_engine.py": """
                from __future__ import annotations

                import unittest

                from minitpl import render


                class TemplateEngineTests(unittest.TestCase):
                    def test_variables_are_html_escaped_by_default(self):
                        output = render("<h1>{{ title }}</h1>", {"title": "<Hello & Goodbye>"})

                        self.assertEqual(output, "<h1>&lt;Hello &amp; Goodbye&gt;</h1>")

                    def test_safe_and_case_filters(self):
                        output = render("{{ name|upper }} {{ html|safe }}", {"name": "Ada", "html": "<strong>ok</strong>"})

                        self.assertEqual(output, "ADA <strong>ok</strong>")

                    def test_for_loop_with_loop_index_and_dotted_lookup(self):
                        template = "{% for item in items %}{{ loop.index }}. {{ item.name }}={{ item.count }};{% endfor %}"
                        context = {"items": [{"name": "apples", "count": 2}, {"name": "pears", "count": 3}]}

                        self.assertEqual(render(template, context), "1. apples=2;2. pears=3;")

                    def test_if_else_and_default_filter(self):
                        template = "{% if user.active %}{{ user.name }}{% else %}{{ missing|default:\\"guest\\" }}{% endif %}"

                        self.assertEqual(render(template, {"user": {"active": False, "name": "Lin"}}), "guest")
                        self.assertEqual(render(template, {"user": {"active": True, "name": "Lin"}}), "Lin")


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_template_engine.py": """
                from __future__ import annotations

                import unittest

                from minitpl import render


                class AdditionalTemplateEngineTests(unittest.TestCase):
                    def test_missing_variable_without_default_renders_empty_string(self):
                        self.assertEqual(render("Hello {{ missing }}!", {}), "Hello !")
                        self.assertEqual(render('Hello {{ missing|default:"<guest>" }}!', {}), "Hello &lt;guest&gt;!")

                    def test_lower_filter_and_default_value_are_escaped(self):
                        template = "{{ name|lower }} {{ missing|default:\"<guest>\" }}"

                        self.assertEqual(render(template, {"name": "ADA"}), "ada &lt;guest&gt;")

                    def test_loop_variable_does_not_leak_after_loop(self):
                        template = "{% for item in items %}{{ item.name }} {% endfor %}{{ item.name|default:\"none\" }}"

                        self.assertEqual(render(template, {"items": [{"name": "one"}]}), "one none")

                    def test_false_condition_without_else_renders_nothing(self):
                        template = "A{% if user.active %}B{% endif %}C"

                        self.assertEqual(render(template, {"user": {"active": False}}), "AC")


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="event_store_snapshots",
        title="Event Store Snapshots",
        summary="Fix ledger replay so account snapshots are ordered, idempotent, and reject overdrafts.",
        tags=["event-sourcing", "ordering", "idempotency"],
        estimated_context_tokens=11200,
        files={
            "README.md": common_readme(
                Task("event_store_snapshots", "Event Store Snapshots", "Fix ledger replay so account snapshots are ordered, idempotent, and reject overdrafts.", [], 0, {}),
                """
                The event store rebuilds account balances from immutable events.
                Input order is not guaranteed, so events must be applied by
                `(timestamp, sequence)` order. Duplicate event ids are ignored.

                Supported types are `deposit`, `withdrawal`, and `transfer`.
                Withdrawals and transfers must not make the source account
                negative. Rejected events are recorded with their id and reason
                and are not included in applied ids.

                The replay function may receive an opening snapshot with
                balances and already-applied ids. This allows incremental
                rebuilds; duplicate ids from the snapshot should not be applied
                again.
                """,
            ),
            "events/__init__.py": """
                from .store import LedgerState, replay

                __all__ = ["LedgerState", "replay"]
            """,
            "events/store.py": """
                from __future__ import annotations

                from dataclasses import dataclass, field
                from decimal import Decimal


                @dataclass
                class LedgerState:
                    balances: dict[str, Decimal] = field(default_factory=dict)
                    applied_ids: set[str] = field(default_factory=set)
                    rejected: list[dict] = field(default_factory=list)


                def _amount(event: dict) -> Decimal:
                    return Decimal(str(event["amount"]))


                def replay(events: list[dict], opening: LedgerState | None = None) -> LedgerState:
                    state = opening or LedgerState()
                    for event in events:
                        event_id = event["id"]
                        amount = _amount(event)
                        kind = event["type"]
                        account = event.get("account")
                        if kind == "deposit":
                            state.balances[account] = state.balances.get(account, Decimal("0")) + amount
                        elif kind == "withdrawal":
                            state.balances[account] = state.balances.get(account, Decimal("0")) - amount
                        elif kind == "transfer":
                            target = event["target"]
                            state.balances[account] = state.balances.get(account, Decimal("0")) - amount
                            state.balances[target] = state.balances.get(target, Decimal("0")) + amount
                        state.applied_ids.add(event_id)
                    return state
            """,
            "tests/test_event_store.py": """
                from __future__ import annotations

                import unittest
                from decimal import Decimal

                from events import LedgerState, replay


                class EventStoreTests(unittest.TestCase):
                    def test_replay_sorts_by_timestamp_then_sequence(self):
                        events = [
                            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "99.00"},
                            {"id": "w1", "timestamp": "2026-01-02T00:00:00Z", "sequence": 3, "type": "withdrawal", "account": "cash", "amount": "4.00"},
                            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "10.00"},
                        ]

                        state = replay(events)

                        self.assertEqual(state.balances["cash"], Decimal("6.00"))
                        self.assertEqual(state.rejected, [])

                    def test_duplicate_event_ids_are_ignored(self):
                        events = [
                            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "10.00"},
                            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "10.00"},
                        ]

                        state = replay(events)

                        self.assertEqual(state.balances["cash"], Decimal("10.00"))
                        self.assertEqual(state.applied_ids, {"d1"})

                    def test_overdrafts_are_rejected_without_mutating_balance(self):
                        events = [
                            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "5.00"},
                            {"id": "w1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "withdrawal", "account": "cash", "amount": "7.00"},
                        ]

                        state = replay(events)

                        self.assertEqual(state.balances["cash"], Decimal("5.00"))
                        self.assertEqual(state.applied_ids, {"d1"})
                        self.assertEqual(state.rejected[0]["id"], "w1")

                    def test_opening_snapshot_applied_ids_are_respected(self):
                        opening = LedgerState(balances={"cash": Decimal("3.00")}, applied_ids={"d0"})
                        events = [
                            {"id": "d0", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "3.00"},
                            {"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "deposit", "account": "cash", "amount": "2.00"},
                        ]

                        state = replay(events, opening)

                        self.assertEqual(state.balances["cash"], Decimal("5.00"))
                        self.assertEqual(state.applied_ids, {"d0", "d1"})


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_event_store.py": """
                from __future__ import annotations

                import unittest
                from decimal import Decimal

                from events import LedgerState, replay


                class AdditionalEventStoreTests(unittest.TestCase):
                    def test_successful_transfer_debits_source_and_credits_target(self):
                        events = [
                            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "9.00"},
                            {"id": "t1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "transfer", "account": "cash", "target": "savings", "amount": "4.50"},
                            {"id": "t1", "timestamp": "2026-01-01T00:00:02Z", "sequence": 3, "type": "transfer", "account": "cash", "target": "savings", "amount": "1.00"},
                        ]

                        state = replay(events)

                        self.assertEqual(state.balances["cash"], Decimal("4.50"))
                        self.assertEqual(state.balances["savings"], Decimal("4.50"))
                        self.assertEqual(state.applied_ids, {"d1", "t1"})

                    def test_transfer_overdraft_does_not_credit_target(self):
                        events = [
                            {"id": "d1", "timestamp": "2026-01-01T00:00:00Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "2.00"},
                            {"id": "t1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 2, "type": "transfer", "account": "cash", "target": "savings", "amount": "5.00"},
                        ]

                        state = replay(events)

                        self.assertEqual(state.balances["cash"], Decimal("2.00"))
                        self.assertNotIn("savings", state.balances)
                        self.assertEqual(state.rejected[0]["id"], "t1")

                    def test_opening_snapshot_is_not_mutated_by_replay(self):
                        opening = LedgerState(balances={"cash": Decimal("1.00")}, applied_ids={"d0"})

                        state = replay(
                            [{"id": "d1", "timestamp": "2026-01-01T00:00:01Z", "sequence": 1, "type": "deposit", "account": "cash", "amount": "2.00"}],
                            opening,
                        )

                        self.assertEqual(state.balances["cash"], Decimal("3.00"))
                        self.assertEqual(opening.balances, {"cash": Decimal("1.00")})
                        self.assertEqual(opening.applied_ids, {"d0"})


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="feature_flags",
        title="Feature Flag Evaluator",
        summary="Fix a deterministic feature flag evaluator with environments, overrides, rules, and percentage rollout.",
        tags=["feature-flags", "hashing", "rules"],
        estimated_context_tokens=12100,
        files={
            "README.md": common_readme(
                Task("feature_flags", "Feature Flag Evaluator", "Fix a deterministic feature flag evaluator with environments, overrides, rules, and percentage rollout.", [], 0, {}),
                """
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
                """,
            ),
            "flags/__init__.py": """
                from .evaluator import bucket, evaluate

                __all__ = ["bucket", "evaluate"]
            """,
            "flags/evaluator.py": """
                from __future__ import annotations

                import random


                def bucket(flag_key: str, user_key: str) -> int:
                    random.seed(user_key)
                    return random.randint(0, 99)


                def _matches(rule: dict, user: dict) -> bool:
                    if "segment" in rule:
                        return rule["segment"] in user.get("segments", [])
                    return True


                def evaluate(config: dict, flag_key: str, user: dict, env: str = "prod") -> bool:
                    flag = config.get(flag_key, {})
                    enabled = bool(flag.get("default", False))
                    for rule in flag.get("rules", []):
                        if _matches(rule, user):
                            enabled = bool(rule.get("value"))
                            break
                    rollout = flag.get("rollout")
                    if rollout is not None:
                        enabled = bucket(flag_key, user["key"]) < int(rollout)
                    return enabled
            """,
            "tests/test_feature_flags.py": """
                from __future__ import annotations

                import hashlib
                import unittest

                from flags import bucket, evaluate


                CONFIG = {
                    "new_nav": {
                        "default": False,
                        "environments": {
                            "prod": {
                                "default": False,
                                "rollout": 0,
                                "rules": [{"segment": "beta", "value": True}],
                                "overrides": {"blocked-user": False, "force-user": True},
                            },
                            "staging": {"default": True},
                        },
                    },
                    "export_v2": {
                        "environments": {
                            "prod": {
                                "default": False,
                                "rollout": 25,
                                "rules": [{"attributes": {"plan": "enterprise"}, "value": True}],
                            }
                        }
                    },
                }


                def expected_bucket(flag_key: str, user_key: str) -> int:
                    digest = hashlib.sha256(f"{flag_key}:{user_key}".encode()).hexdigest()
                    return int(digest[:8], 16) % 100


                class FeatureFlagTests(unittest.TestCase):
                    def test_bucket_is_stable_and_uses_flag_key(self):
                        self.assertEqual(bucket("new_nav", "alice"), expected_bucket("new_nav", "alice"))
                        self.assertNotEqual(bucket("new_nav", "alice"), bucket("export_v2", "alice"))

                    def test_environment_specific_defaults(self):
                        user = {"key": "plain", "segments": []}

                        self.assertFalse(evaluate(CONFIG, "new_nav", user, env="prod"))
                        self.assertTrue(evaluate(CONFIG, "new_nav", user, env="staging"))

                    def test_rules_match_segments_and_attributes(self):
                        self.assertTrue(evaluate(CONFIG, "new_nav", {"key": "u1", "segments": ["beta"]}, env="prod"))
                        self.assertTrue(evaluate(CONFIG, "export_v2", {"key": "u2", "attributes": {"plan": "enterprise"}}, env="prod"))

                    def test_explicit_overrides_win_last(self):
                        self.assertFalse(evaluate(CONFIG, "new_nav", {"key": "blocked-user", "segments": ["beta"]}, env="prod"))
                        self.assertTrue(evaluate(CONFIG, "new_nav", {"key": "force-user", "segments": []}, env="prod"))


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_feature_flags.py": """
                from __future__ import annotations

                import hashlib
                import unittest

                from flags import evaluate


                def expected_bucket(flag_key: str, user_key: str) -> int:
                    digest = hashlib.sha256(f"{flag_key}:{user_key}".encode()).hexdigest()
                    return int(digest[:8], 16) % 100


                class AdditionalFeatureFlagTests(unittest.TestCase):
                    def test_unknown_flag_is_disabled(self):
                        self.assertFalse(evaluate({}, "missing", {"key": "user"}, env="prod"))

                        config = {"known": {"environments": {"prod": {"default": True}}}}
                        self.assertTrue(evaluate(config, "known", {"key": "user"}, env="prod"))

                    def test_rollout_uses_strict_less_than_bucket_boundary(self):
                        user = {"key": "alice"}
                        threshold = expected_bucket("rollout_flag", "alice")
                        config = {
                            "rollout_flag": {
                                "environments": {
                                    "prod": {"default": False, "rollout": threshold},
                                    "wide": {"default": False, "rollout": threshold + 1},
                                }
                            }
                        }

                        self.assertFalse(evaluate(config, "rollout_flag", user, env="prod"))
                        self.assertTrue(evaluate(config, "rollout_flag", user, env="wide"))

                    def test_unmatched_attribute_rule_falls_back_to_environment_default(self):
                        config = {
                            "export": {
                                "environments": {
                                    "prod": {
                                        "default": True,
                                        "rollout": 0,
                                        "rules": [{"attributes": {"plan": "enterprise"}, "value": False}],
                                    }
                                }
                            }
                        }

                        self.assertTrue(evaluate(config, "export", {"key": "u1", "attributes": {"plan": "free"}}, env="prod"))

                    def test_missing_environment_uses_top_level_default(self):
                        config = {"flag": {"default": True, "environments": {"prod": {"default": False}}}}

                        self.assertTrue(evaluate(config, "flag", {"key": "u1"}, env="dev"))
                        self.assertFalse(evaluate(config, "flag", {"key": "u1"}, env="prod"))


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="inventory_forecast",
        title="Inventory Forecast",
        summary="Fix replenishment recommendations that account for stockouts, pack sizes, open orders, and caps.",
        tags=["forecasting", "inventory", "rounding"],
        estimated_context_tokens=11900,
        files={
            "README.md": common_readme(
                Task("inventory_forecast", "Inventory Forecast", "Fix replenishment recommendations that account for stockouts, pack sizes, open orders, and caps.", [], 0, {}),
                """
                The recommender estimates average daily demand over a lookback
                window. Days where the product was out of stock should be
                excluded from the denominator because zero sales on those days
                do not mean zero demand.

                Target stock is `ceil(avg_daily_demand * (lead_time_days +
                safety_days))`. Recommended quantity is target minus on-hand and
                already-on-order units. If positive, round up to the SKU pack
                size. Do not recommend more than `max_stock - on_hand -
                on_order`. If the final positive recommendation is below
                `min_order`, use `min_order` rounded to pack size, still
                respecting the cap.
                """,
            ),
            "stockwise/__init__.py": """
                from .forecast import recommend

                __all__ = ["recommend"]
            """,
            "stockwise/forecast.py": """
                from __future__ import annotations

                import math
                from datetime import date, timedelta


                def _recent(entries: list[dict], today: date, days: int) -> list[dict]:
                    start = today - timedelta(days=days)
                    return [entry for entry in entries if start <= date.fromisoformat(entry["date"]) < today]


                def recommend(skus: list[dict], history: list[dict], today: date) -> list[dict]:
                    results = []
                    by_sku: dict[str, list[dict]] = {}
                    for entry in history:
                        by_sku.setdefault(entry["sku"], []).append(entry)

                    for sku in skus:
                        rows = _recent(by_sku.get(sku["sku"], []), today, sku.get("lookback_days", 14))
                        avg = sum(row.get("units_sold", 0) for row in rows) / max(1, len(rows))
                        target = math.ceil(avg * sku.get("lead_time_days", 0))
                        qty = max(0, target - sku.get("on_hand", 0))
                        results.append({"sku": sku["sku"], "avg_daily_demand": avg, "target_stock": target, "recommended_qty": qty})
                    return results
            """,
            "tests/test_inventory_forecast.py": """
                from __future__ import annotations

                import unittest
                from datetime import date

                from stockwise import recommend


                class InventoryForecastTests(unittest.TestCase):
                    def test_excludes_stockout_days_from_average(self):
                        skus = [{"sku": "A", "on_hand": 0, "on_order": 0, "lead_time_days": 2, "safety_days": 1, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 4}]
                        history = [
                            {"sku": "A", "date": "2026-01-06", "units_sold": 4, "in_stock": True},
                            {"sku": "A", "date": "2026-01-07", "units_sold": 0, "in_stock": False},
                            {"sku": "A", "date": "2026-01-08", "units_sold": 6, "in_stock": True},
                            {"sku": "A", "date": "2026-01-09", "units_sold": 0, "in_stock": False},
                        ]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["avg_daily_demand"], 5.0)
                        self.assertEqual(row["target_stock"], 15)
                        self.assertEqual(row["recommended_qty"], 15)

                    def test_accounts_for_open_orders_and_rounds_to_pack_size(self):
                        skus = [{"sku": "B", "on_hand": 3, "on_order": 4, "lead_time_days": 2, "safety_days": 2, "pack_size": 6, "max_stock": 50, "min_order": 1, "lookback_days": 3}]
                        history = [
                            {"sku": "B", "date": "2026-01-07", "units_sold": 3, "in_stock": True},
                            {"sku": "B", "date": "2026-01-08", "units_sold": 3, "in_stock": True},
                            {"sku": "B", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
                        ]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["target_stock"], 12)
                        self.assertEqual(row["recommended_qty"], 6)

                    def test_respects_max_stock_cap_and_min_order(self):
                        skus = [{"sku": "C", "on_hand": 18, "on_order": 0, "lead_time_days": 5, "safety_days": 1, "pack_size": 5, "max_stock": 21, "min_order": 4, "lookback_days": 2}]
                        history = [
                            {"sku": "C", "date": "2026-01-08", "units_sold": 4, "in_stock": True},
                            {"sku": "C", "date": "2026-01-09", "units_sold": 4, "in_stock": True},
                        ]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["recommended_qty"], 3)


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_inventory_forecast.py": """
                from __future__ import annotations

                import unittest
                from datetime import date

                from stockwise import recommend


                class AdditionalInventoryForecastTests(unittest.TestCase):
                    def test_history_outside_lookback_is_ignored(self):
                        skus = [{"sku": "A", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 1, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 2}]
                        history = [
                            {"sku": "A", "date": "2026-01-01", "units_sold": 100, "in_stock": True},
                            {"sku": "A", "date": "2026-01-09", "units_sold": 4, "in_stock": True},
                        ]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["avg_daily_demand"], 4.0)
                        self.assertEqual(row["target_stock"], 8)
                        self.assertEqual(row["recommended_qty"], 8)

                    def test_all_stockout_window_recommends_zero(self):
                        skus = [{"sku": "B", "on_hand": 0, "on_order": 0, "lead_time_days": 3, "safety_days": 2, "pack_size": 5, "max_stock": 100, "min_order": 5, "lookback_days": 2}]
                        history = [
                            {"sku": "B", "date": "2026-01-08", "units_sold": 5, "in_stock": False},
                            {"sku": "B", "date": "2026-01-09", "units_sold": 0, "in_stock": False},
                        ]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["avg_daily_demand"], 0.0)
                        self.assertEqual(row["target_stock"], 0)
                        self.assertEqual(row["recommended_qty"], 0)

                    def test_minimum_order_is_rounded_to_pack_size(self):
                        skus = [{"sku": "C", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 0, "pack_size": 4, "max_stock": 100, "min_order": 5, "lookback_days": 1}]
                        history = [{"sku": "C", "date": "2026-01-09", "units_sold": 2, "in_stock": True}]

                        [row] = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual(row["target_stock"], 2)
                        self.assertEqual(row["recommended_qty"], 8)

                    def test_multiple_skus_are_forecast_independently(self):
                        skus = [
                            {"sku": "D", "on_hand": 0, "on_order": 0, "lead_time_days": 1, "safety_days": 0, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 1},
                            {"sku": "E", "on_hand": 0, "on_order": 3, "lead_time_days": 1, "safety_days": 0, "pack_size": 1, "max_stock": 100, "min_order": 1, "lookback_days": 1},
                        ]
                        history = [
                            {"sku": "D", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
                            {"sku": "E", "date": "2026-01-09", "units_sold": 3, "in_stock": True},
                        ]

                        rows = recommend(skus, history, date(2026, 1, 10))

                        self.assertEqual([row["sku"] for row in rows], ["D", "E"])
                        self.assertEqual([row["recommended_qty"] for row in rows], [3, 0])


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="line_diff_reporter",
        title="Line Diff Reporter",
        summary="Fix a line diff summarizer with whitespace-insensitive mode and merged context windows.",
        tags=["diff", "text", "reporting"],
        estimated_context_tokens=10800,
        files={
            "README.md": common_readme(
                Task("line_diff_reporter", "Line Diff Reporter", "Fix a line diff summarizer with whitespace-insensitive mode and merged context windows.", [], 0, {}),
                """
                The reporter emits compact hunk dictionaries for review tools.
                Each hunk has 1-based `old_start` and `new_start`, plus
                `old_lines` and `new_lines` lists. Context lines are included on
                both sides. Nearby changes whose context overlaps should be
                merged into one hunk.

                When `ignore_whitespace=True`, lines are compared after
                collapsing all runs of whitespace to a single space and trimming
                edges. The original lines should still be shown in hunks when a
                substantive change remains.
                """,
            ),
            "linediff/__init__.py": """
                from .report import summarize_diff

                __all__ = ["summarize_diff"]
            """,
            "linediff/report.py": """
                from __future__ import annotations

                import difflib


                def summarize_diff(old: str, new: str, context: int = 2, ignore_whitespace: bool = False) -> list[dict]:
                    old_lines = old.splitlines()
                    new_lines = new.splitlines()
                    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)
                    hunks = []
                    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                        if tag == "equal":
                            continue
                        hunks.append(
                            {
                                "old_start": i1,
                                "new_start": j1,
                                "old_lines": old_lines[i1:i2],
                                "new_lines": new_lines[j1:j2],
                            }
                        )
                    return hunks
            """,
            "tests/test_line_diff.py": """
                from __future__ import annotations

                import unittest

                from linediff import summarize_diff


                class LineDiffTests(unittest.TestCase):
                    def test_whitespace_only_changes_can_be_ignored(self):
                        old = "alpha = 1\\nbeta = 2\\n"
                        new = "alpha    =    1\\n beta = 2 \\n"

                        self.assertEqual(summarize_diff(old, new, ignore_whitespace=True), [])

                    def test_hunks_include_one_based_line_numbers_and_context(self):
                        old = "a\\nb\\nc\\nd\\ne\\n"
                        new = "a\\nb\\nC\\nd\\ne\\n"

                        hunks = summarize_diff(old, new, context=1)

                        self.assertEqual(hunks, [{"old_start": 2, "new_start": 2, "old_lines": ["b", "c", "d"], "new_lines": ["b", "C", "d"]}])

                    def test_overlapping_context_windows_are_merged(self):
                        old = "a\\nb\\nc\\nd\\ne\\nf\\n"
                        new = "a\\nB\\nc\\nD\\ne\\nf\\n"

                        hunks = summarize_diff(old, new, context=1)

                        self.assertEqual(len(hunks), 1)
                        self.assertEqual(hunks[0]["old_start"], 1)
                        self.assertEqual(hunks[0]["new_start"], 1)
                        self.assertEqual(hunks[0]["old_lines"], ["a", "b", "c", "d", "e"])
                        self.assertEqual(hunks[0]["new_lines"], ["a", "B", "c", "D", "e"])


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_line_diff.py": """
                from __future__ import annotations

                import unittest

                from linediff import summarize_diff


                class AdditionalLineDiffTests(unittest.TestCase):
                    def test_context_zero_reports_only_changed_lines(self):
                        old = "a\\nb\\nc\\n"
                        new = "a\\nB\\nc\\n"

                        hunks = summarize_diff(old, new, context=0)

                        self.assertEqual(hunks, [{"old_start": 2, "new_start": 2, "old_lines": ["b"], "new_lines": ["B"]}])

                    def test_insertion_hunk_includes_surrounding_context(self):
                        old = "a\\nc\\n"
                        new = "a\\nb\\nc\\n"

                        hunks = summarize_diff(old, new, context=1)

                        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["a", "c"], "new_lines": ["a", "b", "c"]}])

                    def test_deletion_hunk_includes_surrounding_context(self):
                        old = "a\\nb\\nc\\n"
                        new = "a\\nc\\n"

                        hunks = summarize_diff(old, new, context=1)

                        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["a", "b", "c"], "new_lines": ["a", "c"]}])

                    def test_whitespace_insensitive_mode_still_reports_value_changes(self):
                        old = "value = 1\\n"
                        new = " value    =    2 \\n"

                        hunks = summarize_diff(old, new, context=0, ignore_whitespace=True)

                        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["value = 1"], "new_lines": [" value    =    2 "]}])


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
    Task(
        task_id="license_audit",
        title="License Audit",
        summary="Fix transitive dependency license auditing with normalized SPDX expressions and package exceptions.",
        tags=["licenses", "graph", "policy"],
        estimated_context_tokens=11600,
        files={
            "README.md": common_readme(
                Task("license_audit", "License Audit", "Fix transitive dependency license auditing with normalized SPDX expressions and package exceptions.", [], 0, {}),
                """
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
                """,
            ),
            "licensecheck/__init__.py": """
                from .audit import audit

                __all__ = ["audit"]
            """,
            "licensecheck/audit.py": """
                from __future__ import annotations


                def _normalize(license_name: str) -> str:
                    return license_name.strip()


                def audit(packages: dict, root: str, policy: dict) -> list[dict]:
                    violations = []
                    allow = set(policy.get("allow", []))
                    deny = set(policy.get("deny", []))
                    root_info = packages[root]
                    license_name = _normalize(root_info.get("license", ""))
                    if license_name in deny or license_name not in allow:
                        violations.append({"package": root, "license": license_name, "reason": "not allowed"})
                    return violations
            """,
            "tests/test_license_audit.py": """
                from __future__ import annotations

                import unittest

                from licensecheck import audit


                PACKAGES = {
                    "app": {"license": "MIT", "deps": ["ui", "parser", "badlib", "legacy"]},
                    "ui": {"license": "Apache 2", "deps": ["colors"]},
                    "colors": {"license": "BSD 3-Clause", "deps": []},
                    "parser": {"license": "MIT OR GPL-3.0", "deps": []},
                    "badlib": {"license": "GPL-3.0", "deps": []},
                    "legacy": {"license": "LGPL-2.1", "deps": []},
                }

                POLICY = {
                    "allow": ["MIT", "Apache-2.0", "BSD-3-Clause"],
                    "deny": ["GPL-3.0", "AGPL-3.0"],
                    "exceptions": [{"package": "legacy", "license": "LGPL-2.1", "reason": "approved vendor contract"}],
                }


                class LicenseAuditTests(unittest.TestCase):
                    def test_traverses_transitive_dependencies_and_normalizes_aliases(self):
                        violations = audit(PACKAGES, "app", POLICY)

                        self.assertEqual([row["package"] for row in violations], ["badlib"])
                        self.assertEqual(violations[0]["license"], "GPL-3.0")

                    def test_or_expression_is_allowed_when_any_choice_is_allowed(self):
                        packages = {"app": {"license": "MIT OR GPL-3.0", "deps": []}}

                        self.assertEqual(audit(packages, "app", POLICY), [])

                    def test_and_expression_requires_all_parts_allowed(self):
                        packages = {"app": {"license": "MIT AND GPL-3.0", "deps": []}}

                        violations = audit(packages, "app", POLICY)

                        self.assertEqual(len(violations), 1)
                        self.assertEqual(violations[0]["reason"], "denied")

                    def test_package_specific_exception_allows_license(self):
                        packages = {"legacy": {"license": "LGPL-2.1", "deps": []}}

                        self.assertEqual(audit(packages, "legacy", POLICY), [])


                if __name__ == "__main__":
                    unittest.main()
            """,
            "tests/test_additional_license_audit.py": """
                from __future__ import annotations

                import unittest

                from licensecheck import audit


                POLICY = {
                    "allow": ["MIT", "Apache-2.0", "BSD-3-Clause"],
                    "deny": ["GPL-3.0", "AGPL-3.0"],
                    "exceptions": [{"package": "legacy", "license": "LGPL-2.1", "reason": "approved"}],
                }


                class AdditionalLicenseAuditTests(unittest.TestCase):
                    def test_dependency_cycles_are_traversed_once(self):
                        packages = {
                            "app": {"license": "MIT", "deps": ["bad"]},
                            "bad": {"license": "GPL-3.0", "deps": ["app"]},
                        }

                        violations = audit(packages, "app", POLICY)

                        self.assertEqual(violations, [{"package": "bad", "license": "GPL-3.0", "reason": "denied"}])

                    def test_exception_is_package_specific(self):
                        packages = {
                            "app": {"license": "MIT", "deps": ["legacy", "other"]},
                            "legacy": {"license": "LGPL-2.1", "deps": []},
                            "other": {"license": "LGPL-2.1", "deps": []},
                        }

                        violations = audit(packages, "app", POLICY)

                        self.assertEqual([row["package"] for row in violations], ["other"])

                    def test_and_expression_passes_when_all_parts_are_allowed_after_normalization(self):
                        packages = {"app": {"license": "MIT AND Apache 2", "deps": []}}

                        self.assertEqual(audit(packages, "app", POLICY), [])

                    def test_root_package_is_audited_too(self):
                        packages = {"app": {"license": "AGPL-3.0", "deps": []}}

                        violations = audit(packages, "app", POLICY)

                        self.assertEqual(violations[0]["package"], "app")
                        self.assertEqual(violations[0]["reason"], "denied")


                if __name__ == "__main__":
                    unittest.main()
            """,
        },
    ),
]


def generate() -> None:
    TASKS_DIR.mkdir(exist_ok=True)
    write_file(
        TASKS_DIR / "README.md",
        """
        # Agentic Coding Harness Tasks

        This directory contains self-contained SWE benchmark tasks for the
        headless harness runner in `scripts/run_task_benchmark.py`.

        Each task directory contains:

        - `metadata.json`: task id, tags, estimated context size, and scoring
          command.
        - `prompt.md`: the user prompt sent to the coding agent.
        - `repo/`: a disposable Python project copied into a benchmark run
          workspace.

        The task repos intentionally contain failing implementations. The agent
        should inspect the project, edit the implementation, and run:

        ```bash
        python -m unittest discover -s tests -v
        ```

        All tasks use only the Python standard library and are designed to be
        scoreable by counting passing unittest cases.
        """,
    )

    for task in TASKS:
        base = TASKS_DIR / task.task_id
        if base.exists():
            shutil.rmtree(base)
        (base / "repo").mkdir(parents=True)

        metadata = {
            "id": task.task_id,
            "title": task.title,
            "summary": task.summary,
            "language": "python",
            "tags": task.tags,
            "estimated_context_tokens": task.estimated_context_tokens,
            "test_command": "python -m unittest discover -s tests -v",
            "scoring": {"type": "unittest", "max_score": "number_of_tests"},
            "dependency_policy": "standard-library-only",
        }
        write_file(base / "metadata.json", json.dumps(metadata, indent=2, sort_keys=True))
        write_file(base / "prompt.md", task_prompt(task))

        for rel_path, content in task.files.items():
            write_file(base / "repo" / rel_path, content)

        write_file(base / "repo" / "docs" / "maintainer_context.md", maintainer_context(task))
        write_file(base / "repo" / "fixtures" / "regression_notes.json", regression_notes(task))

    print(f"Generated {len(TASKS)} tasks under {TASKS_DIR}")


if __name__ == "__main__":
    generate()
