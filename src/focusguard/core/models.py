"""Plain data types shared across the app."""

from __future__ import annotations

from dataclasses import dataclass
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


# what check_permissions gives back per permission
class PermissionState(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"
