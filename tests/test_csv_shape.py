import tempfile
import unittest
from pathlib import Path

from creator_link_kit.batch import batch_csv
from creator_link_kit.config import convention_from_dict, starter_convention


class CsvShapeTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def _write(self, directory: str, content: str) -> Path:
        path = Path(directory) / "roster.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_rejects_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            roster = self._write(
                tmp,
                "platform,campaign_id,campaign_id,placement_id\n"
                "youtube,cmp-one,cmp-two,plc-one\n",
            )
            with self.assertRaisesRegex(ValueError, "duplicate header"):
                batch_csv(roster, None, self.convention)

    def test_rejects_blank_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            roster = self._write(
                tmp,
                "platform,,placement_id,landing_url\n"
                "youtube,cmp-one,plc-one,https://shop.example.com/product\n",
            )
            with self.assertRaisesRegex(ValueError, "blank header"):
                batch_csv(roster, None, self.convention)

    def test_rejects_surplus_row_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            roster = self._write(
                tmp,
                "platform,campaign_id,placement_id,landing_url\n"
                "youtube,cmp-one,plc-one,https://shop.example.com/product,extra\n",
            )
            with self.assertRaisesRegex(ValueError, "more values than headers"):
                batch_csv(roster, None, self.convention)

    def test_trims_headers_and_keeps_short_row_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            roster = self._write(
                tmp,
                " platform , campaign_id , placement_id , landing_url \n"
                "youtube,cmp-one,plc-one\n",
            )
            rows, summary = batch_csv(roster, None, self.convention)
            self.assertEqual(summary.ok, 1)
            self.assertEqual(rows[0]["status"], "ok")
            self.assertIn("utm_content=plc-one", rows[0]["generated_url"])


if __name__ == "__main__":
    unittest.main()
