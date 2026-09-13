"""Unit tests for the CLK119 encoded-separator helper."""

from __future__ import annotations

import unittest
from urllib.parse import parse_qsl, urlsplit

from creator_link_kit.encoded_utm import has_encoded_utm_separator


def _pairs(url: str):
    parsed = urlsplit(url)
    return parsed.query, parse_qsl(parsed.query, keep_blank_values=True)


class EncodedUtmHelperTests(unittest.TestCase):
    def test_raw_percent_encoded_separator(self) -> None:
        url = "https://shop.example.com/product?utm_source=youtube%26utm_medium=influencer"
        query, pairs = _pairs(url)
        self.assertTrue(has_encoded_utm_separator(query, pairs))

    def test_uppercase_percent_encoding(self) -> None:
        url = "https://shop.example.com/product?utm_source=youtube%26UTM_campaign=spring"
        query, pairs = _pairs(url)
        self.assertTrue(has_encoded_utm_separator(query, pairs))

    def test_normal_ampersand_query_is_clean(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer&utm_campaign=cmp-spring"
        )
        query, pairs = _pairs(url)
        self.assertFalse(has_encoded_utm_separator(query, pairs))

    def test_non_utm_encoded_ampersand_is_clean(self) -> None:
        url = (
            "https://shop.example.com/product?ref=a%26b"
            "&utm_source=youtube&utm_medium=influencer"
        )
        query, pairs = _pairs(url)
        self.assertFalse(has_encoded_utm_separator(query, pairs))


if __name__ == "__main__":
    unittest.main()
