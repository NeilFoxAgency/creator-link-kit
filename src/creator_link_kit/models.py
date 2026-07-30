"""Provider-neutral models for governed creator campaign links.

These models intentionally describe only link provisioning. They do not include
provider credentials, commerce events, orders, customers, or payment data.
Hosted provider adapters belong in a separate private service.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

IDENTIFIER_FIELDS = ("brand_id", "campaign_id", "creator_id", "placement_id")


def _clean_optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string or None")
    cleaned = value.strip()
    return cleaned or None


def _absolute_http_url(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty URL")
    cleaned = value.strip()
    try:
        parsed = urlsplit(cleaned)
    except ValueError as exc:
        raise ValueError(f"{label} cannot be parsed: {exc}") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute http or https URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{label} must not include embedded credentials")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} has an invalid port: {exc}") from exc
    return cleaned


@dataclass(frozen=True)
class LinkIdentifiers:
    """Stable agency identifiers associated with one creator placement."""

    brand_id: str | None = None
    campaign_id: str | None = None
    creator_id: str | None = None
    placement_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in IDENTIFIER_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _clean_optional_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        columns: Mapping[str, str] | None = None,
    ) -> "LinkIdentifiers":
        """Read only the four approved identifier fields from a row mapping.

        Unrelated columns are deliberately ignored so link specifications never
        copy contact details, secrets, order data, or arbitrary roster content.
        """

        column_names = {field_name: field_name for field_name in IDENTIFIER_FIELDS}
        if columns:
            unknown = sorted(set(columns) - set(IDENTIFIER_FIELDS))
            if unknown:
                raise ValueError(
                    "unknown identifier field(s): " + ", ".join(unknown)
                )
            column_names.update(columns)
        extracted: dict[str, str | None] = {}
        for field_name, column_name in column_names.items():
            if not isinstance(column_name, str) or not column_name.strip():
                raise ValueError(
                    f"column name for {field_name} must be a non-empty string"
                )
            raw = values.get(column_name)
            if raw is not None and not isinstance(raw, str):
                raise TypeError(f"{column_name} must contain a string or None")
            extracted[field_name] = raw
        return cls(**extracted)

    def as_dict(self) -> dict[str, str | None]:
        return {
            field_name: getattr(self, field_name)
            for field_name in IDENTIFIER_FIELDS
        }


@dataclass(frozen=True)
class AuditIssue:
    """Serializable representation of a validation issue."""

    code: str
    severity: str
    message: str
    parameter: str | None = None
    row: int | None = None
    url: str | None = None

    @classmethod
    def from_issue(cls, issue: Any) -> "AuditIssue":
        return cls(
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
            parameter=issue.parameter,
            row=issue.row,
            url=issue.url,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "parameter": self.parameter,
            "row": self.row,
            "url": self.url,
        }


@dataclass(frozen=True)
class LinkAudit:
    """Audit result embedded in a machine-readable link specification."""

    issues: tuple[AuditIssue, ...] = ()

    @property
    def errors(self) -> tuple[AuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[AuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class LinkSpecification:
    """Portable record of how one governed campaign link was produced."""

    original_destination: str
    generated_destination: str
    identifiers: LinkIdentifiers
    config_version: int
    audit: LinkAudit
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "original_destination",
            _absolute_http_url(self.original_destination, "original_destination"),
        )
        object.__setattr__(
            self,
            "generated_destination",
            _absolute_http_url(self.generated_destination, "generated_destination"),
        )
        if not isinstance(self.identifiers, LinkIdentifiers):
            raise TypeError("identifiers must be LinkIdentifiers")
        if not isinstance(self.audit, LinkAudit):
            raise TypeError("audit must be LinkAudit")
        if not isinstance(self.config_version, int) or self.config_version < 1:
            raise ValueError("config_version must be a positive integer")
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive integer")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "config_version": self.config_version,
            "original_destination": self.original_destination,
            "generated_destination": self.generated_destination,
            "ids": self.identifiers.as_dict(),
            "audit": self.audit.as_dict(),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        separators = (",", ":") if indent is None else None
        return json.dumps(
            self.as_dict(),
            indent=indent,
            separators=separators,
            sort_keys=True,
        )


@dataclass(frozen=True)
class LinkProvisionRequest:
    """Provider-neutral request consumed by a private link adapter."""

    destination_url: str
    identifiers: LinkIdentifiers
    slug: str | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "destination_url",
            _absolute_http_url(self.destination_url, "destination_url"),
        )
        if not isinstance(self.identifiers, LinkIdentifiers):
            raise TypeError("identifiers must be LinkIdentifiers")
        object.__setattr__(self, "slug", _clean_optional_text(self.slug, "slug"))
        if isinstance(self.tags, str):
            raise ValueError("tags must be an iterable of non-empty strings")
        normalized_tags: list[str] = []
        for tag in self.tags:
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError("tags must contain non-empty strings")
            cleaned = tag.strip()
            if cleaned not in normalized_tags:
                normalized_tags.append(cleaned)
        object.__setattr__(self, "tags", tuple(normalized_tags))

    @classmethod
    def from_specification(
        cls,
        specification: LinkSpecification,
        *,
        slug: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> "LinkProvisionRequest":
        if not specification.audit.valid:
            raise ValueError("cannot provision a link specification with audit errors")
        if specification.identifiers.placement_id is None:
            raise ValueError("placement_id is required for managed link provisioning")
        return cls(
            destination_url=specification.generated_destination,
            identifiers=specification.identifiers,
            slug=slug,
            tags=tags,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "destination_url": self.destination_url,
            "ids": self.identifiers.as_dict(),
            "slug": self.slug,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class ProvisionedLink:
    """Provider-neutral response returned by a private link adapter."""

    provider: str
    provider_link_id: str
    tracking_url: str
    destination_url: str
    identifiers: LinkIdentifiers

    def __post_init__(self) -> None:
        provider = _clean_optional_text(self.provider, "provider")
        provider_link_id = _clean_optional_text(
            self.provider_link_id, "provider_link_id"
        )
        if provider is None or provider_link_id is None:
            raise ValueError("provider and provider_link_id are required")
        if not isinstance(self.identifiers, LinkIdentifiers):
            raise TypeError("identifiers must be LinkIdentifiers")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "provider_link_id", provider_link_id)
        object.__setattr__(
            self,
            "tracking_url",
            _absolute_http_url(self.tracking_url, "tracking_url"),
        )
        object.__setattr__(
            self,
            "destination_url",
            _absolute_http_url(self.destination_url, "destination_url"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "provider_link_id": self.provider_link_id,
            "tracking_url": self.tracking_url,
            "destination_url": self.destination_url,
            "ids": self.identifiers.as_dict(),
        }


class LinkProvider(Protocol):
    """Interface implemented by provider adapters in a private service."""

    def provision(self, request: LinkProvisionRequest) -> ProvisionedLink:
        """Create or retrieve one tracked link idempotently."""
        ...
