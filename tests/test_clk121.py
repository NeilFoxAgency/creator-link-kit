"""CLK121: invisible and format-control characters must not hide in UTM values."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_params, validate_url


class InvisibleUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())
        self.base_params = {
            "utm_source": "youtube",
            "utm_medium": "influencer",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": "plc-greta-01",
        }

    def test_zero_width_space_in_value_is_error(self) -> None:
        params = dict(self.base_params)
        params["utm_source"] = "you\u200btube"
        issues = validate_params(params, self.convention)
        issue = next(item for item in issues if item.code == "CLK121")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "utm_source")
        self.assertIn("U+200B", issue.message)

    def test_nbsp_in_campaign_is_error(self) -> None:
        params = dict(self.base_params)
        params["utm_campaign"] = "cmp\u00a0spring-launch"
        issues = validate_params(params, self.convention)
        self.assertTrue(any(item.code == "CLK121" for item in issues))

    def test_percent_encoded_zwsp_in_url_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=you%E2%80%8Btube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertIn("CLK121", {issue.code for issue in issues})

    def test_bom_prefixed_value_is_error(self) -> None:
        params = dict(self.base_params)
        params["utm_content"] = "\ufeffplc-greta-01"
        issues = validate_params(params, self.convention)
        self.assertTrue(any(item.code == "CLK121" for item in issues))

    def test_clean_ascii_values_are_not_flagged(self) -> None:
        issues = validate_params(self.base_params, self.convention)
        self.assertFalse(any(item.code == "CLK121" for item in issues))

    def test_regular_interior_space_is_not_clk121(self) -> None:
        params = dict(self.base_params)
        params["utm_campaign"] = "cmp spring launch"
        issues = validate_params(params, self.convention)
        self.assertFalse(any(item.code == "CLK121" for item in issues))

    def test_build_rejects_invisible_character(self) -> None:
        params = dict(self.base_params)
        params["utm_source"] = "you\u200btube"
        with self.assertRaisesRegex(ValueError, "CLK121"):
            build_url("https://shop.example.com/product", params, self.convention)

    def test_audit_surfaces_clk121(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=you%E2%80%8Btube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(item.code == "CLK121" for item in result.errors))


if __name__ == "__main__":
    unittest.main()
