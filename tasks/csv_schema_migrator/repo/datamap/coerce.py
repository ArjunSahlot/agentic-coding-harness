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
