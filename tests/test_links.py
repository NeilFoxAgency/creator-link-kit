import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import audit_urls, build_url, validate_url


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    @staticmethod
    def params() -> dict[str, str]:
        return {
            "utm_source": "youtube",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": "plc-greta-01",
        }

    @staticmethod
    def tagged_url(*, source: str = "youtube", host: str = "shop.example.com"):
        return (
            f"https://{host}/product?utm_source={source}"
            "&utm_medium=influencer&utm_campaign=cmp-spring-launch"
            "&utm_id=cmp-spring-launch&utm_content=plc-greta-01"
        )

    def test_build_preserves_existing_query(self):
        url = build_url(
            "https://shop.example.com/product?bundle=pro",
            self.params(),
            self.convention,
        )
        self.assertIn("bundle=pro", url)
        self.assertIn("utm_medium=influencer", url)

    def test_build_blocks_double_tagging(self):
        with self.assertRaisesRegex(ValueError, "double-tag"):
            build_url(
                "https://shop.example.com/product?utm_source=youtube",
                self.params(),
                self.convention,
            )

    def test_build_rejects_invalid_port(self):
        with self.assertRaisesRegex(ValueError, "invalid port"):
            build_url(
                "https://shop.example.com:not-a-port/product",
                self.params(),
                self.convention,
            )

    def test_build_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(ValueError, "embedded credentials"):
            build_url(
                "https://user:secret@shop.example.com/product",
                self.params(),
                self.convention,
            )

    def test_build_rejects_missing_or_malformed_hostnames(self):
        for url in (
            "https://:443/product",
            "https://./product",
            "https://bad host.example/product",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "hostname"):
                    build_url(url, self.params(), self.convention)

                issues = validate_url(url, self.convention)
                self.assertEqual([issue.code for issue in issues], ["CLK001"])

    def test_case_near_miss(self):
        issues = validate_url(self.tagged_url(source="YouTube"), self.convention)
        codes = {issue.code for issue in issues}
        self.assertIn("CLK105", codes)
        self.assertIn("CLK107", codes)

    def test_close_match_suggestion(self):
        issues = validate_url(self.tagged_url(source="youtub"), self.convention)
        issue = next(item for item in issues if item.code == "CLK104")
        self.assertIn("youtube", issue.message)

    def test_missing_required(self):
        issues = validate_url(
            "https://shop.example.com/product?utm_source=youtube",
            self.convention,
        )
        self.assertEqual(sum(i.code == "CLK102" for i in issues), 4)

    def test_repeated_parameter(self):
        url = self.tagged_url() + "&utm_source=tiktok"
        issues = validate_url(url, self.convention)
        self.assertIn("CLK103", {issue.code for issue in issues})

    def test_external_domain_is_error_in_production(self):
        issues = validate_url(self.tagged_url(host="evil.example.net"), self.convention)
        issue = next(item for item in issues if item.code == "CLK003")
        self.assertEqual(issue.severity, "error")

    def test_external_domain_is_warning_in_development(self):
        raw = starter_convention()
        raw["mode"] = "development"
        convention = convention_from_dict(raw)
        issues = validate_url(self.tagged_url(host="evil.example.net"), convention)
        issue = next(item for item in issues if item.code == "CLK003")
        self.assertEqual(issue.severity, "warning")

    def test_subdomain_is_owned(self):
        issues = validate_url(
            self.tagged_url(host="offers.example.com"), self.convention
        )
        self.assertNotIn("CLK003", {issue.code for issue in issues})

    def test_exact_owned_domain_is_owned(self):
        issues = validate_url(self.tagged_url(host="example.com"), self.convention)
        self.assertNotIn("CLK003", {issue.code for issue in issues})

    def test_uppercase_and_trailing_dot_hostnames_are_owned(self):
        for host in ("SHOP.EXAMPLE.COM", "shop.example.com."):
            with self.subTest(host=host):
                issues = validate_url(self.tagged_url(host=host), self.convention)
                self.assertNotIn("CLK003", {issue.code for issue in issues})

    def test_deceptive_suffix_domains_are_external(self):
        for host in ("example.com.evil.net", "notexample.com"):
            with self.subTest(host=host):
                issues = validate_url(self.tagged_url(host=host), self.convention)
                issue = next(item for item in issues if item.code == "CLK003")
                self.assertEqual(issue.severity, "error")

    def test_invalid_port_is_a_parse_error(self):
        url = self.tagged_url().replace(
            "shop.example.com", "shop.example.com:not-a-port", 1
        )
        issues = validate_url(url, self.convention)
        self.assertEqual([issue.code for issue in issues], ["CLK001"])
        self.assertIn("invalid port", issues[0].message)

    def test_embedded_credentials_are_a_parse_error(self):
        url = self.tagged_url().replace(
            "shop.example.com", "user:secret@shop.example.com", 1
        )
        issues = validate_url(url, self.convention)
        self.assertEqual([issue.code for issue in issues], ["CLK001"])
        self.assertIn("embedded credentials", issues[0].message)

    def test_duplicate_detection(self):
        url = self.tagged_url()
        result = audit_urls([url, url], self.convention)
        duplicate = next(issue for issue in result.issues if issue.code == "CLK005")
        self.assertEqual(duplicate.row, 2)

    def test_fragment_does_not_defeat_duplicate_detection(self):
        base = self.tagged_url()
        result = audit_urls([base + "#one", base + "#two"], self.convention)
        self.assertIn("CLK005", {issue.code for issue in result.issues})

    def test_http_warning(self):
        url = self.tagged_url().replace("https://", "http://", 1)
        issues = validate_url(url, self.convention)
        self.assertIn("CLK002", {issue.code for issue in issues})

    def test_plain_url_warning(self):
        issues = validate_url("https://shop.example.com/product", self.convention)
        self.assertIn("CLK004", {issue.code for issue in issues})

    def test_utm_id_pattern_is_enforced(self):
        url = self.tagged_url().replace(
            "utm_id=cmp-spring-launch", "utm_id=Bad Campaign"
        )
        issues = validate_url(url, self.convention)
        self.assertIn("CLK106", {issue.code for issue in issues})

    def test_campaign_id_mismatch_across_rows(self):
        first = self.tagged_url()
        second = (
            self.tagged_url(source="instagram")
            .replace("utm_id=cmp-spring-launch", "utm_id=cmp-other")
            .replace("utm_content=plc-greta-01", "utm_content=plc-priya-01")
        )
        result = audit_urls([first, second], self.convention)
        issues = [issue for issue in result.issues if issue.code == "CLK110"]
        self.assertEqual(len(issues), 2)
        self.assertTrue(all(issue.severity == "error" for issue in issues))

    def test_same_id_multiple_campaigns(self):
        first = self.tagged_url()
        second = (
            self.tagged_url(source="instagram")
            .replace("utm_campaign=cmp-spring-launch", "utm_campaign=cmp-other")
            .replace("utm_content=plc-greta-01", "utm_content=plc-priya-01")
        )
        result = audit_urls([first, second], self.convention)
        self.assertIn("CLK111", {issue.code for issue in result.issues})

    def test_consistent_campaign_id_pairs_are_clean(self):
        urls = [
            self.tagged_url(),
            self.tagged_url(source="instagram").replace(
                "utm_content=plc-greta-01", "utm_content=plc-priya-01"
            ),
            self.tagged_url()
            .replace("utm_campaign=cmp-spring-launch", "utm_campaign=cmp-other")
            .replace("utm_id=cmp-spring-launch", "utm_id=cmp-other")
            .replace("utm_content=plc-greta-01", "utm_content=plc-other-01"),
        ]
        result = audit_urls(urls, self.convention)
        codes = {issue.code for issue in result.issues}
        self.assertNotIn("CLK110", codes)
        self.assertNotIn("CLK111", codes)

    def test_build_with_utm_id(self):
        url = build_url(
            "https://shop.example.com/product",
            self.params(),
            self.convention,
        )
        self.assertIn("utm_id=cmp-spring-launch", url)


if __name__ == "__main__":
    unittest.main()
