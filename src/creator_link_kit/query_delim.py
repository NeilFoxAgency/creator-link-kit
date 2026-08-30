"""CLK127: detect ';' or ',' used as UTM query delimiters."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlsplit

from .config import Convention
from .links import Issue, validate_url as _validate_url

_ALT_QUERY_DELIMITER = re.compile(
    r"[;,]utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)

_installed = False


def has_alt_utm_delimiter(url: str) -> bool:
    """Return True when UTM pairs are separated by ';' or ',' instead of '&'."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return bool(parsed.query and _ALT_QUERY_DELIMITER.search(parsed.query))


def validate_url(url: str, convention: Convention) -> list[Issue]:
    issues = list(_validate_url(url, convention))
    if has_alt_utm_delimiter(url) and not any(i.code == "CLK127" for i in issues):
        issues.append(
            Issue(
                "CLK127",
                "error",
                (
                    "UTM parameters are separated by ';' or ',' instead of '&'; "
                    "GA4 and url parsers only split on '&', so later campaign "
                    "dimensions are absorbed into the previous value. Replace "
                    "those separators with '&' before publishing"
                ),
                url=url,
            )
        )
        issues = [issue.with_context(url=url) for issue in issues]
    return issues


def install(target: Callable[..., list[Issue]] | None = None) -> None:
    """Wrap creator_link_kit.links.validate_url so CLI and audit see CLK127."""
    global _installed
    if _installed:
        return
    from . import links as links_mod

    wrapped = target or validate_url
    links_mod.validate_url = wrapped  # type: ignore[method-assign]
    _installed = True
