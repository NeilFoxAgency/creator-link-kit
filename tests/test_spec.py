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
