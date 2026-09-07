"""Creator Link Kit package."""

from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .links import AuditResult, Issue, audit_urls, build_url, validate_url
from .platform_utm import install_clk126
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

install_clk126()
from .links import validate_url as validate_url  # re-bind wrapped checker

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
