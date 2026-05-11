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
