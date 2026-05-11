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
