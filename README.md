## Running

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/arete
```

cd cac
.venv/bin/arete

### Focus sessions
When Arete opens it asks how long you want to be productive for. Until that time is up it can't be closed:
Ctrl+C is ignored, it leaves the terminal, and a helper reopens it if it's killed. When the time is up you see how far
you climbed, and you can stop or keep going for 30 more minutes.

### The Climb
Click The Climb on the home screen to see your mountain: Mount Fuji, then Everest, then the Matterhorn.
- A session moves you up 1% per hour (at least 0.5%), times how much of it you were focused.
- Opening something unproductive drops you 0.33%, at most once a minute.
- Each mountain has 3 bosses (9 in total), each with its own character. A boss stops your climb until you beat it.
- Bosses have health measured in focus minutes (45 for the first, 25 more for each one after). Every minute you stay focused in a session hits the boss, and opening something unproductive heals it 5 minutes. Beaten bosses are never lost.

- Testing without the lock: run `.venv/bin/arete --debug` (setting `ARETE_DEBUG=1` or starting it from the VS Code debugger does the same). In debug mode:
  - Ctrl+C closes it, it stays in the terminal, and nothing reopens it
  - there's no Windows admin prompt
  - settings show Force quit, Reset lock timers and Clear all memory, plus an Apply now button that skips the 1 hour wait
  - settings also have a Blocking on switch, a box to set your climb % (0 to 300 across all 3 mountains) and a Beat boss now button
  - the startup screen has a 15 sec (testing) option
- Emergency stop on Windows: `taskkill /F /IM pythonw.exe` from an admin terminal (Arete runs as admin)

### Windows admin rights
Arete checks for admin rights when it starts. If it doesn't have them it shows the UAC prompt: Yes restarts it as admin, No closes it.

### Settings and parental controls
- A settings change starts 1 hour after you save it, so it's never made on impulse. You can cancel it during that hour. Once it starts, that setting stays locked for 3 days.
- The parent PIN is never saved. Only a salted scrypt hash of it is, and a PIN saved by an older version is converted the next time Arete starts.

### Gemini key
Paste the key in Settings > AI Categorizations. It's saved only on that computer (`%APPDATA%\Arete`), never in the repo.

### macOS permissions

When running from a terminal, macOS grants permissions to the terminal app, not to Arete:

### to build
go to the actions tab and click the "Build" action on the left. click run action. wait a bit, and then you'll see the zipped executables :)
these, to my knowledge, contain all of the binaries within so they can be shared with anybody without issue


May parth bless suprathik
