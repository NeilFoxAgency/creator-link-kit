import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.cli import main
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.planned import parse_planned_link, reconcile_planned


def _convention():
    return convention_from_dict(starter_convention())


PLANNED = (
    "https://shop.example.com/product"
    "?utm_medium=influencer&utm_source=youtube"
    "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
    "&utm_content=plc-greta-video-01"
)
SHIPPED_OK = PLANNED
SHIPPED_DEST = (
    "https://shop.example.com/other"
    "?utm_medium=influencer&utm_source=youtube"
    "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
    "&utm_content=plc-greta-video-01"
)
SHIPPED_UTM = (
    "https://shop.example.com/product"
    "?utm_medium=influencer&utm_source=tiktok"
    "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
    "&utm_content=plc-greta-video-01"
)
SHIPPED_EXTRA = (
    "https://shop.example.com/product"
    "?utm_medium=influencer&utm_source=youtube"
    "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
    "&utm_content=plc-priya-video-01"
)


class PlannedParseTests(unittest.TestCase):
    def test_strips_utm_from_destination(self):
        dest, utm, err = parse_planned_link(PLANNED)
        self.assertIsNone(err)
        self.assertEqual(dest, "https://shop.example.com/product")
        self.assertEqual(utm["utm_content"], "plc-greta-video-01")


class ReconcileTests(unittest.TestCase):
    def test_matching_set_is_clean(self):
        issues = reconcile_planned([PLANNED], [SHIPPED_OK], _convention())
        self.assertEqual(issues, [])

    def test_missing_planned_placement(self):
        issues = reconcile_planned([PLANNED], [SHIPPED_EXTRA], _convention())
        codes = {issue.code for issue in issues}
        self.assertIn("CLK206", codes)
        self.assertIn("CLK209", codes)

    def test_destination_drift(self):
        issues = reconcile_planned([PLANNED], [SHIPPED_DEST], _convention())
        self.assertTrue(any(issue.code == "CLK207" for issue in issues))

    def test_utm_drift_is_warning(self):
        issues = reconcile_planned([PLANNED], [SHIPPED_UTM], _convention())
        match = [issue for issue in issues if issue.code == "CLK208"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0].severity, "warning")
        self.assertIn("utm_source", match[0].message)

    def test_case_insensitive_content_when_convention_is_lowercase(self):
        shipped = PLANNED.replace("plc-greta-video-01", "PLC-GRETA-VIDEO-01")
        issues = reconcile_planned([PLANNED], [shipped], _convention())
        self.assertFalse(any(issue.code == "CLK206" for issue in issues))

    def test_duplicate_planned_keys(self):
        issues = reconcile_planned([PLANNED, PLANNED], [SHIPPED_OK], _convention())
        self.assertTrue(any(issue.code == "CLK210" for issue in issues))


class CliPlannedTests(unittest.TestCase):
    def test_audit_without_planned_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            links = Path(tmp) / "live.csv"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            links.write_text(f"url\n{SHIPPED_OK}\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["audit", "--config", str(config), "--input", str(links)])
            self.assertEqual(code, 0)
            self.assertNotIn("CLK206", output.getvalue())

    def test_cli_reports_missing_planned_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            planned = Path(tmp) / "planned.csv"
            live = Path(tmp) / "live.csv"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            planned.write_text(f"generated_url\n{PLANNED}\n", encoding="utf-8")
            live.write_text(f"url\n{SHIPPED_EXTRA}\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "audit",
                        "--config",
                        str(config),
                        "--input",
                        str(live),
                        "--planned",
                        str(planned),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("CLK206", output.getvalue())


if __name__ == "__main__":
    unittest.main()
