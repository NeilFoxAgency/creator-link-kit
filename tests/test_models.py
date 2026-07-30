import unittest

from creator_link_kit.models import (
    LinkIdentifiers,
    LinkProvisionRequest,
    ProvisionedLink,
)


class ModelTests(unittest.TestCase):
    def test_identifiers_read_only_approved_fields(self):
        identifiers = LinkIdentifiers.from_mapping(
            {
                "brand_id": " brd-soap ",
                "campaign_id": "cmp-summer",
                "creator_id": "crt-alex",
                "placement_id": "plc-alex-01",
                "customer_email": "customer@example.com",
            }
        )
        self.assertEqual(identifiers.brand_id, "brd-soap")
        self.assertNotIn("customer_email", identifiers.as_dict())

    def test_provision_request_validates_destination(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        with self.assertRaisesRegex(ValueError, "absolute"):
            LinkProvisionRequest("not-a-url", identifiers)

    def test_provisioned_link_is_provider_neutral(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        link = ProvisionedLink(
            provider="example-provider",
            provider_link_id="link-123",
            tracking_url="https://go.example.com/alex",
            destination_url="https://shop.example.com/product",
            identifiers=identifiers,
        )
        self.assertEqual(link.identifiers.placement_id, "plc-alex-01")

    def test_identifier_mapping_rejects_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "unknown identifier"):
            LinkIdentifiers.from_mapping(
                {"placement_id": "plc-alex-01"},
                columns={"order_id": "order_id"},
            )

    def test_identifier_mapping_rejects_non_string_values(self):
        with self.assertRaisesRegex(TypeError, "placement_id"):
            LinkIdentifiers.from_mapping({"placement_id": 42})

    def test_provider_models_reject_credentialed_urls(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        with self.assertRaisesRegex(ValueError, "embedded credentials"):
            LinkProvisionRequest(
                "https://user:secret@example.com/product",
                identifiers,
            )

    def test_provider_models_reject_invalid_ports(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        with self.assertRaisesRegex(ValueError, "invalid port"):
            LinkProvisionRequest(
                "https://example.com:not-a-port/product",
                identifiers,
            )

    def test_tags_must_not_be_a_single_string(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        with self.assertRaisesRegex(ValueError, "iterable"):
            LinkProvisionRequest(
                "https://example.com/product",
                identifiers,
                tags="youtube",  # type: ignore[arg-type]
            )

    def test_provider_models_are_machine_readable(self):
        identifiers = LinkIdentifiers(placement_id="plc-alex-01")
        request = LinkProvisionRequest(
            "https://example.com/product",
            identifiers,
            tags=("youtube", "youtube", "campaign"),
        )
        self.assertEqual(request.as_dict()["tags"], ["youtube", "campaign"])

        link = ProvisionedLink(
            provider="example-provider",
            provider_link_id="link-123",
            tracking_url="https://go.example.com/alex",
            destination_url="https://example.com/product",
            identifiers=identifiers,
        )
        self.assertEqual(link.as_dict()["ids"]["placement_id"], "plc-alex-01")


if __name__ == "__main__":
    unittest.main()
