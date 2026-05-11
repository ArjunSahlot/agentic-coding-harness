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
