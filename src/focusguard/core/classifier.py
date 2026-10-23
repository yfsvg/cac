"""1. URL helpers for identifying which site a browser is on."""
# 2.

from __future__ import annotations

import os
from urllib.parse import urlsplit

from focusguard.core.unproductive_apps import UNPRODUCTIVE_APPS


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








def possible_names(window) -> list[str]:
    app_id = window.app_id.lower()
    names = [window.app_name.lower(), app_id]
    if app_id.endswith(".exe"):
        names.append(app_id[:-4])
    else:
        names.append(app_id.split(".")[-1])
    if window.exe_path:
        exe = os.path.basename(window.exe_path).lower()
        if exe.endswith(".exe"):
            exe = exe[:-4]
        names.append(exe)
    return names


# note prob only works on mac, gdoc contains info on what is unproductive and what is a productive app
def classifyTypeOfApp(backend, window) -> str:
    if backend.is_browser(window):
        return "browser"

    for name in possible_names(window):
        if name in UNPRODUCTIVE_APPS:
            return "unproductive"


    category = backend.get_app_category(window) or ""
    # "games" also matches the game subcategories big headache avoided
    return "unproductive" if any(c in category for c in ("games", "entertainment", "social-networking")) else "neutral"
