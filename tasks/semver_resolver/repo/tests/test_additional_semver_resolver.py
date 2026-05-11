from __future__ import annotations

import unittest

from resolver import resolve_versions, sort_versions


class AdditionalSemverResolverTests(unittest.TestCase):
    def test_prerelease_sorting_uses_identifier_precedence(self):
        versions = ["1.0.0", "1.0.0-alpha.2", "1.0.0-alpha.1", "1.0.1"]

        self.assertEqual(sort_versions(versions), ["1.0.0-alpha.1", "1.0.0-alpha.2", "1.0.0", "1.0.1"])

    def test_exact_constraint_selects_matching_version(self):
        available = [{"version": "2.0.0"}, {"version": "2.1.0"}]

        self.assertEqual(resolve_versions(available, "==2.0.0"), "2.0.0")

        available = [{"version": "1.9.0"}, {"version": "1.10.0"}]
        self.assertEqual(resolve_versions(available, ">=1.0.0,<2.0.0"), "1.10.0")

    def test_returns_none_when_all_candidates_are_yanked_or_out_of_range(self):
        self.assertIsNone(resolve_versions([{"version": "1.0.0", "yanked": True}], ">=1.0.0"))
        self.assertIsNone(resolve_versions([{"version": "3.0.0"}], "<2.0.0"))
        self.assertIsNone(resolve_versions([{"version": "1.10.0"}], "<1.2.0"))

    def test_greater_than_and_less_equal_constraints_are_combined(self):
        available = [{"version": "1.0.0"}, {"version": "1.1.0"}, {"version": "1.2.0"}]

        self.assertEqual(resolve_versions(available, ">1.0.0,<=1.1.0"), "1.1.0")

        available = [{"version": "1.9.0"}, {"version": "1.10.0"}, {"version": "1.11.0"}]
        self.assertEqual(resolve_versions(available, ">1.9.0,<=1.10.0"), "1.10.0")


if __name__ == "__main__":
    unittest.main()
