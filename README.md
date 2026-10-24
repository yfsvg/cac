## Running

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/focusguard
```

cd cac
.venv/bin/focusguard

### Focus sessions
When FocusGuard opens it asks how long you want to be productive for. Until that time is up it can't be closed:
Ctrl+C is ignored, it leaves the terminal, and a helper reopens it if it's killed. When the time is up a message
lets you close it or keep going for 30 more minutes. A bail-out (the x on the session badge) ends it early.

- Testing without the lock: set `FOCUSGUARD_DEBUG=1` before running (also shows the debug buttons in settings).
- Emergency stop on Windows: `taskkill /F /IM pythonw.exe`

### Gemini key
Paste the key in Settings > AI Categorizations. It's saved only on that computer (`%APPDATA%\FocusGuard`), never in the repo.

### macOS permissions

When running from a terminal, macOS grants permissions to the terminal app, not to FocusGuard:

### to build
go to the actions tab and click the "Build" action on the left. click run action. wait a bit, and then you'll see the zipped executables :)
these, to my knowledge, contain all of the binaries within so they can be shared with anybody without issue


May parth bless suprathik
