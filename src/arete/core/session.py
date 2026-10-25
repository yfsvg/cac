import time

from arete.storage import memory

CONTINUE_MINUTES = 30


def startSession(minutes):
    savedMemory = memory.load()
    savedMemory["session"] = {
        "endsAt": time.time() + minutes * 60,
        "minutes": minutes,
        "seconds": 0,
        "productiveSeconds": 0,
    }
    memory.save(savedMemory)


def currentSession():
    return memory.load().get("session")


def sessionSecondsLeft():
    savedSession = currentSession()
    if savedSession is None:
        return 0
    secondsLeft = savedSession["endsAt"] - time.time()
    if secondsLeft < 0:
        return 0
    return int(secondsLeft)


def saveProgress(seconds, productiveSeconds):
    savedMemory = memory.load()
    savedSession = savedMemory.get("session")
    if savedSession is None:
        return
    savedSession["seconds"] = seconds
    savedSession["productiveSeconds"] = productiveSeconds
    memory.save(savedMemory)


def endSession():
    savedMemory = memory.load()
    savedMemory.pop("session", None)
    memory.save(savedMemory)


def productiveFraction(seconds, productiveSeconds):
    if seconds <= 0:
        return 0
    return productiveSeconds / seconds


def timeLeftText(secondsLeft):
    hoursLeft = secondsLeft // 3600
    minutesLeft = (secondsLeft % 3600) // 60
    if hoursLeft > 0:
        return str(hoursLeft) + "h " + str(minutesLeft) + "m left"
    if minutesLeft >= 10:
        return str(minutesLeft) + "m left"
    return str(minutesLeft) + "m " + str(secondsLeft % 60) + "s left"
