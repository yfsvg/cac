from __future__ import annotations
import time

from focusguard.storage import memory

# A saved setting waits an hour before it takes effect, so it can't be changed on impulse.
# Once it takes effect it stays frozen for 3 days.
DELAY_SECONDS = 60 * 60
FREEZE_SECONDS = 3 * 24 * 60 * 60


def markChanged(settingName: str) -> None:
    savedMemory = memory.load()
    changedAt = savedMemory.get("changedAt", {})
    changedAt[settingName] = time.time()
    savedMemory["changedAt"] = changedAt
    memory.save(savedMemory)


def frozenSecondsLeft(settingName: str) -> int:
    changedAt = memory.load().get("changedAt", {})
    if settingName not in changedAt:
        return 0
    secondsLeft = changedAt[settingName] + FREEZE_SECONDS - time.time()
    if secondsLeft < 0:
        return 0
    return int(secondsLeft)


def queueChange(settingName: str, newValues: dict) -> None:
    savedMemory = memory.load()
    pendingChanges = savedMemory.get("pendingChanges", {})
    pendingChanges[settingName] = {"appliesAt": time.time() + DELAY_SECONDS, "values": newValues}
    savedMemory["pendingChanges"] = pendingChanges
    memory.save(savedMemory)


def isPending(settingName: str) -> bool:
    return settingName in memory.load().get("pendingChanges", {})


def pendingSecondsLeft(settingName: str) -> int:
    pendingChange = memory.load().get("pendingChanges", {}).get(settingName)
    if pendingChange is None:
        return 0
    secondsLeft = pendingChange["appliesAt"] - time.time()
    if secondsLeft < 0:
        return 0
    return int(secondsLeft)


def upcomingValue(settingName: str, memoryKey: str, currentValue):
    pendingChange = memory.load().get("pendingChanges", {}).get(settingName)
    if pendingChange is None:
        return currentValue
    return pendingChange["values"].get(memoryKey, currentValue)


def cancelChange(settingName: str) -> None:
    savedMemory = memory.load()
    pendingChanges = savedMemory.get("pendingChanges", {})
    pendingChanges.pop(settingName, None)
    savedMemory["pendingChanges"] = pendingChanges
    memory.save(savedMemory)


def applyChange(savedMemory: dict, settingName: str, appliedAt: float) -> None:
    pendingChange = savedMemory["pendingChanges"].pop(settingName)
    savedMemory.update(pendingChange["values"])
    changedAt = savedMemory.get("changedAt", {})
    changedAt[settingName] = appliedAt
    savedMemory["changedAt"] = changedAt


def applyNow(settingName: str) -> None:
    savedMemory = memory.load()
    if settingName not in savedMemory.get("pendingChanges", {}):
        return
    applyChange(savedMemory, settingName, time.time())
    memory.save(savedMemory)


def applyDueChanges() -> list:
    savedMemory = memory.load()
    pendingChanges = savedMemory.get("pendingChanges", {})
    appliedSettings = []
    for settingName in list(pendingChanges):
        appliesAt = pendingChanges[settingName]["appliesAt"]
        if appliesAt <= time.time():
            applyChange(savedMemory, settingName, appliesAt)
            appliedSettings.append(settingName)
    if len(appliedSettings) > 0:
        memory.save(savedMemory)
    return appliedSettings
