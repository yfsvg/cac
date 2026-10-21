"""URL helpers for identifying which site a browser is on."""

from __future__ import annotations

from urllib.parse import urlsplit


def site_root(url: str | None) -> str | None:
    """Reduce a URL to the site root we classify by, e.g. "https://www.youtube.com/watch?v=x" -> "youtube.com".

    Accepts scheme-less input too, since Windows address bars often omit "https://".
    Returns None for empty input or pages with no host (new tab, settings, file://).
    """
    if not url:
        return None
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host

