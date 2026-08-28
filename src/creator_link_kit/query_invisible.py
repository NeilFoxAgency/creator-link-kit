"""Detect invisible and format-control characters in campaign URLs.

Operators paste links from Slack, Notion, Google Docs, Word, and email.
Those tools often inject zero-width spaces, non-breaking spaces, soft
hyphens, or BOM characters. The link still looks correct in a browser
address bar or a spreadsheet cell, but GA4 stores a different dimension
value (or fails to match an allowlist) because the invisible code point
is part of the string.

Detection runs on the raw URL before parsing so the characters cannot
hide inside a decoded query value.
"""

from __future__ import annotations

import unicodedata

# Named characters that commonly survive copy/paste into campaign links.
_NAMED_INVISIBLE = frozenset(
    {
        "\u00a0",  # NO-BREAK SPACE
        "\u00ad",  # SOFT HYPHEN
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\u2060",  # WORD JOINER
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE / BOM
        "\u2028",  # LINE SEPARATOR
        "\u2029",  # PARAGRAPH SEPARATOR
        "\u180e",  # MONGOLIAN VOWEL SEPARATOR (legacy format)
    }
)


def _is_invisible_or_format(ch: str) -> bool:
    if ch in _NAMED_INVISIBLE:
        return True
    if ch in {"\t", "\n", "\r", "\v", "\f"}:
        return True
    category = unicodedata.category(ch)
    # Cf = format (ZWSP family), Cc = control, Zl/Zp = line/paragraph.
    if category in {"Cf", "Cc", "Zl", "Zp"}:
        return True
    return False


def find_invisible_characters(url: str) -> list[str]:
    """Return unique invisible/format characters found in ``url``."""
    found: list[str] = []
    seen: set[str] = set()
    for ch in url:
        if ch not in seen and _is_invisible_or_format(ch):
            seen.add(ch)
            found.append(ch)
    return found


def describe_character(ch: str) -> str:
    name = unicodedata.name(ch, "UNKNOWN")
    return f"U+{ord(ch):04X} {name}"
