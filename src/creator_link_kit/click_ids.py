"""Detect paid-ad click identifiers on creator campaign URLs.

Paid platforms auto-append click IDs when an operator copies a live ad URL
into a creator brief or YouTube description. GA4 and similar tools then
attribute the session to Paid Search / Paid Social instead of the
influencer UTM dimensions, even though the link still looks tagged.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qsl, urlsplit

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

_installed = False


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


def install() -> None:
    """Wrap links.validate_url so build, audit, and the CLI surface CLK129."""

    global _installed
    if _installed:
        return

    from .links import Issue, validate_url as original
    from . import links as links_mod

    def wrapped(url: str, convention: object, *args: object, **kwargs: object):
        issues = list(original(url, convention, *args, **kwargs))
        try:
            parsed = urlsplit(url)
        except ValueError:
            return issues
        if parsed.scheme not in {"http", "https"} or not parsed.query:
            return issues
        click_keys = paid_click_id_keys(
            parse_qsl(parsed.query, keep_blank_values=True)
        )
        if click_keys:
            listed = ", ".join(repr(key) for key in click_keys)
            issues.append(
                Issue(
                    "CLK129",
                    "error",
                    (
                        f"URL contains paid-ad click identifier(s) {listed}; "
                        "GA4 and similar tools will attribute the session to a "
                        "paid channel instead of the creator UTM dimensions. "
                        "Remove click IDs from creator briefs and descriptions"
                    ),
                    parameter=click_keys[0],
                    url=url,
                )
            )
        return issues

    links_mod.validate_url = wrapped  # type: ignore[method-assign]
    _installed = True
