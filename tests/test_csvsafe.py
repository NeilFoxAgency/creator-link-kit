import csv
import io
from pathlib import Path
import tempfile
import unittest

from creator_link_kit.batch import batch_csv
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.csvsafe import safe_cell, safe_row


class CsvSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralized(self):
        for value in ("=1+1", "+SUM(A1:A2)", "-2+3", "@cmd", "\t=1", "\r=1", "\n=1"):
            with self.subTest(value=value):
                self.assertEqual(safe_cell(value), "'" + value)

    def test_normal_and_non_string_values_are_unchanged(self):
        self.assertEqual(safe_cell("creator-name"), "creator-name")
        self.assertEqual(safe_cell("https://example.com"), "https://example.com")
        self.assertEqual(safe_cell(42), 42)
        self.assertIsNone(safe_cell(None))

    def test_safe_row_returns_a_copy(self):
        source = {"name": "=HYPERLINK(\"https://example.com\")", "count": 1}
        result = safe_row(source)
        self.assertEqual(result["name"], "'=HYPERLINK(\"https://example.com\")")
        self.assertEqual(source["name"], "=HYPERLINK(\"https://example.com\")")

    def test_batch_csv_sanitizes_untrusted_roster_cells(self):
        convention = convention_from_dict(starter_convention())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roster.csv"
            destination = Path(tmp) / "links.csv"
            source.write_text(
                'handle,name,platform,landing_url\ngreta,"=1+1",youtube,\n',
                encoding="utf-8",
            )

            rows, summary = batch_csv(source, destination, convention)

            self.assertEqual(summary.failed, 0)
            self.assertEqual(rows[0]["name"], "=1+1")
            with destination.open(newline="", encoding="utf-8") as handle:
                exported = next(csv.DictReader(handle))
            self.assertEqual(exported["name"], "'=1+1")

    def test_safe_row_remains_valid_csv(self):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=["value"])
        writer.writeheader()
        writer.writerow(safe_row({"value": "=SUM(1,2)"}))
        buffer.seek(0)
        self.assertEqual(next(csv.DictReader(buffer))["value"], "'=SUM(1,2)")


if __name__ == "__main__":
    unittest.main()
