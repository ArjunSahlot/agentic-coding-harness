from __future__ import annotations

import unittest

from logscan import rollup


class AdditionalRollupTests(unittest.TestCase):
    def test_counts_multiple_records_in_same_bucket(self):
        lines = [
            "2026-01-01T00:00:01Z ERROR service=api msg=a",
            "2026-01-01T00:00:30Z ERROR service=api msg=b",
            "2026-01-01T00:00:45Z WARNING service=api msg=c",
        ]

        result = rollup(lines, window_seconds=60, min_level="WARNING")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["counts"], {"api|ERROR": 2, "api|WARNING": 1})

    def test_custom_group_by_can_group_by_service_only(self):
        lines = [
            "2026-01-01T00:00:59Z ERROR service=api msg=a",
            "2026-01-01T00:01:01Z WARNING service=api msg=b",
            "2026-01-01T00:01:03Z ERROR service=worker msg=c",
        ]

        result = rollup(lines, window_seconds=60, group_by=("service",), min_level="WARNING")

        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])
        self.assertEqual(result[0]["counts"], {"api": 1})
        self.assertEqual(result[1]["counts"], {"api": 1, "worker": 1})

    def test_non_minute_window_uses_floor_start(self):
        lines = [
            "2026-01-01T00:01:14Z INFO service=api msg=a",
            "2026-01-01T00:01:30Z INFO service=api msg=b",
        ]

        result = rollup(lines, window_seconds=45, min_level="INFO")

        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:45Z", "2026-01-01T00:01:30Z"])


if __name__ == "__main__":
    unittest.main()
