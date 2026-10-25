## Suggested structure

```
cac/
├── readme
├── pyproject.toml
├── src/focusguard/
│   ├── core/                  # 100% portable
│   │   ├── scheduler.py       # random-interval check loop (~2 min with jitter)
│   │   ├── policy.py          # schedule blocks, "is this allowed right now?" logic
│   │   ├── classifier.py      # app/site -> productive / unproductive / unknown
│   │   ├── enforcement.py     # warn -> grace period -> close, escalation rules
│   │   └── models.py          # dataclasses: ActiveWindow, Verdict, Block, etc.
│   │
│   ├── platform/              # the only OS-specific code
│   │   ├── base.py            # abstract interface (below)
│   │   ├── macos.py           # pyobjc: NSWorkspace, Quartz, AppleScript
│   │   ├── windows.py         # pywin32/ctypes, psutil, UI Automation
│   │   └── __init__.py        # picks backend via sys.platform
│   │
│   ├── ai/
│   │   ├── vision.py          # homepage metadata -> productive/not (for unknown sites)
│   │   └── site_memory.py     # domain -> verdict cache
│   │
│   ├── storage/
│   │   ├── db.py              # SQLite
│   │   └── schema.sql         # sessions, app_rules, site_rules, goals, schedules
│   │
│   ├── daemon/
│   │   ├── main.py            # background process that runs the loop
│   │   └── ipc.py             # local socket the UI talks to
│   │
│   └── ui/                    # PySide6 (Qt)
│       ├── tray.py            # menu bar / system tray icon
│       ├── dashboard.py       # stats, streaks, goals
│       ├── schedule_editor.py
│       ├── app_config.py      # mark apps productive/not
└── tests/
```

The interface in `platform/base.py` is the heart of it:

```python
class PlatformBackend(ABC):
    def get_active_window(self) -> ActiveWindow: ...   # app name, bundle id/exe, title, pid
    def get_browser_url(self, app) -> str | None: ...
    def capture_screen(self) -> bytes: ...
    def close_app(self, pid, force=False) -> None: ...
    def install_autostart(self) -> None: ...
    def check_permissions(self) -> dict: ...
```

`core/` only ever calls this interface, so porting to Windows means writing `windows.py` and nothing else.

## Per-OS implementations

| Need | macOS | Windows |
|---|---|---|
| Active app | `NSWorkspace.frontmostApplication()` (pyobjc) | `GetForegroundWindow` + `psutil` |
| Browser URL | AppleScript for Safari/Chrome | UI Automation, or browser extension |
| Screenshot | `mss` or Quartz (needs Screen Recording permission) | `mss` |
| Close app | `NSRunningApplication.terminate()` / `forceTerminate()` | `psutil.Process.terminate()` |
| Run at login | LaunchAgent plist | Task Scheduler or Registry Run key |

## Things worth knowing early

1. **Admin access matters less than you'd think for blocking.** You can close the user's own apps without elevation. It matters for tamper resistance: stopping the user from just killing your daemon or uninstalling it. That's a harder problem on both OSes, and it's where Python is weakest, since a Python process is easy to kill. For a v1 it's fine, but consider the friction design (see 4).
2. **macOS permissions are the main hurdle.** You'll need Accessibility and Screen Recording, and these are granted per app bundle. That means you'll have to package it (py2app) and eventually code-sign and notarize it. Developing from a bare terminal grants permissions to the terminal, not your app.
3. **Browser extension beats screenshots for sites.** A small extension that reports the current URL to the daemon over a local websocket or native messaging is more reliable and works on both OSes. Keep your screenshot + vision method as the fallback for unknown sites, as you described. It also cuts API cost and the privacy concern of screenshotting constantly.
4. **Self-control design.** Since the user controls the tool, nothing stops them from disabling it at 4pm. Options: a cooldown (changes to schedules take effect after 24h), locking settings behind a password that a friend sets, or a "commitment mode" that can't be turned off mid-block.
5. **Split the daemon from the UI.** The enforcement loop should run in a background process that survives the UI being closed. Connect them with local IPC, with SQLite as the shared state.

## Tooling

- **UI:** PySide6 (Qt) is the best fit for native-feeling cross-platform tray and overlay windows.
- **Packaging:** PyInstaller (Windows) and py2app (macOS).
- **Libraries:** `psutil`, `mss`, `pyobjc` (macOS only), `pywin32`/`uiautomation` (Windows only), `APScheduler` is optional since a simple jittered loop is enough.

I'd build the macOS backend first with the `core/` logic and a minimal tray UI, then add Windows once the interface has settled. If you'd like, I can scaffold this repo and write the `PlatformBackend` interface plus a working macOS `get_active_window`, or put this into the project as a spec doc.