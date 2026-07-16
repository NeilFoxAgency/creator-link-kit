import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from creator_link_kit.cli import main
from creator_link_kit.config import starter_convention


class CliTests(unittest.TestCase):
    def test_init_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.assertEqual(main(["init", str(path)]), 0)
            self.assertEqual(main(["validate-config", "--config", str(path)]), 0)

    def test_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([
                    "build",
                    "--config", str(path),
                    "--param", "utm_source=youtube",
                    "--param", "utm_campaign=spring-launch",
                    "--param", "utm_content=greta",
                ])
            self.assertEqual(code, 0)
            self.assertIn("utm_source=youtube", output.getvalue())

    def test_audit_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            links = Path(tmp) / "links.txt"
            config.write_text(json.dumps(starter_convention()), encoding="utf-8")
            links.write_text("https://shop.example.com/product\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["audit", "--config", str(config), "--input", str(links)]), 1)


if __name__ == "__main__":
    unittest.main()
