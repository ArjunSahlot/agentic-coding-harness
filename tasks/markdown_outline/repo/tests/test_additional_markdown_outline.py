from __future__ import annotations

import unittest

from mdnav import collect_outline


class AdditionalMarkdownOutlineTests(unittest.TestCase):
    def test_headings_inside_fenced_code_are_ignored(self):
        doc = "# Real Heading\n\n```markdown\n## Fake Heading\n```\n"

        headings = collect_outline(doc)["headings"]

        self.assertEqual([heading["title"] for heading in headings], ["Real Heading"])

    def test_external_and_mailto_links_are_not_rebased(self):
        doc = "`[Skip](https://example.com/bad)` [Site](https://example.com/docs#Top) [Mail](mailto:help@example.com)"

        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

        self.assertEqual([link["target"] for link in links], ["https://example.com/docs#Top", "mailto:help@example.com"])

    def test_relative_path_without_fragment_is_normalized(self):
        doc = "![Logo](../assets/logo.png) and [Sibling](sibling.md#Intro Section)"

        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

        self.assertEqual([link["target"] for link in links], ["docs/assets/logo.png", "docs/pages/sibling.md#intro-section"])


if __name__ == "__main__":
    unittest.main()
