"""CLK132 and CLK133: raw URL whitespace and doubled schemes."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.raw_hygiene import audit_urls, validate_url


class RawUrlHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _clean(self) -> str:
        return (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_space_inside_query_is_clk132(self) -> None:
        url = self._clean().replace("youtube", "you tube")
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK132", codes)
        issue = next(i for i in issues if i.code == "CLK132")
        self.assertEqual(issue.severity, "error")
        self.assertIn("whitespace", issue.message.lower())

    def test_newline_wrap_is_clk132(self) -> None:
        url = "https://shop.example.com/product\n?utm_source=youtube"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK132" for i in issues))

    def test_nbsp_is_clk132(self) -> None:
        url = self._clean().replace("product", "product\u00a0page")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK132" for i in issues))

    def test_clean_url_is_not_clk132(self) -> None:
        issues = validate_url(self._clean(), self.convention)
        self.assertFalse(any(i.code == "CLK132" for i in issues))
        self.assertFalse(any(i.code == "CLK133" for i in issues))

    def test_doubled_https_scheme_is_clk133(self) -> None:
        url = "https://https://shop.example.com/product?utm_source=youtube"
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK133", codes)
        issue = next(i for i in issues if i.code == "CLK133")
        self.assertEqual(issue.severity, "error")
        self.assertIn("doubled", issue.message.lower())

    def test_http_then_https_is_clk133(self) -> None:
        url = "http://https://shop.example.com/product"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK133" for i in issues))

    def test_audit_surfaces_both_codes(self) -> None:
        dirty_space = self._clean().replace("youtube", "you tube")
        dirty_scheme = "https://https://shop.example.com/product"
        result = audit_urls([self._clean(), dirty_space, dirty_scheme], self.convention)
        codes = {i.code for i in result.errors}
        self.assertIn("CLK132", codes)
        self.assertIn("CLK133", codes)

    def test_package_export_uses_wrapped_validator(self) -> None:
        from creator_link_kit import validate_url as exported

        url = "https://https://shop.example.com/product"
        self.assertTrue(any(i.code == "CLK133" for i in exported(url, self.convention)))


if __name__ == "__main__":
    unittest.main()
