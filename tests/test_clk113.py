import unittest
from urllib.parse import quote

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import build_url, validate_params, validate_url


class WhitespaceUtmValueTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def test_whitespace_only_value_is_clk113(self):
        issues = validate_params(
            {
                "utm_source": "   ",
                "utm_medium": "influencer",
                "utm_campaign": "cmp-spring-launch",
                "utm_id": "cmp-spring-launch",
                "utm_content": "plc-greta-01",
            },
            self.convention,
        )
        issue = next(item for item in issues if item.code == "CLK113")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "utm_source")
        self.assertIn("whitespace-only", issue.message)

    def test_leading_trailing_whitespace_is_clk113(self):
        issues = validate_params(
            {
                "utm_source": "youtube",
                "utm_medium": "influencer",
                "utm_campaign": " cmp-spring-launch ",
                "utm_id": "cmp-spring-launch",
                "utm_content": "plc-greta-01",
            },
            self.convention,
        )
        issue = next(item for item in issues if item.code == "CLK113")
        self.assertEqual(issue.parameter, "utm_campaign")
        self.assertIn("leading or trailing whitespace", issue.message)

    def test_encoded_whitespace_only_in_url_is_clk113(self):
        url = (
            "https://shop.example.com/product?utm_source="
            + quote("   ")
            + "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertIn("CLK113", {issue.code for issue in issues})

    def test_build_rejects_leading_whitespace(self):
        params = {
            "utm_source": "youtube",
            "utm_medium": "influencer",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": " plc-greta-01",
        }
        with self.assertRaisesRegex(ValueError, "CLK113"):
            build_url("https://shop.example.com/product", params, self.convention)

    def test_interior_whitespace_does_not_trigger_clk113(self):
        issues = validate_params(
            {
                "utm_source": "youtube",
                "utm_medium": "influencer",
                "utm_campaign": "cmp spring launch",
                "utm_id": "cmp-spring-launch",
                "utm_content": "plc-greta-01",
            },
            self.convention,
        )
        self.assertNotIn("CLK113", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
