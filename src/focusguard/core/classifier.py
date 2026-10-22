"""1. URL helpers for identifying which site a browser is on."""
# 2.

from __future__ import annotations

from urllib.parse import urlsplit


def site_root(url: str | None) -> str | None:
    """
    Identifies site root, for ex yotuube would give youtube.com. Allows us to easily track and keep memory of bad websites
    Accepts scheme-less input too, since Windows address bars often omit "https://".
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








# note prob only works on mac, gdoc contains info on what is unproductive and what is a productive app
def classifyTypeOfApp(backend, window) -> str:
    if backend.is_browser(window):
        return "browser"

    
    category = backend.get_app_category(window) or ""
    # "games" also matches the game subcategories big headache avoided
    return "unproductive" if any(c in category for c in ("games", "entertainment", "social-networking")) else "neutral"
