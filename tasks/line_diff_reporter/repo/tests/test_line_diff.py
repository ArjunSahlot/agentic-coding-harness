from __future__ import annotations

import unittest

from linediff import summarize_diff


class LineDiffTests(unittest.TestCase):
    def test_whitespace_only_changes_can_be_ignored(self):
        old = "alpha = 1\nbeta = 2\n"
        new = "alpha    =    1\n beta = 2 \n"

        self.assertEqual(summarize_diff(old, new, ignore_whitespace=True), [])

    def test_hunks_include_one_based_line_numbers_and_context(self):
        old = "a\nb\nc\nd\ne\n"
        new = "a\nb\nC\nd\ne\n"

        hunks = summarize_diff(old, new, context=1)

        self.assertEqual(hunks, [{"old_start": 2, "new_start": 2, "old_lines": ["b", "c", "d"], "new_lines": ["b", "C", "d"]}])

    def test_overlapping_context_windows_are_merged(self):
        old = "a\nb\nc\nd\ne\nf\n"
        new = "a\nB\nc\nD\ne\nf\n"

        hunks = summarize_diff(old, new, context=1)

        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0]["old_start"], 1)
        self.assertEqual(hunks[0]["new_start"], 1)
        self.assertEqual(hunks[0]["old_lines"], ["a", "b", "c", "d", "e"])
        self.assertEqual(hunks[0]["new_lines"], ["a", "B", "c", "D", "e"])


if __name__ == "__main__":
    unittest.main()
