# the OS layer. core/ and ui/ only ever talk to PlatformBackend, never to windows.py / macos.py

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from arete.core.models import ActiveWindow, PermissionState, RunningApp

AUTOSTART_LABEL = "com.arete.daemon"
DAEMON_MODULE = "arete.daemon.main"


# everything arete needs from the OS, windows.py and macos.py fill this in
class PlatformBackend(ABC):
    # exe names on windows / bundle ids on mac (all lowercase) that count as browsers
    BROWSER_IDS: frozenset[str] = frozenset()

    # what is the user doing

    # gets focused inwdow
    @abstractmethod
    def get_active_window(self) -> ActiveWindow | None: ...

    # gets active url tab
    @abstractmethod
    def get_browser_url(self, window: ActiveWindow) -> str | None: ...




    # these two are especially important for classification, provides the LSApplicationCategoryType.
    # note that this is MAC ONLY so we rely on a a massive list "unproductive apps" for wintoes
    def get_app_category(self, window: ActiveWindow) -> str | None:
        return None
    def is_browser(self, window: ActiveWindow) -> bool:
        return window.app_id.lower() in self.BROWSER_IDS

    # apps that have a window / dock icon, one entry per app
    @abstractmethod
    def list_running_apps(self) -> list[RunningApp]: ...

    # seconds since the last key press or mouse move
    @abstractmethod
    def get_idle_seconds(self) -> float: ...

    # png of every monitor together, mac needs screen recording permission for this
    def capture_screen(self) -> bytes:
        import mss
        import mss.tools

        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            return mss.tools.to_png(shot.rgb, shot.size)

    def capture_window(self, window: ActiveWindow) -> bytes | None:
        rect = self.get_window_rect(window)
        if rect is None:
            return None
        return grabRegion(rect)

    # closing stuff

    # asks the app to quit, or kills it if force. True if it got the message
    @abstractmethod
    def close_app(self, pid: int, force: bool = False) -> bool: ...

    def close_tab(self, window: ActiveWindow) -> bool:
        return self.close_app(window.pid)

    # background app, no dock icon on mac. call it after the qt app is made
    @abstractmethod
    def hide_from_taskbar(self) -> None: ...

    def float_above_everything(self, win_id: int) -> None:
        pass

    def get_window_rect(self, window: ActiveWindow) -> tuple[int, int, int, int] | None:
        return None

    # blur function. Currently mac only, if we're windows then we just ignore. True if it blurred.
    def blur_behind(self, win_id: int, corner_radius: float = 0) -> bool:
        return False

    # startup + permissions

    # start the daemon at login
    @abstractmethod
    def install_autostart(self) -> None: ...

    @abstractmethod
    def uninstall_autostart(self) -> None: ...

    @abstractmethod
    def is_autostart_installed(self) -> bool: ...

    # where each permission is at right now, without popping up any prompts
    @abstractmethod
    def check_permissions(self) -> dict[str, PermissionState]: ...

    # pops up the OS prompts for whatever permissions are missing
    @abstractmethod
    def request_permissions(self) -> None: ...

    # only windows needs admin
    def is_admin(self) -> bool:
        return True

    # starts command as admin after the prompt, True if they said yes
    def run_as_admin(self, command: list[str]) -> bool:
        return False

    # command that starts the daemon with whatever python we're running on
    @staticmethod
    def daemon_command() -> list[str]:
        python = Path(sys.executable)
        # pythonw.exe runs without a console window on Windows
        pythonw = python.with_name("pythonw.exe")
        if sys.platform == "win32" and pythonw.exists():
            python = pythonw
        return [str(python), "-m", DAEMON_MODULE]


def grabRegion(rect: tuple[int, int, int, int]) -> bytes | None:
    import mss
    import mss.tools

    left, top, width, height = rect
    with mss.mss() as sct:
        screen = sct.monitors[0]
        right = min(left + width, screen["left"] + screen["width"])
        bottom = min(top + height, screen["top"] + screen["height"])
        left = max(left, screen["left"])
        top = max(top, screen["top"])
        if right - left < 10 or bottom - top < 10:
            return None
        shot = sct.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})
        return mss.tools.to_png(shot.rgb, shot.size)
