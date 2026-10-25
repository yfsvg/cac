# debug mode on from --debug or ARETE_DEBUG

import sys

import pytest

from arete.core.debug_mode import isDebugMode


@pytest.fixture(autouse=True)
def noDebugger(monkeypatch):
    monkeypatch.delitem(sys.modules, "debugpy", raising=False)
    monkeypatch.delenv("ARETE_DEBUG", raising=False)


def test_debug_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["arete", "--debug"])
    assert isDebugMode()


def test_no_debug_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["arete", "--resume"])
    assert not isDebugMode()


def test_debug_environment_variable(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["arete"])
    monkeypatch.setenv("ARETE_DEBUG", "1")
    assert isDebugMode()
