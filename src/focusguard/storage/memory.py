
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






# Loading + saving, load always gives a dict even if file is missing/broken

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




# Everest climb
# 8 stages up to the 8000m peak, 1000m apart except summit ridge (1500m) + the peak (500m)
# offset = the y spot on the background svg that gets centred when ur at that stage

CLIMB_STAGES = [
    {"name": "Trailhead", "startMeters": 0, "offset": 1830,
     "message": "Welcome to your productivity journey on Everest! Try activating the app, being productive, and avoiding distractions."},
    {"name": "First Camp", "startMeters": 1000, "offset": 1591,
     "message": "You’ve made your first decent progress, but much awaits. No more procrastination now!"},
    {"name": "The Treeline", "startMeters": 2000, "offset": 1361,
     "message": "Vegetation disappears, the first unfamiliarity of the impeding task. Let’s keep pushing onwards and stay working!"},
    {"name": "Rocky Ridge", "startMeters": 3000, "offset": 1137,
     "message": "The path forward is more difficult than ever. We’re at the halfway point, let’s keep on staying productive!"},
    {"name": "Sky Clouds", "startMeters": 4000, "offset": 936,
     "message": "The future is uncertain, but we may only know what lies ahead by pushing forward. Let’s remain productive."},
    {"name": "The Snow Line", "startMeters": 5000, "offset": 692,
     "message": "The peak reveals itself! The last stretch is possible through dedication and focus, let’s get to it!"},
    {"name": "Summit Ridge", "startMeters": 6000, "offset": 554,
     "message": "We’re at the final stretch of your productivity journey. We’re so close, no more procrastination now!"},
    {"name": "The Peak", "startMeters": 7500, "offset": 400,
     "message": "You’ve done it! You’ve reached the summit of productivity, and kept procrastination at bay."},
]
SUMMIT_METERS = 8000

# going up, both capped per day
FOCUS_HOUR_METERS = 50
FOCUS_HOUR_DAILY_CAP = 500
BOUNCE_BACK_METERS = 25
BOUNCE_BACK_DAILY_CAP = 400

# going down, only ever happens once a day
DAILY_FALL_METERS = 50


def climbMeters() -> int:
    savedMemory = load()
    if applyDailyFall(savedMemory, date.today()):
        save(savedMemory)
    return int(savedMemory.get("climbMeters", 0))


def applyDailyFall(savedMemory: dict, today: date) -> bool:
    # fall 50m for every day thats passed since the last fall, returns True if memory changed
    lastFallDay = savedMemory.get("climbLastFall")
    todayName = today.isoformat()
    if lastFallDay == todayName:
        return False
    if lastFallDay is not None:
        daysPassed = (today - date.fromisoformat(lastFallDay)).days
        if daysPassed > 0:
            meters = savedMemory.get("climbMeters", 0) - DAILY_FALL_METERS * daysPassed
            if meters < 0:
                meters = 0
            savedMemory["climbMeters"] = meters
    savedMemory["climbLastFall"] = todayName
    return True


def addClimbMeters(earnedMeters: int, todayKey: str, dailyCap: int) -> int:
    # adds meters but never past todays cap or the summit, returns how many actually got added
    savedMemory = load()
    today = date.today()
    applyDailyFall(savedMemory, today)
    climbToday = savedMemory.get("climbToday", {})
    if climbToday.get("day") != today.isoformat():
        climbToday = {"day": today.isoformat()}

    earnedSoFar = climbToday.get(todayKey, 0)
    if earnedSoFar + earnedMeters > dailyCap:
        earnedMeters = dailyCap - earnedSoFar
    if earnedMeters <= 0:
        return 0

    climbToday[todayKey] = earnedSoFar + earnedMeters
    meters = savedMemory.get("climbMeters", 0) + earnedMeters
    if meters > SUMMIT_METERS:
        meters = SUMMIT_METERS
    savedMemory["climbMeters"] = meters
    savedMemory["climbToday"] = climbToday
    save(savedMemory)
    return earnedMeters


def setClimbMeters(meters: int) -> int:
    # debug only, writes meters straight in (kept between 0 and the summit)
    if meters < 0:
        meters = 0
    if meters > SUMMIT_METERS:
        meters = SUMMIT_METERS
    savedMemory = load()
    applyDailyFall(savedMemory, date.today())
    savedMemory["climbMeters"] = meters
    save(savedMemory)
    return meters


def addFocusHourMeters() -> int:
    return addClimbMeters(FOCUS_HOUR_METERS, "focusMeters", FOCUS_HOUR_DAILY_CAP)


def addBounceBackMeters(breakPeriods: int) -> int:
    # 25m for an immediate bounce back (back after the first reminder), less the longer it took
    if breakPeriods < 1:
        breakPeriods = 1
    return addClimbMeters(BOUNCE_BACK_METERS // breakPeriods, "bounceMeters", BOUNCE_BACK_DAILY_CAP)


def climbStage(meters: int) -> dict:
    returnVal = CLIMB_STAGES[0]
    for stage in CLIMB_STAGES:
        if meters >= stage["startMeters"]:
            returnVal = stage
    return returnVal


def nextClimbGoal(meters: int) -> tuple:
    # (name of the next goal, meters left), the top of the peak is the last goal
    for stage in CLIMB_STAGES:
        if stage["startMeters"] > meters:
            return stage["name"], stage["startMeters"] - meters
    return "the top", SUMMIT_METERS - meters




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
