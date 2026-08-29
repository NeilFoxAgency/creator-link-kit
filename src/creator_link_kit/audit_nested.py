"""Apply CLK123 nested-tracking findings onto audit results."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import parse_qsl, urlsplit

from .config import Convention
from .links import AuditResult, Issue, audit_urls as _audit_urls
from .nested import find_nested_tracking


def audit_urls(urls: Iterable[str], convention: Convention) -> AuditResult:
    materialized = list(urls)
    result = _audit_urls(materialized, convention)
    extra: list[Issue] = []
    for row, raw_url in enumerate(materialized, start=1):
        url = raw_url.strip()
        if not url:
            continue
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        for parameter, message in find_nested_tracking(pairs):
            extra.append(
                Issue(
                    "CLK123",
                    "error",
                    message,
                    parameter=parameter,
                    row=row,
                    url=url,
                )
            )
    if not extra:
        return result
    return AuditResult(checked=result.checked, issues=result.issues + tuple(extra))
