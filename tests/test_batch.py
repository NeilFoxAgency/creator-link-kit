import csv
from pathlib import Path
import tempfile
import unittest

from creator_link_kit.batch import batch_csv, generate_rows
from creator_link_kit.config import convention_from_dict, starter_convention


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def test_generate_good_rows(self):
        rows, summary = generate_rows(
            [{"handle": "greta", "platform": "youtube", "landing_url": ""}],
            self.convention,
        )
        self.assertEqual(summary.ok, 1)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertIn("utm_content=greta", rows[0]["generated_url"])

    def test_row_error_is_isolated(self):
        rows, summary = generate_rows(
            [
                {"handle": "greta", "platform": "youtube", "landing_url": ""},
                {"handle": "bad", "platform": "YouTube", "landing_url": ""},
            ],
            self.convention,
        )
        self.assertEqual(summary.ok, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(rows[1]["status"], "error")

    def test_per_row_url(self):
        rows, _ = generate_rows(
            [{
                "handle": "greta",
                "platform": "youtube",
                "landing_url": "https://shop.example.com/special?bundle=pro",
            }],
            self.convention,
        )
        self.assertIn("/special?bundle=pro", rows[0]["generated_url"])

    def test_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roster.csv"
            destination = Path(tmp) / "links.csv"
            source.write_text(
                "handle,platform,landing_url\ngreta,youtube,\n", encoding="utf-8"
            )
            _, summary = batch_csv(source, destination, self.convention)
            self.assertEqual(summary.failed, 0)
            with destination.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["status"], "ok")


if __name__ == "__main__":
    unittest.main()
