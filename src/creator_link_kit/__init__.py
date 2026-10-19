"""Creator Link Kit package."""

from . import encoded_separators as _encoded_separators  # noqa: F401  # side effect: installs CLK119 on links.validate_url
from . import links as _links
from .clk131 import install as _install_clk131
from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .links import AuditResult, Issue, build_url
from .models import (
    AuditIssue,
    LinkAudit,
    LinkIdentifiers,
    LinkProvider,
    LinkProvisionRequest,
    LinkSpecification,
    ProvisionedLink,
)
from .raw_hygiene import audit_urls, validate_url
from .spec import build_link_specification

_install_clk131(_links)
from .links import validate_params  # noqa: E402  # re-bind after CLK131 wrap

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
    "validate_params",
    "validate_url",
]

__version__ = "0.2.0"
