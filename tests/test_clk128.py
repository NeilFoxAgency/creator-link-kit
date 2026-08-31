"""CLK128: UTM pairs must be separated by a real query delimiter."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.query_glued import has_glued_utm_pair, install

install()

from creator_link_kit.links import audit_urls, validate_url


class GluedUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_helper_detects_glued_keys(self) -> None:
        self.assertTrue(
            has_glued_utm_pair(
                "https://shop.example.com/offer?utm_source=youtubeutm_medium=influencer"
            )
        )

    def test_helper_detects_space_separator(self) -> None:
        self.assertTrue(
            has_glued_utm_pair(
                "https://shop.example.com/offer?utm_source=youtube utm_medium=influencer"
            )
        )

    def test_helper_allows_clean_ampersand_query(self) -> None:
        self.assertFalse(
            has_glued_utm_pair(
                "https://shop.example.com/offer"
                "?utm_source=youtube&utm_medium=influencer"
                "&utm_campaign=cmp-spring"
            )
        )

    def test_helper_allows_comma_inside_content_value(self) -> None:
        self.assertFalse(
            has_glued_utm_pair(
                "https://shop.example.com/offer"
                "?utm_source=youtube&utm_content=video,short-form"
            )
        )

    def test_glued_medium_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtubeutm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK128", codes)
        issue = next(i for i in issues if i.code == "CLK128")
        self.assertEqual(issue.severity, "error")
        self.assertIn("delimiter", issue.message.lower())

    def test_uppercase_glued_keys(self) -> None:
        url = "https://shop.example.com/product?UTM_SOURCE=youtubeUTM_CAMPAIGN=cmp-spring"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK128" for i in issues))

    def test_space_separated_pairs_are_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK128" for i in issues))

    def test_clean_query_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK128" for i in issues))

    def test_audit_surfaces_clk128(self) -> None:
        dirty = "https://shop.example.com/product?utm_source=youtubeutm_campaign=cmp-spring"
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK128" for i in result.errors))

    def test_package_export_is_wrapped(self) -> None:
        from creator_link_kit import validate_url as exported

        url = "https://shop.example.com/product?utm_source=youtubeutm_medium=influencer"
        issues = exported(url, self.convention)
        self.assertTrue(any(i.code == "CLK128" for i in issues))


if __name__ == "__main__":
    unittest.main()
