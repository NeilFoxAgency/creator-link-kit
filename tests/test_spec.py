import unittest

from creator_link_kit.config import convention_from_dict, starter_convention
from creator_link_kit.models import LinkIdentifiers, LinkProvisionRequest
from creator_link_kit.spec import build_link_specification


class SpecificationTests(unittest.TestCase):
    def setUp(self):
        self.convention = convention_from_dict(starter_convention())

    def test_identifiers_can_supply_utm_id_and_content(self):
        identifiers = LinkIdentifiers(
            brand_id="brd-soap",
            campaign_id="cmp-summer-launch",
            creator_id="crt-alex",
            placement_id="plc-alex-video-01",
        )
        specification = build_link_specification(
            "https://shop.example.com/product",
            {
                "utm_source": "youtube",
                "utm_campaign": "cmp-summer-launch",
            },
            self.convention,
            identifiers=identifiers,
        )
        self.assertIn("utm_id=cmp-summer-launch", specification.generated_destination)
        self.assertIn(
            "utm_content=plc-alex-video-01", specification.generated_destination
        )
        request = LinkProvisionRequest.from_specification(specification)
        self.assertEqual(request.destination_url, specification.generated_destination)
        self.assertRegex(specification.config_fingerprint or "", r"^[0-9a-f]{64}$")
        self.assertEqual(
            specification.as_dict()["config_fingerprint"],
            specification.config_fingerprint,
        )

    def test_utm_content_alone_is_not_a_placement_id(self):
        specification = build_link_specification(
            "https://shop.example.com/product",
            {
                "utm_source": "youtube",
                "utm_campaign": "cmp-summer-launch",
                "utm_id": "cmp-summer-launch",
                "utm_content": "glowwithgreta",
            },
            self.convention,
        )
        self.assertIsNone(specification.identifiers.placement_id)
        self.assertEqual(specification.audit.errors, ())

    def test_development_warning_is_valid_and_can_be_provisioned(self):
        raw = starter_convention()
        raw["mode"] = "development"
        convention = convention_from_dict(raw)
        specification = build_link_specification(
            "https://example.net/product",
            {
                "utm_source": "youtube",
                "utm_campaign": "cmp-summer-launch",
                "utm_id": "cmp-summer-launch",
                "utm_content": "plc-summer-01",
            },
            convention,
            identifiers=LinkIdentifiers(
                campaign_id="cmp-summer-launch",
                placement_id="plc-summer-01",
            ),
        )
        self.assertTrue(specification.audit.valid)
        self.assertGreater(len(specification.audit.warnings), 0)
        self.assertIsNotNone(LinkProvisionRequest.from_specification(specification))

    def test_mismatched_campaign_identifier_is_rejected(self):
        identifiers = LinkIdentifiers(campaign_id="cmp-one")
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_link_specification(
                "https://shop.example.com/product",
                {
                    "utm_source": "youtube",
                    "utm_campaign": "cmp-two",
                    "utm_id": "cmp-two",
                    "utm_content": "plc-alex-video-01",
                },
                self.convention,
                identifiers=identifiers,
            )

    def test_mismatched_placement_identifier_is_rejected(self):
        identifiers = LinkIdentifiers(
            campaign_id="cmp-one",
            placement_id="plc-one",
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_link_specification(
                "https://shop.example.com/product",
                {
                    "utm_source": "youtube",
                    "utm_campaign": "cmp-one",
                    "utm_id": "cmp-one",
                    "utm_content": "plc-two",
                },
                self.convention,
                identifiers=identifiers,
            )


if __name__ == "__main__":
    unittest.main()
