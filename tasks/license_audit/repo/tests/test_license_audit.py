from __future__ import annotations

import unittest

from licensecheck import audit


PACKAGES = {
    "app": {"license": "MIT", "deps": ["ui", "parser", "badlib", "legacy"]},
    "ui": {"license": "Apache 2", "deps": ["colors"]},
    "colors": {"license": "BSD 3-Clause", "deps": []},
    "parser": {"license": "MIT OR GPL-3.0", "deps": []},
    "badlib": {"license": "GPL-3.0", "deps": []},
    "legacy": {"license": "LGPL-2.1", "deps": []},
}

POLICY = {
    "allow": ["MIT", "Apache-2.0", "BSD-3-Clause"],
    "deny": ["GPL-3.0", "AGPL-3.0"],
    "exceptions": [{"package": "legacy", "license": "LGPL-2.1", "reason": "approved vendor contract"}],
}


class LicenseAuditTests(unittest.TestCase):
    def test_traverses_transitive_dependencies_and_normalizes_aliases(self):
        violations = audit(PACKAGES, "app", POLICY)

        self.assertEqual([row["package"] for row in violations], ["badlib"])
        self.assertEqual(violations[0]["license"], "GPL-3.0")

    def test_or_expression_is_allowed_when_any_choice_is_allowed(self):
        packages = {"app": {"license": "MIT OR GPL-3.0", "deps": []}}

        self.assertEqual(audit(packages, "app", POLICY), [])

    def test_and_expression_requires_all_parts_allowed(self):
        packages = {"app": {"license": "MIT AND GPL-3.0", "deps": []}}

        violations = audit(packages, "app", POLICY)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["reason"], "denied")

    def test_package_specific_exception_allows_license(self):
        packages = {"legacy": {"license": "LGPL-2.1", "deps": []}}

        self.assertEqual(audit(packages, "legacy", POLICY), [])


if __name__ == "__main__":
    unittest.main()
