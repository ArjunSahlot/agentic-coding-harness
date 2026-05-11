from __future__ import annotations

import re

from .normalize import normalize_href, slugify

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


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
