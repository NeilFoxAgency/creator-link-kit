import unittest

from creator_link_kit.config import (
    ConfigError,
    convention_from_dict,
    starter_convention,
)
from creator_link_kit.models import LinkAudit, LinkIdentifiers, LinkSpecification


class StrictConventionSchemaTests(unittest.TestCase):
    def test_rejects_boolean_version(self):
        raw = starter_convention()
        raw["version"] = True
        with self.assertRaisesRegex(ConfigError, "version"):
            convention_from_dict(raw)

    def test_rejects_boolean_max_value_length(self):
        raw = starter_convention()
        raw["max_value_length"] = True
        with self.assertRaisesRegex(ConfigError, "positive integer"):
            convention_from_dict(raw)

    def test_rejects_unknown_top_level_key(self):
        raw = starter_convention()
        raw["max_value_lenght"] = 120
        with self.assertRaisesRegex(ConfigError, "max_value_lenght"):
            convention_from_dict(raw)

    def test_rejects_unknown_parameter_rule_key(self):
        raw = starter_convention()
        raw["parameters"]["utm_source"]["allowd"] = ["youtube"]
        with self.assertRaisesRegex(ConfigError, "allowd"):
            convention_from_dict(raw)

    def test_rejects_unknown_batch_key(self):
        raw = starter_convention()
        raw["batch"]["url_colum"] = "landing_url"
        with self.assertRaisesRegex(ConfigError, "url_colum"):
            convention_from_dict(raw)

    def test_link_specification_rejects_boolean_versions(self):
        values = {
            "original_destination": "https://example.com/product",
            "generated_destination": ("https://example.com/product?utm_source=youtube"),
            "identifiers": LinkIdentifiers(),
            "audit": LinkAudit(),
        }
        with self.assertRaisesRegex(ValueError, "config_version"):
            LinkSpecification(**values, config_version=True)
        with self.assertRaisesRegex(ValueError, "schema_version"):
            LinkSpecification(**values, config_version=1, schema_version=True)


if __name__ == "__main__":
    unittest.main()
