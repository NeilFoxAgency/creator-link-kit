"""CLK119: percent-encoded UTM separators glue later pairs into one value."""

from __future__ import annotations

import unittest
from urllib.parse import parse_qsl, urlsplit

from creator_link_kit.encoded_utm import CLK119_MESSAGE, has_encoded_utm_separator


def _query_and_pairs(url: str) -> tuple[str, list[tuple[str, str]]]:
    parsed = urlsplit(url)
    return parsed.query, parse_qsl(parsed.query, keep_blank_values=True)


class EncodedUtmSeparatorTests(unittest.TestCase):
    def test_percent_encoded_ampersand_before_utm_is_detected(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        query, pairs = _query_and_pairs(url)
        self.assertTrue(has_encoded_utm_separator(query, pairs))
        self.assertIn("%26", CLK119_MESSAGE)

    def test_uppercase_encoded_separator_is_detected(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26UTM_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        query, pairs = _query_and_pairs(url)
        self.assertTrue(has_encoded_utm_separator(query, pairs))

    def test_normal_query_string_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        query, pairs = _query_and_pairs(url)
        self.assertFalse(has_encoded_utm_separator(query, pairs))

    def test_encoded_ampersand_in_non_utm_value_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?ref=a%26b"
            "&utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        query, pairs = _query_and_pairs(url)
        self.assertFalse(has_encoded_utm_separator(query, pairs))


if __name__ == "__main__":
    unittest.main()
