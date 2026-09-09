"""CLK119: detect percent-encoded UTM query separators."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .links import Issue

_ENCODED_UTM_SEPARATOR_IN_VALUE = re.compile(
    r"(?:[?&]|%26)utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


def encoded_separator_issue(url: str, raw_query: str, pairs: Iterable[tuple[str, str]]) -> Issue | None:
    if "%26utm_" in raw_query.lower() or any(
        _ENCODED_UTM_SEPARATOR_IN_VALUE.search(value) for _key, value in pairs
    ):
        return Issue(
            "CLK119",
            "error",
            (
                "Query string contains a percent-encoded '&' that glues a "
                "later UTM pair into an earlier value; parse_qsl and GA4 "
                "split only on a raw '&'. Replace '%26' with '&' before "
                "publishing"
            ),
            url=url,
        )
    return None
