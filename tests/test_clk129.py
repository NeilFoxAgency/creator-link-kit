"""CLK129: UTM parameters must not live in the URL path."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class PathUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_missing_question_mark_puts_utms_in_path(self) -> None:
        url = (
            "https://shop.example.com/offer/"
            "utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK129", codes)
        issue = next(i for i in issues if i.code == "CLK129")
        self.assertEqual(issue.severity, "error")
        self.assertIn("path", issue.message.lower())

    def test_glued_path_segment_is_flagged(self) -> None:
        url = "https://shop.example.com/offerutm_source=youtube"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK129" for i in issues))

    def test_uppercase_path_key_is_flagged(self) -> None:
        url = "https://shop.example.com/shop/UTM_CAMPAIGN=cmp-spring-launch"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK129" for i in issues))

    def test_clean_query_string_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK129" for i in issues))

    def test_utm_guide_path_without_equals_is_clean(self) -> None:
        url = (
            "https://shop.example.com/guides/what-is-utm-source"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK129" for i in issues))

    def test_audit_surfaces_clk129(self) -> None:
        dirty = "https://shop.example.com/offer/utm_source=youtube&utm_medium=influencer"
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK129" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
