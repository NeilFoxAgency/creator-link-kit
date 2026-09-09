"""CLK119: percent-encoded '&' must not glue later UTM pairs into one value."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class EncodedUtmSeparatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _clean(self) -> str:
        return (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_percent_encoded_ampersand_before_utm_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK119", codes)
        issue = next(i for i in issues if i.code == "CLK119")
        self.assertEqual(issue.severity, "error")
        self.assertIn("%26", issue.message)

    def test_uppercase_encoded_separator_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26UTM_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in issues))

    def test_glued_pair_in_decoded_value_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_campaign=cmp-spring-launch"
            "&utm_medium=influencer"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in issues))

    def test_normal_query_is_not_flagged(self) -> None:
        issues = validate_url(self._clean(), self.convention)
        self.assertFalse(any(i.code == "CLK119" for i in issues))

    def test_literal_ampersand_in_product_name_without_utm_key_is_clean(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?ref=salt%26pepper"
            "&utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK119" for i in issues))

    def test_audit_surfaces_clk119(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        result = audit_urls([self._clean(), dirty], self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
