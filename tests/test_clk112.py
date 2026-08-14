import unittest
from urllib.parse import quote

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import build_url, validate_params, validate_url


class UnresolvedTemplateTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def test_common_template_forms_are_clk112(self):
        for value in ("{{paid_social}}", "${SOURCE}", "%{campaign}%", "[[CREATOR]]"):
            with self.subTest(value=value):
                issues = validate_params(
                    {
                        "utm_source": "youtube",
                        "utm_medium": value,
                        "utm_campaign": "cmp-spring-launch",
                        "utm_id": "cmp-spring-launch",
                        "utm_content": "plc-greta-01",
                    },
                    self.convention,
                )
                issue = next(item for item in issues if item.code == "CLK112")
                self.assertEqual(issue.severity, "error")
                self.assertEqual(issue.parameter, "utm_medium")

    def test_url_decoding_surfaces_clk112(self):
        encoded = quote("{{paid_social}}", safe="")
        url = (
            "https://shop.example.com/product?utm_source=youtube"
            f"&utm_medium={encoded}&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        self.assertIn("CLK112", {issue.code for issue in validate_url(url, self.convention)})

    def test_build_rejects_unresolved_template(self):
        params = {
            "utm_source": "youtube",
            "utm_medium": "{{paid_social}}",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": "plc-greta-01",
        }
        with self.assertRaisesRegex(ValueError, "CLK112"):
            build_url("https://shop.example.com/product", params, self.convention)

    def test_ordinary_values_are_not_false_positives(self):
        issues = validate_params(
            {
                "utm_source": "youtube",
                "utm_medium": "influencer",
                "utm_campaign": "cmp-spring-launch",
                "utm_id": "cmp-spring-launch",
                "utm_content": "plc-greta-01",
            },
            self.convention,
        )
        self.assertNotIn("CLK112", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
