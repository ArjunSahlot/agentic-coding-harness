from __future__ import annotations

import unittest

from minitpl import render


class AdditionalTemplateEngineTests(unittest.TestCase):
    def test_missing_variable_without_default_renders_empty_string(self):
        self.assertEqual(render("Hello {{ missing }}!", {}), "Hello !")
        self.assertEqual(render('Hello {{ missing|default:"<guest>" }}!', {}), "Hello &lt;guest&gt;!")

    def test_lower_filter_and_default_value_are_escaped(self):
        template = "{{ name|lower }} {{ missing|default:\"<guest>\" }}"

        self.assertEqual(render(template, {"name": "ADA"}), "ada &lt;guest&gt;")

    def test_loop_variable_does_not_leak_after_loop(self):
        template = "{% for item in items %}{{ item.name }} {% endfor %}{{ item.name|default:\"none\" }}"

        self.assertEqual(render(template, {"items": [{"name": "one"}]}), "one none")

    def test_false_condition_without_else_renders_nothing(self):
        template = "A{% if user.active %}B{% endif %}C"

        self.assertEqual(render(template, {"user": {"active": False}}), "AC")


if __name__ == "__main__":
    unittest.main()
