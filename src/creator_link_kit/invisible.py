"""Detect invisible and format-control characters in UTM strings."""

from __future__ import annotations

# Invisible or format-control characters that survive copy/paste from Slack,
# Notion, Word, and spreadsheets. They split GA4 dimensions without being
# visible in most UIs. Regular ASCII space is excluded (CLK113 covers trim).
INVISIBLE_CHARS = frozenset(
    {
        "\u0000",
        "\t",
        "\n",
        "\r",
        "\u00a0",  # no-break space
        "\u00ad",  # soft hyphen
        "\u200b",  # zero-width space
        "\u200c",  # zero-width non-joiner
        "\u200d",  # zero-width joiner
        "\u2060",  # word joiner
        "\ufeff",  # BOM / zero-width no-break space
    }
)
INVISIBLE_PERCENT = (
    "%00",
    "%09",
    "%0a",
    "%0d",
    "%c2%a0",
    "%c2%ad",
    "%e2%80%8b",
    "%e2%80%8c",
    "%e2%80%8d",
    "%e2%81%a0",
    "%ef%bb%bf",
)


def first_invisible_label(text: str) -> str | None:
    lowered = text.lower()
    for marker in INVISIBLE_PERCENT:
        if marker in lowered:
            return marker
    for char in text:
        if char in INVISIBLE_CHARS:
            return f"U+{ord(char):04X}"
    return None
