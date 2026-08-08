import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.cli import main
from creator_link_kit.config import starter_convention


class CliTests(unittest.TestCase):
    def test_init_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.assertEqual(main(["init", str(path)]), 0)
            self.assertEqual(main(["validate-config", "--config", str(path)]), 0)

    def test_build_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "build",
                        "--config",
                        str(path),
                        "--param",
                        "utm_source=youtube",
                        "--param",
                        "utm_campaign=cmp-spring-launch",
                        "--campaign-id",
                        "cmp-spring-launch",
                        "--placement-id",
                        "plc-greta-video-01",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("utm_source=youtube", output.getvalue())
            self.assertIn("utm_id=cmp-spring-launch", output.getvalue())

    def test_build_json_specification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "build",
                        "--config",
                        str(path),
                        "--param",
                        "utm_source=youtube",
                        "--param",
                        "utm_campaign=cmp-spring-launch",
                        "--brand-id",
                        "brd-soap",
                        "--campaign-id",
                        "cmp-spring-launch",
                        "--creator-id",
                        "crt-greta",
                        "--placement-id",
                        "plc-greta-video-01",
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["ids"]["placement_id"], "plc-greta-video-01")
            self.assertTrue(payload["audit"]["valid"])

    def test_batch_writes_spec_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            roster = Path(tmp) / "roster.csv"
            output = Path(tmp) / "links.csv"
            specs = Path(tmp) / "links.jsonl"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            roster.write_text(
                "brand_id,campaign_id,creator_id,placement_id,handle,platform,"
                "landing_url\n"
                "brd-soap,cmp-spring-launch,crt-greta,plc-greta-video-01,"
                "greta,youtube,\n",
                encoding="utf-8",
            )
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(
                    [
                        "batch",
                        "--config",
                        str(config),
                        "--roster",
                        str(roster),
                        "--out",
                        str(output),
                        "--spec-out",
                        str(specs),
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(specs.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["ids"]["creator_id"], "crt-greta")

    def test_audit_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            links = Path(tmp) / "links.txt"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            links.write_text("https://shop.example.com/product\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["audit", "--config", str(config), "--input", str(links)]),
                    1,
                )

    def test_audit_extracts_urls_from_description_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            prose = Path(tmp) / "description.txt"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            prose.write_text(
                "Shop now: https://shop.example.com/product?utm_source=youtube"
                "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
                "&utm_id=cmp-spring-launch&utm_content=plc-greta-video-01).\n"
                "Thanks for watching!\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["audit", "--config", str(config), "--input", str(prose)])
            self.assertEqual(code, 0)
            self.assertIn("checked", output.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
