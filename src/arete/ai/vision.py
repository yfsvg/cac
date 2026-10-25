from __future__ import annotations
import base64
import json
import urllib.request
from datetime import date

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QImage

from arete.ai.site_memory import saveSiteCategory
from arete.storage import memory
from arete.storage.memory import dataDirectory

# cheapest gemini model, 40 checks a day max so no surprise bill
MODEL = "gemini-flash-lite-latest"
AI_CHECKS_PER_DAY = 40
SCREENSHOT_SIZE = 1024
KEY_FILE = dataDirectory() / "gemini_key.txt"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"

QUESTION = (
    "A student is using a website while they are supposed to be studying. "
    "Site: {site}. Page title: {title}. "
    "Is this site productive for school work or unproductive (games, videos, social media, shopping, entertainment)? "
    "Answer with exactly one word: productive, unproductive, or unsure."
)

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





# shrink screenshot + jpg it so its cheap to send

def shrinkScreenshot(screenshot: bytes) -> bytes:
    image = QImage.fromData(screenshot)
    if image.isNull():
        return screenshot
    if image.width() > SCREENSHOT_SIZE or image.height() > SCREENSHOT_SIZE:
        image = image.scaled(SCREENSHOT_SIZE, SCREENSHOT_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    imageBytes = QByteArray()
    imageBuffer = QBuffer(imageBytes)
    imageBuffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(imageBuffer, "JPG", 70)
    imageBuffer.close()
    return bytes(imageBytes.data())





# asks gemini, gives back productive / unproductive / unsure or None if it couldnt

def askGemini(site: str, pageTitle: str, screenshot: bytes | None = None) -> str | None:
    apiKey = getApiKey()
    if apiKey == "":
        return None
    if aiChecksToday() >= AI_CHECKS_PER_DAY:
        return None
    countAiCheck()
    parts = [{"text": QUESTION.format(site=site, title=pageTitle or "unknown")}]
    if screenshot is not None:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(shrinkScreenshot(screenshot)).decode()}})
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





# New site -- ask w/ just the title first, only screenshot if AI is unsure

def classifySite(backend, window, site: str) -> None:
    category = askGemini(site, window.title)
    if category == "unsure":
        screenshot = backend.capture_window(window)
        if screenshot is not None:
            notices.append("Arete took a screenshot of your browser to check " + site + ".")
            category = askGemini(site, window.title, screenshot)
    if category == "unsure":
        category = "productive"
    if category == "productive" or category == "unproductive":
        saveSiteCategory(site, category)
        notices.append("Arete's AI checked " + site + ": " + category + ".")
