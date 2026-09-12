"""CLK120: platform redirect wrappers hide the brand landing page."""

from __future__ import annotations

import unittest
from urllib.parse import quote

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


INNER = "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch&utm_content=plc-greta-01"


class RedirectWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_youtube_redirect_is_error(self) -> None:
        url = "https://www.youtube.com/redirect?event=video_description&q=" + quote(
            INNER, safe=""
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))
        issue = next(i for i in issues if i.code == "CLK120")
        self.assertEqual(issue.severity, "error")
        self.assertIn("youtube.com", issue.message.lower())
        self.assertIn("shop.example.com", issue.message)

    def test_facebook_lphp_is_error(self) -> None:
        url = "https://l.facebook.com/l.php?u=" + quote(INNER, safe="")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_instagram_wrapper_is_error(self) -> None:
        url = "https://l.instagram.com/?u=" + quote(INNER, safe="")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_google_url_wrapper_is_error(self) -> None:
        url = "https://www.google.com/url?q=" + quote(INNER, safe="")
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_href_li_query_destination_is_error(self) -> None:
        url = "https://href.li/?" + INNER
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in issues))

    def test_owned_landing_page_is_not_flagged(self) -> None:
        issues = validate_url(INNER, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_youtube_watch_page_is_not_a_wrapper(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_google_search_is_not_flagged(self) -> None:
        url = "https://www.google.com/search?q=https://shop.example.com/product"
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK120" for i in issues))

    def test_audit_surfaces_clk120(self) -> None:
        dirty = "https://www.youtube.com/redirect?q=" + quote(INNER, safe="")
        result = audit_urls([INNER, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK120" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
