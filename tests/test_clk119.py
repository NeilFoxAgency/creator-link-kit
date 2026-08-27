"""CLK119: extra '?' before the fragment silently swallows UTM pairs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url
from creator_link_kit.query_shape import has_extra_question_mark


class ExtraQuestionMarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_helper_detects_second_question_mark(self) -> None:
        self.assertTrue(
            has_extra_question_mark(
                "https://shop.example.com/offer?ref=homepage?utm_source=youtube"
            )
        )
        self.assertFalse(
            has_extra_question_mark(
                "https://shop.example.com/offer?utm_source=youtube#section?tab=1"
            )
        )

    def test_concatenated_utm_suffix_is_clk119(self) -> None:
        url = (
            "https://shop.example.com/product?ref=homepage"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        codes = {issue.code for issue in validate_url(url, self.convention)}
        self.assertIn("CLK119", codes)

    def test_second_question_mark_before_fragment_is_clk119(self) -> None:
        url = "https://shop.example.com/?utm_source=youtube?utm_medium=influencer"
        codes = {issue.code for issue in validate_url(url, self.convention)}
        self.assertIn("CLK119", codes)

    def test_single_query_string_is_not_clk119(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        codes = {issue.code for issue in validate_url(url, self.convention)}
        self.assertNotIn("CLK119", codes)

    def test_question_mark_only_in_fragment_is_not_clk119(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
            "#section?tab=reviews"
        )
        codes = {issue.code for issue in validate_url(url, self.convention)}
        self.assertNotIn("CLK119", codes)
        self.assertNotIn("CLK118", codes)

    def test_audit_urls_surfaces_clk119_as_error(self) -> None:
        dirty = (
            "https://shop.example.com/product?ref=home"
            "?utm_source=youtube&utm_medium=influencer"
        )
        result = audit_urls([dirty], self.convention)
        self.assertTrue(any(issue.code == "CLK119" for issue in result.errors))


if __name__ == "__main__":
    unittest.main()
