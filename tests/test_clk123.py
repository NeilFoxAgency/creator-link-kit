"""CLK123: nested tracking detector for UTM values and wrappers."""

from __future__ import annotations

import unittest

from creator_link_kit.nested import find_nested_tracking


class NestedTrackingDetectorTests(unittest.TestCase):
    def test_utm_content_that_is_a_url(self) -> None:
        findings = find_nested_tracking(
            [
                ("utm_source", "youtube"),
                ("utm_content", "https://shop.example.com/product"),
            ]
        )
        self.assertEqual(len(findings), 1)
        parameter, message = findings[0]
        self.assertEqual(parameter, "utm_content")
        self.assertIn("embeds another URL", message)

    def test_utm_term_embedding_utm_pairs(self) -> None:
        findings = find_nested_tracking(
            [
                ("utm_term", "utm_source=newsletter"),
            ]
        )
        self.assertEqual(findings[0][0], "utm_term")

    def test_redirect_wrapping_tagged_url(self) -> None:
        findings = find_nested_tracking(
            [
                (
                    "redirect",
                    "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer",
                )
            ]
        )
        self.assertEqual(findings[0][0], "redirect")
        self.assertIn("wraps a destination", findings[0][1])

    def test_plain_next_url_without_utms_is_clean(self) -> None:
        findings = find_nested_tracking(
            [("next", "https://shop.example.com/thanks")]
        )
        self.assertEqual(findings, [])

    def test_ordinary_placement_id_is_clean(self) -> None:
        findings = find_nested_tracking(
            [
                ("utm_source", "youtube"),
                ("utm_medium", "influencer"),
                ("utm_campaign", "cmp-spring-launch"),
                ("utm_content", "plc-greta-01"),
            ]
        )
        self.assertEqual(findings, [])

    def test_duplicate_keys_report_once(self) -> None:
        findings = find_nested_tracking(
            [
                ("utm_content", "https://shop.example.com/a"),
                ("utm_content", "https://shop.example.com/b"),
            ]
        )
        self.assertEqual(len(findings), 1)


if __name__ == "__main__":
    unittest.main()
