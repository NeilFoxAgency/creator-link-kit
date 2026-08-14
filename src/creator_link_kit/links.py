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

# HTML entity forms that appear when a real query separator (&) is copied from
# CMS/email HTML, Word, or a rendered page source. GA4 never sees the intended
# separate parameters because the URL is not decoded as HTML before use.
_HTML_ENTITY_QUERY_MARKERS = (
    "&amp;",
    "&#38;",
    "&#x26;",
    "&AMP;",
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

    # Scan the raw URL first. Numeric entities such as &#38; contain '#' and
    # would be treated as the start of a fragment by urlsplit, hiding the rest
    # of the query from parse_qsl. Named entities like &amp; stay in the query
    # string but still prevent proper UTM separation.
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

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    # Near-miss keys that look like UTMs but are not the canonical forms.
    # GA4 ignores unknown parameter names, so these produce silent data loss.
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


def _canonical_link(url: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if not parsed.netloc or _authority_error(parsed) is not None:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    utm_pairs = tuple(sorted((k, v) for k, v in pairs if k.startswith("utm_")))
    non_utm = urlencode(sorted((k, v) for k, v in pairs if not k.startswith("utm_")))
    destination = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", non_utm, "")
    )
    return destination, utm_pairs


def _utm_params(url: str) -> dict[str, str] | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if not parsed.netloc or _authority_error(parsed) is not None:
        return None
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    return {key: value for key, value in pairs if key.startswith("utm_")}


def _campaign_id_consistency_issues(
    observations: list[tuple[int, str, str, str]],
) -> list[Issue]:
    """Flag campaign-name and campaign-ID mismatches across an audit set."""

    if not observations:
        return []

    campaign_to_ids: dict[str, set[str]] = defaultdict(set)
    id_to_campaigns: dict[str, set[str]] = defaultdict(set)
    campaign_to_rows: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    id_to_rows: dict[str, list[tuple[int, str, str]]] = defaultdict(list)

    for row, url, campaign, utm_id in observations:
        campaign_to_ids[campaign].add(utm_id)
        id_to_campaigns[utm_id].add(campaign)
        campaign_to_rows[campaign].append((row, url, utm_id))
        id_to_rows[utm_id].append((row, url, campaign))

    issues: list[Issue] = []

    for campaign, ids in sorted(campaign_to_ids.items()):
        if len(ids) < 2:
            continue
        id_list = ", ".join(sorted(repr(value) for value in ids))
        for row, url, _utm_id in campaign_to_rows[campaign]:
            issues.append(
                Issue(
                    "CLK110",
                    "error",
                    (
                        f"utm_campaign {campaign!r} is paired with multiple "
                        f"utm_id values across this audit set ({id_list}); "
                        "GA4 campaign ID reporting will split"
                    ),
                    parameter="utm_id",
                    row=row,
                    url=url,
                )
            )

    for utm_id, campaigns in sorted(id_to_campaigns.items()):
        if len(campaigns) < 2:
            continue
        campaign_list = ", ".join(sorted(repr(value) for value in campaigns))
        for row, url, _campaign in id_to_rows[utm_id]:
            issues.append(
                Issue(
                    "CLK111",
                    "error",
                    (
                        f"utm_id {utm_id!r} is paired with multiple "
                        f"utm_campaign values across this audit set "
                        f"({campaign_list}); the same GA4 campaign ID must not "
                        "label different campaigns"
                    ),
                    parameter="utm_id",
                    row=row,
                    url=url,
                )
            )

    return issues


def _placement_consistency_issues(
    observations: list[tuple[int, str, str, str | None, str]],
) -> list[Issue]:
    """Flag placement IDs reused across campaigns or destinations in an audit set.

    When the convention maps stable placement_id values into utm_content, the same
    placement must not label different campaigns or different landing destinations.
    Reuse across platforms for the *same* campaign and destination is allowed.
    """

    if not observations:
        return []

    content_to_campaigns: dict[str, set[str]] = defaultdict(set)
    content_to_destinations: dict[str, set[str]] = defaultdict(set)
    content_to_rows: dict[str, list[tuple[int, str, str | None, str]]] = defaultdict(
        list
    )

    for row, url, content, campaign, destination in observations:
        if campaign:
            content_to_campaigns[content].add(campaign)
        content_to_destinations[content].add(destination)
        content_to_rows[content].append((row, url, campaign, destination))

    issues: list[Issue] = []

    for content, campaigns in sorted(content_to_campaigns.items()):
        if len(campaigns) < 2:
            continue
        campaign_list = ", ".join(sorted(repr(value) for value in campaigns))
        for row, url, _campaign, _destination in content_to_rows[content]:
            issues.append(
                Issue(
                    "CLK116",
                    "error",
                    (
                        f"utm_content {content!r} is paired with multiple "
                        f"utm_campaign values across this audit set "
                        f"({campaign_list}); a placement ID must identify one "
                        "sponsored asset under one campaign"
                    ),
                    parameter="utm_content",
                    row=row,
                    url=url,
                )
            )

    for content, destinations in sorted(content_to_destinations.items()):
        if len(destinations) < 2:
            continue
        already = {
            (issue.row, issue.url)
            for issue in issues
            if issue.code == "CLK116" and issue.parameter == "utm_content"
        }
        dest_list = ", ".join(sorted(repr(value) for value in destinations))
        for row, url, _campaign, _destination in content_to_rows[content]:
            if (row, url) in already:
                continue
            issues.append(
                Issue(
                    "CLK116",
                    "error",
                    (
                        f"utm_content {content!r} is paired with multiple "
                        f"destinations across this audit set ({dest_list}); "
                        "a placement ID must point at one landing destination"
                    ),
                    parameter="utm_content",
                    row=row,
                    url=url,
                )
            )

    return issues


def audit_urls(urls: Iterable[str], convention: Convention) -> AuditResult:
    issues: list[Issue] = []
    seen: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
    campaign_id_pairs: list[tuple[int, str, str, str]] = []
    placement_pairs: list[tuple[int, str, str, str | None, str]] = []
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
                        (
                            f"duplicates row {seen[canonical]}: same destination "
                            "and UTM values"
                        ),
                        row=row,
                        url=url,
                    )
                )
            else:
                seen[canonical] = row

        params = _utm_params(url)
        if params is not None:
            campaign = params.get("utm_campaign")
            utm_id = params.get("utm_id")
            if campaign and utm_id:
                campaign_id_pairs.append((row, url, campaign, utm_id))
            content = params.get("utm_content")
            if content:
                destination = "unknown"
                if canonical is not None:
                    destination = canonical[0]
                else:
                    try:
                        parsed = urlsplit(url)
                        if parsed.netloc and _authority_error(parsed) is None:
                            pairs = parse_qsl(parsed.query, keep_blank_values=True)
                            non_utm = urlencode(
                                sorted(
                                    (k, v) for k, v in pairs if not k.startswith("utm_")
                                )
                            )
                            destination = urlunsplit(
                                (
                                    parsed.scheme.lower(),
                                    parsed.netloc.lower(),
                                    parsed.path or "/",
                                    non_utm,
                                    "",
                                )
                            )
                    except ValueError:
                        pass
                placement_pairs.append((row, url, content, campaign, destination))

    issues.extend(_campaign_id_consistency_issues(campaign_id_pairs))
    issues.extend(_placement_consistency_issues(placement_pairs))
    return AuditResult(checked=checked, issues=tuple(issues))
