"""Detect invisible copy/paste characters that break shipped campaign URLs."""

from __future__ import annotations

# Invisible or format characters that survive copy/paste from Google Docs,
# Slack, Word, and PDF viewers. They are not visible in most spreadsheets but
# they split hostnames, glue UTM keys, or become literal percent-encodings
# that GA4 treats as a different value.
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
