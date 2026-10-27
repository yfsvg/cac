# the OS layer. core/ and ui/ only ever talk to PlatformBackend, never to windows.py / macos.py

from __future__ import annotations

from abc import ABC, abstractmethod

from arete.core.models import ActiveWindow, PermissionState


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


    # seconds since the last key press or mouse move
    @abstractmethod
    def get_idle_seconds(self) -> float: ...


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


    # where each permission is at right now, without popping up any prompts
    @abstractmethod
    def check_permissions(self) -> dict[str, PermissionState]: ...


    # only windows needs admin
    def is_admin(self) -> bool:
        return True

    # starts command as admin after the prompt, True if they said yes
    def run_as_admin(self, command: list[str]) -> bool:
        return False

