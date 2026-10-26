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

from arete.core.models import ActiveWindow, PermissionState, RunningApp
from arete.platform.base import AUTOSTART_LABEL, PlatformBackend

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
URL_SCRIPT = """
tell application id "{bundleId}"
    if (count of windows) is 0 then return ""
    return URL of active tab of front window
end tell
"""

SAFARI_URL_SCRIPT = """
tell application id "com.apple.safari"
    if (count of windows) is 0 then return ""
    return URL of current tab of front window
end tell
"""

CHROME_FAMILY = (
    "com.google.chrome",
    "com.microsoft.edgemac",
    "com.brave.browser",
    "com.vivaldi.vivaldi",
    "org.chromium.chromium",
)

OSASCRIPT_TIMEOUT = 2.0
ANY_INPUT_EVENT = getattr(Quartz, "kCGAnyInputEventType", 0xFFFFFFFF)


class MacOSBackend(PlatformBackend):
    BROWSER_IDS = frozenset(k.lower() for k in BROWSERS)

    #what is the user doing

    def get_active_window(self) -> ActiveWindow | None:
        app = self.frontmostApp()
        if app is None:
            return None
        pid = int(app.processIdentifier())
        windowId, cgTitle = self.frontCgWindow(pid)
        title = self.axFocusedWindowTitle(pid) or cgTitle or ""
        exeUrl = app.executableURL()
        return ActiveWindow(
            app_name=str(app.localizedName() or ""),
            app_id=str(app.bundleIdentifier() or "").lower() or exeName(exeUrl),
            pid=pid,
            title=title,
            exe_path=str(exeUrl.path()) if exeUrl else None,
            window_handle=windowId,
        )


    def get_app_category(self, window: ActiveWindow) -> str | None:
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(window.pid)
        bundle = app and app.bundleURL() and NSBundle.bundleWithURL_(app.bundleURL())
        return bundle and bundle.objectForInfoDictionaryKey_("LSApplicationCategoryType")

    def get_browser_url(self, window: ActiveWindow) -> str | None:
        if not self.is_browser(window):
            return None
        # Bundle ids are case-insensitive to AppleScript, so the lowercased app_id is fine.

        script = URL_SCRIPT.format(bundleId=window.app_id)
        if window.app_id == "com.apple.safari":
            script = SAFARI_URL_SCRIPT
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=OSASCRIPT_TIMEOUT,
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
            exeUrl = app.executableURL()
            apps.append(
                RunningApp(
                    app_name=str(app.localizedName() or ""),
                    app_id=str(app.bundleIdentifier() or "").lower() or exeName(exeUrl),
                    pid=int(app.processIdentifier()),
                    exe_path=str(exeUrl.path()) if exeUrl else None,
                )
            )
        return apps

    def get_idle_seconds(self) -> float:
        return float(
            Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateCombinedSessionState, ANY_INPUT_EVENT
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

    def close_tab(self, window: ActiveWindow) -> bool:
        if window.app_id == "com.apple.safari":
            script = 'tell application id "com.apple.safari" to close current tab of front window'
        elif window.app_id in CHROME_FAMILY:
            script = 'tell application id "' + window.app_id + '" to close active tab of front window'
        else:
            script = (
                'tell application id "' + window.app_id + '" to activate\n'
                'delay 0.2\n'
                'tell application "System Events" to keystroke "w" using command down'
            )
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=OSASCRIPT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False
        return result.returncode == 0

    def hide_from_taskbar(self) -> None:
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self.noAppNap = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
            NSActivityUserInitiatedAllowingIdleSystemSleep, "Arete tracks the active app"
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

    def blur_behind(self, win_id: int, corner_radius: float = 0) -> bool:
        # qts winId on mac is the NSView it draws into, draw blur beneath
        qtView = objc.objc_object(c_void_p=win_id)
        frameView = qtView.superview()
        blur = NSVisualEffectView.alloc().initWithFrame_(frameView.bounds())

        blur.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        blur.setMaterial_(NSVisualEffectMaterialHUDWindow)
        blur.setState_(NSVisualEffectStateActive)
        blur.setAppearance_(NSAppearance.appearanceNamed_(NSAppearanceNameVibrantDark))
        blur.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        blur.setWantsLayer_(True)
        blur.layer().setCornerRadius_(corner_radius)
        blur.layer().setMasksToBounds_(True)
        # unfortunately native app le doesnt have a blur strength parameter. Its just ugly blur for now haha

        frameView.addSubview_positioned_relativeTo_(blur, NSWindowBelow, qtView)
        return True

    @property
    def launchAgentPath(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{AUTOSTART_LABEL}.plist"

    def install_autostart(self) -> None:
        logPath = Path.home() / "Library" / "Logs" / "Arete.log"
        plist = {
            "Label": AUTOSTART_LABEL,
            "ProgramArguments": self.daemon_command(),
            "RunAtLoad": True,
            # Relaunch if the daemon is killed, so quitting it isn't an easy escape.
            "KeepAlive": True,
            "ProcessType": "Interactive",
            "StandardOutPath": str(logPath),
            "StandardErrorPath": str(logPath),
        }
        path = self.launchAgentPath
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.is_autostart_installed():
            self.uninstall_autostart()
        with path.open("wb") as f:
            plistlib.dump(plist, f)
        subprocess.run(["launchctl", "bootstrap", guiDomain(), str(path)], check=True)

    def uninstall_autostart(self) -> None:
        # bootout fails harmlessly if the agent isn't loaded.
        subprocess.run(
            ["launchctl", "bootout", f"{guiDomain()}/{AUTOSTART_LABEL}"],
            capture_output=True,
        )
        self.launchAgentPath.unlink(missing_ok=True)

    def is_autostart_installed(self) -> bool:
        return self.launchAgentPath.exists()

    def check_permissions(self) -> dict[str, PermissionState]:
        return {
            "accessibility": stateFor(AXIsProcessTrusted()),
            "screen_recording": stateFor(Quartz.CGPreflightScreenCaptureAccess()),
            # macOS has no way to check Automation consent without possibly prompting.
            "automation": PermissionState.UNKNOWN,
        }

    def request_permissions(self) -> None:
        if not AXIsProcessTrusted():
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        if not Quartz.CGPreflightScreenCaptureAccess():
            Quartz.CGRequestScreenCaptureAccess()

    # ---- internals -------------------------------------------------------------------------

    def frontmostApp(self) -> NSRunningApplication | None:
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
    def axFocusedWindowTitle(pid: int) -> str | None:
        if not AXIsProcessTrusted():
            return None
        appElement = AXUIElementCreateApplication(pid)
        err, window = AXUIElementCopyAttributeValue(appElement, kAXFocusedWindowAttribute, None)
        if err != kAXErrorSuccess or window is None:
            return None
        err, title = AXUIElementCopyAttributeValue(window, kAXTitleAttribute, None)
        if err != kAXErrorSuccess or not title:
            return None
        return str(title)

    @staticmethod
    def frontCgWindow(pid: int) -> tuple[int | None, str | None]:
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


def exeName(exeUrl) -> str:
    return exeUrl.lastPathComponent().lower() if exeUrl else ""


def guiDomain() -> str:
    return f"gui/{os.getuid()}"


def stateFor(granted: bool) -> PermissionState:
    return PermissionState.GRANTED if granted else PermissionState.DENIED
