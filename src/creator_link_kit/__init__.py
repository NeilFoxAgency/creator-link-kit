"""Creator Link Kit package."""

from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .encoded_separators import attach_encoded_separator_check
from .links import AuditResult, Issue, audit_urls, build_url, validate_url
from .links import validate_url as _validate_url
from . import links as _links
from .models import (
    AuditIssue,
    LinkAudit,
    LinkIdentifiers,
    LinkProvider,
    LinkProvisionRequest,
    LinkSpecification,
    ProvisionedLink,
)
from .spec import build_link_specification

validate_url = attach_encoded_separator_check(_validate_url)
_links.validate_url = validate_url

__all__ = [
    "AuditIssue",
    "AuditResult",
    "ConfigError",
    "Convention",
    "Issue",
    "LinkAudit",
    "LinkIdentifiers",
    "LinkProvider",
    "LinkProvisionRequest",
    "LinkSpecification",
    "ProvisionedLink",
    "audit_urls",
    "build_link_specification",
    "build_url",
    "convention_fingerprint",
    "load_convention",
    "validate_url",
]

__version__ = "0.2.0"
