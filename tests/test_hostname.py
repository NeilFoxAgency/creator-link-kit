import unittest
from urllib.parse import urlsplit

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.links import build_url, validate_url
from creator_link_kit.urls import authority_error


class HostnameAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())
        self.params = {
            "utm_source": "youtube",
            "utm_campaign": "cmp-spring-launch",
            "utm_id": "cmp-spring-launch",
            "utm_content": "plc-greta-01",
        }

    def test_rejects_space_in_hostname(self):
        issues = validate_url(
            "https://bad host.example/product?utm_source=youtube",
            self.convention,
        )
        self.assertTrue(any(i.code == "CLK001" for i in issues))

    def test_rejects_underscore_hostname(self):
        issues = validate_url(
            "https://bad_host.example/product?utm_source=youtube",
            self.convention,
        )
        self.assertTrue(any(i.code == "CLK001" for i in issues))

    def test_rejects_empty_dns_label(self):
        with self.assertRaisesRegex(ValueError, "malformed hostname"):
            build_url("https://.example.com/product", self.params, self.convention)

    def test_accepts_ip_literal_authority(self):
        parsed = urlsplit("https://127.0.0.1/product")
        self.assertIsNone(authority_error(parsed))

    def test_accepts_normal_hostname(self):
        parsed = urlsplit("https://shop.example.com/product")
        self.assertIsNone(authority_error(parsed))


if __name__ == "__main__":
    unittest.main()
