import unittest

from creator_link_kit.urls import extract_http_urls


class ExtractHttpUrlsTests(unittest.TestCase):
    def test_bare_url_lines(self):
        text = (
            "https://shop.example.com/a?utm_source=youtube\n"
            "\n"
            "https://shop.example.com/b\n"
        )
        self.assertEqual(
            extract_http_urls(text),
            [
                "https://shop.example.com/a?utm_source=youtube",
                "https://shop.example.com/b",
            ],
        )

    def test_extracts_from_youtube_style_description(self):
        text = (
            "Thanks for watching!\n"
            "Shop the bundle here: https://shop.example.com/product?"
            "utm_source=youtube&utm_medium=influencer&utm_campaign=cmp-glow"
            "&utm_id=cmp-glow&utm_content=plc-greta-01).\n"
            "Also see https://shop.example.com/about for details.\n"
            "No link on this line.\n"
        )
        urls = extract_http_urls(text)
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].startswith("https://shop.example.com/product?"))
        self.assertNotIn(")", urls[0])
        self.assertEqual(urls[1], "https://shop.example.com/about")

    def test_preserves_duplicate_urls_for_audit(self):
        text = "https://shop.example.com/x\nagain: https://shop.example.com/x\n"
        self.assertEqual(
            extract_http_urls(text),
            ["https://shop.example.com/x", "https://shop.example.com/x"],
        )

    def test_ignores_non_http_schemes(self):
        text = "ftp://files.example.com/a and mailto:hi@example.com"
        self.assertEqual(extract_http_urls(text), [])


if __name__ == "__main__":
    unittest.main()
