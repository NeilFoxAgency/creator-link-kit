import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.cli import main
from creator_link_kit.codes import (
    discount_values_in_url,
    load_planned_codes,
    planned_codes_from_rows,
    reconcile_codes,
)
from creator_link_kit.config import load_convention, starter_convention
from creator_link_kit.links import audit_urls


class DiscountCodeReconcileTests(unittest.TestCase):
    def test_extracts_known_query_keys(self):
        url = (
            "https://shop.example.com/offer?utm_source=youtube"
            "&discount=PLC-GRETA-VIDEO-01"
        )
        self.assertEqual(
            discount_values_in_url(url),
            [("discount", "PLC-GRETA-VIDEO-01")],
        )

    def test_ignores_generic_id_query(self):
        url = "https://shop.example.com/offer?utm_source=youtube&id=abc"
        self.assertEqual(discount_values_in_url(url), [])

    def test_missing_planned_code_is_clk203(self):
        planned, dupes = planned_codes_from_rows(
            [{"discount_code": "plc-greta-video-01"}],
            column="discount_code",
        )
        self.assertEqual(dupes, [])
        issues = reconcile_codes(
            ["https://shop.example.com/offer?utm_source=youtube"],
            planned,
        )
        self.assertEqual([issue.code for issue in issues], ["CLK203"])
        self.assertEqual(issues[0].severity, "error")

    def test_unexpected_shipped_code_is_clk204(self):
        planned, _ = planned_codes_from_rows(
            [{"discount_code": "plc-greta-video-01"}],
            column="discount_code",
        )
        issues = reconcile_codes(
            [
                "https://shop.example.com/offer?discount=plc-greta-video-01",
                "https://shop.example.com/offer?coupon=TESTCODE",
            ],
            planned,
        )
        unexpected = [issue for issue in issues if issue.code == "CLK204"]
        self.assertEqual(len(unexpected), 1)
        self.assertEqual(unexpected[0].severity, "warning")

    def test_matching_is_case_insensitive(self):
        planned, _ = planned_codes_from_rows(
            [{"discount_code": "Plc-Greta-Video-01"}],
            column="discount_code",
        )
        issues = reconcile_codes(
            ["https://shop.example.com/offer?promo=plc-greta-video-01"],
            planned,
        )
        self.assertEqual(issues, [])

    def test_duplicate_planned_codes_are_clk205(self):
        planned, issues = planned_codes_from_rows(
            [
                {"discount_code": "SHARED"},
                {"discount_code": "shared"},
            ],
            column="discount_code",
        )
        self.assertEqual(list(planned), ["shared"])
        self.assertEqual(issues[0].code, "CLK205")
        self.assertEqual(issues[0].severity, "error")

    def test_cli_audit_with_codes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            codes = root / "codes.csv"
            links = root / "links.csv"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            codes.write_text(
                "placement_id,discount_code\n"
                "plc-greta-video-01,plc-greta-video-01\n"
                "plc-missing,plc-missing\n",
                encoding="utf-8",
            )
            links.write_text(
                "url\n"
                "https://shop.example.com/glowdrop?utm_source=youtube"
                "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
                "&utm_id=cmp-spring-launch&utm_content=plc-greta-video-01"
                "&discount=plc-greta-video-01\n",
                encoding="utf-8",
            )
            loaded, dupes = load_planned_codes(codes, load_convention(config))
            self.assertEqual(dupes, [])
            self.assertIn("plc-greta-video-01", loaded)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exit_code = main(
                    [
                        "audit",
                        "--config",
                        str(config),
                        "--input",
                        str(links),
                        "--codes",
                        str(codes),
                    ]
                )
            text = out.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("CLK203", text)
            self.assertIn("plc-missing", text)

    def test_audit_without_codes_flag_does_not_emit_clk20x(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            convention = load_convention(config_path)
        result = audit_urls(
            [
                "https://shop.example.com/glowdrop?utm_source=youtube"
                "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
                "&utm_id=cmp-spring-launch&utm_content=plc-greta-video-01"
                "&discount=X"
            ],
            convention,
        )
        self.assertFalse(any(issue.code.startswith("CLK20") for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
