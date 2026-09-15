"""Detect invisible copy/paste format characters in raw campaign URLs."""

from __future__ import annotations

from collections.abc import Callable

from .links import Issue

# Characters that look like nothing in Docs, Slack, Word, and most spreadsheets
# but change how browsers and GA4 parse a host or UTM value. Ordinary ASCII
# spaces are intentionally excluded; those remain CLK113 / CLK001.
INVISIBLE_FORMAT_CHARS: dict[str, str] = {
    "\u200b": "zero-width space (U+200B)",
    "\u00ad": "soft hyphen (U+00AD)",
    "\ufeff": "byte order mark (U+FEFF)",
    "\u00a0": "non-breaking space (U+00A0)",
    "\u202f": "narrow no-break space (U+202F)",
    "\u200c": "zero-width non-joiner (U+200C)",
    "\u200d": "zero-width joiner (U+200D)",
    "\u2060": "word joiner (U+2060)",
}

CLK120_MESSAGE_PREFIX = (
    "URL contains invisible format characters that copy/paste tools insert "
    "and analytics tools treat as part of the host or UTM value"
)

_installed = False


def find_invisible_format_labels(text: str) -> tuple[str, ...]:
    """Return unique human labels for invisible format characters in *text*."""

    found: list[str] = []
    seen: set[str] = set()
    for char in text:
        label = INVISIBLE_FORMAT_CHARS.get(char)
        if label is None or char in seen:
            continue
        seen.add(char)
        found.append(label)
    return tuple(found)


def clk120_message(labels: tuple[str, ...]) -> str:
    listed = ", ".join(labels)
    return f"{CLK120_MESSAGE_PREFIX}: {listed}"


def attach_clk120(url: str, issues: list[Issue]) -> list[Issue]:
    """Prepend CLK120 when the raw string contains invisible format characters."""

    if any(issue.code == "CLK120" for issue in issues):
        return issues
    labels = find_invisible_format_labels(url)
    if not labels:
        return issues
    extra = Issue("CLK120", "error", clk120_message(labels), url=url)
    return [extra, *issues]


def install() -> None:
    """Wrap links.validate_url so CLK120 is kept even on CLK001 early returns.

    links.py is left unchanged so this change can land without replacing the
    23KB module (previous CLK120 branches truncated that file on upload).
    audit_urls looks up validate_url at call time, so the CLI and Action pick
    up CLK120 after package import.
    """

    global _installed
    if _installed:
        return

    from . import links

    original: Callable = links.validate_url

    def wrapped(url: str, convention: object) -> list[Issue]:
        return attach_clk120(url, original(url, convention))

    links.validate_url = wrapped  # type: ignore[method-assign]
    _installed = True
