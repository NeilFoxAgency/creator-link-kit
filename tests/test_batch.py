import csv
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.batch import batch_csv, generate_rows
from creator_link_kit.config import convention_from_dict, starter_convention


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    @staticmethod
    def row(
        placement_id: str,
        *,
        creator_id: str = "crt-greta",
        platform: str = "youtube",
        landing_url: str = "",
    ) -> dict[str, str]:
        return {
            "brand_id": "brd-glowdrop",
            "campaign_id": "cmp-glowdrop-launch",
            "creator_id": creator_id,
            "placement_id": placement_id,
            "handle": "glowwithgreta",
            "platform": platform,
            "landing_url": landing_url,
        }

    def test_generate_good_rows(self):
        rows, summary = generate_rows([self.row("plc-greta-video-01")], self.convention)
        self.assertEqual(summary.ok, 1)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertIn("utm_id=cmp-glowdrop-launch", rows[0]["generated_url"])
        self.assertIn("utm_content=plc-greta-video-01", rows[0]["generated_url"])
        self.assertEqual(rows[0]["discount_code"], "plc-greta-video-01")

    def test_row_error_is_isolated(self):
        rows, summary = generate_rows(
            [
                self.row("plc-greta-video-01"),
                self.row("plc-greta-video-02", platform="YouTube"),
            ],
            self.convention,
        )
        self.assertEqual(summary.ok, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(rows[1]["status"], "error")

    def test_per_row_url(self):
        rows, _ = generate_rows(
            [
                self.row(
                    "plc-greta-video-01",
                    landing_url="https://shop.example.com/special?bundle=pro",
                )
            ],
            self.convention,
        )
        self.assertIn("/special?bundle=pro", rows[0]["generated_url"])

    def test_duplicate_placement_id_fails_every_duplicate_row(self):
        rows, summary = generate_rows(
            [
                self.row("plc-greta-video-01"),
                self.row("plc-greta-video-01", creator_id="crt-priya"),
            ],
            self.convention,
        )
        self.assertEqual(summary.failed, 2)
        self.assertTrue(all(row["status"] == "error" for row in rows))
        self.assertTrue(all("duplicated within batch" in row["issues"] for row in rows))

    def test_duplicate_detection_uses_custom_placement_column(self):
        raw = starter_convention()
        raw["batch"]["id_columns"] = {
            "brand_id": "brand_key",
            "campaign_id": "campaign_key",
            "creator_id": "creator_key",
            "placement_id": "asset_key",
        }
        raw["batch"]["param_map"].update(
            {
                "utm_campaign": "{campaign_key}",
                "utm_id": "{campaign_key}",
                "utm_content": "{asset_key}",
            }
        )
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [
                {
                    "brand_key": "brd-glowdrop",
                    "campaign_key": "cmp-glowdrop-launch",
                    "creator_key": "crt-greta",
                    "asset_key": "plc-duplicate",
                    "platform": "youtube",
                },
                {
                    "brand_key": "brd-glowdrop",
                    "campaign_key": "cmp-glowdrop-launch",
                    "creator_key": "crt-priya",
                    "asset_key": "plc-duplicate",
                    "platform": "youtube",
                },
            ],
            convention,
        )
        self.assertEqual(summary.failed, 2)
        self.assertTrue(all("asset_key" in row["issues"] for row in rows))

    def test_roster_without_optional_id_columns_is_supported(self):
        raw = starter_convention()
        raw["batch"].pop("id_columns")
        raw["batch"].pop("discount_code_template")
        raw["batch"].pop("discount_code_pattern")
        raw["batch"].pop("discount_code_column")
        raw["batch"]["param_map"].update(
            {
                "utm_campaign": "cmp-legacy-shaped",
                "utm_id": "cmp-legacy-shaped",
                "utm_content": "{handle}",
            }
        )
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [{"handle": "greta", "platform": "youtube"}], convention
        )
        self.assertEqual(summary.ok, 1)
        payload = json.loads(rows[0]["link_spec"])
        self.assertIsNone(payload["ids"]["brand_id"])
        self.assertIsNone(payload["ids"]["creator_id"])
        self.assertIsNone(payload["ids"]["placement_id"])

    def test_empty_present_placement_id_fails(self):
        rows, summary = generate_rows([self.row("")], self.convention)
        self.assertEqual(summary.failed, 1)
        self.assertIn("placement_id must be non-empty", rows[0]["issues"])

    def test_external_per_row_destination_fails_in_production(self):
        rows, summary = generate_rows(
            [self.row("plc-external", landing_url="https://example.net/product")],
            self.convention,
        )
        self.assertEqual(summary.failed, 1)
        self.assertIn("outside owned_domains", rows[0]["issues"])

    def test_external_per_row_destination_warns_in_development(self):
        raw = starter_convention()
        raw["mode"] = "development"
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [self.row("plc-external", landing_url="https://example.net/product")],
            convention,
        )
        self.assertEqual(summary.ok, 1)
        payload = json.loads(rows[0]["link_spec"])
        self.assertTrue(payload["audit"]["valid"])
        self.assertGreater(payload["audit"]["warnings"], 0)

    def test_multiple_placements_for_same_creator_are_allowed(self):
        rows, summary = generate_rows(
            [
                self.row("plc-greta-video-01"),
                self.row("plc-greta-video-02"),
                self.row("plc-greta-video-03"),
            ],
            self.convention,
        )
        self.assertEqual(summary.ok, 3)
        self.assertEqual(
            {json.loads(row["link_spec"])["ids"]["creator_id"] for row in rows},
            {"crt-greta"},
        )
        self.assertEqual(
            {json.loads(row["link_spec"])["ids"]["placement_id"] for row in rows},
            {
                "plc-greta-video-01",
                "plc-greta-video-02",
                "plc-greta-video-03",
            },
        )

    def test_link_spec_is_whitelisted_and_machine_readable(self):
        source = self.row("plc-greta-video-01")
        source["api_key"] = "do-not-copy"
        source["customer_email"] = "customer@example.com"
        rows, _ = generate_rows([source], self.convention)
        payload = json.loads(rows[0]["link_spec"])
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["config_version"], 1)
        self.assertEqual(payload["ids"]["brand_id"], "brd-glowdrop")
        self.assertTrue(payload["audit"]["valid"])
        serialized = rows[0]["link_spec"]
        self.assertNotIn("do-not-copy", serialized)
        self.assertNotIn("customer@example.com", serialized)

    def test_duplicate_discount_codes_fail_case_insensitively(self):
        raw = starter_convention()
        raw["batch"]["discount_code_template"] = "{handle}15"
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [
                self.row("plc-greta-video-01"),
                {
                    **self.row("plc-priya-video-01", creator_id="crt-priya"),
                    "handle": "GLOWWITHGRETA",
                },
            ],
            convention,
        )
        self.assertEqual(summary.ok, 1)
        self.assertEqual(summary.failed, 1)
        self.assertIn("duplicates row 1", rows[1]["issues"])

    def test_discount_code_pattern_rejects_bad_code(self):
        raw = starter_convention()
        raw["batch"]["discount_code_template"] = "x"
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [self.row("plc-greta-video-01")],
            convention,
        )
        self.assertEqual(summary.failed, 1)
        self.assertIn("does not match pattern", rows[0]["issues"])

    def test_discount_codes_are_optional(self):
        raw = starter_convention()
        raw["batch"].pop("discount_code_template")
        raw["batch"].pop("discount_code_pattern")
        raw["batch"].pop("discount_code_column")
        convention = convention_from_dict(raw)
        rows, summary = generate_rows(
            [self.row("plc-greta-video-01")],
            convention,
        )
        self.assertEqual(summary.ok, 1)
        self.assertNotIn("discount_code", rows[0])

    def test_ragged_roster_row_fails_cleanly(self):
        # A row with fewer cells than the header makes csv.DictReader yield
        # None for the missing columns; this must not crash the whole batch.
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roster.csv"
            source.write_text(
                "brand_id,campaign_id,creator_id,placement_id,handle,platform,"
                "landing_url\n"
                "brd-soap,cmp-spring-launch,crt-greta,plc-greta-video-01,"
                "greta,youtube,\n"
                "brd-soap,cmp-spring-launch,crt-priya\n",
                encoding="utf-8",
            )
            rows, summary = batch_csv(source, None, self.convention)
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.ok, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(rows[1]["status"], "error")
        self.assertIn("placement_id must be non-empty", rows[1]["issues"])

    def test_missing_trailing_url_cell_falls_back_to_base_url(self):
        source = self.row("plc-greta-video-01")
        source["landing_url"] = None  # type: ignore[dict-item]
        rows, summary = generate_rows([source], self.convention)
        self.assertEqual(summary.ok, 1)
        self.assertIn("https://shop.example.com/product?", rows[0]["generated_url"])

    def test_csv_round_trip_and_jsonl_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roster.csv"
            destination = Path(tmp) / "links.csv"
            spec_destination = Path(tmp) / "links.jsonl"
            source.write_text(
                "brand_id,campaign_id,creator_id,placement_id,handle,platform,"
                "landing_url\n"
                "brd-glowdrop,cmp-glowdrop-launch,crt-greta,"
                "plc-greta-video-01,glowwithgreta,youtube,\n",
                encoding="utf-8",
            )
            _, summary = batch_csv(
                source,
                destination,
                self.convention,
                spec_output_path=spec_destination,
            )
            self.assertEqual(summary.failed, 0)
            with destination.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["discount_code"], "plc-greta-video-01")
            specs = [
                json.loads(line)
                for line in spec_destination.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(specs[0]["ids"]["placement_id"], "plc-greta-video-01")

    def test_jsonl_contains_only_valid_specs_for_mixed_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roster.csv"
            specs_path = Path(tmp) / "links.jsonl"
            source.write_text(
                "brand_id,campaign_id,creator_id,placement_id,handle,platform\n"
                "brd-glowdrop,cmp-glowdrop-launch,crt-greta,plc-good,greta,youtube\n"
                "brd-glowdrop,cmp-glowdrop-launch,crt-greta,plc-bad,greta,YouTube\n",
                encoding="utf-8",
            )
            _, summary = batch_csv(
                source,
                None,
                self.convention,
                spec_output_path=specs_path,
            )
            specs = specs_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(summary.ok, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(len(specs), 1)
        self.assertEqual(json.loads(specs[0])["ids"]["placement_id"], "plc-good")


if __name__ == "__main__":
    unittest.main()
