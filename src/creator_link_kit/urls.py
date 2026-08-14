"""Shared URL authority validation and extraction helpers."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import SplitResult

# DNS label: letters/digits, optional interior hyphen; not empty.
_DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_MAX_HOSTNAME_LEN = 253

# Absolute http(s) URLs only. The match is deliberately conservative: it stops
# at whitespace, HTML angle brackets, and quotes. Sentence punctuation is
# trimmed after matching so pasted prose remains useful without inventing URLs.
_HTTP_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SIMPLE_TRAILING_PUNCT = ".,;:!?"
_PAIRED_PUNCT = (("(", ")"), ("[", "]"), ("{", "}"))


def _is_valid_hostname(host: str) -> bool:
    """Return True for a usable DNS name or IP literal."""

    if not host or len(host) > _MAX_HOSTNAME_LEN:
        return False
    if " " in host or "\t" in host or "_" in host:
        return False
    # Trailing dot is allowed in DNS but strip for validation.
    candidate = host.rstrip(".")
    if not candidate:
        return False
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        pass
    labels = candidate.split(".")
    if any(not label for label in labels):
        return False
    return all(_DNS_LABEL.fullmatch(label) for label in labels)


def authority_error(parsed: SplitResult) -> str | None:
    """Return a precise error for unsafe or malformed URL authorities."""

    if parsed.username is not None or parsed.password is not None:
        return "URL must not include embedded credentials"
    try:
        _ = parsed.port
    except ValueError as exc:
        return f"URL has an invalid port: {exc}"

    host = parsed.hostname
    if host is None or host == "":
        return "URL authority must include a hostname"
    if not _is_valid_hostname(host):
        return f"URL has a malformed hostname: {host!r}"
    return None


def _trim_trailing_url_punctuation(value: str) -> str:
    trimmed = value
    while trimmed:
        previous = trimmed
        trimmed = trimmed.rstrip(_SIMPLE_TRAILING_PUNCT)
        for opener, closer in _PAIRED_PUNCT:
            unmatched_closer = trimmed.count(closer) > trimmed.count(opener)
            if trimmed.endswith(closer) and unmatched_closer:
                trimmed = trimmed[:-1]
                break
        if trimmed == previous:
            break
    return trimmed


def extract_http_urls(text: str) -> list[str]:
    """Extract absolute http(s) URLs from free-form text in appearance order.

    Exact duplicates are retained so the audit layer can still report CLK005.
    Unmatched prose punctuation is removed, while balanced parentheses,
    brackets, and braces that are part of a URL are preserved.
    """

    found: list[str] = []
    for match in _HTTP_URL_RE.finditer(text):
        candidate = _trim_trailing_url_punctuation(match.group(0))
        if candidate:
            found.append(candidate)
    return found
