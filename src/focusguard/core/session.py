from __future__ import annotations
import time
from datetime import date

from focusguard.storage import memory

CONTINUE_MINUTES = 30
DEFAULT_BAIL_OUTS = 2
MAX_BAIL_OUTS = 5

resumeAllowed = False


def startSession(minutes: int) -> None:
    savedMemory = memory.load()
    savedMemory["sessionEndsAt"] = time.time() + minutes * 60
    memory.save(savedMemory)


def sessionEndsAt() -> float:
    return float(memory.load().get("sessionEndsAt", 0))


def sessionSecondsLeft() -> int:
    secondsLeft = sessionEndsAt() - time.time()
    if secondsLeft < 0:
        return 0
    return int(secondsLeft)


def extendSession(minutes: int) -> None:
    startTime = sessionEndsAt()
    if startTime < time.time():
        startTime = time.time()
    savedMemory = memory.load()
    savedMemory["sessionEndsAt"] = startTime + minutes * 60
    memory.save(savedMemory)


def extendSessionUntil(endTime: float) -> bool:
    if sessionEndsAt() >= endTime:
        return False
    savedMemory = memory.load()
    savedMemory["sessionEndsAt"] = endTime
    memory.save(savedMemory)
    return True


def endSession() -> None:
    savedMemory = memory.load()
    savedMemory["sessionEndsAt"] = 0
    memory.save(savedMemory)


def timeLeftText(secondsLeft: int) -> str:
    hoursLeft = secondsLeft // 3600
    minutesLeft = (secondsLeft % 3600) // 60
    if hoursLeft > 0:
        return str(hoursLeft) + "h " + str(minutesLeft) + "m left"
    if minutesLeft >= 10:
        return str(minutesLeft) + "m left"
    return str(minutesLeft) + "m " + str(secondsLeft % 60) + "s left"


def thisWeek() -> str:
    year, week, weekday = date.today().isocalendar()
    return str(year) + "-" + str(week)


def bailOutsPerWeek() -> int:
    return int(memory.load().get("bailOutsPerWeek", DEFAULT_BAIL_OUTS))


def bailOutsUsedThisWeek() -> int:
    bailOutsUsed = memory.load().get("bailOutsUsed", {})
    if bailOutsUsed.get("week") != thisWeek():
        return 0
    return int(bailOutsUsed.get("count", 0))


def bailOutsLeftThisWeek() -> int:
    bailOutsLeft = bailOutsPerWeek() - bailOutsUsedThisWeek()
    if bailOutsLeft < 0:
        return 0
    return bailOutsLeft


def useBailOut() -> None:
    savedMemory = memory.load()
    savedMemory["bailOutsUsed"] = {"week": thisWeek(), "count": bailOutsUsedThisWeek() + 1}
    memory.save(savedMemory)
