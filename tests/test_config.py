import json
from pathlib import Path
import tempfile
import unittest

from creator_link_kit.config import ConfigError, convention_from_dict, load_convention, starter_convention


class ConfigTests(unittest.TestCase):
    def test_starter_is_valid(self):
        convention = convention_from_dict(starter_convention())
        self.assertEqual(convention.version, 1)
        self.assertEqual(convention.defaults["utm_medium"], "influencer")

    def test_rejects_wrong_version(self):
        raw = starter_convention()
        raw["version"] = 2
        with self.assertRaisesRegex(ConfigError, "version"):
            convention_from_dict(raw)

    def test_rejects_bad_regex(self):
        raw = starter_convention()
        raw["parameters"]["utm_campaign"]["pattern"] = "["
        with self.assertRaisesRegex(ConfigError, "invalid"):
            convention_from_dict(raw)

    def test_rejects_unknown_required_rule(self):
        raw = starter_convention()
        raw["required"].append("utm_term")
        with self.assertRaisesRegex(ConfigError, "need rules"):
            convention_from_dict(raw)

    def test_load_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            self.assertEqual(load_convention(path).base_url, "https://shop.example.com/product")

    def test_bad_json_reports_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "line 1"):
                load_convention(path)


if __name__ == "__main__":
    unittest.main()
