from __future__ import annotations

import unittest

from resolver import resolve_versions, sort_versions


class SemverResolverTests(unittest.TestCase):
    def test_versions_compare_numerically(self):
        versions = ["1.9.9", "1.10.0", "1.2.10", "1.2.9"]

        self.assertEqual(sort_versions(versions), ["1.2.9", "1.2.10", "1.9.9", "1.10.0"])

    def test_resolves_highest_non_yanked_with_range(self):
        available = [
            {"version": "1.2.0"},
            {"version": "1.10.0"},
            {"version": "2.0.0"},
            {"version": "1.11.0", "yanked": True},
        ]

        self.assertEqual(resolve_versions(available, ">=1.2.0,<2.0.0"), "1.10.0")

    def test_caret_constraints_expand_by_semver_rules(self):
        self.assertEqual(
            resolve_versions(
                [{"version": "0.2.3"}, {"version": "0.2.9"}, {"version": "0.3.0"}],
                "^0.2.3",
            ),
            "0.2.9",
        )
        self.assertEqual(
            resolve_versions(
                [{"version": "0.0.3"}, {"version": "0.0.4"}, {"version": "0.1.0"}],
                "^0.0.3",
            ),
            "0.0.3",
        )

    def test_prereleases_require_explicit_prerelease_constraint(self):
        available = [{"version": "1.4.0-rc.1"}, {"version": "1.3.9"}]

        self.assertEqual(resolve_versions(available, ">=1.0.0,<1.4.0"), "1.3.9")
        self.assertEqual(resolve_versions(available, ">=1.4.0-rc.1,<1.4.0"), "1.4.0-rc.1")


if __name__ == "__main__":
    unittest.main()
