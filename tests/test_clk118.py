"""CLK118: UTM parameters must not live only in the URL fragment."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class FragmentUtmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_utms_only_in_fragment_are_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "#utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK118", codes)
        issue = next(i for i in issues if i.code == "CLK118")
        self.assertEqual(issue.severity, "error")
        self.assertIn("fragment", issue.message.lower())

    def test_query_before_fragment_with_extra_utm_in_hash(self) -> None:
        # Query is valid; hash still contains a stray UTM and must be flagged.
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
            "#utm_term=fitness"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK118" for i in issues))

    def test_innocent_spa_hash_is_not_flagged(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
            "#section-reviews"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK118" for i in issues))

    def test_empty_fragment_is_clean(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK118" for i in issues))

    def test_audit_surfaces_clk118(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "#utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
        )
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK118" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
