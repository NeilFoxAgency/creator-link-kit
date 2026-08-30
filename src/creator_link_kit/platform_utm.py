"""Detect UTM parameters attached to video / social platform hosts.

Creator briefs and YouTube descriptions often tag the *watch page* instead
of the brand landing page:

    https://youtu.be/dQw4w9WgXcQ?utm_source=youtube&utm_campaign=cmp-spring

GA4 for the brand never sees those pairs. YouTube, TikTok, Instagram, and
similar hosts either ignore unknown query keys or record them against the
platform property. Attribution then looks like the campaign never shipped.

CLK126 is independent of CLK003 (owned-domain policy) and of CLK125
(public shortener hosts). A platform host listed in owned_domains is treated
as first-party and is not flagged.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

from .config import domain_is_owned

# Video and social *roots*. Subdomains match (e.g. www.youtube.com, m.tiktok.com).
# Keep this list conservative: only hosts that routinely appear as mistaken
# campaign destinations in creator briefs. Do not include generic shorteners
# (those belong to CLK125).
PLATFORM_ROOTS: tuple[str, ...] = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "tiktok.com",
    "instagram.com",
    "instagr.am",
    "facebook.com",
    "fb.com",
    "fb.watch",
    "twitter.com",
    "x.com",
    "twitch.tv",
    "vimeo.com",
    "snapchat.com",
    "pinterest.com",
    "reddit.com",
)

_INSTALLED = False


def is_platform_host(host: str) -> bool:
    """Return True when host is a known video/social platform or a subdomain."""

    normalized = (host or "").lower().rstrip(".")
    if not normalized:
        return False
    return any(
        normalized == root or normalized.endswith("." + root) for root in PLATFORM_ROOTS
    )


def should_flag_platform_utm(
    url: str,
    *,
    owned_domains: tuple[str, ...] = (),
) -> bool:
    """Return True when the URL puts UTM keys on a third-party platform host."""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = parsed.hostname or ""
    if not is_platform_host(host):
        return False
    if owned_domains and domain_is_owned(host, owned_domains):
        return False
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    return any(key.lower().startswith("utm_") for key, _ in pairs)


def install_clk126() -> None:
    """Wrap links.validate_url so CLK126 is visible on every audit path."""

    global _INSTALLED
    if _INSTALLED:
        return

    from . import links

    original = links.validate_url

    def validate_url_with_clk126(url: str, convention):
        issues = original(url, convention)
        if any(issue.code == "CLK126" for issue in issues):
            return issues
        owned = getattr(convention, "owned_domains", ()) or ()
        if not should_flag_platform_utm(url, owned_domains=tuple(owned)):
            return issues
        try:
            host = urlsplit(url).hostname or ""
        except ValueError:
            host = ""
        issues.append(
            links.Issue(
                "CLK126",
                "error",
                (
                    f"UTM parameters are attached to video/platform host "
                    f"{host!r}; platforms do not forward those keys to the "
                    "brand landing page, so GA4 never sees the campaign. "
                    "Put UTMs on the owned destination URL instead"
                ),
                url=url,
            )
        )
        return issues

    links.validate_url = validate_url_with_clk126  # type: ignore[method-assign]
    _INSTALLED = True
