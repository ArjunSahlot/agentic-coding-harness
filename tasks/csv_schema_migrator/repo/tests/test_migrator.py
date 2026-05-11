from __future__ import annotations

import unittest

from datamap import migrate_rows


SCHEMA = {
    "customer_id": {"aliases": ["Customer ID", "customer"], "type": "int", "required": True},
    "joined_on": {"aliases": ["Joined", "Signup Date"], "type": "date", "required": True},
    "active": {"aliases": ["Active"], "type": "bool", "required": False},
    "seats": {"aliases": ["Seat Count"], "type": "int", "required": False},
}


class MigratorTests(unittest.TestCase):
    def test_aliases_and_type_coercion(self):
        rows = [{"Customer ID": " 42 ", "Joined": "01/05/2026", "Active": "yes", "Seat Count": "3", "Ignored": "x"}]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records, [{"customer_id": 42, "joined_on": "2026-01-05", "active": True, "seats": 3}])

    def test_boolean_false_strings_are_false(self):
        rows = [
            {"Customer ID": "1", "Joined": "2026-02-01", "Active": "no"},
            {"Customer ID": "2", "Joined": "2026-02-02", "Active": "0"},
        ]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual([row["active"] for row in records], [False, False])

    def test_invalid_rows_are_omitted_and_reported_one_based(self):
        rows = [
            {"Customer ID": "abc", "Joined": "2026-02-01", "Active": "yes"},
            {"Customer ID": "", "Joined": "not a date", "Active": "yes"},
            {"Customer ID": "8", "Joined": "5 Feb 2026", "Active": "false"},
        ]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(records, [{"customer_id": 8, "joined_on": "2026-02-05", "active": False, "seats": None}])
        self.assertEqual([err["row"] for err in errors], [1, 2])
        self.assertTrue(all("message" in err and err["message"] for err in errors))


if __name__ == "__main__":
    unittest.main()
