# FocusGuard

A productivity agent for students. You decide which apps and sites are productive and when you're
supposed to be working; FocusGuard checks what you're actually doing at random ~2 minute intervals
and warns you, then closes the app, if you're off task during a scheduled block.

See [projectStructure.md](projectStructure.md) for the architecture.

## Status

Scaffold only. What works today:

- `platform/`: full macOS and Windows backends (active window, browser URL, screenshots,
  closing apps, autostart, permissions, idle time, overlay window setup).
- `ui/warning_overlay.py`: an always-on-top overlay showing the current app/window, and the site
  root when the frontmost app is a browser (Helium, Chrome and Arc are hard-coded for now).

Everything else (`core/`, `ai/`, `storage/`, `daemon/`, the other UI screens) is stubbed out.

## Running

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/focusguard
```

### macOS permissions

When running from a terminal, macOS grants permissions to the terminal app, not to FocusGuard:

- **Accessibility**: needed for reliable window titles. System Settings → Privacy & Security → Accessibility.
- **Automation**: the first time each browser is in front, macOS asks whether the terminal may control
  it. Allow it, or the overlay can't read the URL.
- **Screen Recording**: only needed later for screenshots, and as a fallback for window titles.

May parth bless suprathik
