"""Cross-link audit set checks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention
from .links_audit import validate_url
from .links_validate import AuditResult, Issue
from .urls import authority_error as _authority_error


def _canonical_link(url: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if not parsed.netloc or _authority_error(parsed) is not None:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    utm_pairs = tuple(sorted((k, v) for k, v in pairs if k.startswith("utm_")))
    non_utm = urlencode(sorted((k, v) for k, v in pairs if not k.startswith("utm_")))
    destination = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", non_utm, "")
    )
    return destination, utm_pairs


def _utm_params(url: str) -> dict[str, str] | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if not parsed.netloc or _authority_error(parsed) is not None:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    return {key: value for key, value in pairs if key.startswith("utm_")}
