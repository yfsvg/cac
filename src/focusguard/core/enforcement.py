from __future__ import annotations
from datetime import date

from focusguard.storage import memory


# Break limits, how many breaks you get per day + how long each one is

MIN_BREAKS = 1
MAX_BREAKS = 8
DEFAULT_BREAKS = 4

MIN_BREAK_MINUTES = 3
MAX_BREAK_MINUTES = 15
DEFAULT_BREAK_MINUTES = 5




# Break limits, saved settings + how many breaks were used today

def getMaxBreaks() -> int:
    return int(memory.load().get("maxBreaks", DEFAULT_BREAKS))


def getBreakMinutes() -> int:
    return int(memory.load().get("breakMinutes", DEFAULT_BREAK_MINUTES))


def breaksUsedToday() -> int:
    breaksUsed = memory.load().get("breaksUsed", {})
    if breaksUsed.get("day") != date.today().isoformat():
        return 0
    return int(breaksUsed.get("count", 0))


def breaksLeftToday() -> int:
    breaksLeft = getMaxBreaks() - breaksUsedToday()
    if breaksLeft < 0:
        return 0
    return breaksLeft


def useBreak() -> None:
    savedMemory = memory.load()
    savedMemory["breaksUsed"] = {"day": date.today().isoformat(), "count": breaksUsedToday() + 1}
    memory.save(savedMemory)




# Enforcer, warns you then closes unproductive apps

LIMIT = 180
WARNING = 150


class Enforcer:
    def __init__(self, backend):
        self.backend = backend
        self.notify = None
        self.alreadyWarned = []
        self.closedForToday = []

    def sendNotification(self, text):
        if self.notify is not None:
            self.notify("FocusGuard", text)

    def checkApp(self, window, appKind, secondsUsed, siteName=None):
        if appKind != "unproductive":
            return False

        appName = window.app_name
        if siteName is not None:
            appName = siteName
        if secondsUsed >= WARNING:
            if appName not in self.alreadyWarned:
                self.alreadyWarned.append(appName)
                self.sendNotification("Hey, you've been on " + appName + " for a little while. It'll close in " + str(LIMIT - secondsUsed) + " seconds, no stress, your work will be right where you left it.")

        if secondsUsed < LIMIT:
            return False

        self.sendNotification("Closing " + appName + " for now. Take a breath, you've got this.")
        if siteName is None:
            self.backend.close_app(window.pid)
        else:
            self.backend.close_tab(window)
        if appName in self.alreadyWarned:
            self.alreadyWarned.remove(appName)
        return True

    # Out of breaks for today, closes it with one gentle notification per app
    def closeForToday(self, window, siteName=None):
        appName = window.app_name
        if siteName is not None:
            appName = siteName
        if appName not in self.closedForToday:
            self.closedForToday.append(appName)
            self.sendNotification("You've used all your breaks for today, so " + appName + " stays closed until tomorrow. You've got this!")
        if siteName is None:
            self.backend.close_app(window.pid)
        else:
            self.backend.close_tab(window)
