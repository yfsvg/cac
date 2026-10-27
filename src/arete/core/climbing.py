# The climb, split into five segments:
# 1. How much everything is worth
# 2. Loading + reading where you are
# 3. Moving up and down the mountain
# 4. Earning + losing climb
# 5. Bosses
#
# Climb % runs 0 - 300 across all three mountains (100 each). Bosses block the trail,
# you cant climb past one until its beaten


import time

from arete.core import mountains
from arete.storage import memory


# How much everything is worth

PERCENT_CLIMBED_PER_FOCUSED_HOUR = 1.0
SHORTEST_SESSION_MINUTES = 10

BOUNCE_BACK_PERCENT = 0.25
BOUNCE_BACK_DAILY_CAP_PERCENT = 1.0

BOSS_STARTING_HEALTH_MINUTES = 45
BOSS_EXTRA_HEALTH_MINUTES_EACH = 25
BOSS_HEAL_MINUTES_PER_DISTRACTION = 5

DISTRACTION_PENALTY_PERCENT = PERCENT_CLIMBED_PER_FOCUSED_HOUR / 3
SECONDS_BETWEEN_DISTRACTION_PENALTIES = 60

# old versions saved meters instead of %, this turns them into %
OLD_METERS_PER_PERCENT = 80






# Loading the climb, upgrades old meter saves the first time

def loadClimbMemory():
    savedMemory = memory.load()
    if "climbPercent" not in savedMemory:
        # never let an old save skip past the first boss
        savedMemory["climbPercent"] = min(savedMemory.get("climbMeters", 0) / OLD_METERS_PER_PERCENT, mountains.bossPercents()[0])
        savedMemory["bossesBeaten"] = 0
        memory.save(savedMemory)
    return savedMemory


# Reading the climb, everything the rest of the app wants to know in one dict

def climbState():
    savedMemory = loadClimbMemory()
    totalPercent = float(savedMemory.get("climbPercent", 0))
    bossesBeaten = int(savedMemory.get("bossesBeaten", 0))
    everyBossPercent = mountains.bossPercents()

    # 3 bosses per mountain, so bosses beaten says which mountain ur on (stays on the last one at the end)
    mountainNumber = min(bossesBeaten // len(mountains.BOSS_CHECKPOINTS), len(mountains.MOUNTAINS) - 1)
    percentUpThisMountain = totalPercent - mountainNumber * 100

    nextBossPercent = None
    if bossesBeaten < len(everyBossPercent):
        nextBossPercent = everyBossPercent[bossesBeaten]

    return {
        "totalPercent": totalPercent,
        "mountainNumber": mountainNumber,
        "percent": percentUpThisMountain,
        "stageNumber": mountains.stageNumber(percentUpThisMountain),
        "bossesBeaten": bossesBeaten,
        "nextBoss": nextBossPercent,
        "atBoss": nextBossPercent is not None and totalPercent >= nextBossPercent - 0.001,
        "finished": bossesBeaten >= len(everyBossPercent),
        "lastChange": savedMemory.get("lastClimbChange"),
    }






# Moving up and down, never below the last boss you beat or above the next one

def lowestAllowedPercent(bossesBeaten):
    if bossesBeaten == 0:
        return 0
    return mountains.bossPercents()[bossesBeaten - 1]


def highestAllowedPercent(bossesBeaten):
    if bossesBeaten >= len(mountains.bossPercents()):
        return len(mountains.MOUNTAINS) * 100
    return mountains.bossPercents()[bossesBeaten]


# moves the climb by percentChange, gives back how much it actually moved after the limits
def changeClimbBy(percentChange, reasonText):
    savedMemory = loadClimbMemory()
    bossesBeaten = int(savedMemory.get("bossesBeaten", 0))
    oldPercent = float(savedMemory.get("climbPercent", 0))
    newPercent = min(max(oldPercent + percentChange, lowestAllowedPercent(bossesBeaten)), highestAllowedPercent(bossesBeaten))
    actuallyChangedBy = round(newPercent - oldPercent, 2)

    savedMemory["climbPercent"] = newPercent
    if actuallyChangedBy != 0:
        savedMemory["lastClimbChange"] = {"amount": actuallyChangedBy, "reason": reasonText, "time": time.time()}
    memory.save(savedMemory)
    return actuallyChangedBy


# debug only, puts u straight at a spot on the climb
def setClimbPercent(totalPercent, bossesBeaten):
    savedMemory = loadClimbMemory()
    savedMemory["bossesBeaten"] = bossesBeaten
    savedMemory["climbPercent"] = min(max(totalPercent, lowestAllowedPercent(bossesBeaten)), highestAllowedPercent(bossesBeaten))
    savedMemory["bossDamage"] = 0
    memory.save(savedMemory)






# Earning, focus sessions + bouncing back from breaks

# % a session is worth, sessions under 10 min dont count
def sessionPercentWorth(sessionMinutes, focusedFraction):
    if sessionMinutes < SHORTEST_SESSION_MINUTES:
        return 0
    return round(PERCENT_CLIMBED_PER_FOCUSED_HOUR * (sessionMinutes / 60) * min(max(focusedFraction, 0), 1), 2)


def sessionEarned(sessionMinutes, focusedFraction):
    return changeClimbBy(sessionPercentWorth(sessionMinutes, focusedFraction), "your " + str(int(round(sessionMinutes))) + " min session")


# quicker bounce back = more %, capped each day so breaks cant be farmed
def bounceBackEarned(breakPeriods):
    savedMemory = loadClimbMemory()
    today = time.strftime("%Y-%m-%d")
    bounceBacksToday = savedMemory.get("bounceToday", {})
    if bounceBacksToday.get("day") != today:
        bounceBacksToday = {"day": today, "percent": 0}

    percentEarned = BOUNCE_BACK_PERCENT / max(breakPeriods, 1)
    if bounceBacksToday["percent"] + percentEarned > BOUNCE_BACK_DAILY_CAP_PERCENT:
        percentEarned = BOUNCE_BACK_DAILY_CAP_PERCENT - bounceBacksToday["percent"]
    if percentEarned <= 0:
        return 0

    bounceBacksToday["percent"] = bounceBacksToday["percent"] + percentEarned
    savedMemory["bounceToday"] = bounceBacksToday
    memory.save(savedMemory)
    return changeClimbBy(percentEarned, "bouncing back")






# Losing, opening something unproductive

# slides u back down, or heals the boss instead if ur fighting one. once a minute at most
def unproductivePenalty(appName):
    savedMemory = loadClimbMemory()
    if time.time() - savedMemory.get("lastPenaltyAt", 0) < SECONDS_BETWEEN_DISTRACTION_PENALTIES:
        return 0
    savedMemory["lastPenaltyAt"] = time.time()
    memory.save(savedMemory)

    if climbState()["atBoss"]:
        healBoss(BOSS_HEAL_MINUTES_PER_DISTRACTION)
        return 0
    return changeClimbBy(-DISTRACTION_PENALTY_PERCENT, "opening " + appName)






# Bosses, health is in focus minutes. Every focused minute in a session hits it

def bossHealth(bossNumber):
    return BOSS_STARTING_HEALTH_MINUTES + BOSS_EXTRA_HEALTH_MINUTES_EACH * bossNumber


def bossMinutesLeft():
    return max(bossHealth(climbState()["bossesBeaten"]) - float(loadClimbMemory().get("bossDamage", 0)), 0)


# True if that hit beat the boss
def damageBoss(focusMinutes):
    state = climbState()
    if not state["atBoss"] or state["finished"]:
        return False

    savedMemory = loadClimbMemory()
    savedMemory["bossDamage"] = float(savedMemory.get("bossDamage", 0)) + focusMinutes
    memory.save(savedMemory)
    if savedMemory["bossDamage"] >= bossHealth(state["bossesBeaten"]):
        beatBoss()
        return True
    return False


def healBoss(healMinutes):
    savedMemory = loadClimbMemory()
    savedMemory["bossDamage"] = max(float(savedMemory.get("bossDamage", 0)) - healMinutes, 0)
    savedMemory["lastClimbChange"] = {"amount": 0, "reason": "the boss healed", "time": time.time()}
    memory.save(savedMemory)


# opens the trail again, damage resets for the next boss
def beatBoss():
    savedMemory = loadClimbMemory()
    savedMemory["bossesBeaten"] = int(savedMemory.get("bossesBeaten", 0)) + 1
    savedMemory["bossDamage"] = 0
    if savedMemory.get("climbPercent", 0) < lowestAllowedPercent(savedMemory["bossesBeaten"]):
        savedMemory["climbPercent"] = lowestAllowedPercent(savedMemory["bossesBeaten"])
    memory.save(savedMemory)






# Text, "+0.5% from your 30 min session" / "-0.33% for opening Steam" / "The boss healed"

def changeText(climbChange):
    if climbChange is None:
        return ""
    if climbChange["amount"] == 0:
        return climbChange["reason"][0].upper() + climbChange["reason"][1:]

    amountText = format(abs(climbChange["amount"]), ".2f").rstrip("0").rstrip(".")
    if climbChange["amount"] >= 0:
        return "+" + amountText + "% from " + climbChange["reason"]
    return "-" + amountText + "% for " + climbChange["reason"]
