"""CLK119: extra '?' before the fragment silently swallows UTM pairs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import load_convention
from creator_link_kit.links import audit_urls, validate_url
from creator_link_kit.spec import starter_convention_text


def _codes(url: str) -> set[str]:
    convention = load_convention(starter_convention_text())
    return {issue.code for issue in validate_url(url, convention)}


class ExtraQuestionMarkTests(unittest.TestCase):
    def test_concatenated_utm_suffix_is_clk119(self) -> None:
        url = (
            "https://shop.example.com/offer?ref=homepage"
            "?utm_source=youtube&utm_medium=paid_social"
            "&utm_campaign=spring-launch"
        )
        self.assertIn("CLK119", _codes(url))

    def test_second_question_mark_before_fragment_is_clk119(self) -> None:
        url = "https://shop.example.com/?utm_source=youtube?utm_medium=paid_social"
        self.assertIn("CLK119", _codes(url))

    def test_single_query_string_is_not_clk119(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=youtube"
            "&utm_medium=paid_social&utm_campaign=spring-launch"
            "&utm_content=plc-greta-video-01&utm_id=cmp-spring-launch"
        )
        self.assertNotIn("CLK119", _codes(url))

    def test_question_mark_only_in_fragment_is_not_clk119(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=youtube"
            "&utm_medium=paid_social&utm_campaign=spring-launch"
            "&utm_content=plc-greta-video-01&utm_id=cmp-spring-launch"
            "#section?tab=reviews"
        )
        codes = _codes(url)
        self.assertNotIn("CLK119", codes)
        self.assertNotIn("CLK118", codes)

    def test_audit_urls_surfaces_clk119_as_error(self) -> None:
        convention = load_convention(starter_convention_text())
        report = audit_urls(
            [
                "https://shop.example.com/offer?ref=home?utm_source=youtube"
                "&utm_medium=paid_social"
            ],
            convention,
        )
        codes = {issue.code for issue in report.issues}
        self.assertIn("CLK119", codes)
        self.assertGreaterEqual(report.error_count, 1)


if __name__ == "__main__":
    unittest.main()
