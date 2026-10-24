
from __future__ import annotations
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


# Json storage system, for now just tracks if you've opened the application before for persistent
# memory demo. Also not hashed just for quick mvp

# TO CHECK OR EDIT:
# ~/Library/Application Support/FocusGuard/ on macOS and %APPDATA%\FocusGuard\ on Windows.
# it wont show up in project tree sorry


def dataDirectory() -> Path:
    if sys.platform == "win32":
        baseDirectory = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        baseDirectory = Path.home() / "Library" / "Application Support"
    else:
        baseDirectory = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return baseDirectory / "FocusGuard"




FILE = dataDirectory() / "memory.json"



def load() -> dict:
    defaultMemory = {"first_time": True, "themeChoice": "system"}
    try:
        loadedMemory = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return defaultMemory
    if not isinstance(loadedMemory, dict):
        return defaultMemory
    returnVal = dict(defaultMemory)
    returnVal.update(loadedMemory)
    return returnVal


def save(memory: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tempFile = FILE.with_suffix(".tmp")
    tempFile.write_text(json.dumps(memory, indent=2))
    os.replace(tempFile, FILE)


def startupOpened() -> bool:
    return bool(load()["startupOpened"])


def markOpened() -> None:
    memory = load()
    memory["startupOpened"] = False
    save(memory)




# Streak, counts days in a row that FocusGuard was opened

def markOpenedToday() -> int:
    savedMemory = load()
    openedDays = savedMemory.get("openedDays", [])
    todayName = date.today().isoformat()
    if todayName not in openedDays:
        openedDays.append(todayName)
    savedMemory["openedDays"] = openedDays
    save(savedMemory)
    return countStreak(openedDays, date.today())


def countStreak(openedDays: list, today: date) -> int:
    streakDays = 0
    checkDay = today
    while checkDay.isoformat() in openedDays:
        streakDays = streakDays + 1
        checkDay = checkDay - timedelta(days=1)
    return streakDays


def streakText(streakDays: int) -> str:
    if streakDays <= 1:
        return "Day 1 of your streak. Open FocusGuard tomorrow to keep it going!"
    return "You're on a " + str(streakDays) + " day streak of using FocusGuard. Keep it going!"




# there are three main stats shwon daily + weekly
# % time focused, how much of your tracked time wasn't unproductive
# Hours spent productive, basically any time not unprod so neutral counts
# and then average rebounding speed or more like # of times, how many break periods it took to get back to work (1 is the best)

# Splitting up tracked seconds

def focusedSeconds(times: dict) -> int:
    returnVal = 0
    for (appName, appKind), seconds in times.items():
        if appKind != "unproductive":
            returnVal = returnVal + seconds
    return returnVal


def unproductiveSeconds(times: dict) -> int:
    returnVal = 0
    for (appName, appKind), seconds in times.items():
        if appKind == "unproductive":
            returnVal = returnVal + seconds
    return returnVal





# The big thre stast, None means there's nothing to show yet

def percentFocused(times: dict) -> int | None:
    totalSeconds = focusedSeconds(times) + unproductiveSeconds(times)
    if totalSeconds == 0:
        return None
    return round(focusedSeconds(times) * 100 / totalSeconds)


def hoursProductive(times: dict) -> float:
    return round(focusedSeconds(times) / 3600, 1)


def averageRebound(allRebounds: list, dayNames: list) -> float | None:
    breakPeriodsUsed = []
    for rebound in allRebounds:
        if rebound.get("day") in dayNames:
            breakPeriodsUsed.append(rebound.get("breakPeriods", 1))
    if len(breakPeriodsUsed) == 0:
        return None
    return round(sum(breakPeriodsUsed) / len(breakPeriodsUsed), 1)




# Loading days, today comes from the live dashboard s

def lastSevenDays(today: date) -> list:
    returnVal = []
    for daysAgo in range(7):
        returnVal.append((today - timedelta(days=daysAgo)).isoformat())
    return returnVal


def weekTimes(todayTimes: dict, today: date) -> dict:
    # Imported here since time_tracking imports this file
    from focusguard.storage import time_tracking

    returnVal = dict(todayTimes)
    for dayName in lastSevenDays(today)[1:]:
        for timeKey, seconds in time_tracking.loadDay(dayName).items():
            returnVal[timeKey] = returnVal.get(timeKey, 0) + seconds
    return returnVal


def savedRebounds() -> list:
    return load().get("rebounds", [])
