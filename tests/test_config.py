import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from creator_link_kit.config import (
    ConfigError,
    convention_fingerprint,
    convention_from_dict,
    load_convention,
    starter_convention,
)


class ConfigTests(unittest.TestCase):
    def test_starter_is_valid(self):
        convention = convention_from_dict(starter_convention())
        self.assertEqual(convention.version, 1)
        self.assertEqual(convention.mode, "production")
        self.assertEqual(convention.defaults["utm_medium"], "influencer")
        self.assertIn("utm_id", convention.required)
        self.assertEqual(convention.batch.placement_id_column, "placement_id")
        self.assertEqual(
            convention.batch.discount_code_template,
            "{placement_id}",
        )

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

    def test_rejects_unknown_mode(self):
        raw = starter_convention()
        raw["mode"] = "strict"
        with self.assertRaisesRegex(ConfigError, "mode"):
            convention_from_dict(raw)

    def test_production_requires_owned_domain(self):
        raw = starter_convention()
        raw["owned_domains"] = []
        with self.assertRaisesRegex(ConfigError, "requires at least one"):
            convention_from_dict(raw)

    def test_production_base_url_must_be_owned(self):
        raw = starter_convention()
        raw["base_url"] = "https://example.net/product"
        with self.assertRaisesRegex(ConfigError, "base_url"):
            convention_from_dict(raw)

    def test_domain_matching_normalizes_case_and_trailing_dots(self):
        raw = starter_convention()
        raw["base_url"] = "https://SHOP.Example.COM./product"
        raw["owned_domains"] = ["Example.COM."]
        convention = convention_from_dict(raw)
        self.assertEqual(convention.owned_domains, ("example.com",))

    def test_rejects_non_hostname_owned_domain(self):
        raw = starter_convention()
        raw["owned_domains"] = ["https://example.com/path"]
        with self.assertRaisesRegex(ConfigError, "hostname"):
            convention_from_dict(raw)

    def test_rejects_unknown_identifier_column(self):
        raw = starter_convention()
        raw["batch"]["id_columns"]["order_id"] = "order_id"
        with self.assertRaisesRegex(ConfigError, "order_id"):
            convention_from_dict(raw)

    def test_rejects_bad_discount_pattern(self):
        raw = starter_convention()
        raw["batch"]["discount_code_pattern"] = "["
        with self.assertRaisesRegex(ConfigError, "discount_code_pattern"):
            convention_from_dict(raw)

    def test_rejects_reserved_discount_column(self):
        raw = starter_convention()
        raw["batch"]["discount_code_column"] = "link_spec"
        with self.assertRaisesRegex(ConfigError, "reserved output column"):
            convention_from_dict(raw)

    def test_rejects_discount_column_overwriting_placement_id(self):
        raw = starter_convention()
        raw["batch"]["discount_code_column"] = "placement_id"
        with self.assertRaisesRegex(ConfigError, "identifier or URL column"):
            convention_from_dict(raw)

    def test_rejects_credentialed_base_url(self):
        raw = starter_convention()
        raw["base_url"] = "https://user:secret@shop.example.com/product"
        with self.assertRaisesRegex(ConfigError, "embedded credentials"):
            convention_from_dict(raw)

    def test_rejects_invalid_base_url_port(self):
        raw = starter_convention()
        raw["base_url"] = "https://shop.example.com:not-a-port/product"
        with self.assertRaisesRegex(ConfigError, "invalid port"):
            convention_from_dict(raw)

    def test_legacy_config_defaults_to_development(self):
        raw = starter_convention()
        raw.pop("mode")
        raw["batch"].pop("id_columns")
        convention = convention_from_dict(raw)
        self.assertEqual(convention.mode, "development")
        self.assertEqual(convention.batch.id_columns, {})

    def test_configuration_fingerprint_is_stable_and_policy_sensitive(self):
        first = convention_from_dict(starter_convention())
        second = convention_from_dict(starter_convention())
        changed_raw = starter_convention()
        changed_raw["mode"] = "development"
        changed = convention_from_dict(changed_raw)
        self.assertEqual(convention_fingerprint(first), convention_fingerprint(second))
        self.assertNotEqual(
            convention_fingerprint(first), convention_fingerprint(changed)
        )

    @unittest.skipUnless(
        importlib.util.find_spec("yaml") is not None,
        "PyYAML optional dependency is not installed",
    )
    def test_yaml_extra_loads_with_real_dependency(self):
        import yaml

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text(yaml.safe_dump(starter_convention()), encoding="utf-8")
            self.assertEqual(load_convention(path).version, 1)

    def test_load_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(starter_convention()), encoding="utf-8")
            self.assertEqual(
                load_convention(path).base_url, "https://shop.example.com/product"
            )

    def test_bad_json_reports_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "line 1"):
                load_convention(path)


if __name__ == "__main__":
    unittest.main()
