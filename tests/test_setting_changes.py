import pytest

from focusguard.core import setting_changes
from focusguard.storage import memory


class FakeClock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now


@pytest.fixture(autouse=True)
def tempMemory(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "FILE", tmp_path / "memory.json")


@pytest.fixture
def clock(monkeypatch):
    fakeClock = FakeClock()
    monkeypatch.setattr(setting_changes.time, "time", fakeClock.time)
    return fakeClock


def test_change_waits_an_hour(clock):
    setting_changes.queueChange("Absolute Time Limits", {"maxBreaks": 5})
    assert "maxBreaks" not in memory.load()
    assert setting_changes.isPending("Absolute Time Limits")
    assert setting_changes.pendingSecondsLeft("Absolute Time Limits") == 3600
    assert setting_changes.upcomingValue("Absolute Time Limits", "maxBreaks", 2) == 5

    clock.now = clock.now + 3599
    assert setting_changes.applyDueChanges() == []
    assert "maxBreaks" not in memory.load()

    clock.now = clock.now + 1
    assert setting_changes.applyDueChanges() == ["Absolute Time Limits"]
    assert memory.load()["maxBreaks"] == 5
    assert not setting_changes.isPending("Absolute Time Limits")


def test_setting_freezes_once_the_change_starts(clock):
    setting_changes.queueChange("Schedule Time Limits", {"studySchedule": {"days": [0]}})
    assert setting_changes.frozenSecondsLeft("Schedule Time Limits") == 0
    clock.now = clock.now + setting_changes.DELAY_SECONDS
    setting_changes.applyDueChanges()
    assert setting_changes.frozenSecondsLeft("Schedule Time Limits") == setting_changes.FREEZE_SECONDS


def test_cancel_keeps_the_old_value(clock):
    memory.save({"maxBreaks": 4})
    setting_changes.queueChange("Absolute Time Limits", {"maxBreaks": 8, "breakMinutes": 15})
    setting_changes.cancelChange("Absolute Time Limits")
    clock.now = clock.now + 2 * setting_changes.DELAY_SECONDS
    assert setting_changes.applyDueChanges() == []
    assert memory.load()["maxBreaks"] == 4
    assert setting_changes.upcomingValue("Absolute Time Limits", "maxBreaks", 4) == 4


def test_apply_now_skips_the_wait(clock):
    setting_changes.queueChange("Absolute Time Limits", {"maxBreaks": 0})
    setting_changes.applyNow("Absolute Time Limits")
    assert memory.load()["maxBreaks"] == 0
    assert not setting_changes.isPending("Absolute Time Limits")
    assert setting_changes.frozenSecondsLeft("Absolute Time Limits") == setting_changes.FREEZE_SECONDS
