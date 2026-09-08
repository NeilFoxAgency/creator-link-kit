import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, validate_url


class EncodedSeparatorTests(unittest.TestCase):
    """CLK119: percent-encoded '&' glues later UTM pairs into one value."""

    def setUp(self) -> None:
        self.convention = convention_from_dict(starter_convention())

    def test_percent_encoded_ampersand_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        issues = validate_url(url, self.convention)
        issue = next(item for item in issues if item.code == "CLK119")
        self.assertEqual(issue.severity, "error")
        self.assertIn("%26", issue.message)

    def test_decoded_embedded_pair_in_value_is_error(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        values_ok = any(
            i.code == "CLK119" for i in validate_url(url, self.convention)
        )
        self.assertTrue(values_ok)

    def test_clean_query_has_no_clk119(self) -> None:
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        codes = {issue.code for issue in validate_url(url, self.convention)}
        self.assertNotIn("CLK119", codes)

    def test_value_mentioning_utm_without_separator_is_clean(self) -> None:
        raw = starter_convention()
        raw["parameters"]["utm_campaign"] = {"pattern": "^[a-z0-9][a-z0-9-]{2,48}$"}
        convention = convention_from_dict(raw)
        url = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        codes = {issue.code for issue in validate_url(url, convention)}
        self.assertNotIn("CLK119", codes)

    def test_audit_surfaces_encoded_separator(self) -> None:
        clean = (
            "https://shop.example.com/product"
            "?utm_source=youtube&utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )
        dirty = (
            "https://shop.example.com/product"
            "?utm_source=youtube%26utm_medium=influencer"
            "&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-priya-01"
        )
        result = audit_urls([clean, dirty], self.convention)
        self.assertTrue(any(i.code == "CLK119" for i in result.errors))


if __name__ == "__main__":
    unittest.main()
