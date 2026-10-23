"""1. URL helpers for identifying which site a browser is on."""
# 2.

from __future__ import annotations

import os
from urllib.parse import urlsplit

from focusguard.core.unproductive_apps import UNPRODUCTIVE_APPS


def siteRoot(url: str | None) -> str | None:
    """
    Identifies site root, for ex yotuube would give youtube.com. Allows us to easily track and keep memory of bad websites
    Accepts scheme-less input too, since Windows address bars often omit "https://".
    """
    if not url:
        return None
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    urlParts = urlsplit(url)
    if urlParts.scheme not in ("http", "https"):
        return None
    hostName = ""
    if urlParts.hostname:
        hostName = urlParts.hostname
    hostName = hostName.lower().rstrip(".")
    if not hostName:
        return None
    if hostName.startswith("www."):
        hostName = hostName[4:]
    return hostName








def possibleNames(window) -> list[str]:
    appId = window.app_id.lower()
    allNames = [window.app_name.lower(), appId]
    if appId.endswith(".exe"):
        allNames.append(appId[:-4])
    else:
        allNames.append(appId.split(".")[-1])
    if window.exe_path:
        exeName = os.path.basename(window.exe_path).lower()
        if exeName.endswith(".exe"):
            exeName = exeName[:-4]
        allNames.append(exeName)
    return allNames


# note prob only works on mac, gdoc contains info on what is unproductive and what is a productive app
def classifyTypeOfApp(backend, window) -> str:
    if backend.is_browser(window):
        return "browser"

    for name in possibleNames(window):
        if name in UNPRODUCTIVE_APPS:
            return "unproductive"

    if window.app_id.lower() in ("java", "javaw.exe", "java.exe"):
        if window.title.lower().startswith("minecraft"):
            return "unproductive"


    appCategory = backend.get_app_category(window)
    if appCategory is None:
        appCategory = ""
    # "games" also matches the game subcategories big headache avoided
    for unproductiveCategory in ("games", "entertainment", "social-networking"):
        if unproductiveCategory in appCategory:
            return "unproductive"
    return "neutral"
