# close countdown from the tray menu

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from arete.ui import close_screen
from arete.ui.close_screen import WAIT_SECONDS, CloseScreen, timeText


@pytest.fixture(scope="module", autouse=True)
def app():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(close_screen.time, "monotonic", lambda: now[0])
    return now


def makeScreen(inSession=False):
    calls = []
    screen = CloseScreen(lambda: inSession, lambda: calls.append("resumed"), lambda: calls.append("quit"))
    return screen, calls


@pytest.mark.parametrize(("seconds", "expected"), [(60, "1:00"), (59, "0:59"), (5, "0:05"), (0, "0:00")])
def test_time_text(seconds, expected):
    assert timeText(seconds) == expected


def test_quit_locked_until_wait_is_over(clock):
    screen, calls = makeScreen()
    assert screen.title.text() == "Closing Arete in 1:00"
    assert not screen.quitButton.isEnabled()

    clock[0] += WAIT_SECONDS - 0.5
    screen.countDown()
    assert screen.title.text() == "Closing Arete in 0:01"
    assert not screen.quitButton.isEnabled()

    clock[0] += 0.5
    screen.countDown()
    assert screen.quitButton.isEnabled()
    screen.quitButton.click()
    assert calls == ["quit"]


def test_resume_works_any_time(clock):
    screen, calls = makeScreen()
    clock[0] += 20
    screen.countDown()
    screen.resumeButton.click()
    assert calls == ["resumed"]


def test_closing_the_window_counts_as_resume(clock):
    screen, calls = makeScreen()
    screen.popUp()
    screen.close()
    assert calls == ["resumed"]


def test_escape_resumes(clock):
    screen, calls = makeScreen()
    screen.popUp()
    QTest.keyClick(screen, Qt.Key.Key_Escape)
    assert calls == ["resumed"]


def test_session_warning_only_in_session(clock):
    inSession, _ = makeScreen(inSession=True)
    notInSession, _ = makeScreen(inSession=False)
    assert inSession.warning.isVisibleTo(inSession)
    assert not notInSession.warning.isVisibleTo(notInSession)
