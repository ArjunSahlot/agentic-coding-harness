from __future__ import annotations

import unittest

from logscan import parse_line, rollup


class RollupTests(unittest.TestCase):
    def test_parse_line_extracts_timestamp_level_and_fields(self):
        record = parse_line("2026-01-01T00:00:05Z ERROR service=api request_id=abc msg=boom")

        self.assertEqual(record["level"], "ERROR")
        self.assertEqual(record["service"], "api")
        self.assertEqual(record["request_id"], "abc")
        self.assertEqual(record["timestamp"].tzinfo.utcoffset(record["timestamp"]).total_seconds(), 0)

        result = rollup(["2026-01-01T00:00:31Z ERROR service=api msg=late"], window_seconds=60, min_level="ERROR")
        self.assertEqual(result[0]["start"], "2026-01-01T00:00:00Z")

    def test_bucket_boundaries_are_floor_based_and_end_exclusive(self):
        lines = [
            "2026-01-01T00:00:59Z INFO service=api msg=late",
            "2026-01-01T00:01:00Z INFO service=api msg=next",
        ]

        result = rollup(lines, window_seconds=60)

        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])
        self.assertEqual([row["counts"] for row in result], [{"api|INFO": 1}, {"api|INFO": 1}])

    def test_fills_empty_windows_and_filters_by_severity(self):
        lines = [
            "2026-01-01T00:00:05Z DEBUG service=api msg=debug",
            "2026-01-01T00:00:05Z ERROR service=api msg=boom",
            "2026-01-01T00:02:05Z CRITICAL service=worker msg=down",
        ]

        result = rollup(lines, window_seconds=60, min_level="WARNING")

        self.assertEqual([row["start"] for row in result], ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-01T00:02:00Z"])
        self.assertEqual(result[0]["counts"], {"api|ERROR": 1})
        self.assertEqual(result[1]["counts"], {})
        self.assertEqual(result[2]["counts"], {"worker|CRITICAL": 1})


if __name__ == "__main__":
    unittest.main()
