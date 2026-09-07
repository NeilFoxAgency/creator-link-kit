"""CLK121: invisible and format-control characters in campaign URLs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.query_invisible import (
    describe_character,
    find_invisible_characters,
    install,
)

install()

from creator_link_kit import links  # noqa: E402


class QueryInvisibleTests(unittest.TestCase):
    def test_clean_url_has_no_hits(self) -> None:
        self.assertEqual(
            find_invisible_characters(
                "https://shop.example.com/offer?utm_source=youtube&utm_medium=influencer"
            ),
            [],
        )

    def test_zero_width_space(self) -> None:
        found = find_invisible_characters(
            "https://shop.example.com/offer?utm_source=you\u200btube"
        )
        self.assertEqual(found, ["\u200b"])

    def test_nbsp_and_bom(self) -> None:
        found = find_invisible_characters(
            "\ufeffhttps://shop.example.com/offer?utm_source=youtube\u00a0"
        )
        self.assertEqual(found, ["\ufeff", "\u00a0"])

    def test_newline_from_email_wrap(self) -> None:
        found = find_invisible_characters(
            "https://shop.example.com/offer?utm_source=youtube\n&utm_medium=influencer"
        )
        self.assertEqual(found, ["\n"])

    def test_describe_character(self) -> None:
        self.assertIn("ZERO WIDTH SPACE", describe_character("\u200b"))


class Clk121ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_zwsp_in_utm_source_is_error(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=you\u200btube"
            "&utm_medium=influencer&utm_campaign=spring&utm_content=pl_001"
        )
        codes = [i.code for i in links.validate_url(url, self.convention)]
        self.assertIn("CLK121", codes)

    def test_clean_tracked_url_has_no_clk121(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=youtube"
            "&utm_medium=influencer&utm_campaign=spring&utm_content=pl_001"
        )
        codes = [i.code for i in links.validate_url(url, self.convention)]
        self.assertNotIn("CLK121", codes)

    def test_soft_hyphen_is_error(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=you\u00adtube"
            "&utm_medium=influencer&utm_campaign=spring&utm_content=pl_001"
        )
        issue = next(
            i for i in links.validate_url(url, self.convention) if i.code == "CLK121"
        )
        self.assertEqual(issue.severity, "error")
        self.assertIn("U+00AD", issue.message)

    def test_audit_urls_surfaces_clk121(self) -> None:
        url = (
            "https://shop.example.com/offer?utm_source=youtube\u200b"
            "&utm_medium=influencer&utm_campaign=spring&utm_content=pl_001"
        )
        result = links.audit_urls([url], self.convention)
        codes = [i.code for i in result.issues]
        self.assertIn("CLK121", codes)


if __name__ == "__main__":
    unittest.main()
