from __future__ import annotations
import json
import os
from datetime import date

from focusguard.storage.memory import dataDirectory

FILE = dataDirectory() / "times.json"


def todayName() -> str:
    return date.today().isoformat()


def loadAllDays() -> dict:
    try:
        allDays = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(allDays, dict):
        return {}
    return allDays


def loadToday() -> dict:
    return loadDay(todayName())


def loadDay(dayName: str) -> dict:
    return dayTimes(loadAllDays().get(dayName, {}))


def dayTimes(savedTimes: dict) -> dict:
    times = {}
    for savedKey in savedTimes:
        if "|" not in savedKey:
            continue
        appName, appKind = savedKey.rsplit("|", 1)
        times[(appName, appKind)] = int(savedTimes[savedKey])
    return times


def saveDay(dayName: str, times: dict) -> None:
    allDays = loadAllDays()
    savedTimes = {}
    for (appName, appKind), seconds in times.items():
        savedTimes[appName + "|" + appKind] = seconds
    allDays[dayName] = savedTimes
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tempFile = FILE.with_suffix(".tmp")
    tempFile.write_text(json.dumps(allDays, indent=2))
    os.replace(tempFile, FILE)
