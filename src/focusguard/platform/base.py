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
        """The frontmost app and its focused window, or None if nothing is focused."""

    @abstractmethod
    def get_browser_url(self, window: ActiveWindow) -> str | None:
        """URL of the active tab of `window`, or None if it isn't a browser or the URL can't be read."""

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

    # ---- enforcement -----------------------------------------------------------------------

    @abstractmethod
    def close_app(self, pid: int, force: bool = False) -> bool:
        """Ask the app owning `pid` to quit, or kill it outright with `force`. Returns True if it was signalled."""

    @abstractmethod
    def hide_from_taskbar(self) -> None:
        """Run as a background app: no Dock icon on macOS. Call after the Qt app is created."""

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
