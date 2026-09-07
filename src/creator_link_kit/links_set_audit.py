"""Placement-ID consistency checks and the audit_urls entrypoint."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention
from .links import AuditResult, Issue
from .links_audit import validate_url
from .links_set_run import (
    _campaign_id_consistency_issues,
    _canonical_link,
    _utm_params,
)
from .urls import authority_error as _authority_error


def _placement_consistency_issues(
    observations: list[tuple[int, str, str, str | None, str]],
) -> list[Issue]:
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
