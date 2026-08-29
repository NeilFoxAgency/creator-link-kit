"""CLK125: UTM parameters must not live on public shortener hosts."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url
from creator_link_kit.shortener_utm import (
    is_shortener_host,
    should_flag_shortener_utm,
)


class ShortenerUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _tagged(self, host_and_path: str) -> str:
        return (
            f"https://{host_and_path}"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_bitly_with_utms_is_error(self) -> None:
        issues = validate_url(self._tagged("bit.ly/abc123"), self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK125", codes)
        issue = next(i for i in issues if i.code == "CLK125")
        self.assertEqual(issue.severity, "error")
        self.assertIn("bit.ly", issue.message)

    def test_tco_and_amzn_to_are_flagged(self) -> None:
        for host in ("t.co/xyz", "amzn.to/3abc", "lnkd.in/abc"):
            with self.subTest(host=host):
                issues = validate_url(self._tagged(host), self.convention)
                self.assertTrue(any(i.code == "CLK125" for i in issues), host)

    def test_shortener_subdomain_is_flagged(self) -> None:
        issues = validate_url(self._tagged("custom.bit.ly/abc"), self.convention)
        self.assertTrue(any(i.code == "CLK125" for i in issues))

    def test_owned_shop_with_utms_is_not_clk125(self) -> None:
        url = self._tagged("shop.example.com/product")
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK125" for i in issues))

    def test_shortener_without_utms_is_not_clk125(self) -> None:
        issues = validate_url("https://bit.ly/abc123", self.convention)
        self.assertFalse(any(i.code == "CLK125" for i in issues))

    def test_first_party_shortener_in_owned_domains_is_allowed(self) -> None:
        raw = starter_convention()
        raw["owned_domains"] = ["example.com", "bit.ly"]
        raw["mode"] = "development"
        convention = convention_from_dict(raw)
        issues = validate_url(self._tagged("bit.ly/abc123"), convention)
        self.assertFalse(any(i.code == "CLK125" for i in issues))

    def test_helper_does_not_match_bitly_lookalike(self) -> None:
        self.assertFalse(is_shortener_host("notbit.ly.example.com"))
        self.assertFalse(is_shortener_host("bit.ly.evil.example"))
        self.assertTrue(is_shortener_host("bit.ly"))
        self.assertFalse(
            should_flag_shortener_utm("https://shop.example.com/?utm_source=youtube")
        )

    def test_audit_surfaces_clk125(self) -> None:
        clean = self._tagged("shop.example.com/product")
        dirty = self._tagged("buff.ly/xyz")
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK125" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
