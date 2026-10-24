"""
Apps that aren't really "being used": OS shell surfaces (taskbar, Start, notification centre),
screenshot overlays, and FocusGuard itself. They're left out of time tracking entirely, and switching
to one doesn't count as leaving the app you were in.

Keyed on app_id: lowercased exe names on Windows, lowercased bundle ids on macOS.
"""

IGNORED_APPS = frozenset({
    # Windows shell. explorer.exe is the taskbar, desktop and Alt+Tab as well as File Explorer.
    "explorer.exe",
    "shellexperiencehost.exe",  # notification centre, calendar flyout (Start on Windows 10)
    "shellhost.exe",  # quick settings flyout
    "startmenuexperiencehost.exe",
    "searchhost.exe", "searchapp.exe",  # Start search (Windows 11 / 10)
    "textinputhost.exe",  # emoji panel, clipboard history, touch keyboard
    "widgets.exe",
    "lockapp.exe",
    "applicationframehost.exe",  # Store app frame, when the real app behind it can't be found
    "snippingtool.exe", "screenclippinghost.exe",

    # macOS
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.systemuiserver",
    "com.apple.controlcenter",
    "com.apple.notificationcenterui",
    "com.apple.spotlight",
    "com.apple.loginwindow",
    "com.apple.windowmanager",  # Stage Manager
    "com.apple.screencaptureui", "com.apple.screenshot.launcher",

    # FocusGuard: the focusguard.exe launcher's console window, and the packaged builds.
    "focusguard.exe",
    "com.focusguard.app",
})
