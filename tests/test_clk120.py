"""CLK120: percent-encoded query delimiters must not hide UTM keys."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class EncodedDelimiterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_encoded_ampersand_before_utm_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "%26utm_campaign=cmp-spring-launch%26utm_id=cmp-spring-launch"
            "%26utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK120", codes)
        issue = next(i for i in issues if i.code == "CLK120")
        self.assertEqual(issue.severity, "error")
        self.assertIn("%26", issue.message)

    def test_encoded_question_mark_before_utm_is_error(self) -> None:
        url = (
            "https://shop.example.com/product%3Futm_source=youtube"
            "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_uppercase_hex_encoding_is_caught(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26UTM_medium=influencer"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_literal_ampersand_in_value_is_not_clk120(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_encoded_ampersand_in_non_utm_value_is_not_clk120(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?bundle=pro%26lite"
            "&utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_audit_surfaces_clk120(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
