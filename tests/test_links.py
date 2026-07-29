import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_url


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def test_build_preserves_existing_query(self):
        url = build_url(
            "https://shop.example.com/product?bundle=pro",
            {
                "utm_source": "youtube",
                "utm_campaign": "spring-launch",
                "utm_content": "creator.one",
            },
            self.convention,
        )
        self.assertIn("bundle=pro", url)
        self.assertIn("utm_medium=influencer", url)

    def test_build_blocks_double_tagging(self):
        with self.assertRaisesRegex(ValueError, "double-tag"):
            build_url(
                "https://shop.example.com/product?utm_source=youtube",
                {"utm_source": "youtube", "utm_campaign": "spring-launch"},
                self.convention,
            )

    def test_case_near_miss(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=YouTube&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        codes = {issue.code for issue in issues}
        self.assertIn("CLK105", codes)
        self.assertIn("CLK107", codes)

    def test_close_match_suggestion(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtub&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        issue = next(item for item in issues if item.code == "CLK104")
        self.assertIn("youtube", issue.message)

    def test_missing_required(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtube",
            self.convention,
        )
        self.assertEqual(sum(i.code == "CLK102" for i in issues), 2)

    def test_repeated_parameter(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtube&utm_source=tiktok&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        self.assertIn("CLK103", {issue.code for issue in issues})

    def test_external_domain_warning(self):
        issues = validate_url(
            "https://evil.example.net/?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        self.assertIn("CLK003", {issue.code for issue in issues})

    def test_subdomain_is_owned(self):
        issues = validate_url(
            "https://offers.example.com/?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        self.assertNotIn("CLK003", {issue.code for issue in issues})

    def test_duplicate_detection(self):
        url = "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch"
        result = audit_urls([url, url], self.convention)
        duplicate = next(issue for issue in result.issues if issue.code == "CLK005")
        self.assertEqual(duplicate.row, 2)

    def test_fragment_does_not_defeat_duplicate_detection(self):
        base = "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch"
        result = audit_urls([base + "#one", base + "#two"], self.convention)
        self.assertIn("CLK005", {issue.code for issue in result.issues})

    def test_http_warning(self):
        issues = validate_url(
            "http://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch",
            self.convention,
        )
        self.assertIn("CLK002", {issue.code for issue in issues})

    def test_plain_url_warning(self):
        issues = validate_url("https://shop.example.com/product", self.convention)
        self.assertIn("CLK004", {issue.code for issue in issues})

    def test_utm_id_pattern_accepts_valid(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch&utm_id=cmp_2026_q3_glow",
            self.convention,
        )
        self.assertNotIn("CLK106", {issue.code for issue in issues})
        self.assertNotIn("CLK101", {issue.code for issue in issues})

    def test_utm_id_pattern_rejects_spaces(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=spring-launch&utm_id=bad id",
            self.convention,
        )
        self.assertIn("CLK106", {issue.code for issue in issues})

    def test_campaign_id_mismatch_across_rows(self):
        urls = [
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=glowdrop&utm_id=id-a",
            "https://shop.example.com/product?utm_source=instagram&utm_medium=influencer&utm_campaign=glowdrop&utm_id=id-b",
        ]
        result = audit_urls(urls, self.convention)
        clk110 = [i for i in result.issues if i.code == "CLK110"]
        self.assertEqual(len(clk110), 2)
        self.assertTrue(all(i.severity == "error" for i in clk110))

    def test_same_id_multiple_campaigns(self):
        urls = [
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=alpha&utm_id=shared-id",
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=beta&utm_id=shared-id",
        ]
        result = audit_urls(urls, self.convention)
        self.assertIn("CLK111", {issue.code for issue in result.issues})

    def test_consistent_campaign_id_pairs_clean(self):
        urls = [
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=glowdrop&utm_id=id-a",
            "https://shop.example.com/product?utm_source=instagram&utm_medium=influencer&utm_campaign=glowdrop&utm_id=id-a",
            "https://shop.example.com/product?utm_source=youtube&utm_medium=influencer&utm_campaign=other&utm_id=id-b",
        ]
        result = audit_urls(urls, self.convention)
        codes = {issue.code for issue in result.issues}
        self.assertNotIn("CLK110", codes)
        self.assertNotIn("CLK111", codes)

    def test_build_with_utm_id(self):
        url = build_url(
            "https://shop.example.com/product",
            {
                "utm_source": "youtube",
                "utm_campaign": "spring-launch",
                "utm_id": "cmp_spring_2026",
            },
            self.convention,
        )
        self.assertIn("utm_id=cmp_spring_2026", url)


if __name__ == "__main__":
    unittest.main()
