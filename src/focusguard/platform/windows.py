"""Windows backend: Win32 via ctypes, process info via psutil, browser URLs via UI Automation."""

from __future__ import annotations

import ctypes
import logging
import subprocess
import winreg
from ctypes import wintypes
from pathlib import Path

import psutil

from focusguard.core.models import ActiveWindow, PermissionState, RunningApp
from focusguard.platform.base import PlatformBackend

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

# Hard-coded for now; will come from the user's app config later.
BROWSERS = {
    "helium.exe": "Helium",
    "chrome.exe": "Google Chrome",
    "arc.exe": "Arc",
}

# Accessible names of the address bar in English builds. Other locales fall back to the
# "first edit box inside a toolbar" search in _find_address_bar.
_ADDRESS_BAR_NAMES = ("Address and search bar", "Search or enter address", "Address bar")
_UIA_SEARCH_DEPTH = 12

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "FocusGuard"

# Win32 constants
GW_OWNER = 4
GWL_EXSTYLE = -20
WM_CLOSE = 0x0010
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
LWA_ALPHA = 0x00000002

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]
user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
kernel32.GetTickCount.restype = wintypes.DWORD

# The *LongPtr variants only exist in 64-bit user32.
_GetWindowLong = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
_SetWindowLong = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
_GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
_GetWindowLong.restype = ctypes.c_ssize_t
_SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_SetWindowLong.restype = ctypes.c_ssize_t


class WindowsBackend(PlatformBackend):
    BROWSER_IDS = frozenset(BROWSERS)

    # ---- what is the user doing ------------------------------------------------------------

    def get_active_window(self) -> ActiveWindow | None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = _window_pid(hwnd)
        proc = _process(pid)
        if proc is None:
            return None
        # Store apps are hosted by ApplicationFrameHost; the real app owns a child window.
        if _proc_name(proc) == "applicationframehost.exe":
            child_pid = _uwp_child_pid(hwnd, pid)
            if child_pid and (child := _process(child_pid)):
                pid, proc = child_pid, child
        exe = _proc_exe(proc)
        return ActiveWindow(
            app_name=_friendly_name(proc, exe),
            app_id=_proc_name(proc),
            pid=pid,
            title=_window_text(hwnd),
            exe_path=exe,
            window_handle=int(hwnd),
        )

    def get_browser_url(self, window: ActiveWindow) -> str | None:
        if not self.is_browser(window) or not window.window_handle:
            return None
        try:
            import uiautomation as auto
        except ImportError:
            log.warning("uiautomation isn't installed; can't read browser URLs")
            return None
        try:
            with auto.UIAutomationInitializerInThread(debug=False):
                root = auto.ControlFromHandle(window.window_handle)
                edit = _find_address_bar(root) if root else None
                if edit is None:
                    return None
                return edit.GetValuePattern().Value.strip() or None
        except Exception:  # UIA throws COM errors when windows vanish mid-query
            log.debug("UI Automation lookup failed for %s", window.app_name, exc_info=True)
            return None

    def list_running_apps(self) -> list[RunningApp]:
        apps: dict[int, RunningApp] = {}
        for hwnd in _top_level_windows():
            pid = _window_pid(hwnd)
            if pid in apps or not (proc := _process(pid)):
                continue
            if _proc_name(proc) == "applicationframehost.exe":
                child_pid = _uwp_child_pid(hwnd, pid)
                if not child_pid or child_pid in apps or not (proc := _process(child_pid)):
                    continue
                pid = child_pid
            exe = _proc_exe(proc)
            apps[pid] = RunningApp(
                app_name=_friendly_name(proc, exe), app_id=_proc_name(proc), pid=pid, exe_path=exe
            )
        return list(apps.values())

    def get_idle_seconds(self) -> float:
        info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        # Both counters are 32-bit milliseconds and wrap every ~49.7 days.
        elapsed_ms = (kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
        return elapsed_ms / 1000.0

    # ---- enforcement -----------------------------------------------------------------------

    def close_app(self, pid: int, force: bool = False) -> bool:
        proc = _process(pid)
        if proc is None:
            return False
        if not force:
            # WM_CLOSE lets the app prompt to save, same as clicking the X.
            windows = [h for h in _top_level_windows() if _window_pid(h) == pid]
            for hwnd in windows:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            if windows:
                return True
        try:
            proc.kill() if force else proc.terminate()
            return True
        except psutil.Error:
            return False

    # ---- overlay windows -------------------------------------------------------------------

    def configure_overlay_window(self, native_handle: int, click_through: bool = True) -> None:
        hwnd = wintypes.HWND(native_handle)
        old = _GetWindowLong(hwnd, GWL_EXSTYLE)
        style = old | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        if click_through:
            style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            style &= ~WS_EX_TRANSPARENT
        _SetWindowLong(hwnd, GWL_EXSTYLE, style)
        # A window that just became layered is invisible until it has layered attributes.
        # Leave already-layered windows alone so per-pixel alpha keeps working.
        if style & WS_EX_LAYERED and not old & WS_EX_LAYERED:
            user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED
        )

    def hide_from_taskbar(self) -> None:
        # Nothing app-wide on Windows: WS_EX_TOOLWINDOW (set per window above) keeps windows
        # off the taskbar, and the tray icon is the only other presence.
        pass

    # ---- installation ----------------------------------------------------------------------

    def install_autostart(self) -> None:
        command = subprocess.list2cmdline(self.daemon_command())
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, command)

    def uninstall_autostart(self) -> None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, _RUN_VALUE)
        except FileNotFoundError:
            pass

    def is_autostart_installed(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                winreg.QueryValueEx(key, _RUN_VALUE)
            return True
        except FileNotFoundError:
            return False

    def check_permissions(self) -> dict[str, PermissionState]:
        try:
            import uiautomation  # noqa: F401

            uia = PermissionState.GRANTED
        except ImportError:
            uia = PermissionState.DENIED
        return {
            # Not needed to close the user's own apps; only for tamper resistance later.
            "administrator": PermissionState.GRANTED if shell32.IsUserAnAdmin() else PermissionState.DENIED,
            "ui_automation": uia,
            "accessibility": PermissionState.NOT_REQUIRED,
            "screen_recording": PermissionState.NOT_REQUIRED,
        }

    def request_permissions(self) -> None:
        # Windows has no per-app consent prompts for anything we use. Elevation can't be granted
        # to a running process; it would need a relaunch through the UAC "runas" verb.
        pass


# ---- helpers ---------------------------------------------------------------------------------


def _window_pid(hwnd) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _window_text(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _top_level_windows() -> list[int]:
    """Visible, titled, unowned top-level windows, i.e. the ones that show in Alt+Tab."""
    found: list[int] = []

    def callback(hwnd, _lparam):
        if (
            user32.IsWindowVisible(hwnd)
            and not user32.GetWindow(hwnd, GW_OWNER)
            and not _GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW
            and user32.GetWindowTextLengthW(hwnd) > 0
        ):
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found


def _uwp_child_pid(hwnd, host_pid: int) -> int | None:
    result: list[int] = []

    def callback(child, _lparam):
        pid = _window_pid(child)
        if pid != host_pid:
            result.append(pid)
            return False
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(callback), 0)
    return result[0] if result else None


def _process(pid: int) -> psutil.Process | None:
    try:
        return psutil.Process(pid)
    except psutil.Error:
        return None


def _proc_name(proc: psutil.Process) -> str:
    try:
        return proc.name().lower()
    except psutil.Error:
        return ""


def _proc_exe(proc: psutil.Process) -> str | None:
    try:
        return proc.exe() or None
    except psutil.Error:  # AccessDenied for elevated processes when we aren't admin
        return None


def _friendly_name(proc: psutil.Process, exe: str | None) -> str:
    """The exe's FileDescription ("Google Chrome"), falling back to its file name ("chrome")."""
    name = _proc_name(proc)
    if name in BROWSERS:
        return BROWSERS[name]
    if exe:
        try:
            import win32api

            langs = win32api.GetFileVersionInfo(exe, r"\VarFileInfo\Translation")
            if langs:
                lang, codepage = langs[0]
                desc = win32api.GetFileVersionInfo(
                    exe, rf"\StringFileInfo\{lang:04x}{codepage:04x}\FileDescription"
                )
                if desc:
                    return str(desc)
        except Exception:  # pywin32 missing, or the exe has no version resource
            pass
        return Path(exe).stem
    return Path(name).stem if name else "Unknown"


def _find_address_bar(root):
    for name in _ADDRESS_BAR_NAMES:
        edit = root.EditControl(Name=name, searchDepth=_UIA_SEARCH_DEPTH)
        if edit.Exists(0, 0):
            return edit
    toolbar = root.ToolBarControl(searchDepth=_UIA_SEARCH_DEPTH)
    if toolbar.Exists(0, 0):
        edit = toolbar.EditControl(searchDepth=4)
        if edit.Exists(0, 0):
            return edit
    return None
