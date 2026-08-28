"""URL building and auditing rules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import get_close_matches

from .config import Convention
from .invisible import first_invisible_label

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


def validate_params(
    params: Mapping[str, str],
    convention: Convention,
    *,
    require_all: bool = True,
) -> list[Issue]:
    issues: list[Issue] = []

    if require_all:
        for key in convention.required:
            if key not in params:
                issues.append(
                    Issue("CLK102", "error", "required parameter is missing", key)
                )

    for key, value in params.items():
        invisible = first_invisible_label(key) or first_invisible_label(value)
        if invisible is not None:
            issues.append(
                Issue(
                    "CLK121",
                    "error",
                    (
                        f"parameter contains invisible or format-control "
                        f"character {invisible}; GA4 treats it as a distinct "
                        "dimension. Remove zero-width, NBSP, BOM, and control "
                        "characters before publishing"
                    ),
                    key,
                )
            )
        if key.startswith("utm_") and key not in convention.parameters:
            issues.append(
                Issue("CLK101", "warning", "UTM parameter has no governing rule", key)
            )
            continue
        rule = convention.parameters.get(key)
        if rule is None:
            continue
        if value == "":
            issues.append(Issue("CLK109", "error", "value is empty", key))
            continue
        if value.strip() == "":
            issues.append(Issue("CLK113", "error", "value is whitespace-only", key))
            continue
        if value != value.strip():
            issues.append(
                Issue(
                    "CLK113",
                    "error",
                    "value has leading or trailing whitespace",
                    key,
                )
            )
        if _UNRESOLVED_TEMPLATE.search(value) is not None:
            issues.append(
                Issue(
                    "CLK112",
                    "error",
                    (
                        f"{value!r} contains an unresolved template placeholder; "
                        "expand the macro before publishing or the literal "
                        "placeholder will appear in analytics"
                    ),
                    key,
                )
            )
        if value.strip().lower() in _PLACEHOLDER_UTM_VALUES:
            issues.append(
                Issue(
                    "CLK115",
                    "error",
                    (
                        f"{value!r} is a reserved or placeholder UTM value "
                        "and will pollute analytics"
                    ),
                    key,
                )
            )
            continue
        if len(value) > convention.max_value_length:
            issues.append(
                Issue(
                    "CLK108",
                    "error",
                    f"value exceeds {convention.max_value_length} characters",
                    key,
                )
            )
        if convention.casing == "lowercase" and value != value.lower():
            issues.append(Issue("CLK107", "warning", "value is not lowercase", key))
        if rule.allowed and value not in rule.allowed:
            case_match = next(
                (
                    candidate
                    for candidate in rule.allowed
                    if candidate.lower() == value.lower()
                ),
                None,
            )
            if case_match is not None:
                issues.append(
                    Issue(
                        "CLK105",
                        "error",
                        (
                            f"{value!r} differs from allowed value "
                            f"{case_match!r} only by case"
                        ),
                        key,
                    )
                )
            else:
                close = get_close_matches(value, rule.allowed, n=1, cutoff=0.55)
                suggestion = f"; did you mean {close[0]!r}?" if close else ""
                issues.append(
                    Issue(
                        "CLK104",
                        "error",
                        f"{value!r} is not in the allowlist{suggestion}",
                        key,
                    )
                )
        if rule.pattern and re.fullmatch(rule.pattern, value) is None:
            issues.append(
                Issue(
                    "CLK106",
                    "error",
                    f"{value!r} does not match required pattern {rule.pattern!r}",
                    key,
                )
            )
    return issues
