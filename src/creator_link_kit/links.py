"""URL building and auditing rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from difflib import get_close_matches
import re
from typing import Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    parameter: str | None = None
    row: int | None = None
    url: str | None = None

    def with_context(self, *, row: int | None = None, url: str | None = None) -> "Issue":
        return Issue(
            code=self.code,
            severity=self.severity,
            message=self.message,
            parameter=self.parameter,
            row=row if row is not None else self.row,
            url=url if url is not None else self.url,
        )


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


def _domain_is_owned(host: str, owned_domains: tuple[str, ...]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in owned_domains)


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
            issues.append(
                Issue("CLK107", "warning", "value is not lowercase", key)
            )
        if rule.allowed and value not in rule.allowed:
            case_match = next(
                (candidate for candidate in rule.allowed if candidate.lower() == value.lower()),
                None,
            )
            if case_match is not None:
                issues.append(
                    Issue(
                        "CLK105",
                        "error",
                        f"{value!r} differs from allowed value {case_match!r} only by case",
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
    if parsed.scheme == "http":
        issues.append(Issue("CLK002", "warning", "URL uses http instead of https"))
    if convention.owned_domains and not _domain_is_owned(
        parsed.hostname or "", convention.owned_domains
    ):
        issues.append(
            Issue(
                "CLK003",
                "warning",
                f"destination host {parsed.hostname!r} is outside owned_domains",
            )
        )

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
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

    # The last value mirrors how many analytics systems resolve repeated keys,
    # while CLK103 still makes the ambiguity a hard error.
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
        raise ValueError("; ".join(f"{i.code} {i.parameter}: {i.message}" for i in errors))

    query = urlencode(existing_pairs + list(merged.items()), doseq=True)
    result = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))
    final_errors = [
        issue for issue in validate_url(result, convention) if issue.severity == "error"
    ]
    if final_errors:
        raise ValueError("; ".join(f"{i.code}: {i.message}" for i in final_errors))
    return result


def _canonical_link(url: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if not parsed.netloc:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    utm_pairs = tuple(sorted((k, v) for k, v in pairs if k.startswith("utm_")))
    non_utm = urlencode(sorted((k, v) for k, v in pairs if not k.startswith("utm_")))
    destination = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", non_utm, "")
    )
    return destination, utm_pairs


def audit_urls(urls: Iterable[str], convention: Convention) -> AuditResult:
    issues: list[Issue] = []
    seen: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
    checked = 0
    for row, raw_url in enumerate(urls, start=1):
        url = raw_url.strip()
        if not url:
            continue
        checked += 1
        row_issues = validate_url(url, convention)
        issues.extend(issue.with_context(row=row, url=url) for issue in row_issues)
        canonical = _canonical_link(url)
        if canonical is not None:
            if canonical in seen:
                issues.append(
                    Issue(
                        "CLK005",
                        "error",
                        f"duplicates row {seen[canonical]}: same destination and UTM values",
                        row=row,
                        url=url,
                    )
                )
            else:
                seen[canonical] = row
    return AuditResult(checked=checked, issues=tuple(issues))
