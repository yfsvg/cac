# FocusGuard

A productivity agent for students. You decide which apps and sites are productive and when you're
supposed to be working; FocusGuard checks what you're actually doing at random ~2 minute intervals
and warns you, then closes the app, if you're off task during a scheduled block.

See [projectStructure.md](projectStructure.md) for the architecture.

## Status

Work in progress. What works today:

- `platform/`: full macOS and Windows backends (active window, browser URL, screenshots,
  closing apps, autostart, permissions, idle time).
- Side panel: shows the current app, with minimise (–), hide (✕) and a **Close** button.
- Tray / menu bar icon: click it to open/hide the side panel (Windows and Mac).
- PIN to close: the **Close** button is the only way to quit, and it asks for the PIN. Ctrl+C,
  closing the terminal and Task Manager / Force Quit don't stop it (a helper process restarts it).
- Parental controls: the **Parental Controls** button in the panel asks for the PIN, then opens a window
  for blocked apps, blocked sites, study times, apps/sites allowed while studying, daily time limits
  and changing the PIN. Every 5 seconds FocusGuard checks the app in front; if it breaks a rule it
  warns you, then closes it after 30 seconds.

Still stubbed out: `core/`, `ai/`, `daemon/`, the other UI screens.

## Running

Windows:

```bash
cd cac
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\focusguard
```

macOS:

```bash
cd cac
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/focusguard
```

The app moves itself into the background, so the terminal frees up right away.

### PIN and settings

- The first time you press **Close**, it asks you to create a PIN. After that, closing needs that PIN.
- Settings and the PIN are saved in `src/focusguard/storage/memory.dat`, created on first run. It's
  in `.gitignore`, so everyone gets their own. Delete it to reset your PIN.
- Open the parental controls window on its own with `python -m focusguard.ui.parental_controls`.

### Emergency stop (without the PIN)

- Windows: `taskkill /F /IM pythonw.exe`
- macOS: `pkill -9 -f focusguard`

### macOS permissions

When running from a terminal, macOS grants permissions to the terminal app, not to FocusGuard:

- **Accessibility**: needed for reliable window titles. System Settings → Privacy & Security → Accessibility.
- **Automation**: the first time each browser is in front, macOS asks whether the terminal may control
  it. Allow it, or the browser URL can't be read.
- **Screen Recording**: only needed later for screenshots, and as a fallback for window titles.

May parth bless suprathik
