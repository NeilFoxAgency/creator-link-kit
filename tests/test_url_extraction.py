import tempfile
import unittest
from pathlib import Path

from creator_link_kit.cli import _read_audit_urls
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

    def test_extracts_from_description_prose(self):
        text = (
            "Shop here: https://shop.example.com/product?utm_source=youtube"
            "&utm_medium=influencer&utm_campaign=cmp-glow"
            "&utm_id=cmp-glow&utm_content=plc-greta-01).\n"
            "About: https://shop.example.com/about.\n"
        )
        urls = extract_http_urls(text)
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith("utm_content=plc-greta-01"))
        self.assertEqual(urls[1], "https://shop.example.com/about")

    def test_preserves_balanced_parentheses(self):
        self.assertEqual(
            extract_http_urls("See https://example.com/a_(b)."),
            ["https://example.com/a_(b)"],
        )

    def test_preserves_duplicates_and_ignores_other_schemes(self):
        text = (
            "https://shop.example.com/x\n"
            "again: https://shop.example.com/x\n"
            "ftp://files.example.com/a\n"
        )
        self.assertEqual(
            extract_http_urls(text),
            ["https://shop.example.com/x", "https://shop.example.com/x"],
        )

    def test_audit_text_reader_uses_prose_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "description.txt"
            path.write_text(
                "Sponsor: https://shop.example.com/product?utm_source=youtube).\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _read_audit_urls(path, None),
                ["https://shop.example.com/product?utm_source=youtube"],
            )


if __name__ == "__main__":
    unittest.main()
