"""Raw-string URL hygiene checks that must run before urlsplit."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .config import Convention
from .links import AuditResult, Issue, audit_urls as _audit_urls, validate_url as _validate_url

_DOUBLED_SCHEME = re.compile(r"^https?://https?://", re.IGNORECASE)


def raw_url_issues(url: str) -> list[Issue]:
    """Return CLK132/CLK133 issues for spreadsheet and concat paste failures."""

    issues: list[Issue] = []
    if any(ch.isspace() for ch in url):
        issues.append(
            Issue(
                "CLK132",
                "error",
                (
                    "URL contains whitespace (space, tab, newline, or Unicode "
                    "separator); paste and QR tools will split or encode the "
                    "link and attribution will be lost. Remove the whitespace "
                    "before publishing"
                ),
                url=url,
            )
        )
    if _DOUBLED_SCHEME.search(url.lstrip()) is not None:
        issues.append(
            Issue(
                "CLK133",
                "error",
                (
                    "URL starts with a doubled http(s) scheme "
                    "(for example https://https://); this usually comes from "
                    "concatenating a scheme onto an already-absolute URL. "
                    "Keep a single scheme"
                ),
                url=url,
            )
        )
    return issues


def validate_url(url: str, convention: Convention) -> list[Issue]:
    """Validate a URL, including raw-string hygiene that urlsplit would hide."""

    return raw_url_issues(url) + _validate_url(url, convention)


def audit_urls(urls: Iterable[str], convention: Convention) -> AuditResult:
    """Audit URLs with CLK132/CLK133 applied to each non-empty row."""

    result = _audit_urls(urls, convention)
    extra: list[Issue] = []
    for row, raw_url in enumerate(urls, start=1):
        url = raw_url.strip()
        if not url:
            continue
        extra.extend(issue.with_context(row=row, url=url) for issue in raw_url_issues(url))
    return AuditResult(checked=result.checked, issues=tuple(extra) + result.issues)
