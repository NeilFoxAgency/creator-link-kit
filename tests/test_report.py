import csv
import io
import json
import unittest
from html.parser import HTMLParser

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls
from creator_link_kit.report import to_csv, to_html, to_json, to_text


class _ScriptTagFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_tags = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "script":
            self.script_tags += 1


class ReportTests(unittest.TestCase):
    def setUp(self):
        convention = convention_from_dict(starter_convention())
        self.result = audit_urls(["https://shop.example.com/product"], convention)

    def test_json(self):
        payload = json.loads(to_json(self.result))
        self.assertEqual(payload["checked"], 1)
        self.assertGreater(payload["warnings"], 0)
        self.assertGreater(payload["errors"], 0)
        self.assertIn("by_code", payload)
        self.assertIn("CLK004", payload["by_code"])
        self.assertEqual(payload["by_code"]["CLK004"]["warnings"], 1)

    def test_csv(self):
        rows = list(csv.DictReader(io.StringIO(to_csv(self.result))))
        self.assertEqual(rows[0]["code"], "CLK004")

    def test_text(self):
        report = to_text(self.result)
        self.assertIn("CLK004", report)
        self.assertIn("1 links checked", report)
        self.assertIn("By rule code:", report)
        self.assertIn("CLK004:", report)

    def test_text_code_summary_aggregates(self):
        convention = convention_from_dict(starter_convention())
        urls = [
            "https://shop.example.com/product",
            "https://shop.example.com/other",
        ]
        result = audit_urls(urls, convention)
        report = to_text(result)
        self.assertIn("By rule code:", report)
        # Both URLs lack UTMs, so CLK004 should appear twice as warnings.
        self.assertRegex(report, r"CLK004: 2 warning\(s\)")

    def test_html_includes_summary_and_issue(self):
        report = to_html(self.result)
        self.assertIn("<!DOCTYPE html>", report)
        self.assertIn("1 links checked", report)
        self.assertIn("CLK004", report)
        self.assertIn("https://shop.example.com/product", report)
        self.assertIn("By rule code", report)
        self.assertIn("<table>", report)

    def test_html_escapes_dynamic_content(self):
        convention = convention_from_dict(starter_convention())
        hostile = (
            "https://shop.example.com/x?utm_source=<script>alert(1)</script>"
            "&utm_medium=influencer&utm_campaign=cmp-test"
            "&utm_id=cmp-test&utm_content=plc-test-01"
        )
        result = audit_urls([hostile], convention)
        report = to_html(result)
        self.assertNotIn("<script>alert(1)</script>", report)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", report)
        finder = _ScriptTagFinder()
        finder.feed(report)
        self.assertEqual(finder.script_tags, 0)


if __name__ == "__main__":
    unittest.main()
