from __future__ import annotations
import json
import urllib.request
from datetime import date
from html.parser import HTMLParser

from focusguard.ai.site_memory import saveSiteCategory
from focusguard.storage import memory
from focusguard.storage.memory import dataDirectory

# cheapest gemini model, 40 checks a day max so no surprise bill
# 100 checks go fuck yourself pee vee pee parthie
MODEL = "gemini-flash-lite-latest"
AI_CHECKS_PER_DAY = 100
# only the public homepage is read, never the page ur actually on
PAGE_BYTES_LIMIT = 500_000
PAGE_TEXT_LIMIT = 2000
KEY_FILE = dataDirectory() / "gemini_key.txt"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"

QUESTION = (
    "A student is using a website while they are supposed to be studying. "
    "Site: {site}.{about}\n"
    "Is this site productive for school work or unproductive (games, videos, social media, shopping, entertainment)? "
    "Answer with exactly one word: {choices}."
)
ABOUT_HOMEPAGE = "\nWhat the site's homepage says about itself:\n"

# bot checks + error pages, these say nothing about the real site but just say like hey we cant rely on text content
BLOCKED_TITLES = ("client challenge", "just a moment", "attention required", "access denied", "are you a robot", "403 forbidden", "security check")

# notifications for the dashboard to show, AI is on a background thread
notices = []





# api key gets its own file so clear memory doesnt nuke it

def getApiKey() -> str:
    try:
        return KEY_FILE.read_text().strip()
    except OSError:
        return ""


def saveApiKey(apiKey: str) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(apiKey.strip())





# daily AI check limit

def aiChecksToday() -> int:
    aiChecks = memory.load().get("aiChecks", {})
    if aiChecks.get("day") != date.today().isoformat():
        return 0
    return int(aiChecks.get("count", 0))


def countAiCheck() -> None:
    savedMemory = memory.load()
    savedMemory["aiChecks"] = {"day": date.today().isoformat(), "count": aiChecksToday() + 1}
    memory.save(savedMemory)





# reading the public homepage, metadata first, then a bit of the text if thats not enough
"""
process goes like this:
1. Look at site metadata. Usually enough for like 75% of all sites
2. Look at text content
3. Possible for tc to be blocked, then just look at site link and then you EHAVE to come to a decision.


"""

class HomepageReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.metadata = []
        self.textParts = []
        self.skipDepth = 0
        self.inTitle = False

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript", "nav", "footer", "svg"):
            self.skipDepth = self.skipDepth + 1
        if tag == "title":
            self.inTitle = True
        if tag == "meta" and attrs.get("content"):
            metaName = (attrs.get("name") or attrs.get("property") or "").lower()
            if metaName in ("description", "keywords", "og:site_name", "og:title", "og:description", "application-name"):
                self.metadata.append(metaName + ": " + attrs["content"].strip())

    def handle_endtag(self, tag) -> None:
        if tag in ("script", "style", "noscript", "nav", "footer", "svg") and self.skipDepth > 0:
            self.skipDepth = self.skipDepth - 1
        if tag == "title":
            self.inTitle = False

    def handle_data(self, data) -> None:
        if self.inTitle:
            self.title = self.title + data
        elif self.skipDepth == 0 and data.strip() != "":
            self.textParts.append(" ".join(data.split()))


def readHomepage(site: str) -> HomepageReader | None:
    # no cookies or login, so this only ever sees what anyone visiting the homepage would
    request = urllib.request.Request("https://" + site + "/", headers={"User-Agent": "Mozilla/5.0 FocusGuard"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            pageBytes = response.read(PAGE_BYTES_LIMIT)
            charset = response.headers.get_content_charset() or "utf-8"
        reader = HomepageReader()
        reader.feed(pageBytes.decode(charset, errors="replace"))
    except Exception:
        return None
    return reader


def metadataText(reader: HomepageReader) -> str:
    lines = []
    if reader.title.strip() != "":
        lines.append("title: " + " ".join(reader.title.split()))
    lines.extend(reader.metadata)
    return "\n".join(lines)


def pageText(reader: HomepageReader) -> str:
    return " ".join(reader.textParts)[:PAGE_TEXT_LIMIT]


def isBlocked(reader: HomepageReader | None) -> bool:
    if reader is None:
        return True
    title = reader.title.strip().lower()
    for blockedTitle in BLOCKED_TITLES:
        if blockedTitle in title:
            return True
    return metadataText(reader) == "" and pageText(reader) == ""





# asks gemini, gives back productive / unproductive / unsure or None if it couldnt

def askGemini(site: str, about: str, mustDecide: bool = False) -> str | None:
    apiKey = getApiKey()
    if apiKey == "":
        return None
    if aiChecksToday() >= AI_CHECKS_PER_DAY:
        return None
    countAiCheck()
    choices = "productive, unproductive, or unsure"
    if mustDecide:
        choices = "productive or unproductive"
    aboutText = ""
    if about != "":
        aboutText = ABOUT_HOMEPAGE + about
    parts = [{"text": QUESTION.format(site=site, about=aboutText, choices=choices)}]
    settings = {"maxOutputTokens": 20, "temperature": 0, "thinkingConfig": {"thinkingLevel": "minimal"}}
    body = json.dumps({"contents": [{"parts": parts}], "generationConfig": settings}).encode()
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": apiKey},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            answer = json.loads(response.read())
        answerText = answer["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
    except Exception:
        return None
    for category in ("unproductive", "productive", "unsure"):
        if category in answerText:
            return category
    return None





# New site -- homepage metadata first, then some homepage text, then just the link (has to pick one)
# never looks at ur screen, the window title or the page ur actually on

def classifySite(site: str) -> None:
    category = "unsure"
    reader = readHomepage(site)
    if not isBlocked(reader) and metadataText(reader) != "":
        category = askGemini(site, metadataText(reader))
    if not isBlocked(reader) and category == "unsure" and pageText(reader) != "":
        category = askGemini(site, metadataText(reader) + "\nhomepage text: " + pageText(reader))
    if category == "unsure":
        category = askGemini(site, "", mustDecide=True)
    if category == "unsure":
        category = "productive"
    if category == "productive" or category == "unproductive":
        saveSiteCategory(site, category)
        notices.append("FocusGuard's AI checked " + site + ": " + category + ".")
