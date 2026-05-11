from __future__ import annotations

import unittest

from licensecheck import audit


POLICY = {
    "allow": ["MIT", "Apache-2.0", "BSD-3-Clause"],
    "deny": ["GPL-3.0", "AGPL-3.0"],
    "exceptions": [{"package": "legacy", "license": "LGPL-2.1", "reason": "approved"}],
}


class AdditionalLicenseAuditTests(unittest.TestCase):
    def test_dependency_cycles_are_traversed_once(self):
        packages = {
            "app": {"license": "MIT", "deps": ["bad"]},
            "bad": {"license": "GPL-3.0", "deps": ["app"]},
        }

        violations = audit(packages, "app", POLICY)

        self.assertEqual(violations, [{"package": "bad", "license": "GPL-3.0", "reason": "denied"}])

    def test_exception_is_package_specific(self):
        packages = {
            "app": {"license": "MIT", "deps": ["legacy", "other"]},
            "legacy": {"license": "LGPL-2.1", "deps": []},
            "other": {"license": "LGPL-2.1", "deps": []},
        }

        violations = audit(packages, "app", POLICY)

        self.assertEqual([row["package"] for row in violations], ["other"])

    def test_and_expression_passes_when_all_parts_are_allowed_after_normalization(self):
        packages = {"app": {"license": "MIT AND Apache 2", "deps": []}}

        self.assertEqual(audit(packages, "app", POLICY), [])

    def test_root_package_is_audited_too(self):
        packages = {"app": {"license": "AGPL-3.0", "deps": []}}

        violations = audit(packages, "app", POLICY)

        self.assertEqual(violations[0]["package"], "app")
        self.assertEqual(violations[0]["reason"], "denied")


if __name__ == "__main__":
    unittest.main()
