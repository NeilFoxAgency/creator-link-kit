"""Offline, fail-closed preparation for the NFA attribution connector.

No provider credentials, network calls, campaign creation, or inferred approvals.
Run ``python -m creator_link_kit.agency intake.json --output plan.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

from .config import convention_from_dict
from .models import LinkIdentifiers
from .spec import build_link_specification
from .urls import authority_error

_ID = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}"
_PAID = {"gclid", "dclid", "fbclid", "msclkid", "ttclid", "gbraid", "wbraid"}
_PRIVATE = {"email", "phone", "password", "token", "access_token", "api_key"}
_ROOT = {
    "source_system",
    "supabase_snapshot_version",
    "brand_id",
    "campaign_id",
    "approved_domains",
    "placements",
}
_ROW = {"creator_id", "placement_id", "destination_url", "discount_code", "slug"}


def _object(value: Any, allowed: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError(f"{label}: expected object with only {sorted(allowed)}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(_ID, value) is None:
        raise ValueError(f"invalid {label}; use a stable ID without sanitization")
    return value


def _hidden(value: str) -> bool:
    return any(c.isspace() or unicodedata.category(c) in {"Cc", "Cf"} for c in value)


def _host(value: Any) -> str:
    if not isinstance(value, str) or not value or _hidden(value):
        raise ValueError("approved_domains must contain explicit DNS hostnames")
    host = value.lower().removesuffix(".")
    if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host:
        raise ValueError("use ASCII DNS hostnames, not URLs, wildcards or IP addresses")
    parsed = urlsplit("https://" + host)
    if authority_error(parsed):
        raise ValueError("invalid approved domain")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP destinations are not supported")
    if host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        raise ValueError("private or special-use destination is not supported")
    return host


def _destination(value: Any, domains: list[str]) -> str:
    if not isinstance(value, str) or len(value) > 2000 or _hidden(value):
        raise ValueError("invalid destination_url")
    if _hidden(unquote(value)) or "\\" in value:
        raise ValueError("destination contains encoded whitespace or unsafe characters")
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or authority_error(parsed)
            or parsed.port not in (None, 443)
            or parsed.fragment
        ):
            raise ValueError(
                "destination requires HTTPS, default port, no credentials/fragment"
            )
        if _host(parsed.hostname) not in domains:
            raise ValueError("destination host is not explicitly approved")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid destination: {exc}") from exc
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if key.casefold().startswith("utm_") or key.casefold() in _PAID | _PRIVATE:
            raise ValueError(
                "remove existing UTMs, paid click IDs, or private query fields"
            )
    return value


def prepare_campaign(raw: Any) -> dict[str, Any]:
    """Validate the entire batch before returning unsigned, unprovisioned drafts."""
    data = _object(raw, _ROOT, "intake")
    if data.get("source_system") != "supabase":
        raise ValueError(
            "source_system must be supabase; do not create canonical records here"
        )
    version = data.get("supabase_snapshot_version")
    if not isinstance(version, str) or not 1 <= len(version) <= 100 or _hidden(version):
        raise ValueError("supabase_snapshot_version is required")
    brand = _id(data.get("brand_id"), "brand_id")
    campaign = _id(data.get("campaign_id"), "campaign_id")
    source_domains = data.get("approved_domains")
    if not isinstance(source_domains, list) or not source_domains:
        raise ValueError("approved_domains must not be empty")
    domains = sorted({_host(value) for value in source_domains})
    rows = data.get("placements")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 40:
        raise ValueError(
            "provide 1-40 placements; this technical limit is not scope approval"
        )
    seen: set[str] = set()
    prepared = []
    for raw_row in rows:
        row = _object(raw_row, _ROW, "placement")
        creator = _id(row.get("creator_id"), "creator_id")
        placement = _id(row.get("placement_id"), "placement_id")
        if placement.casefold() in seen:
            raise ValueError("duplicate or case-colliding placement_id")
        seen.add(placement.casefold())
        destination = _destination(row.get("destination_url"), domains)
        params = {
            "utm_source": "youtube",
            "utm_medium": "creator_sponsorship",
            "utm_campaign": campaign,
            "utm_id": campaign,
            "utm_content": placement,
        }
        config = convention_from_dict(
            {
                "version": 1,
                "base_url": destination,
                "owned_domains": domains,
                "mode": "production",
                "casing": "any",
                "max_value_length": 100,
                "required": list(params),
                "parameters": {key: {"pattern": "^" + _ID + "$"} for key in params},
            }
        )
        identifiers = LinkIdentifiers(brand, campaign, creator, placement)
        spec = build_link_specification(
            destination, params, config, identifiers=identifiers
        )
        arguments = {
            **identifiers.as_dict(),
            "platform": "youtube",
            "destination_url": destination,
            "source_system": "supabase",
            "supabase_snapshot_version": version,
            "utm_source": "youtube",
            "utm_medium": "creator_sponsorship",
            "utm_campaign": campaign,
        }
        for field, pattern in (
            ("discount_code", r"[A-Za-z0-9_-]{1,64}"),
            ("slug", r"[a-z0-9][a-z0-9-]{1,63}"),
        ):
            if field in row:
                value = row[field]
                if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
                    raise ValueError(
                        f"invalid {field}; use the approved value, never invent one"
                    )
                arguments[field] = value
        prepared.append(
            {
                "link_specification": spec.as_dict(),
                "tool": "create_campaign_link",
                "arguments": arguments,
            }
        )
    plan = {
        "schema_version": 1,
        "status": "prepared_not_provisioned",
        "source_system": "supabase",
        "supabase_snapshot_version": version,
        "brand_id": brand,
        "campaign_id": campaign,
        "approved_domains": domains,
        "placements": prepared,
        "requirements_before_execution": [
            "Re-fetch authoritative campaign/placements; reject stale snapshots.",
            "Confirm destination/code approval and creator/deliverable identity.",
            "Execute only under the current operations mode and write permissions.",
            "Read back each delivery link; verify its redirect before publication.",
        ],
    }
    canonical = json.dumps(
        plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    plan["plan_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.intake.stat().st_size > 1_000_000:
            raise ValueError("intake exceeds 1 MB")
        plan = prepare_campaign(json.loads(args.intake.read_text(encoding="utf-8")))
        # Never overwrite a prior plan or leave output on validation failure.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(plan, indent=2, ensure_ascii=True) + "\n")
    except (OSError, ValueError, TypeError) as exc:
        print(f"Cannot prepare campaign: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
