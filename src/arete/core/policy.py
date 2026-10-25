from datetime import datetime

from arete.storage import memory


IDLE_SECONDS = 300


def studySchedules():
    savedMemory = memory.load()
    schedules = savedMemory.get("studySchedules")
    if schedules is None and savedMemory.get("studySchedule", {}).get("days"):
        schedules = [savedMemory["studySchedule"]]
    return schedules or []


def activeSchedule(now=None):
    if now is None:
        now = datetime.now()
    timeText = now.strftime("%H:%M")
    for schedule in studySchedules():
        if now.weekday() in schedule["days"] and schedule["start"] <= timeText < schedule["end"]:
            return schedule
    return None


def minutesLeftInSchedule(schedule, now=None):
    if now is None:
        now = datetime.now()
    endHour, endMinute = schedule["end"].split(":")
    endsAt = now.replace(hour=int(endHour), minute=int(endMinute), second=0, microsecond=0)
    return max(1, int((endsAt - now).total_seconds() // 60))


def isIdle(idleSeconds):
    return idleSeconds >= IDLE_SECONDS
