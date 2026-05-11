from __future__ import annotations

import unittest

from linediff import summarize_diff


class AdditionalLineDiffTests(unittest.TestCase):
    def test_context_zero_reports_only_changed_lines(self):
        old = "a\nb\nc\n"
        new = "a\nB\nc\n"

        hunks = summarize_diff(old, new, context=0)

        self.assertEqual(hunks, [{"old_start": 2, "new_start": 2, "old_lines": ["b"], "new_lines": ["B"]}])

    def test_insertion_hunk_includes_surrounding_context(self):
        old = "a\nc\n"
        new = "a\nb\nc\n"

        hunks = summarize_diff(old, new, context=1)

        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["a", "c"], "new_lines": ["a", "b", "c"]}])

    def test_deletion_hunk_includes_surrounding_context(self):
        old = "a\nb\nc\n"
        new = "a\nc\n"

        hunks = summarize_diff(old, new, context=1)

        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["a", "b", "c"], "new_lines": ["a", "c"]}])

    def test_whitespace_insensitive_mode_still_reports_value_changes(self):
        old = "value = 1\n"
        new = " value    =    2 \n"

        hunks = summarize_diff(old, new, context=0, ignore_whitespace=True)

        self.assertEqual(hunks, [{"old_start": 1, "new_start": 1, "old_lines": ["value = 1"], "new_lines": [" value    =    2 "]}])


if __name__ == "__main__":
    unittest.main()
