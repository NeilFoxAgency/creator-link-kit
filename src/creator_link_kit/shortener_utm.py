"""Detect UTM parameters attached to public link-shortener hosts.

Creator briefs often paste a Bitly, t.co, or Amazon short link and then add
UTM pairs onto *that* host. Many shorteners strip unknown query parameters, or
they never forward them to the brand landing page. GA4 then records the
shortener hostname (or nothing) instead of the shop destination.

CLK125 is independent of CLK003 (owned-domain policy) and of platform-host
checks that target YouTube/TikTok video URLs. A shortener listed in
owned_domains is treated as first-party and is not flagged.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

from .config import domain_is_owned

# Public shortener *roots*. Subdomains match (e.g. foo.bit.ly).
# Keep this list conservative: only well-known redirectors that routinely
# appear in creator descriptions. Do not include first-party shop domains or
# video platforms (youtu.be belongs with platform-host rules).
SHORTENER_ROOTS: tuple[str, ...] = (
    "bit.ly",
    "bitly.com",
    "j.mp",
    "t.co",
    "tinyurl.com",
    "tiny.cc",
    "tiny.one",
    "ow.ly",
    "buff.ly",
    "lnkd.in",
    "is.gd",
    "v.gd",
    "rebrand.ly",
    "cutt.ly",
    "shorturl.at",
    "goo.gl",
    "t.ly",
    "trib.al",
    "rb.gy",
    "amzn.to",
    "a.co",
)

_INSTALLED = False


def is_shortener_host(host: str) -> bool:
    """Return True when host is a known public shortener or a subdomain of one."""

    normalized = (host or "").lower().rstrip(".")
    if not normalized:
        return False
    return any(
        normalized == root or normalized.endswith("." + root) for root in SHORTENER_ROOTS
    )


def should_flag_shortener_utm(
    url: str,
    *,
    owned_domains: tuple[str, ...] = (),
) -> bool:
    """Return True when the URL puts UTM keys on a third-party shortener host."""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = parsed.hostname or ""
    if not is_shortener_host(host):
        return False
    if owned_domains and domain_is_owned(host, owned_domains):
        return False
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    return any(key.lower().startswith("utm_") for key, _ in pairs)


def install_clk125() -> None:
    """Wrap links.validate_url so CLK125 is visible on every audit path."""

    global _INSTALLED
    if _INSTALLED:
        return

    from . import links

    original = links.validate_url

    def validate_url_with_clk125(url: str, convention):
        issues = original(url, convention)
        if any(issue.code == "CLK125" for issue in issues):
            return issues
        owned = getattr(convention, "owned_domains", ()) or ()
        if not should_flag_shortener_utm(url, owned_domains=tuple(owned)):
            return issues
        try:
            host = urlsplit(url).hostname or ""
        except ValueError:
            host = ""
        issues.append(
            links.Issue(
                "CLK125",
                "error",
                (
                    f"UTM parameters are attached to shortener host "
                    f"{host!r}; many shorteners strip or do not "
                    "forward unknown query keys, so GA4 never sees the "
                    "campaign. Put UTMs on the final owned destination, or "
                    "configure forwarding on a first-party short domain"
                ),
                url=url,
            )
        )
        return issues

    links.validate_url = validate_url_with_clk125  # type: ignore[method-assign]
    _INSTALLED = True
