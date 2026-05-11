from __future__ import annotations

import unittest

from mdnav import collect_outline


class MarkdownOutlineTests(unittest.TestCase):
    def test_github_style_heading_anchors_and_duplicates(self):
        doc = "# Hello, World!\n## Hello World\n### Hello   World?\n"

        headings = collect_outline(doc)["headings"]

        self.assertEqual(
            [h["anchor"] for h in headings],
            ["hello-world", "hello-world-1", "hello-world-2"],
        )
        self.assertEqual([h["level"] for h in headings], [1, 2, 3])

    def test_ignores_fenced_code_and_inline_code_links(self):
        doc = '''
        # Links

        ```markdown
        [Fake](bad.md)
        ```

        Real [Guide](../guide.md#Intro Section) and `inline [Nope](bad.md)`.
        '''

        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["label"], "Guide")
        self.assertEqual(links[0]["target"], "docs/guide.md#intro-section")

    def test_reference_links_are_resolved_case_insensitively(self):
        doc = '''
        # Reference Test

        See [Install Guide][GUIDE] and [API][api-ref].

        [guide]: ../install.md#Install Steps
        [api-ref]: /api/index.md#HTTP API
        '''

        links = collect_outline(doc, base_path="docs/pages/current.md")["links"]

        self.assertEqual([link["target"] for link in links], ["docs/install.md#install-steps", "/api/index.md#http-api"])
        self.assertEqual([link["kind"] for link in links], ["reference", "reference"])


if __name__ == "__main__":
    unittest.main()
