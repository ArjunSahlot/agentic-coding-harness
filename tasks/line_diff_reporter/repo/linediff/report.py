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
