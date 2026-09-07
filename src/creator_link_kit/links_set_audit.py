"""Audit-set consistency rules (CLK005/110/111/116)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention
from .links_audit import validate_url
from .links_set import _canonical_link, _utm_params
from .links_validate import AuditResult, Issue
from .urls import authority_error as _authority_error


def _campaign_id_consistency_issues(
    observations: list[tuple[int, str, str, str]],
) -> list[Issue]:
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
