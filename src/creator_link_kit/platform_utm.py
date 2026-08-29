"""Detect UTM parameters applied to creator-platform URLs.

Campaign operators often paste a YouTube, TikTok, Instagram, or X *video*
URL into a brief and add UTM tags. GA4 then attributes the platform host,
not the brand store. CLK003 already notes an unowned host; CLK124 names
the specific mistake so operators move tags onto the landing page.
"""

from __future__ import annotations

from .config import Convention, domain_is_owned

# Registrable roots only. Subdomains such as m.youtube.com and
# vm.tiktok.com match via suffix. Do not include generic shorteners here;
# those are a different class of defect.
PLATFORM_ROOTS = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "fb.com",
    "fb.watch",
    "linkedin.com",
)


def is_creator_platform_host(host: str) -> bool:
    """Return True if host is a known creator-platform domain."""

    normalized = (host or "").lower().rstrip(".")
    if not normalized:
        return False
    return any(
        normalized == root or normalized.endswith("." + root)
        for root in PLATFORM_ROOTS
    )


def platform_utm_message(host: str) -> str:
    return (
        f"UTM parameters are on creator-platform host {host!r}. "
        "Analytics will attribute the video or profile URL, not the brand "
        "landing page. Put the UTM tags on the shop or campaign destination "
        "and leave the platform URL untagged in the description."
    )


def should_flag_platform_utm(
    host: str,
    query: str,
    convention: Convention,
) -> bool:
    """True when a platform host carries UTM query keys and is not owned."""

    if not is_creator_platform_host(host):
        return False
    if "utm_" not in (query or "").lower():
        return False
    if convention.owned_domains and domain_is_owned(host, convention.owned_domains):
        return False
    return True
