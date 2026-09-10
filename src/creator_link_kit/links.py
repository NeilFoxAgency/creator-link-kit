"""URL building and auditing rules."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import get_close_matches
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention, domain_is_owned
from .urls import authority_error as _authority_error

# Canonical UTM keys recognized by GA4 and most analytics tools.
# Typos (utm_souce, utm-source, UTM_Source) are ignored silently by GA4.
_STANDARD_UTM_KEYS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
)

# Case-insensitive exact matches for values that almost always indicate an
# unfilled template, CMS default, or programming null rather than a real
# campaign dimension. Keeping the set tight avoids false positives on
# legitimate short codes such as "yt" or "na" region tags when they appear
# only as substrings.
_PLACEHOLDER_UTM_VALUES = frozenset(
    {
        "null",
        "undefined",
        "none",
        "n/a",
        "na",
        "n.a.",
        "n.a",
        "nil",
        "test",
        "testing",
        "example",
        "sample",
        "placeholder",
        "xxx",
        "todo",
        "tbd",
        "default",
        "unknown",
        "notset",
        "not-set",
        "not_set",
        "(not set)",
        "(none)",
    }
)

# Common unresolved ad-platform / CMS template markers that ship as literal
# query values when a macro is never expanded. Matching is intentionally narrow
# so ordinary product SKUs and placement IDs are not false positives.
_UNRESOLVED_TEMPLATE = re.compile(
    r"(\{\{[^}]*\}\}"
    r"|\$\{[^}]*\}"
    r"|%\{[^}]*\}%"
    r"|\[\[[^\]]*\]\])"
)

# HTML entity forms that appear when a real query separator (&) is copied from
# CMS/email HTML, Word, or a rendered page source. GA4 never sees the intended
# separate parameters because the URL is not decoded as HTML before use.
_HTML_ENTITY_QUERY_MARKERS = (
    "&amp;",
    "&#38;",
    "&#x26;",
    "&AMP;",
)

# UTM-looking key=value pairs that were placed in the fragment. Anything after
# # is not sent to the server or to GA4 measurement; these links look tracked
# but attribute as direct/none.
_FRAGMENT_UTM_PAIR = re.compile(
    r"(?:^|[?#&])utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)

# Encoded ampersands that glue a later UTM pair into an earlier value.
# parse_qsl and GA4 split only on a raw '&', so "%26utm_medium=..." is one
# source value rather than a separate medium parameter.
_ENCODED_UTM_SEPARATOR = re.compile(r"%26utm_", re.IGNORECASE)
_GLUED_UTM_IN_VALUE = re.compile(
    r"(?:[?&]|%26)utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    parameter: str | None = None
    row: int | None = None
    url: str | None = None

    def with_context(self, *, row: int | None = None, url: str | None = None) -> Issue:
        return Issue(
            code=self.code,
            severity=self.severity,
            message=self.message,
            parameter=self.parameter,
            row=row if row is not None else self.row,
            url=url if url is not None else self.url,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "url": self.url,
            "code": self.code,
            "severity": self.severity,
            "parameter": self.parameter,
            "message": self.message,
        }
