"""Shared URL authority validation and extraction helpers."""

from __future__ import annotations

import re
from urllib.parse import SplitResult

# Absolute http(s) URLs only. Trailing sentence punctuation is stripped after
# the match so pasted prose like "...here: https://x.example/y)." works.
_HTTP_URL_RE = re.compile(r"https?://[^\s<>\"'\]\)}\]]+", re.IGNORECASE)
_TRAILING_PUNCT = ")]}>.,;:!?'\""


def authority_error(parsed: SplitResult) -> str | None:
    """Return a precise error for unsafe or malformed URL authorities."""

    if parsed.username is not None or parsed.password is not None:
        return "URL must not include embedded credentials"
    try:
        _ = parsed.port
    except ValueError as exc:
        return f"URL has an invalid port: {exc}"
    return None


def extract_http_urls(text: str) -> list[str]:
    """Extract absolute http(s) URLs from free-form text.

    Used by ``clk audit`` when the input is not a CSV roster of links. Lines
    that are already a single bare URL are kept as-is. Prose lines may yield
    zero or more URLs. Order of first appearance is preserved; exact duplicates
    are kept so audit still reports CLK005 when the same link appears twice.
    """

    found: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"https?://\S+", line, flags=re.IGNORECASE):
            found.append(line.rstrip(_TRAILING_PUNCT))
            continue
        for match in _HTTP_URL_RE.finditer(line):
            candidate = match.group(0).rstrip(_TRAILING_PUNCT)
            if candidate:
                found.append(candidate)
    return found
