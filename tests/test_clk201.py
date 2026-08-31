import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.cli import main
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.roster import load_expected_placement_ids, roster_coverage_issues


class RosterCoverageTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def _url(self, content: str) -> str:
        return (
            "https://shop.example.com/product?utm_source=youtube"
            "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
            f"&utm_id=cmp-spring-launch&utm_content={content}"
        )

    def test_loader_reads_unique_placement_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            roster = Path(tmp) / "roster.csv"
            roster.write_text(
                "placement_id,platform\n"
                "plc-greta-video-01,youtube\n"
                "PLC-GRETA-VIDEO-01,youtube\n"
                ",youtube\n"
                "plc-priya-video-01,youtube\n",
                encoding="utf-8",
            )
            loaded = load_expected_placement_ids(roster, self.convention)
            self.assertEqual(
                loaded, ("plc-greta-video-01", "plc-priya-video-01")
            )

    def test_missing_expected_placement_is_clk201(self):
        issues = roster_coverage_issues(
            [self._url("plc-greta-video-01")],
            ("plc-greta-video-01", "plc-priya-video-01"),
            self.convention,
        )
        codes = [issue.code for issue in issues]
        self.assertIn("CLK201", codes)
        missing = [issue for issue in issues if issue.code == "CLK201"]
        self.assertEqual(len(missing), 1)
        self.assertIn("plc-priya-video-01", missing[0].message)
        self.assertEqual(missing[0].severity, "error")

    def test_unexpected_shipped_placement_is_clk202_warning(self):
        issues = roster_coverage_issues(
            [self._url("plc-extra-video-01")],
            ("plc-greta-video-01",),
            self.convention,
        )
        extra = [issue for issue in issues if issue.code == "CLK202"]
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra[0].severity, "warning")
        self.assertEqual(extra[0].parameter, "utm_content")

    def test_matching_roster_emits_no_coverage_codes(self):
        issues = roster_coverage_issues(
            [self._url("plc-greta-video-01"), self._url("plc-priya-video-01")],
            ("plc-greta-video-01", "plc-priya-video-01"),
            self.convention,
        )
        codes = {issue.code for issue in issues}
        self.assertNotIn("CLK201", codes)
        self.assertNotIn("CLK202", codes)

    def test_cli_audit_with_roster_flags_missing_placement(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            roster = Path(tmp) / "roster.csv"
            shipped = Path(tmp) / "live.txt"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            roster.write_text(
                "brand_id,campaign_id,creator_id,placement_id,platform\n"
                "brd-soap,cmp-spring-launch,crt-greta,plc-greta-video-01,youtube\n"
                "brd-soap,cmp-spring-launch,crt-priya,plc-priya-video-01,youtube\n",
                encoding="utf-8",
            )
            shipped.write_text(self._url("plc-greta-video-01") + "\n", encoding="utf-8")
            import contextlib
            import io

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "audit",
                        "--config",
                        str(config),
                        "--input",
                        str(shipped),
                        "--roster",
                        str(roster),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("CLK201", output.getvalue())


if __name__ == "__main__":
    unittest.main()
