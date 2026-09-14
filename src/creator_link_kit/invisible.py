"""CLK120: detect invisible copy/paste characters in shipped campaign URLs.

Creator and brand teams copy tracking links out of Google Docs, Slack, Word,
and PDFs. Those tools silently insert format characters that do not show up
in most spreadsheets:

- U+200B zero-width space
- U+00AD soft hyphen
- U+FEFF BOM
- U+00A0 / U+202F non-breaking spaces
- U+200C / U+200D / U+2060 joiners

The link looks valid, but browsers and GA4 parse a different host or UTM
value. Attribution then lands in (direct) / (none) or a polluted dimension.

Ordinary ASCII spaces are not flagged here (CLK113 / CLK001). This module
wraps ``links.validate_url`` on import so audit, CLI, and package exports
all surface CLK120 without rewriting the large links module.
"""

from __future__ import annotations

from collections.abc import Callable

from .links import Issue, validate_url as _validate_url

INVISIBLE_URL_CHARS: dict[str, str] = {
    "\u00ad": "soft hyphen",
    "\u00a0": "non-breaking space",
    "\u200b": "zero-width space",
    "\u200c": "zero-width non-joiner",
    "\u200d": "zero-width joiner",
    "\u2060": "word joiner",
    "\ufeff": "BOM / zero-width no-break space",
    "\u202f": "narrow no-break space",
}


def invisible_url_markers(url: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for char in url:
        label = INVISIBLE_URL_CHARS.get(char)
        if label and label not in seen:
            seen.add(label)
            found.append(label)
    return found


def detect_invisible_url_characters(url: str) -> list[Issue]:
    markers = invisible_url_markers(url)
    if not markers:
        return []
    listed = ", ".join(markers)
    return [
        Issue(
            "CLK120",
            "error",
            (
                f"URL contains invisible copy/paste characters ({listed}); "
                "browsers and GA4 treat the host or UTM value as different "
                "from the visible text. Remove the format characters before "
                "shipping the link"
            ),
            url=url,
        )
    ]


def validate_url_with_clk120(url: str, convention) -> list[Issue]:
    extras = detect_invisible_url_characters(url)
    issues = _validate_url(url, convention)
    if extras and not any(issue.code == "CLK120" for issue in issues):
        return extras + issues
    return issues


def install() -> Callable:
    """Replace ``links.validate_url`` with the CLK120-aware wrapper."""
    from . import links

    links.validate_url = validate_url_with_clk120  # type: ignore[method-assign]
    return links.validate_url


install()
