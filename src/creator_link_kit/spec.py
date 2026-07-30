"""Machine-readable link specification generation."""

from __future__ import annotations

from collections.abc import Mapping

from .config import Convention
from .links import build_url, validate_url
from .models import AuditIssue, LinkAudit, LinkIdentifiers, LinkSpecification


def _params_with_identifier_defaults(
    params: Mapping[str, str],
    convention: Convention,
    identifiers: LinkIdentifiers,
) -> dict[str, str]:
    effective = dict(params)
    alignments = (
        ("utm_id", identifiers.campaign_id, "campaign_id"),
        ("utm_content", identifiers.placement_id, "placement_id"),
    )
    for parameter, identifier, label in alignments:
        if identifier is None:
            continue
        current = effective.get(parameter)
        if current is not None and current != identifier:
            raise ValueError(
                f"{parameter} {current!r} does not match {label} {identifier!r}"
            )
        if parameter in convention.parameters:
            effective.setdefault(parameter, identifier)
    return effective


def build_link_specification(
    original_destination: str,
    params: Mapping[str, str],
    convention: Convention,
    *,
    identifiers: LinkIdentifiers | None = None,
) -> LinkSpecification:
    """Build, audit, and serialize the provenance of one campaign link."""

    supplied_identifiers = identifiers or LinkIdentifiers()
    resolved_identifiers = LinkIdentifiers(
        brand_id=supplied_identifiers.brand_id,
        campaign_id=supplied_identifiers.campaign_id or params.get("utm_id"),
        creator_id=supplied_identifiers.creator_id,
        placement_id=(supplied_identifiers.placement_id or params.get("utm_content")),
    )
    effective_params = _params_with_identifier_defaults(
        params, convention, resolved_identifiers
    )
    generated_destination = build_url(
        original_destination,
        effective_params,
        convention,
    )
    issues = validate_url(generated_destination, convention)
    audit = LinkAudit(tuple(AuditIssue.from_issue(issue) for issue in issues))
    return LinkSpecification(
        original_destination=original_destination,
        generated_destination=generated_destination,
        identifiers=resolved_identifiers,
        config_version=convention.version,
        audit=audit,
    )
