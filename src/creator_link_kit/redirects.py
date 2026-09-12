"""Offline detection of platform click wrappers around brand URLs."""

from __future__ import annotations

from urllib.parse import parse_qsl, unquote

# Platform click wrappers that hide the real landing page in a query value.
# Creators often paste these from a YouTube/Facebook/Instagram "copy link"
# control. Analytics then attributes the wrapper host, not the brand site.
# Detection is offline and does not fetch the nested destination.
REDIRECT_WRAPPERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("youtube.com", "/redirect", ("q", "dest")),
    ("youtu.be", "/redirect", ("q", "dest")),
    ("facebook.com", "/l.php", ("u",)),
    ("l.facebook.com", "/", ("u",)),
    ("lm.facebook.com", "/l.php", ("u",)),
    ("l.instagram.com", "/", ("u",)),
    ("lm.instagram.com", "/", ("u",)),
    ("google.com", "/url", ("q", "url")),
)


def hostname_matches(host: str, suffix: str) -> bool:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host == suffix or host.endswith("." + suffix)


def looks_like_absolute_http_url(value: str) -> bool:
    raw = unquote(value.strip())
    lowered = raw.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def redirect_wrapper_message(parsed, url: str) -> str | None:
    """Return a CLK120 message if *parsed* is a known platform wrapper."""
    host = parsed.hostname or ""
    path = parsed.path or "/"
    pairs = parse_qsl(parsed.query, keep_blank_values=True)

    for suffix, path_prefix, dest_keys in REDIRECT_WRAPPERS:
        if not hostname_matches(host, suffix):
            continue
        if path_prefix == "/":
            path_ok = True
        else:
            path_ok = path == path_prefix or path.startswith(path_prefix + "/")
        if not path_ok:
            continue
        for key, value in pairs:
            if key.lower() in dest_keys and looks_like_absolute_http_url(value):
                nested = unquote(value.strip())
                return (
                    f"URL is a {suffix} redirect wrapper around "
                    f"{nested!r}; analytics records the wrapper host, "
                    "not the brand destination. Paste the inner "
                    "https landing page instead of the platform redirect"
                )

    if hostname_matches(host, "href.li") and looks_like_absolute_http_url(parsed.query):
        return (
            f"URL is an href.li redirect wrapper around "
            f"{unquote(parsed.query)!r}; paste the inner landing page "
            "instead of the wrapper"
        )
    return None
