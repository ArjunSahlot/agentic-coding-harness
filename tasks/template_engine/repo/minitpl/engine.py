from __future__ import annotations

import re

VAR_RE = re.compile(r"{{\s*(.*?)\s*}}")


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
