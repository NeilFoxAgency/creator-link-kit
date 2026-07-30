import csv
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.batch import batch_csv
from creator_link_kit.config import load_convention

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "v0.1"


class V01CompatibilityTests(unittest.TestCase):
    def test_literal_v01_fixture_loads_and_batches_without_v02_columns(self):
        convention = load_convention(FIXTURE_DIR / "convention.json")
        self.assertEqual(convention.mode, "development")
        self.assertEqual(convention.batch.id_columns, {})
        self.assertIsNone(convention.batch.discount_code_template)
        self.assertEqual(
            convention.required,
            ("utm_source", "utm_medium", "utm_campaign"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "links.csv"
            specs = Path(tmp) / "links.jsonl"
            rows, summary = batch_csv(
                FIXTURE_DIR / "roster.csv",
                output,
                convention,
                spec_output_path=specs,
            )
            specification_lines = specs.read_text(encoding="utf-8").splitlines()
            with output.open(newline="", encoding="utf-8") as handle:
                exported = list(csv.DictReader(handle))

        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.ok, 3)
        self.assertEqual(summary.failed, 0)
        self.assertIn("utm_content=glowwithgreta", rows[0]["generated_url"])
        self.assertNotIn("discount_code", rows[0])

        specifications = [json.loads(line) for line in specification_lines]
        self.assertEqual(len(specifications), 3)
        self.assertEqual(specifications[0]["schema_version"], 1)
        self.assertEqual(specifications[0]["config_version"], 1)
        self.assertEqual(specifications[0]["ids"]["placement_id"], None)
        self.assertTrue(specifications[0]["audit"]["valid"])

        self.assertEqual(exported[2]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
