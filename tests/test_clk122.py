"""CLK122: mixed-script and confusable characters in UTM keys/values."""

from __future__ import annotations

import unittest

from creator_link_kit.confusables import mixed_script_label
from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_params, validate_url


class ConfusableHelperTests(unittest.TestCase):
    def test_ascii_is_clean(self) -> None:
        self.assertIsNone(mixed_script_label("cmp-glowdrop-launch"))

    def test_cyrillic_a_in_latin_word(self) -> None:
        # U+0430 CYRILLIC SMALL LETTER A
        dirty = "cmp-l\u0430unch"
        label = mixed_script_label(dirty)
        self.assertIsNotNone(label)
        assert label is not None
        self.assertIn("Cyrillic", label)

    def test_fullwidth_latin(self) -> None:
        dirty = "youtube\uff41"
        label = mixed_script_label(dirty)
        self.assertIsNotNone(label)
        assert label is not None
        self.assertIn("NFKC", label)

    def test_soft_hyphen(self) -> None:
        dirty = "cmp-glow\u00addrop"
        label = mixed_script_label(dirty)
        self.assertIsNotNone(label)
        assert label is not None
        self.assertIn("SOFT HYPHEN", label)

    def test_pure_cyrillic_is_allowed(self) -> None:
        # Intentional localized campaign name, no Latin mix.
        self.assertIsNone(mixed_script_label("\u043a\u0430\u043c\u043f\u0430\u043d\u0438\u044f"))


class Clk122ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def _valid_params(self, **overrides: str) -> dict[str, str]:
        params = {
            "utm_source": "youtube",
            "utm_medium": "influencer",
            "utm_campaign": "cmp-glowdrop-launch",
            "utm_id": "cmp-glowdrop-launch",
            "utm_content": "plc-greta-video-01",
        }
        params.update(overrides)
        return params

    def test_cyrillic_letter_in_campaign_is_error(self) -> None:
        params = self._valid_params(utm_campaign="cmp-l\u0430unch")
        issues = validate_params(params, self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK122", codes)
        issue = next(i for i in issues if i.code == "CLK122")
        self.assertEqual(issue.severity, "error")
        self.assertEqual(issue.parameter, "utm_campaign")
        self.assertIn("Cyrillic", issue.message)

    def test_soft_hyphen_in_content_is_error(self) -> None:
        params = self._valid_params(utm_content="plc-greta\u00advideo-01")
        issues = validate_params(params, self.convention)
        self.assertTrue(any(i.code == "CLK122" for i in issues))

    def test_clean_params_have_no_clk122(self) -> None:
        issues = validate_params(self._valid_params(), self.convention)
        self.assertFalse(any(i.code == "CLK122" for i in issues))

    def test_build_rejects_mixed_script(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_url(
                "https://shop.example.com/product",
                self._valid_params(utm_campaign="cmp-l\u0430unch"),
                self.convention,
            )
        self.assertIn("CLK122", str(ctx.exception))

    def test_audit_surfaces_clk122_on_value(self) -> None:
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-l%D0%B0unch"
            "&utm_id=cmp-glowdrop-launch&utm_content=plc-greta-video-01"
        )
        result = audit_urls([dirty], self.convention)
        self.assertTrue(any(i.code == "CLK122" for i in result.errors))

    def test_audit_surfaces_clk122_on_key(self) -> None:
        # utm_source with Cyrillic 's' (U+0441) in the key.
        dirty = (
            "https://shop.example.com/product"
            "?utm_\u0441ource=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-glowdrop-launch"
            "&utm_id=cmp-glowdrop-launch&utm_content=plc-greta-video-01"
        )
        issues = validate_url(dirty, self.convention)
        self.assertTrue(any(i.code == "CLK122" and i.parameter for i in issues))


if __name__ == "__main__":
    unittest.main()
