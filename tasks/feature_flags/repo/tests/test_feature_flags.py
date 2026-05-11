from __future__ import annotations

import hashlib
import unittest

from flags import bucket, evaluate


CONFIG = {
    "new_nav": {
        "default": False,
        "environments": {
            "prod": {
                "default": False,
                "rollout": 0,
                "rules": [{"segment": "beta", "value": True}],
                "overrides": {"blocked-user": False, "force-user": True},
            },
            "staging": {"default": True},
        },
    },
    "export_v2": {
        "environments": {
            "prod": {
                "default": False,
                "rollout": 25,
                "rules": [{"attributes": {"plan": "enterprise"}, "value": True}],
            }
        }
    },
}


def expected_bucket(flag_key: str, user_key: str) -> int:
    digest = hashlib.sha256(f"{flag_key}:{user_key}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


class FeatureFlagTests(unittest.TestCase):
    def test_bucket_is_stable_and_uses_flag_key(self):
        self.assertEqual(bucket("new_nav", "alice"), expected_bucket("new_nav", "alice"))
        self.assertNotEqual(bucket("new_nav", "alice"), bucket("export_v2", "alice"))

    def test_environment_specific_defaults(self):
        user = {"key": "plain", "segments": []}

        self.assertFalse(evaluate(CONFIG, "new_nav", user, env="prod"))
        self.assertTrue(evaluate(CONFIG, "new_nav", user, env="staging"))

    def test_rules_match_segments_and_attributes(self):
        self.assertTrue(evaluate(CONFIG, "new_nav", {"key": "u1", "segments": ["beta"]}, env="prod"))
        self.assertTrue(evaluate(CONFIG, "export_v2", {"key": "u2", "attributes": {"plan": "enterprise"}}, env="prod"))

    def test_explicit_overrides_win_last(self):
        self.assertFalse(evaluate(CONFIG, "new_nav", {"key": "blocked-user", "segments": ["beta"]}, env="prod"))
        self.assertTrue(evaluate(CONFIG, "new_nav", {"key": "force-user", "segments": []}, env="prod"))


if __name__ == "__main__":
    unittest.main()
