from __future__ import annotations
import base64
import json
import urllib.request

from focusguard.ai.site_memory import saveSiteCategory
from focusguard.storage.memory import dataDirectory

MODEL = "gemini-flash-latest"
KEY_FILE = dataDirectory() / "gemini_key.txt"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"

QUESTION = (
    "A student is using a website while they are supposed to be studying. "
    "Site: {site}. Page title: {title}. "
    "Is this site productive for school work or unproductive (games, videos, social media, shopping, entertainment)? "
    "Answer with exactly one word: productive, unproductive, or unsure."
)

notices = []


def getApiKey() -> str:
    try:
        return KEY_FILE.read_text().strip()
    except OSError:
        return ""


def saveApiKey(apiKey: str) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(apiKey.strip())


def askGemini(site: str, pageTitle: str, screenshot: bytes | None = None) -> str | None:
    apiKey = getApiKey()
    if apiKey == "":
        return None
    parts = [{"text": QUESTION.format(site=site, title=pageTitle or "unknown")}]
    if screenshot is not None:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(screenshot).decode()}})
    body = json.dumps({"contents": [{"parts": parts}]}).encode()
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


def classifySite(backend, window, site: str) -> None:
    category = askGemini(site, window.title)
    if category == "unsure":
        screenshot = backend.capture_window(window)
        if screenshot is not None:
            notices.append("FocusGuard took a screenshot of your browser to check " + site + ".")
            category = askGemini(site, window.title, screenshot)
    if category == "productive" or category == "unproductive":
        saveSiteCategory(site, category)
