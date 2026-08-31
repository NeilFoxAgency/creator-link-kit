"""CLK129: paid-ad click identifiers must not ship on creator links."""

from __future__ import annotations

import unittest

from creator_link_kit.click_ids import paid_click_id_keys
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_url


def _tracked(extra: str = "") -> str:
    query = (
        "utm_source=youtube&utm_medium=influencer"
        "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
        "&utm_content=plc-greta-01"
    )
    if extra:
        query = f"{query}&{extra}"
    return f"https://shop.example.com/product?{query}"


class PaidClickIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_helper_finds_known_keys_case_insensitively(self) -> None:
        found = paid_click_id_keys(
            [("utm_source", "youtube"), ("GCLID", "abc"), ("fbclid", "xyz")]
        )
        self.assertEqual(found, ("GCLID", "fbclid"))

    def test_helper_ignores_unrelated_keys(self) -> None:
        found = paid_click_id_keys(
            [("ref", "homepage"), ("discount", "VIDEO15"), ("utm_term", "gclid")]
        )
        self.assertEqual(found, ())

    def test_gclid_on_tracked_url_is_error(self) -> None:
        issues = validate_url(_tracked("gclid=EAIaIQobChMI"), self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK129", codes)
        issue = next(i for i in issues if i.code == "CLK129")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "gclid")
        self.assertIn("paid-ad", issue.message.lower())

    def test_fbclid_and_ttclid_are_flagged(self) -> None:
        url = _tracked("fbclid=IwAR0&ttclid=E.C.P")
        issues = validate_url(url, self.convention)
        issue = next(i for i in issues if i.code == "CLK129")
        self.assertIn("fbclid", issue.message)
        self.assertIn("ttclid", issue.message)

    def test_uppercase_msclkid_is_flagged(self) -> None:
        issues = validate_url(_tracked("MSCLKID=abc123"), self.convention)
        self.assertTrue(any(i.code == "CLK129" for i in issues))

    def test_clean_creator_url_is_not_flagged(self) -> None:
        issues = validate_url(_tracked(), self.convention)
        self.assertFalse(any(i.code == "CLK129" for i in issues))

    def test_value_that_mentions_gclid_is_not_a_click_id(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=notes-about-gclid"
        )
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK129" for i in issues))

    def test_build_refuses_base_url_that_already_has_gclid(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_url(
                "https://shop.example.com/product?gclid=EAIaIQobChMI",
                {
                    "utm_source": "youtube",
                    "utm_campaign": "cmp-spring-launch",
                    "utm_id": "cmp-spring-launch",
                    "utm_content": "plc-greta-01",
                },
                self.convention,
            )
        self.assertIn("CLK129", str(ctx.exception))

    def test_audit_surfaces_clk129(self) -> None:
        result = audit_urls(
            [_tracked(), _tracked("wbraid=CkA")],
            self.convention,
        )
        self.assertTrue(any(i.code == "CLK129" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
