from __future__ import annotations
import json
import os

from arete.core.unproductive_sites import PRODUCTIVE_SITES, UNPRODUCTIVE_SITES
from arete.storage.memory import dataDirectory

# every site the AI sorted, {"site.com": "productive"}, only ask once per site
FILE = dataDirectory() / "sites.json"
rememberedSites = None





# matches subdomains too so m.youtube.com = youtube.com

def siteIsInList(site: str, siteList) -> bool:
    siteParts = site.split(".")
    for index in range(len(siteParts) - 1):
        if ".".join(siteParts[index:]) in siteList:
            return True
    return False





# remembered sites, load once then keep in memory

def loadSiteMemory() -> dict:
    global rememberedSites
    if rememberedSites is not None:
        return rememberedSites
    try:
        loadedSites = json.loads(FILE.read_text())
    except (OSError, ValueError):
        loadedSites = {}
    if not isinstance(loadedSites, dict):
        loadedSites = {}
    rememberedSites = loadedSites
    return rememberedSites


def saveSiteCategory(site: str, category: str) -> None:
    allSites = loadSiteMemory()
    allSites[site] = category
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tempFile = FILE.with_suffix(".tmp")
    tempFile.write_text(json.dumps(allSites, indent=2))
    os.replace(tempFile, FILE)





# built in lists beat whatever the AI said

def siteCategory(site: str | None) -> str | None:
    if not site:
        return None
    if siteIsInList(site, PRODUCTIVE_SITES):
        return "productive"
    if siteIsInList(site, UNPRODUCTIVE_SITES):
        return "unproductive"
    allSites = loadSiteMemory()
    if site in allSites:
        return allSites[site]
    return None


def rememberedSitesList() -> list:
    allSites = loadSiteMemory()
    sitesList = []
    for site in sorted(allSites):
        sitesList.append((site, allSites[site]))
    return sitesList
