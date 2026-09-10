"""CLK119: percent-encoded UTM separators that glue later pairs."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

from .links import Issue

_ENCODED_UTM_SEPARATOR = re.compile(r"%26utm_", re.IGNORECASE)
_GLUED_UTM_IN_VALUE = re.compile(
    r"(?:[?&]|%26)utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


def encoded_separator_issue(url: str) -> Issue | None:
    """Return CLK119 when %26 glued a later UTM pair into an earlier value."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if _ENCODED_UTM_SEPARATOR.search(parsed.query) or any(
        _GLUED_UTM_IN_VALUE.search(value) for _key, value in pairs
    ):
        return Issue(
            "CLK119",
            "error",
            (
                "query string contains a percent-encoded '&' (%26) that "
                "glues a later UTM pair into an earlier value; GA4 and "
                "parse_qsl split only on a raw '&'. Replace '%26utm_' "
                "with '&utm_'"
            ),
            url=url,
        )
    return None


def attach_encoded_separator_check(validate_url):
    """Wrap validate_url so CLK119 is appended after the existing checks."""

    def wrapped(url: str, convention):
        issues = list(validate_url(url, convention))
        extra = encoded_separator_issue(url)
        if extra is not None and not any(issue.code == "CLK119" for issue in issues):
            issues.append(extra.with_context(url=url))
        return issues

    return wrapped
