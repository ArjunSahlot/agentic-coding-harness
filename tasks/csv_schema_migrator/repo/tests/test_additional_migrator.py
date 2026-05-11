from __future__ import annotations

import unittest

from datamap import migrate_rows


SCHEMA = {
    "customer_id": {"aliases": ["Customer ID", "customer"], "type": "int", "required": True},
    "joined_on": {"aliases": ["Joined", "Signup Date"], "type": "date", "required": True},
    "active": {"aliases": ["Active"], "type": "bool", "required": False},
    "seats": {"aliases": ["Seat Count"], "type": "int", "required": False},
}


class AdditionalMigratorTests(unittest.TestCase):
    def test_canonical_field_takes_precedence_over_alias(self):
        rows = [{"customer_id": "7", "Customer ID": "999", "Joined": "2026-03-01", "Active": "y"}]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["customer_id"], 7)
        self.assertEqual(records[0]["active"], True)

        rows = [{"customer_id": "8", "Customer ID": "999", "Joined": "2026-03-01", "Active": "no"}]
        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["customer_id"], 8)
        self.assertEqual(records[0]["active"], False)

    def test_optional_blank_values_are_kept_as_none(self):
        rows = [{"Customer ID": "11", "Joined": "2026-03-02", "Active": "", "Seat Count": ""}]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["active"], None)
        self.assertEqual(records[0]["seats"], None)

        rows = [{"Customer ID": "12", "Joined": "2026-03-02", "Active": "false", "Seat Count": "0"}]
        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["active"], False)
        self.assertEqual(records[0]["seats"], 0)

    def test_invalid_boolean_omits_row_and_reports_field(self):
        rows = [{"Customer ID": "12", "Joined": "2026-03-03", "Active": "sometimes"}]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(records, [])
        self.assertEqual(errors[0]["row"], 1)
        self.assertEqual(errors[0]["field"], "active")

    def test_day_month_name_dates_are_accepted(self):
        rows = [{"Customer ID": "13", "Joined": "17 Mar 2026", "Active": "true"}]

        records, errors = migrate_rows(rows, SCHEMA)

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["joined_on"], "2026-03-17")


if __name__ == "__main__":
    unittest.main()
