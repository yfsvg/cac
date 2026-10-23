"""macOS backend: AppKit / Accessibility / Quartz via pyobjc, browsers via AppleScript."""

from __future__ import annotations

import logging
import os
import plistlib
import subprocess
from pathlib import Path

import objc
import psutil
import Quartz
from Foundation import NSActivityUserInitiatedAllowingIdleSystemSleep, NSProcessInfo
from AppKit import (
    NSAppearance,
    NSAppearanceNameVibrantDark,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSBundle,
    NSRunningApplication,
    NSStatusWindowLevel,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialHUDWindow,
    NSVisualEffectStateActive,
    NSVisualEffectView,
    NSWindowBelow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWorkspace,
)
from ApplicationServices import (
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    AXUIElementGetPid,
    kAXErrorSuccess,
    kAXFocusedApplicationAttribute,
    kAXFocusedWindowAttribute,
    kAXTitleAttribute,
    kAXTrustedCheckOptionPrompt,
)

from focusguard.core.models import ActiveWindow, PermissionState, RunningApp
from focusguard.platform.base import AUTOSTART_LABEL, PlatformBackend

log = logging.getLogger(__name__)

# Hard-coded for now; will come from the user's app config later.
BROWSERS = {
    "com.google.Chrome": "Google Chrome",
    "com.microsoft.edgemac": "Microsoft Edge",
    "org.mozilla.firefox": "Mozilla Firefox",
    "com.apple.Safari": "Apple Safari",
    "com.operasoftware.Opera": "Opera",
    "com.brave.Browser": "Brave",
    "company.thebrowser.browser": "Arc",
    "com.vivaldi.Vivaldi": "Vivaldi",
    "org.waterfox.waterfox": "Waterfox",
    "org.torproject.torbrowser": "Tor Browser",
    "io.gitlab.librewolf-community.librewolf": "LibreWolf",
    "com.mullvad.vpn.browser": "Mullvad Browser",
    "com.maxthon.mac.Maxthon": "Maxthon",
    "com.yandex.MacBrowser": "Yandex Browser",
    "com.duckduckgo.macos": "DuckDuckGo",
    "org.chromium.Chromium": "Chromium",
    "org.mozilla.seamonkey": "SeaMonkey",
    "net.imput.helium": "Helium"
}

# All three are Chromium-based and share Chrome's AppleScript dictionary.
_URL_SCRIPT = """
tell application id "{bundle_id}"
    if (count of windows) is 0 then return ""
    return URL of active tab of front window
end tell
"""

_OSASCRIPT_TIMEOUT = 2.0
_ANY_INPUT_EVENT = getattr(Quartz, "kCGAnyInputEventType", 0xFFFFFFFF)


class MacOSBackend(PlatformBackend):
    BROWSER_IDS = frozenset(k.lower() for k in BROWSERS)

    # ---- what is the user doing ------------------------------------------------------------

    def get_active_window(self) -> ActiveWindow | None:
        app = self._frontmost_app()
        if app is None:
            return None
        pid = int(app.processIdentifier())
        window_id, cg_title = self._front_cg_window(pid)
        title = self._ax_focused_window_title(pid) or cg_title or ""
        exe_url = app.executableURL()
        return ActiveWindow(
            app_name=str(app.localizedName() or ""),
            app_id=str(app.bundleIdentifier() or "").lower() or _exe_name(exe_url),
            pid=pid,
            title=title,
            exe_path=str(exe_url.path()) if exe_url else None,
            window_handle=window_id,
        )


    def get_app_category(self, window: ActiveWindow) -> str | None:
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(window.pid)
        bundle = app and app.bundleURL() and NSBundle.bundleWithURL_(app.bundleURL())
        return bundle and bundle.objectForInfoDictionaryKey_("LSApplicationCategoryType")

    def get_browser_url(self, window: ActiveWindow) -> str | None:
        if not self.is_browser(window):
            return None
        # Bundle ids are case-insensitive to AppleScript, so the lowercased app_id is fine.

        script = _URL_SCRIPT.format(bundle_id=window.app_id)
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=_OSASCRIPT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            log.warning("Timed out reading URL from %s", window.app_name)
            return None
        if result.returncode != 0:
            # -1743 means the user hasn't allowed Automation for this browser.
            log.debug("osascript failed for %s: %s", window.app_name, result.stderr.strip())
            return None
        return result.stdout.strip() or None

    def list_running_apps(self) -> list[RunningApp]:
        apps = []
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            if app.activationPolicy() != NSApplicationActivationPolicyRegular:
                continue
            exe_url = app.executableURL()
            apps.append(
                RunningApp(
                    app_name=str(app.localizedName() or ""),
                    app_id=str(app.bundleIdentifier() or "").lower() or _exe_name(exe_url),
                    pid=int(app.processIdentifier()),
                    exe_path=str(exe_url.path()) if exe_url else None,
                )
            )
        return apps

    def get_idle_seconds(self) -> float:
        return float(
            Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateCombinedSessionState, _ANY_INPUT_EVENT
            )
        )

    # ---- enforcement -----------------------------------------------------------------------

    def close_app(self, pid: int, force: bool = False) -> bool:
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is not None:
            return bool(app.forceTerminate() if force else app.terminate())
        try:
            proc = psutil.Process(pid)
            proc.kill() if force else proc.terminate()
            return True
        except psutil.Error:
            return False

    def hide_from_taskbar(self) -> None:
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._no_app_nap = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
            NSActivityUserInitiatedAllowingIdleSystemSleep, "FocusGuard tracks the active app"
        )

    def float_above_everything(self, win_id: int) -> None:
        window = objc.objc_object(c_void_p=win_id).window()
        window.setLevel_(NSStatusWindowLevel)
        window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def get_window_rect(self, window: ActiveWindow) -> tuple[int, int, int, int] | None:
        if not window.window_handle:
            return None
        info = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionIncludingWindow, window.window_handle
        ) or []
        if len(info) == 0:
            return None
        bounds = info[0][Quartz.kCGWindowBounds]
        return int(bounds["X"]), int(bounds["Y"]), int(bounds["Width"]), int(bounds["Height"])

    def blur_behind(self, win_id: int, corner_radius: float = 0) -> None:
        # qts winId on mac is the NSView it draws into, draw blur beneath
        qt_view = objc.objc_object(c_void_p=win_id)
        frame_view = qt_view.superview()
        blur = NSVisualEffectView.alloc().initWithFrame_(frame_view.bounds())

        blur.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        blur.setMaterial_(NSVisualEffectMaterialHUDWindow)
        blur.setState_(NSVisualEffectStateActive)
        blur.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameVibrantDark))
        blur.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        blur.setWantsLayer_(True)
        blur.layer().setCornerRadius_(corner_radius)
        blur.layer().setMasksToBounds_(True)
        # unfortunately native app le doesnt have a blur strength parameter. Its just ugly blur for now haha

        frame_view.addSubview_positioned_relativeTo_(blur, NSWindowBelow, qt_view)

    @property
    def _launch_agent_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{AUTOSTART_LABEL}.plist"

    def install_autostart(self) -> None:
        log_path = Path.home() / "Library" / "Logs" / "FocusGuard.log"
        plist = {
            "Label": AUTOSTART_LABEL,
            "ProgramArguments": self.daemon_command(),
            "RunAtLoad": True,
            # Relaunch if the daemon is killed, so quitting it isn't an easy escape.
            "KeepAlive": True,
            "ProcessType": "Interactive",
            "StandardOutPath": str(log_path),
            "StandardErrorPath": str(log_path),
        }
        path = self._launch_agent_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.is_autostart_installed():
            self.uninstall_autostart()
        with path.open("wb") as f:
            plistlib.dump(plist, f)
        subprocess.run(["launchctl", "bootstrap", _gui_domain(), str(path)], check=True)

    def uninstall_autostart(self) -> None:
        # bootout fails harmlessly if the agent isn't loaded.
        subprocess.run(
            ["launchctl", "bootout", f"{_gui_domain()}/{AUTOSTART_LABEL}"],
            capture_output=True,
        )
        self._launch_agent_path.unlink(missing_ok=True)

    def is_autostart_installed(self) -> bool:
        return self._launch_agent_path.exists()

    def check_permissions(self) -> dict[str, PermissionState]:
        return {
            "accessibility": _state(AXIsProcessTrusted()),
            "screen_recording": _state(Quartz.CGPreflightScreenCaptureAccess()),
            # macOS has no way to check Automation consent without possibly prompting.
            "automation": PermissionState.UNKNOWN,
        }

    def request_permissions(self) -> None:
        if not AXIsProcessTrusted():
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        if not Quartz.CGPreflightScreenCaptureAccess():
            Quartz.CGRequestScreenCaptureAccess()

    # ---- internals -------------------------------------------------------------------------

    def _frontmost_app(self) -> NSRunningApplication | None:
        # NSWorkspace only refreshes frontmostApplication while a run loop is spinning on the
        # main thread. The Accessibility API is always current, so prefer it when we're trusted.
        if AXIsProcessTrusted():
            err, focused = AXUIElementCopyAttributeValue(
                AXUIElementCreateSystemWide(), kAXFocusedApplicationAttribute, None
            )
            if err == kAXErrorSuccess and focused is not None:
                err, pid = AXUIElementGetPid(focused, None)
                if err == kAXErrorSuccess:
                    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                    if app is not None:
                        return app
        return NSWorkspace.sharedWorkspace().frontmostApplication()

    @staticmethod
    def _ax_focused_window_title(pid: int) -> str | None:
        if not AXIsProcessTrusted():
            return None
        app_el = AXUIElementCreateApplication(pid)
        err, window = AXUIElementCopyAttributeValue(app_el, kAXFocusedWindowAttribute, None)
        if err != kAXErrorSuccess or window is None:
            return None
        err, title = AXUIElementCopyAttributeValue(window, kAXTitleAttribute, None)
        if err != kAXErrorSuccess or not title:
            return None
        return str(title)

    @staticmethod
    def _front_cg_window(pid: int) -> tuple[int | None, str | None]:
        """(CGWindowID, title) of `pid`'s frontmost normal window. Title needs Screen Recording."""
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        ) or []
        # The list is in front-to-back order; layer 0 is ordinary app windows.
        for info in windows:
            if info.get(Quartz.kCGWindowOwnerPID) == pid and info.get(Quartz.kCGWindowLayer) == 0:
                title = info.get(Quartz.kCGWindowName)
                return int(info[Quartz.kCGWindowNumber]), str(title) if title else None
        return None, None


def _exe_name(exe_url) -> str:
    return exe_url.lastPathComponent().lower() if exe_url else ""


def _gui_domain() -> str:
    return f"gui/{os.getuid()}"


def _state(granted: bool) -> PermissionState:
    return PermissionState.GRANTED if granted else PermissionState.DENIED
