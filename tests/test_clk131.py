import unittest
from urllib.parse import quote

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import build_url, validate_params, validate_url


class ControlCharacterUtmValueTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def _params(self, **overrides):
        values = {
            "utm_source": "youtube",
            "utm_medium": "influencer",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": "plc-greta-01",
        }
        values.update(overrides)
        return values

    def test_newline_in_campaign_is_clk131(self):
        issues = validate_params(self._params(utm_campaign="cmp-\nspring"), self.convention)
        issue = next(item for item in issues if item.code == "CLK131")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "utm_campaign")
        self.assertIn("LF", issue.message)

    def test_tab_in_content_is_clk131(self):
        issues = validate_params(self._params(utm_content="plc\tgreta-01"), self.convention)
        issue = next(item for item in issues if item.code == "CLK131")
        self.assertEqual(issue.parameter, "utm_content")
        self.assertIn("TAB", issue.message)

    def test_carriage_return_is_clk131(self):
        issues = validate_params(self._params(utm_source="you\rtube"), self.convention)
        issue = next(item for item in issues if item.code == "CLK131")
        self.assertIn("CR", issue.message)

    def test_ordinary_space_is_not_clk131(self):
        issues = validate_params(
            self._params(utm_campaign="cmp spring launch"), self.convention
        )
        self.assertNotIn("CLK131", {issue.code for issue in issues})

    def test_encoded_newline_in_url_is_clk131(self):
        url = (
            "https://shop.example.com/product?utm_source=youtube"
            "&utm_medium=influencer&utm_campaign="
            + quote("cmp-\nspring")
            + "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertIn("CLK131", {issue.code for issue in issues})

    def test_build_rejects_control_characters(self):
        with self.assertRaisesRegex(ValueError, "CLK131"):
            build_url(
                "https://shop.example.com/product",
                self._params(utm_content="plc-greta-01\n"),
                self.convention,
            )


if __name__ == "__main__":
    unittest.main()
