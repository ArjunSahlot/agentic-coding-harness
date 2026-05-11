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
