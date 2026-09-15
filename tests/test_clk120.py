"""CLK120: invisible copy/paste characters in shipped campaign URLs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.invisible import find_invisible_format_labels
from creator_link_kit.links import audit_urls, validate_url


class InvisibleCharacterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _tagged(self, extra: str = "") -> str:
        return (
            "https://shop.example.com/product"
            f"{extra}"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_zwsp_inside_utm_source_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=you\u200btube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        codes = [issue.code for issue in issues]
        self.assertIn("CLK120", codes)
        issue = next(i for i in issues if i.code == "CLK120")
        self.assertEqual(issue.severity, "error")
        self.assertIn("zero-width space", issue.message.lower())

    def test_soft_hyphen_in_hostname_keeps_clk120_with_clk001(self) -> None:
        url = (
            "https://shop.exam\u00adple.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK120", codes)
        self.assertIn("CLK001", codes)
        self.assertTrue(any("soft hyphen" in i.message.lower() for i in issues))

    def test_nbsp_before_query_pair_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube\u00a0&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_bom_prefix_keeps_clk120_with_clk001(self) -> None:
        url = "\ufeff" + self._tagged()
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK120", codes)
        self.assertIn("CLK001", codes)
        self.assertTrue(any("byte order mark" in i.message.lower() for i in issues))

    def test_clean_ascii_url_is_not_flagged(self) -> None:
        issues = validate_url(self._tagged(), self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_ordinary_ascii_space_is_not_clk120(self) -> None:
        labels = find_invisible_format_labels(
            "https://shop.example.com/product?utm_source=you tube"
        )
        self.assertEqual(labels, ())

    def test_audit_urls_surfaces_clk120_as_error(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=you\u200btube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        clean = self._tagged()
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in result.errors))

    def test_joiners_are_detected_once_per_kind(self) -> None:
        text = "https://shop.example.com/a\u200c\u200c\u200db"
        labels = find_invisible_format_labels(text)
        self.assertEqual(
            labels,
            (
                "zero-width non-joiner (U+200C)",
                "zero-width joiner (U+200D)",
            ),
        )


if __name__ == "__main__":
    unittest.main()
