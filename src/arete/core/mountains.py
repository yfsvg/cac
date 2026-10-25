from pathlib import Path

ASSETS = Path(__file__).parent.parent / "ui" / "assets"

CHECKPOINT_COUNT = 8
BOSS_CHECKPOINTS = [2, 5, 7]

MOUNTAINS = [
    {
        "name": "Mount Fuji",
        "shortName": "Fuji",
        "picture": ASSETS / "fuji.svg",
        "topCrop": 150,
        "heightMeters": 3776,
        "startMessage": "The climb starts here. Stay on task and every session moves you up.",
        "stages": [
            ("Base Station", "Nice start, you made it to the first station. Keep the focus going."),
            ("Pine Forest", "The trees are getting thinner. A boss is waiting just up the trail."),
            ("Lantern Path", "The first boss blocks the path. Beat it after a session to keep climbing."),
            ("Old Shrine", "You got past the first guardian. The path gets steeper from here."),
            ("Cloud Line", "You're above the clouds now. Don't let distractions pull you back down."),
            ("Ash Fields", "Another boss blocks the trail. Finish a session and take it on."),
            ("Crater Rim", "Almost there, the summit is right above you."),
            ("Fuji Summit", "The top of Fuji. Beat the summit boss to head to Everest."),
        ],
    },
    {
        "name": "Mount Everest",
        "shortName": "Everest",
        "picture": ASSETS / "everest.svg",
        "topCrop": 140,
        "heightMeters": 8849,
        "startMessage": "Welcome to Everest. It's a lot taller than Fuji, so keep showing up.",
        "stages": [
            ("Base Camp", "You made it to base camp. The real climb starts now."),
            ("Khumbu Icefall", "The ice is moving under you. Steady sessions get you through."),
            ("Camp One", "A boss guards the camp. Beat it with focus minutes to pass."),
            ("Western Cwm", "Halfway up the biggest mountain on Earth. Keep it going."),
            ("Lhotse Face", "The air is getting thin, and so is the room for slacking off."),
            ("South Col", "The death zone boss is waiting. Show it what focus looks like."),
            ("Hillary Step", "One last hard push. The summit is right there."),
            ("Everest Summit", "The roof of the world. Beat the summit boss to unlock the Matterhorn."),
        ],
    },
    {
        "name": "Matterhorn",
        "shortName": "Matterhorn",
        "picture": ASSETS / "matterhorn.svg",
        "topCrop": 70,
        "heightMeters": 4478,
        "startMessage": "The final mountain. Shorter than Everest, but way harder.",
        "stages": [
            ("Zermatt", "You left the village behind. No turning back now."),
            ("Alpine Meadow", "Green grass for now. Enjoy it while it lasts."),
            ("Hornli Hut", "The hut is guarded by the toughest boss yet."),
            ("Hornli Ridge", "Nothing but rock and focus from here on."),
            ("The Shoulder", "The ridge narrows. One slip and you slide back down."),
            ("Solvay Hut", "Another boss blocks the ridge. You know what to do."),
            ("Fixed Ropes", "Pull yourself up, the summit is so close."),
            ("Matterhorn Summit", "The final summit. Beat the last boss to finish Arete."),
        ],
    },
]


def bossPercents():
    bossList = []
    for mountainNumber in range(len(MOUNTAINS)):
        for checkpointNumber in BOSS_CHECKPOINTS:
            bossList.append(mountainNumber * 100 + checkpointPercent(checkpointNumber))
    return bossList


def checkpointPercent(checkpointNumber):
    return (checkpointNumber + 1) * 100 / CHECKPOINT_COUNT


def stageNumber(percent):
    number = -1
    for checkpointNumber in range(CHECKPOINT_COUNT):
        if percent >= checkpointPercent(checkpointNumber) - 0.001:
            number = checkpointNumber
    return number

