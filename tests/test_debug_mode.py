import sys

import pytest

from focusguard.core.debug_mode import isDebugMode


@pytest.fixture(autouse=True)
def noDebugger(monkeypatch):
    monkeypatch.delitem(sys.modules, "debugpy", raising=False)
    monkeypatch.delenv("FOCUSGUARD_DEBUG", raising=False)


def test_debug_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["focusguard", "--debug"])
    assert isDebugMode()


def test_no_debug_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["focusguard", "--resume"])
    assert not isDebugMode()


def test_debug_environment_variable(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["focusguard"])
    monkeypatch.setenv("FOCUSGUARD_DEBUG", "1")
    assert isDebugMode()
