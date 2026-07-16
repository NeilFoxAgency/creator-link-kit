import csv
import io
import json
import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls
from creator_link_kit.report import to_csv, to_json, to_text


class ReportTests(unittest.TestCase):
    def setUp(self):
        convention = convention_from_dict(starter_convention())
        self.result = audit_urls(["https://shop.example.com/product"], convention)

    def test_json(self):
        payload = json.loads(to_json(self.result))
        self.assertEqual(payload["checked"], 1)
        self.assertGreater(payload["warnings"], 0)

    def test_csv(self):
        rows = list(csv.DictReader(io.StringIO(to_csv(self.result))))
        self.assertEqual(rows[0]["code"], "CLK004")

    def test_text(self):
        report = to_text(self.result)
        self.assertIn("CLK004", report)
        self.assertIn("1 links checked", report)


if __name__ == "__main__":
    unittest.main()
