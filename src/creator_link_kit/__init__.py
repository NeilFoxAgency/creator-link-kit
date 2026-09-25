"""Creator Link Kit package."""

from . import encoded_separators as _encoded_separators
from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .links import AuditResult, Issue, audit_urls, build_url
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

# Re-export the CLK119-aware validator installed on package import.
validate_url = _encoded_separators.validate_url_with_clk119

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
