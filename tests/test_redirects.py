"""Unit tests for offline platform redirect-wrapper detection."""

from __future__ import annotations

import unittest
from urllib.parse import quote, urlsplit

from creator_link_kit.redirects import redirect_wrapper_message


INNER = (
    "https://shop.example.com/product?utm_source=youtube"
    "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
)


class RedirectMessageTests(unittest.TestCase):
    def test_youtube_redirect(self) -> None:
        url = "https://www.youtube.com/redirect?q=" + quote(INNER, safe="")
        msg = redirect_wrapper_message(urlsplit(url), url)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("youtube.com", msg)
        self.assertIn("shop.example.com", msg)

    def test_facebook_lphp(self) -> None:
        url = "https://l.facebook.com/l.php?u=" + quote(INNER, safe="")
        self.assertIsNotNone(redirect_wrapper_message(urlsplit(url), url))

    def test_instagram(self) -> None:
        url = "https://l.instagram.com/?u=" + quote(INNER, safe="")
        self.assertIsNotNone(redirect_wrapper_message(urlsplit(url), url))

    def test_google_url(self) -> None:
        url = "https://www.google.com/url?q=" + quote(INNER, safe="")
        self.assertIsNotNone(redirect_wrapper_message(urlsplit(url), url))

    def test_href_li(self) -> None:
        url = "https://href.li/?" + INNER
        self.assertIsNotNone(redirect_wrapper_message(urlsplit(url), url))

    def test_plain_owned_url(self) -> None:
        self.assertIsNone(redirect_wrapper_message(urlsplit(INNER), INNER))

    def test_youtube_watch_is_not_wrapper(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertIsNone(redirect_wrapper_message(urlsplit(url), url))

    def test_google_search_is_not_wrapper(self) -> None:
        url = "https://www.google.com/search?q=https://shop.example.com/product"
        self.assertIsNone(redirect_wrapper_message(urlsplit(url), url))


if __name__ == "__main__":
    unittest.main()
