"""URL building and single-link validation rules."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import get_close_matches
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention, domain_is_owned
from .query_shape import CLK119_CODE, CLK119_MESSAGE, has_extra_question_mark
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


def validate_url(url: str, convention: Convention) -> list[Issue]:
    issues: list[Issue] = []

    for marker in _HTML_ENTITY_QUERY_MARKERS:
        if marker in url:
            issues.append(
                Issue(
                    "CLK117",
                    "error",
                    (
                        f"URL contains HTML entity {marker!r}; "
                        "UTM parameters after this point are not separated "
                        "for GA4 and similar tools. Replace with a bare '&'"
                    ),
                    url=url,
                )
            )
            break

    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        return [Issue("CLK001", "error", f"URL cannot be parsed: {exc}", url=url)]

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return [
            Issue(
                "CLK001",
                "error",
                "URL must be an absolute http or https URL",
                url=url,
            )
        ]
    authority_error = _authority_error(parsed)
    if authority_error is not None:
        return [Issue("CLK001", "error", authority_error, url=url)]
    if parsed.scheme == "http":
        issues.append(Issue("CLK002", "warning", "URL uses http instead of https"))
    if convention.owned_domains and not domain_is_owned(
        parsed.hostname or "", convention.owned_domains
    ):
        severity = "error" if convention.mode == "production" else "warning"
        issues.append(
            Issue(
                "CLK003",
                severity,
                f"destination host {parsed.hostname!r} is outside owned_domains",
            )
        )

    if has_extra_question_mark(url):
        issues.append(
            Issue(
                CLK119_CODE,
                "error",
                CLK119_MESSAGE,
                url=url,
            )
        )

    if parsed.fragment and _FRAGMENT_UTM_PAIR.search(parsed.fragment):
        issues.append(
            Issue(
                "CLK118",
                "error",
                (
                    "UTM parameters appear in the URL fragment (#...); "
                    "browsers and GA4 do not send the fragment to the server, "
                    "so attribution is lost. Move UTM parameters into the "
                    "query string before the fragment"
                ),
                url=url,
            )
        )

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    for key, _value in pairs:
        normalized = key.lower().replace("-", "_")
        if key in _STANDARD_UTM_KEYS:
            continue
        if normalized in _STANDARD_UTM_KEYS or (
            key.lower().startswith("utm")
            and get_close_matches(normalized, _STANDARD_UTM_KEYS, n=1, cutoff=0.75)
        ):
            suggestion = get_close_matches(
                normalized, list(_STANDARD_UTM_KEYS), n=1, cutoff=0.5
            )
            hint = f"; did you mean {suggestion[0]!r}?" if suggestion else ""
            issues.append(
                Issue(
                    "CLK114",
                    "error",
                    (
                        f"query parameter {key!r} looks like a misspelled UTM key"
                        f"{hint}; GA4 ignores unknown parameter names"
                    ),
                    parameter=key,
                )
            )

    utm_pairs = [(key, value) for key, value in pairs if key.startswith("utm_")]
    if not utm_pairs:
        issues.append(Issue("CLK004", "warning", "URL has no UTM parameters"))

    counts = Counter(key for key, _ in utm_pairs)
    for key, count in counts.items():
        if count > 1:
            issues.append(
                Issue(
                    "CLK103",
                    "error",
                    f"parameter appears {count} times in the query string",
                    key,
                )
            )

    params = {key: value for key, value in utm_pairs}
    issues.extend(validate_params(params, convention))
    return [issue.with_context(url=url) for issue in issues]


def build_url(
    base_url: str,
    params: Mapping[str, str],
    convention: Convention,
) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute http or https URL")
    authority_error = _authority_error(parsed)
    if authority_error is not None:
        raise ValueError(authority_error)

    existing_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    existing_keys = {key for key, _ in existing_pairs}
    merged = dict(convention.defaults)
    merged.update(params)
    collisions = sorted(key for key in merged if key in existing_keys)
    if collisions:
        raise ValueError(
            "refusing to double-tag existing parameter(s): " + ", ".join(collisions)
        )

    issues = validate_params(merged, convention)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ValueError(
            "; ".join(f"{i.code} {i.parameter}: {i.message}" for i in errors)
        )

    query = urlencode(existing_pairs + list(merged.items()), doseq=True)
    result = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
    )
    final_errors = [
        issue for issue in validate_url(result, convention) if issue.severity == "error"
    ]
    if final_errors:
        raise ValueError("; ".join(f"{i.code}: {i.message}" for i in final_errors))
    return result
