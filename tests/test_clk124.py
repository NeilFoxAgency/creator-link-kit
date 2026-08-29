"""CLK124: UTM tags on creator-platform hosts instead of the brand landing page."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url
from creator_link_kit.platform_utm import is_creator_platform_host, should_flag_platform_utm


class PlatformUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_tagged_youtube_watch_url_is_error(self) -> None:
        url = (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            "&utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-glowdrop-launch"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK124", codes)
        issue = next(i for i in issues if i.code == "CLK124")
        self.assertEqual(issue.severity, "error")
        self.assertIn("youtube.com", issue.message.lower())

    def test_tagged_youtu_be_short_url_is_error(self) -> None:
        url = "https://youtu.be/dQw4w9WgXcQ?utm_source=youtube&utm_campaign=cmp-x"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK124" for i in issues))

    def test_tagged_tiktok_url_is_error(self) -> None:
        url = "https://www.tiktok.com/@demo/video/1?utm_source=tiktok&utm_medium=influencer"
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK124" for i in issues))

    def test_untagged_youtube_url_is_not_clk124(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK124" for i in issues))

    def test_owned_shop_url_is_not_clk124(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-glowdrop-launch&utm_id=cmp-glowdrop-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK124" for i in issues))

    def test_owned_platform_domain_is_allowed(self) -> None:
        data = starter_convention()
        data["owned_domains"] = ["example.com", "youtube.com"]
        convention = convention_from_dict(data)
        self.assertFalse(
            should_flag_platform_utm(
                "www.youtube.com",
                "utm_source=youtube",
                convention,
            )
        )

    def test_helper_recognizes_mobile_subdomain(self) -> None:
        self.assertTrue(is_creator_platform_host("m.youtube.com"))
        self.assertTrue(is_creator_platform_host("vm.tiktok.com"))
        self.assertFalse(is_creator_platform_host("shop.example.com"))
        self.assertFalse(is_creator_platform_host("notyoutube.com"))

    def test_audit_surfaces_clk124(self) -> None:
        dirty = "https://www.instagram.com/p/abc/?utm_source=instagram&utm_medium=influencer"
        clean = (
            "https://shop.example.com/product"
            "?utm_source=instagram&utm_medium=influencer"
            "&utm_campaign=cmp-glowdrop-launch&utm_id=cmp-glowdrop-launch"
            "&utm_content=plc-priya-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK124" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
