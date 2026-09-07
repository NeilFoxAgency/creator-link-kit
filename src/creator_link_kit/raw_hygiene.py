"""Raw-string URL hygiene checks that must run before urlsplit."""

from __future__ import annotations

import re

_DOUBLED_SCHEME = re.compile(r"^https?://https?://", re.IGNORECASE)


def raw_url_issues(url: str, issue_cls: type) -> list[object]:
    """Return CLK132/CLK133 issues for spreadsheet and concat paste failures."""

    issues: list[object] = []
    if any(ch.isspace() for ch in url):
        issues.append(
            issue_cls(
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
            issue_cls(
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
