"""CLK120: invisible/format characters must not hide inside shipped URLs."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


def _clean() -> str:
    return (
        "https://shop.example.com/product"
        "?utm_source=youtube&utm_medium=influencer"
        "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
        "&utm_content=plc-greta-01"
    )


class InvisibleUrlCharacterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_zero_width_space_in_utm_value_is_error(self) -> None:
        url = _clean().replace("youtube", "you\u200btube")
        issues = validate_url(url, self.convention)
        issue = next(i for i in issues if i.code == "CLK120")
        self.assertEqual(issue.severity, "error")
        self.assertIn("zero-width space", issue.message)

    def test_soft_hyphen_in_host_is_error(self) -> None:
        url = _clean().replace("shop.example.com", "shop.exam\u00adple.com")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_nbsp_between_query_pairs_is_error(self) -> None:
        url = _clean().replace("&utm_medium", "\u00a0&utm_medium")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_bom_prefix_is_error(self) -> None:
        issues = validate_url("\ufeff" + _clean(), self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_clk120_survives_clk001_on_soft_hyphen_host(self) -> None:
        url = _clean().replace("shop.example.com", "shop.exam\u00adple.com")
        issues = validate_url(url, self.convention)
        codes = {i.code for i in issues}
        self.assertIn("CLK120", codes)

    def test_ordinary_ascii_space_is_not_clk120(self) -> None:
        url = _clean().replace("youtube", "you tube")
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_clean_ascii_url_is_not_flagged(self) -> None:
        issues = validate_url(_clean(), self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_audit_surfaces_clk120(self) -> None:
        dirty = _clean().replace("influencer", "influ\u200cencer")
        result = audit_urls([_clean(), dirty], self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
