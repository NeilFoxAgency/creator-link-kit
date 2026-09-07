import copy
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from creator_link_kit.agency import main, prepare_campaign


def intake():
    return {
        "source_system": "supabase",
        "supabase_snapshot_version": "2026-09-06T00:00:00Z",
        "brand_id": "brand-demo",
        "campaign_id": "cmp-demo",
        "approved_domains": ["shop.example.com"],
        "placements": [
            {
                "creator_id": "creator-demo",
                "placement_id": "plc-demo-1",
                "destination_url": "https://shop.example.com/product?variant=blue",
            }
        ],
    }


class AgencyTests(unittest.TestCase):
    def test_plan_is_deterministic_and_does_not_provision(self):
        a, b = prepare_campaign(intake()), prepare_campaign(intake())
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "prepared_not_provisioned")
        row = a["placements"][0]
        self.assertNotIn("tracking_url", row)
        self.assertNotIn("discount_code", row["arguments"])
        url = row["link_specification"]["generated_destination"]
        self.assertEqual(
            parse_qs(urlsplit(url).query)["utm_medium"], ["creator_sponsorship"]
        )
        self.assertEqual(row["arguments"]["source_system"], "supabase")

    def test_two_videos_same_creator_have_different_placements(self):
        data = intake()
        second = copy.deepcopy(data["placements"][0])
        second["placement_id"] = "plc-demo-2"
        data["placements"].append(second)
        rows = prepare_campaign(data)["placements"]
        self.assertNotEqual(
            rows[0]["link_specification"], rows[1]["link_specification"]
        )

    def test_duplicate_and_case_collision_fail(self):
        for identifier in ("plc-demo-1", "PLC-DEMO-1"):
            data = intake()
            row = copy.deepcopy(data["placements"][0])
            row["placement_id"] = identifier
            data["placements"].append(row)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                prepare_campaign(data)

    def test_identifier_case_is_not_changed(self):
        data = intake()
        data["campaign_id"] = "CMP-Demo"
        data["placements"][0]["placement_id"] = "PLC-Demo-1"
        row = prepare_campaign(data)["placements"][0]
        query = parse_qs(
            urlsplit(row["link_specification"]["generated_destination"]).query
        )
        self.assertEqual(query["utm_id"], ["CMP-Demo"])
        self.assertEqual(query["utm_content"], ["PLC-Demo-1"])

    def test_destinations_fail_closed(self):
        for url in (
            "http://shop.example.com/p",
            "https://evil.example/p",
            "https://sub.shop.example.com/p",
            "https://user:pass@shop.example.com/p",
            "https://shop.example.com:444/p",
            "https://shop.example.com/p#x",
            "https://shop.example.com/p?UTM_Source=x",
            "https://shop.example.com/p?gclid=x",
            "https://shop.example.com/p?email=x",
            "https://shop.example.com/p?x=%0a",
            "https://shop.example.com/p\n",
            "https://shop.example.com/p?x=%E2%80%8B",
        ):
            with self.subTest(url=url):
                data = intake()
                data["placements"][0]["destination_url"] = url
                with self.assertRaises(ValueError):
                    prepare_campaign(data)

    def test_approval_list_and_snapshot_required(self):
        for field, value in (
            ("approved_domains", []),
            ("source_system", "d1"),
            ("supabase_snapshot_version", ""),
        ):
            data = intake()
            data[field] = value
            with self.assertRaises(ValueError):
                prepare_campaign(data)

    def test_domain_normalization_and_no_wildcards_or_ips(self):
        data = intake()
        data["approved_domains"] = ["SHOP.EXAMPLE.COM."]
        self.assertEqual(
            prepare_campaign(data)["approved_domains"], ["shop.example.com"]
        )
        for value in ("*.example.com", "127.0.0.1", "localhost", "https://example.com"):
            data["approved_domains"] = [value]
            with self.assertRaises(ValueError):
                prepare_campaign(data)

    def test_preserve_supplied_discount_and_slug(self):
        data = intake()
        data["placements"][0].update(discount_code="DEMO10", slug="demo-one")
        args = prepare_campaign(data)["placements"][0]["arguments"]
        self.assertEqual(args["discount_code"], "DEMO10")
        self.assertEqual(args["slug"], "demo-one")

    def test_unknown_fields_are_rejected(self):
        data = intake()
        data["customer_email"] = "not-real@example.com"
        with self.assertRaises(ValueError):
            prepare_campaign(data)

    def test_cli_no_partial_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source, out = Path(directory) / "intake.json", Path(directory) / "plan.json"
            source.write_text(json.dumps(intake()))
            self.assertEqual(main([str(source), "--output", str(out)]), 0)
            before = out.read_bytes()
            self.assertEqual(main([str(source), "--output", str(out)]), 2)
            self.assertEqual(before, out.read_bytes())
            source.write_text("{}")
            other = Path(directory) / "bad.json"
            self.assertEqual(main([str(source), "--output", str(other)]), 2)
            self.assertFalse(other.exists())
