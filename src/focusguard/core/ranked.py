from __future__ import annotations
import json
import os
import random
from datetime import date, timedelta

from focusguard.storage.memory import dataDirectory

FILE = dataDirectory() / "ranked.json"

TIERS = ["Spark", "Ember", "Flame", "Blaze", "Comet", "Nova", "Galaxy", "Supernova"]
TIER_COLORS = ["#9E9E9E", "#C77C48", "#E8590C", "#F59F00", "#4DABF7", "#9775FA", "#5C7CFA", "#F06595"]
LEGEND_COLOR = "#FFD43B"
DIVISIONS = ["I", "II", "III"]
SHIELD_DAYS = 3
DAILY_LOSS_CAP = 25
BACK_TO_WORK_BONUS = 5
BOUNCE_BACK_BONUS = 8
KICK_PENALTY = 5

BOT_NAMES = [
    "StudyNinja", "PixelPanda", "QuietStorm", "MathWizard42", "NovaNerd", "LateNightLeo", "FocusFox", "ByteSizedBen",
    "ChemQueen", "HistoryBuff7", "CalcCrusher", "SleepySloth", "CoffeeKat", "DeepWorkDan", "ZenZara", "TurboTurtle",
    "NoteTakerNia", "FlashcardFin", "LibraryLuna", "GridlockGabe", "OrbitOlive", "MaplePrep", "ChillChloe", "RocketRaj",
    "SilentSam", "PageTurnerPia", "QuizKidQuinn", "EssayEli", "AlgebraAce", "BioBoss", "StarStudent", "MidtermMax",
    "FocusedFaye", "GrindGrace", "SteadySteve", "BrainyBella", "HomeworkHero", "TimerTom", "CrunchTimeCal", "LabRatLiam",
    "PencilPip", "LogicLeah", "MarathonMia", "VocabVic", "ThesisTheo", "ProtonPaige", "IvyIvan", "CramClubCora",
    "DueDateDev", "PomodoroPete", "SyntaxSofia", "GeoGenius", "NightOwlNoah", "AceAtlas", "QuietQuasar", "MindfulMo",
    "ScholarSky", "CometKai", "FinalsFrank", "StreakSiena",
]


def divisionCost(divisionNumber: int) -> int:
    tierNumber = divisionNumber // 3
    return 60 + tierNumber * 20


def totalRanks() -> int:
    return len(TIERS) * len(DIVISIONS)


def rankFromPoints(points: float) -> tuple:
    pointsLeft = points
    for divisionNumber in range(totalRanks()):
        cost = divisionCost(divisionNumber)
        if pointsLeft < cost:
            return divisionNumber, pointsLeft, cost
        pointsLeft = pointsLeft - cost
    return totalRanks(), pointsLeft, 0


def pointsAtDivisionStart(divisionNumber: int) -> float:
    points = 0
    for number in range(divisionNumber):
        points = points + divisionCost(number)
    return points


def rankName(divisionNumber: int) -> str:
    if divisionNumber >= totalRanks():
        return "Legend"
    return TIERS[divisionNumber // 3] + " " + DIVISIONS[divisionNumber % 3]


def rankColor(divisionNumber: int) -> str:
    if divisionNumber >= totalRanks():
        return LEGEND_COLOR
    return TIER_COLORS[divisionNumber // 3]


def newRanked() -> dict:
    return {"points": 0, "day": "", "gainedToday": 0, "lostToday": 0, "shieldDivision": 0, "shieldUntil": "", "floorToday": 0}


def loadRanked() -> dict:
    try:
        ranked = json.loads(FILE.read_text())
    except (OSError, ValueError):
        ranked = {}
    if not isinstance(ranked, dict):
        ranked = {}
    defaults = newRanked()
    for key in defaults:
        if key not in ranked:
            ranked[key] = defaults[key]
    today = date.today().isoformat()
    if ranked["day"] != today:
        ranked["day"] = today
        ranked["gainedToday"] = 0
        ranked["lostToday"] = 0
        divisionNumber = rankFromPoints(ranked["points"])[0]
        ranked["floorToday"] = max(0, divisionNumber - 1)
    return ranked


def saveRanked(ranked: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tempFile = FILE.with_suffix(".tmp")
    tempFile.write_text(json.dumps(ranked, indent=2))
    os.replace(tempFile, FILE)


def lowestAllowedPoints(ranked: dict) -> float:
    floorDivision = ranked["floorToday"]
    if ranked["shieldUntil"] >= date.today().isoformat():
        floorDivision = max(floorDivision, ranked["shieldDivision"])
    return pointsAtDivisionStart(floorDivision)


def addPoints(amount: float) -> tuple:
    ranked = loadRanked()
    oldDivision = rankFromPoints(ranked["points"])[0]
    if amount >= 0:
        ranked["points"] = ranked["points"] + amount
        ranked["gainedToday"] = ranked["gainedToday"] + amount
    else:
        lossLeft = DAILY_LOSS_CAP - ranked["lostToday"]
        loss = min(-amount, max(0, lossLeft))
        newPoints = max(ranked["points"] - loss, lowestAllowedPoints(ranked))
        loss = ranked["points"] - newPoints
        if loss < 0:
            loss = 0
        ranked["points"] = ranked["points"] - loss
        ranked["lostToday"] = ranked["lostToday"] + loss
    newDivision = rankFromPoints(ranked["points"])[0]
    if newDivision > oldDivision:
        ranked["shieldDivision"] = newDivision
        ranked["shieldUntil"] = (date.today() + timedelta(days=SHIELD_DAYS)).isoformat()
    saveRanked(ranked)
    return oldDivision, newDivision


def hasShield(ranked: dict) -> bool:
    return ranked["shieldUntil"] >= date.today().isoformat() and rankFromPoints(ranked["points"])[0] == ranked["shieldDivision"]


def botPoints(botName: str, playerPoints: float) -> float:
    startRandom = random.Random(botName)
    points = startRandom.uniform(0, 2600)
    firstDay = date(2026, 10, 1)
    today = date.today()
    dayCount = (today - firstDay).days
    for dayNumber in range(max(0, dayCount)):
        dayRandom = random.Random(botName + str(firstDay + timedelta(days=dayNumber)))
        points = points + dayRandom.uniform(-15, 45)
    if points < 0:
        points = 0
    return round(points)


def leaderboard(playerName: str = "You") -> list:
    ranked = loadRanked()
    playerPoints = round(ranked["points"])
    players = []
    for botName in BOT_NAMES:
        players.append((botName, botPoints(botName, playerPoints), False))
    nearbyRandom = random.Random("nearby" + date.today().isoformat())
    for nearbyNumber in range(3):
        players[nearbyNumber] = (players[nearbyNumber][0], playerPoints + nearbyRandom.randint(5, 40) * (nearbyNumber + 1), False)
    players.append((playerName, playerPoints, True))
    players.sort(key=lambda player: -player[1])
    board = []
    for position in range(len(players)):
        name, points, isPlayer = players[position]
        board.append((position + 1, name, points, isPlayer))
    return board
