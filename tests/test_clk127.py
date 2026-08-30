"""CLK127: UTM pairs must be separated by '&', not ';' or ','."""

from __future__ import annotations

import unittest

import creator_link_kit
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls
from creator_link_kit.query_delim import has_alt_utm_delimiter, validate_url


class AltQueryDelimiterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _clean(self) -> str:
        return (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_helper_detects_semicolon(self) -> None:
        self.assertTrue(
            has_alt_utm_delimiter(
                "https://shop.example.com/p?utm_source=youtube;utm_medium=influencer"
            )
        )

    def test_semicolon_separated_pairs_are_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube;utm_medium=influencer"
            ";utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in issues))
        issue = next(i for i in issues if i.code == "CLK127")
        self.assertEqual(issue.severity, "error")
        self.assertIn("&", issue.message)

    def test_comma_separated_pairs_are_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube,utm_medium=influencer"
            ",utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in issues))

    def test_mixed_ampersand_then_semicolon_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer;utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in issues))

    def test_comma_inside_content_value_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=video,short-form"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK127" for i in issues))
        self.assertFalse(has_alt_utm_delimiter(url))

    def test_ampersand_query_is_clean(self) -> None:
        issues = validate_url(self._clean(), self.convention)
        self.assertFalse(any(i.code == "CLK127" for i in issues))

    def test_uppercase_key_after_semicolon_is_flagged(self) -> None:
        url = "https://shop.example.com/offer?utm_source=youtube;UTM_MEDIUM=influencer"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in issues))

    def test_package_validate_url_is_wrapped(self) -> None:
        url = "https://shop.example.com/offer?utm_source=youtube;utm_medium=influencer"
        issues = creator_link_kit.validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in issues))

    def test_audit_surfaces_clk127(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube;utm_medium=influencer"
            ";utm_campaign=cmp-spring-launch"
        )
        result = audit_urls([self._clean(), dirty], self.convention)
        self.assertTrue(any(i.code == "CLK127" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
