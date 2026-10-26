# plain data types shared across the app

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# whatever the user is looking at right now
@dataclass(frozen=True)
class ActiveWindow:
    app_name: str
    app_id: str  # bundle id on mac ("com.google.chrome"), lowercase exe name on windows ("chrome.exe")
    pid: int
    title: str = ""  # can be empty if the OS hides it (missing permissions)
    exe_path: str | None = None
    window_handle: int | None = None  # HWND on windows, CGWindowID on mac, used to read browser urls


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
