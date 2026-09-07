"""CLK126: UTM parameters must not live on video/platform hosts."""

from __future__ import annotations

import unittest

import creator_link_kit  # noqa: F401  — install CLK126 on links.validate_url
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url
from creator_link_kit.platform_utm import (
    is_platform_host,
    should_flag_platform_utm,
)


class PlatformUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _tagged(self, host_and_path: str) -> str:
        return (
            f"https://{host_and_path}"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )

    def test_youtu_be_with_utms_is_error(self) -> None:
        issues = validate_url(self._tagged("youtu.be/dQw4w9WgXcQ"), self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK126", codes)
        issue = next(i for i in issues if i.code == "CLK126")
        self.assertEqual(issue.severity, "error")
        self.assertIn("youtu.be", issue.message)

    def test_youtube_watch_url_is_flagged(self) -> None:
        issues = validate_url(
            self._tagged("www.youtube.com/watch"),
            self.convention,
        )
        self.assertTrue(any(i.code == "CLK126" for i in issues))

    def test_tiktok_instagram_x_are_flagged(self) -> None:
        for host in (
            "www.tiktok.com/@brand/video/1",
            "instagram.com/p/abc",
            "x.com/brand/status/1",
        ):
            with self.subTest(host=host):
                issues = validate_url(self._tagged(host), self.convention)
                self.assertTrue(any(i.code == "CLK126" for i in issues), host)

    def test_owned_shop_with_utms_is_not_clk126(self) -> None:
        url = self._tagged("shop.example.com/product")
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK126" for i in issues))

    def test_platform_without_utms_is_not_clk126(self) -> None:
        issues = validate_url("https://youtu.be/dQw4w9WgXcQ", self.convention)
        self.assertFalse(any(i.code == "CLK126" for i in issues))

    def test_first_party_platform_in_owned_domains_is_allowed(self) -> None:
        raw = starter_convention()
        raw["owned_domains"] = ["example.com", "youtu.be"]
        raw["mode"] = "development"
        convention = convention_from_dict(raw)
        issues = validate_url(self._tagged("youtu.be/abc123"), convention)
        self.assertFalse(any(i.code == "CLK126" for i in issues))

    def test_helper_does_not_match_lookalike(self) -> None:
        self.assertFalse(is_platform_host("notyoutube.com.example"))
        self.assertFalse(is_platform_host("youtu.be.evil.example"))
        self.assertTrue(is_platform_host("youtu.be"))
        self.assertTrue(is_platform_host("m.youtube.com"))
        self.assertFalse(
            should_flag_platform_utm("https://shop.example.com/?utm_source=youtube")
        )
        self.assertFalse(is_platform_host("bit.ly"))

    def test_audit_surfaces_clk126(self) -> None:
        clean = self._tagged("shop.example.com/product")
        dirty = self._tagged("youtu.be/abc")
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK126" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
