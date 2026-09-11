"""CLK119: percent-encoded UTM separators must not glue later pairs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class EncodedUtmSeparatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

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

    def test_glued_pair_inside_decoded_value_is_error(self) -> None:
        # A later pair can also be pasted into a value after a raw '?' or '&'.
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube?utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in issues))

    def test_normal_query_string_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK119" for i in issues))

    def test_encoded_ampersand_in_unrelated_value_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
            "&ref=a%26b"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK119" for i in issues))

    def test_audit_surfaces_clk119(self) -> None:
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
