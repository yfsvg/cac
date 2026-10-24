from __future__ import annotations
from datetime import date, timedelta

from focusguard.storage import memory


def markOpenedToday() -> int:
    savedMemory = memory.load()
    openedDays = savedMemory.get("openedDays", [])
    todayName = date.today().isoformat()
    if todayName not in openedDays:
        openedDays.append(todayName)
    savedMemory["openedDays"] = openedDays
    memory.save(savedMemory)
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
