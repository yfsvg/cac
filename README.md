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

- Testing without the lock: run `.venv/bin/focusguard --debug` (setting `FOCUSGUARD_DEBUG=1` or starting it from the VS Code debugger does the same). In debug mode:
  - Ctrl+C closes it, it stays in the terminal, and nothing reopens it
  - there's no Windows admin prompt
  - settings show Force quit, Reset lock timers and Clear all memory, plus an Apply now button that skips the 1 hour wait
  - the startup screen has a 15 sec (testing) option
- Emergency stop on Windows: `taskkill /F /IM pythonw.exe` from an admin terminal (FocusGuard runs as admin)

### Windows admin rights
FocusGuard checks for admin rights when it starts. If it doesn't have them it shows the UAC prompt: Yes restarts it as admin, No closes it.

### Settings and parental controls
- A settings change starts 1 hour after you save it, so it's never made on impulse. You can cancel it during that hour. Once it starts, that setting stays locked for 3 days.
- The parent PIN is never saved. Only a salted scrypt hash of it is, and a PIN saved by an older version is converted the next time FocusGuard starts.

### Gemini key
Paste the key in Settings > AI Categorizations. It's saved only on that computer (`%APPDATA%\FocusGuard`), never in the repo.

### macOS permissions

When running from a terminal, macOS grants permissions to the terminal app, not to FocusGuard:

### to build
go to the actions tab and click the "Build" action on the left. click run action. wait a bit, and then you'll see the zipped executables :)
these, to my knowledge, contain all of the binaries within so they can be shared with anybody without issue


May parth bless suprathik
