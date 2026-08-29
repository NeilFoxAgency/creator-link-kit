"""CLK123: UTM values and wrappers must not embed another tracked URL."""

from __future__ import annotations

import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_url


def _clean_params() -> dict[str, str]:
    return {
        "utm_source": "youtube",
        "utm_medium": "influencer",
        "utm_campaign": "cmp-spring-launch",
        "utm_id": "cmp-spring-launch",
        "utm_content": "plc-greta-01",
    }


class NestedTrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _url(self, extra: str = "") -> str:
        base = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
        )
        return base + extra

    def test_utm_content_that_is_a_url_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=https://shop.example.com/product"
        )
        issues = validate_url(url, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK123", codes)
        issue = next(i for i in issues if i.code == "CLK123")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "utm_content")

    def test_utm_term_embedding_utm_pairs_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=plc-greta-01"
            "&utm_term=utm_source=newsletter"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK123" and i.parameter == "utm_term" for i in issues))

    def test_redirect_param_wrapping_tagged_url_is_error(self) -> None:
        url = (
            "https://shop.example.com/go"
            "?redirect=https://shop.example.com/product"
            "%3Futm_source%3Dyoutube%26utm_medium%3Dinfluencer"
            "%26utm_campaign%3Dcmp-spring-launch"
        )
        issues = validate_url(url, self.convention)
        self.assertTrue(any(i.code == "CLK123" and i.parameter == "redirect" for i in issues))

    def test_plain_next_url_without_utms_is_not_flagged(self) -> None:
        url = self._url("&next=https://shop.example.com/thanks")
        issues = validate_url(url, self.convention)
        self.assertFalse(any(i.code == "CLK123" for i in issues))

    def test_ordinary_placement_id_is_not_flagged(self) -> None:
        issues = validate_url(self._url(), self.convention)
        self.assertFalse(any(i.code == "CLK123" for i in issues))

    def test_build_url_rejects_nested_utm_content(self) -> None:
        # Starter conventions reject this URL as CLK106 first. A convention that
        # allows long values still must refuse nested tracking on the final URL.
        data = starter_convention()
        data["parameters"]["utm_content"] = {}
        data["max_value_length"] = 200
        convention = convention_from_dict(data)
        params = _clean_params()
        params["utm_content"] = "https://shop.example.com/product?utm_source=youtube"
        with self.assertRaises(ValueError) as ctx:
            build_url("https://shop.example.com/product", params, convention)
        self.assertIn("CLK123", str(ctx.exception))

    def test_audit_surfaces_clk123(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch&utm_id=cmp-spring-launch"
            "&utm_content=https://othershop.example.net/deal"
        )
        clean = self._url()
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK123" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
