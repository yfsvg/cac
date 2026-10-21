"""Plain data types shared across the app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum


@dataclass(frozen=True)
class ActiveWindow:
    """Snapshot of whatever the user is looking at right now."""

    app_name: str
    """Human-readable app name, e.g. "Google Chrome" or "Steam"."""

    app_id: str
    """Stable identifier: bundle id on macOS ("com.google.Chrome"), lowercased exe name on Windows ("chrome.exe")."""

    pid: int
    title: str = ""
    """Title of the focused window. May be empty if the OS withholds it (missing permissions)."""

    exe_path: str | None = None
    window_handle: int | None = None
    """Native window handle: HWND on Windows, CGWindowID on macOS. Used for browser URL lookup."""


@dataclass(frozen=True)
class RunningApp:
    app_name: str
    app_id: str
    pid: int
    exe_path: str | None = None


class Verdict(str, Enum):
    PRODUCTIVE = "productive"
    UNPRODUCTIVE = "unproductive"
    UNKNOWN = "unknown"


class PermissionState(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"


@dataclass
class ScheduleBlock:
    """A recurring window of time the user committed to being productive."""

    name: str
    weekdays: set[int]
    """0 = Monday ... 6 = Sunday."""
    start: time
    end: time
    allow_list: set[str] = field(default_factory=set)
    """Extra app ids / site roots allowed during this block only."""


@dataclass
class ActivitySample:
    """One check of the scheduler loop, persisted for stats."""

    timestamp: datetime
    window: ActiveWindow
    site_root: str | None
    verdict: Verdict


class EnforcementAction(str, Enum):
    NONE = "none"
    WARN = "warn"
    CLOSE = "close"
