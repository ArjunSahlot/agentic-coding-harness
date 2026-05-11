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
