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
