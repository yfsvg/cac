import time

from arete.core import mountains
from arete.storage import memory

PERCENT_PER_HOUR = 1.0
SHORTEST_SESSION_MINUTES = 10
BOUNCE_BACK_PERCENT = 0.25
BOUNCE_BACK_DAILY_CAP = 1.0
PENALTY_PERCENT = PERCENT_PER_HOUR / 3
PENALTY_GAP_SECONDS = 60
OLD_METERS_PER_PERCENT = 80


def loadClimb():
    savedMemory = memory.load()
    if "climbPercent" not in savedMemory:
        oldPercent = savedMemory.get("climbMeters", 0) / OLD_METERS_PER_PERCENT
        firstBoss = mountains.bossPercents()[0]
        if oldPercent > firstBoss:
            oldPercent = firstBoss
        savedMemory["climbPercent"] = oldPercent
        savedMemory["bossesBeaten"] = 0
        memory.save(savedMemory)
    return savedMemory


def climbState():
    savedMemory = loadClimb()
    totalPercent = float(savedMemory.get("climbPercent", 0))
    bossesBeaten = int(savedMemory.get("bossesBeaten", 0))
    allBosses = mountains.bossPercents()
    mountainNumber = bossesBeaten // len(mountains.BOSS_CHECKPOINTS)
    if mountainNumber > len(mountains.MOUNTAINS) - 1:
        mountainNumber = len(mountains.MOUNTAINS) - 1
    percent = totalPercent - mountainNumber * 100
    nextBoss = None
    if bossesBeaten < len(allBosses):
        nextBoss = allBosses[bossesBeaten]
    return {
        "totalPercent": totalPercent,
        "mountainNumber": mountainNumber,
        "percent": percent,
        "stageNumber": mountains.stageNumber(percent),
        "bossesBeaten": bossesBeaten,
        "nextBoss": nextBoss,
        "atBoss": nextBoss is not None and totalPercent >= nextBoss - 0.001,
        "finished": bossesBeaten >= len(allBosses),
        "lastChange": savedMemory.get("lastClimbChange"),
    }


def lowestPercent(bossesBeaten):
    if bossesBeaten == 0:
        return 0
    return mountains.bossPercents()[bossesBeaten - 1]


def highestPercent(bossesBeaten):
    allBosses = mountains.bossPercents()
    if bossesBeaten >= len(allBosses):
        return len(mountains.MOUNTAINS) * 100
    return allBosses[bossesBeaten]


def changeClimb(amount, reason):
    savedMemory = loadClimb()
    bossesBeaten = int(savedMemory.get("bossesBeaten", 0))
    oldPercent = float(savedMemory.get("climbPercent", 0))
    newPercent = oldPercent + amount
    if newPercent > highestPercent(bossesBeaten):
        newPercent = highestPercent(bossesBeaten)
    if newPercent < lowestPercent(bossesBeaten):
        newPercent = lowestPercent(bossesBeaten)
    changedBy = round(newPercent - oldPercent, 2)
    savedMemory["climbPercent"] = newPercent
    savedMemory["lastClimbChange"] = {"amount": changedBy, "reason": reason, "time": time.time()}
    memory.save(savedMemory)
    return changedBy


def sessionAmount(minutes, productiveFraction):
    if minutes < SHORTEST_SESSION_MINUTES:
        return 0
    hours = minutes / 60
    if productiveFraction < 0:
        productiveFraction = 0
    if productiveFraction > 1:
        productiveFraction = 1
    return round(PERCENT_PER_HOUR * hours * productiveFraction, 2)


def sessionEarned(minutes, productiveFraction):
    reason = "your " + str(int(round(minutes))) + " min session"
    return changeClimb(sessionAmount(minutes, productiveFraction), reason)


def unproductivePenalty(appName):
    savedMemory = loadClimb()
    if time.time() - savedMemory.get("lastPenaltyAt", 0) < PENALTY_GAP_SECONDS:
        return 0
    savedMemory["lastPenaltyAt"] = time.time()
    memory.save(savedMemory)
    return changeClimb(-PENALTY_PERCENT, "opening " + appName)


def bounceBackEarned(breakPeriods):
    if breakPeriods < 1:
        breakPeriods = 1
    savedMemory = loadClimb()
    today = time.strftime("%Y-%m-%d")
    bounceToday = savedMemory.get("bounceToday", {})
    if bounceToday.get("day") != today:
        bounceToday = {"day": today, "percent": 0}
    amount = BOUNCE_BACK_PERCENT / breakPeriods
    if bounceToday["percent"] + amount > BOUNCE_BACK_DAILY_CAP:
        amount = BOUNCE_BACK_DAILY_CAP - bounceToday["percent"]
    if amount <= 0:
        return 0
    bounceToday["percent"] = bounceToday["percent"] + amount
    savedMemory["bounceToday"] = bounceToday
    memory.save(savedMemory)
    return changeClimb(amount, "bouncing back")


def beatBoss():
    savedMemory = loadClimb()
    bossesBeaten = int(savedMemory.get("bossesBeaten", 0)) + 1
    savedMemory["bossesBeaten"] = bossesBeaten
    if savedMemory.get("climbPercent", 0) < lowestPercent(bossesBeaten):
        savedMemory["climbPercent"] = lowestPercent(bossesBeaten)
    memory.save(savedMemory)


def bossDifficulty():
    return climbState()["bossesBeaten"] + 1


def setClimbPercent(totalPercent, bossesBeaten):
    savedMemory = loadClimb()
    if totalPercent > highestPercent(bossesBeaten):
        totalPercent = highestPercent(bossesBeaten)
    if totalPercent < lowestPercent(bossesBeaten):
        totalPercent = lowestPercent(bossesBeaten)
    savedMemory["bossesBeaten"] = bossesBeaten
    savedMemory["climbPercent"] = totalPercent
    memory.save(savedMemory)


def changeText(change):
    if change is None:
        return ""
    amountText = format(abs(change["amount"]), ".2f").rstrip("0").rstrip(".")
    if change["amount"] >= 0:
        return "+" + amountText + "% from " + change["reason"]
    return "-" + amountText + "% for " + change["reason"]
