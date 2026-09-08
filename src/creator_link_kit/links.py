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

_STANDARD_UTM_KEYS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
)

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

_UNRESOLVED_TEMPLATE = re.compile(
    r"(\{\{[^}]*\}\}"
    r"|\$\{[^}]*\}"
    r"|%\{[^}]*\}%"
    r"|\[\[[^\]]*\]\])"
)

_HTML_ENTITY_QUERY_MARKERS = (
    "&amp;",
    "&#38;",
    "&#x26;",
    "&AMP;",
)

_FRAGMENT_UTM_PAIR = re.compile(
    r"(?:^|[?#&])utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)

_GLUED_UTM_PAIR = re.compile(
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


@dataclass(frozen=True)
class AuditResult:
    checked: int
    issues: tuple[Issue, ...]

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def clean(self) -> int:
        bad_rows = {issue.row for issue in self.issues if issue.row is not None}
        return max(0, self.checked - len(bad_rows))
