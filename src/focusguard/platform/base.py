"""The OS abstraction. `core/` and `ui/` only ever talk to `PlatformBackend`."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from focusguard.core.models import ActiveWindow, PermissionState, RunningApp

AUTOSTART_LABEL = "com.focusguard.daemon"
DAEMON_MODULE = "focusguard.daemon.main"


class PlatformBackend(ABC):
    """Everything FocusGuard needs from the operating system."""

    #: App identifiers (bundle ids on macOS, lowercased exe names on Windows) treated as browsers.
    BROWSER_IDS: frozenset[str] = frozenset()

    # ---- what is the user doing ------------------------------------------------------------

    @abstractmethod
    def get_active_window(self) -> ActiveWindow | None:
        """gets focused inwdow"""

    @abstractmethod
    def get_browser_url(self, window: ActiveWindow) -> str | None:
        """Gets active url tab"""




    # these two are especially important for classification, provides the LSApplicationCategoryType.
    # note that this is MAC ONLY so we rely on a a massive list "unproductive apps" for wintoes
    def get_app_category(self, window: ActiveWindow) -> str | None:
        return None
    def is_browser(self, window: ActiveWindow) -> bool:
        return window.app_id.lower() in self.BROWSER_IDS

    @abstractmethod
    def list_running_apps(self) -> list[RunningApp]:
        """User-facing apps that are currently running (ones with windows / a dock icon), one per app."""

    @abstractmethod
    def get_idle_seconds(self) -> float:
        """Seconds since the last keyboard or mouse input."""

    def capture_screen(self) -> bytes:
        """PNG of all monitors combined. On macOS this needs Screen Recording permission."""
        import mss
        import mss.tools

        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            return mss.tools.to_png(shot.rgb, shot.size)

    def capture_window(self, window: ActiveWindow) -> bytes | None:
        rect = self.get_window_rect(window)
        if rect is None:
            return None
        return grab_region(rect)

    # ---- enforcement -----------------------------------------------------------------------

    @abstractmethod
    def close_app(self, pid: int, force: bool = False) -> bool:
        """Ask the app owning `pid` to quit, or kill it outright with `force`. Returns True if it was signalled."""

    def close_tab(self, window: ActiveWindow) -> bool:
        return self.close_app(window.pid)

    @abstractmethod
    def hide_from_taskbar(self) -> None:
        """Run as a background app: no Dock icon on macOS. Call after the Qt app is created."""

    def float_above_everything(self, win_id: int) -> None:
        pass

    def get_window_rect(self, window: ActiveWindow) -> tuple[int, int, int, int] | None:
        return None

    def blur_behind(self, win_id: int, corner_radius: float = 0) -> None:
        """blur function. Currently mac only, if we're windows then we just ignore."""

    # ---- installation ----------------------------------------------------------------------

    @abstractmethod
    def install_autostart(self) -> None:
        """Start the daemon at login."""

    @abstractmethod
    def uninstall_autostart(self) -> None: ...

    @abstractmethod
    def is_autostart_installed(self) -> bool: ...

    @abstractmethod
    def check_permissions(self) -> dict[str, PermissionState]:
        """State of each OS permission FocusGuard relies on, without prompting the user."""

    @abstractmethod
    def request_permissions(self) -> None:
        """Trigger the OS prompts for any missing permissions."""

    def is_admin(self) -> bool:
        """Whether FocusGuard has the admin rights it needs. Only Windows asks for them."""
        return True

    def run_as_admin(self, command: list[str]) -> bool:
        """Start `command` with admin rights after asking the user. Returns True if they said yes."""
        return False

    # ---- shared helpers --------------------------------------------------------------------

    @staticmethod
    def daemon_command() -> list[str]:
        """Command line that launches the daemon with the current interpreter."""
        python = Path(sys.executable)
        # pythonw.exe runs without a console window on Windows
        pythonw = python.with_name("pythonw.exe")
        if sys.platform == "win32" and pythonw.exists():
            python = pythonw
        return [str(python), "-m", DAEMON_MODULE]


def grab_region(rect: tuple[int, int, int, int]) -> bytes | None:
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
