# OS stuff (taskbar, start menu, finder, dock etc) + focusguard itself
# never tracked counted or closed

IGNORED_APPS = frozenset({
    "explorer.exe",
    "shellexperiencehost.exe",
    "shellhost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe", "searchapp.exe",
    "textinputhost.exe",
    "widgets.exe",
    "lockapp.exe",
    "applicationframehost.exe",
    "snippingtool.exe", "screenclippinghost.exe",
    # mac
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.systemuiserver",
    "com.apple.controlcenter",
    "com.apple.notificationcenterui",
    "com.apple.spotlight",
    "com.apple.loginwindow",
    "com.apple.windowmanager",
    "com.apple.screencaptureui", "com.apple.screenshot.launcher",
    # us
    "focusguard.exe",
    "com.focusguard.app",
})
