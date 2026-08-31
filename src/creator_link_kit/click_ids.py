"""Detect paid-ad click identifiers on creator campaign URLs.

Paid platforms auto-append click IDs when an operator copies a live ad URL
into a creator brief or YouTube description. GA4 and similar tools then
attribute the session to Paid Search / Paid Social instead of the
influencer UTM dimensions, even though the link still looks tagged.
"""

from __future__ import annotations

# Conservative, well-known click-id keys. Values are never inspected.
# Keep this list explicit so a product SKU named "gclid" in a path is not
# flagged and so we do not treat generic analytics cookies as click IDs.
PAID_CLICK_ID_KEYS = frozenset(
    {
        "gclid",
        "gclsrc",
        "wbraid",
        "gbraid",
        "dclid",
        "fbclid",
        "msclkid",
        "ttclid",
        "twclid",
        "li_fat_id",
        "epik",
        "sccid",
        "irclickid",
        "yclid",
    }
)


def paid_click_id_keys(pairs: list[tuple[str, str]]) -> tuple[str, ...]:
    """Return paid-ad click-id keys present in already-parsed query pairs."""

    found: list[str] = []
    seen: set[str] = set()
    for key, _value in pairs:
        lowered = key.lower()
        if lowered in PAID_CLICK_ID_KEYS and lowered not in seen:
            seen.add(lowered)
            found.append(key)
    return tuple(found)
