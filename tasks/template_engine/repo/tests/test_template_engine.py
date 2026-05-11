from __future__ import annotations

import unittest

from minitpl import render


class TemplateEngineTests(unittest.TestCase):
    def test_variables_are_html_escaped_by_default(self):
        output = render("<h1>{{ title }}</h1>", {"title": "<Hello & Goodbye>"})

        self.assertEqual(output, "<h1>&lt;Hello &amp; Goodbye&gt;</h1>")

    def test_safe_and_case_filters(self):
        output = render("{{ name|upper }} {{ html|safe }}", {"name": "Ada", "html": "<strong>ok</strong>"})

        self.assertEqual(output, "ADA <strong>ok</strong>")

    def test_for_loop_with_loop_index_and_dotted_lookup(self):
        template = "{% for item in items %}{{ loop.index }}. {{ item.name }}={{ item.count }};{% endfor %}"
        context = {"items": [{"name": "apples", "count": 2}, {"name": "pears", "count": 3}]}

        self.assertEqual(render(template, context), "1. apples=2;2. pears=3;")

    def test_if_else_and_default_filter(self):
        template = "{% if user.active %}{{ user.name }}{% else %}{{ missing|default:\"guest\" }}{% endif %}"

        self.assertEqual(render(template, {"user": {"active": False, "name": "Lin"}}), "guest")
        self.assertEqual(render(template, {"user": {"active": True, "name": "Lin"}}), "Lin")


if __name__ == "__main__":
    unittest.main()
