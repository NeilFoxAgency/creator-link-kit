"""Detect invisible and format-control characters in campaign URLs.

Operators paste links from Slack, Notion, Google Docs, Word, and email.
Those tools often inject zero-width spaces, non-breaking spaces, soft
hyphens, or BOM characters. The link still looks correct on screen, but
GA4 stores a different dimension value.

Detection runs on the raw URL before parsing. `install()` patches
`links.validate_url` so build, audit, and the public API all emit CLK121
without rewriting the large links module.
"""

from __future__ import annotations

import unicodedata
from typing import Any

_NAMED_INVISIBLE = frozenset(
    {
        "\u00a0",  # NO-BREAK SPACE
        "\u00ad",  # SOFT HYPHEN
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\u2060",  # WORD JOINER
        "\ufeff",  # BOM / ZWNBSP
        "\u2028",  # LINE SEPARATOR
        "\u2029",  # PARAGRAPH SEPARATOR
        "\u180e",  # MONGOLIAN VOWEL SEPARATOR
    }
)

_installed = False


def _is_invisible_or_format(ch: str) -> bool:
    if ch in _NAMED_INVISIBLE:
        return True
    if ch in {"\t", "\n", "\r", "\v", "\f"}:
        return True
    return unicodedata.category(ch) in {"Cf", "Cc", "Zl", "Zp"}


def find_invisible_characters(url: str) -> list[str]:
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


def clk121_issue(url: str) -> Any | None:
    chars = find_invisible_characters(url)
    if not chars:
        return None
    from .links import Issue

    labels = ", ".join(describe_character(ch) for ch in chars)
    return Issue(
        "CLK121",
        "error",
        (
            "URL contains invisible or format-control character(s): "
            + labels
            + ". Copy/paste from Slack, Docs, or email often inserts these; "
            "GA4 stores a different value than the one on screen. "
            "Delete the hidden character and rebuild the link"
        ),
        url=url,
    )


def install() -> None:
    """Patch links.validate_url so CLK121 runs on every validation path."""
    global _installed
    if _installed:
        return
    from . import links

    original = links.validate_url

    def validate_url(url: str, convention: Any) -> list[Any]:
        issues = []
        extra = clk121_issue(url)
        if extra is not None:
            issues.append(extra)
        issues.extend(original(url, convention))
        return issues

    links.validate_url = validate_url  # type: ignore[method-assign]
    _installed = True
