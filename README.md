## Features

Everything Arete does right now, grouped by part of the app.

### Tracking
- checks what app or window you're on every second
- sorts apps into productive, neutral, browser or unproductive
- skips background and system apps
- reads what website you're on in the browser (Windows and Mac)
- saves your time every 10 seconds and when the app closes
- if you don't touch the mouse or keyboard for 5 min, your session pauses and it says welcome back when you return
- a helper process reopens Arete if someone closes or kills it
- only one copy can run at a time

### Pause screen
- opening something unproductive brings up a "Taking a break with ___?" screen
- you pick a reason: short break, done with work, need it for school, other (you have to type it), or emergency
- you have to wait 15 seconds before "Open anyway" works, emergency skips the wait
- "Back to work" closes the app or tab for you
- clicking outside the box makes it shake
- once you get past it, that app won't ask again for 10 min
- slipping costs 0.33% of your climb (max once a minute)

### Breaks
- you get a number of breaks a day (1 to 8, default 4), each 3 to 15 min (default 5)
- a "Break time!" badge counts down in the corner, it fades when your mouse gets close and has an X to end early
- when the break ends it checks in: "I'm ready, back to work" or "Still feeling down, continue break"
- once you're out of breaks, unproductive apps stay closed until tomorrow
- unproductive apps give a warning at 2.5 min and close at 3 min

### AI website sorting
- new sites get sorted by Gemini Flash Lite
- it only reads the site's public homepage, not your screen
- it remembers every site so it only checks once
- max 100 checks a day
- catches random game sites a blacklist would miss, without blocking useful sites like a whitelist
- the AI tab in settings has the Gemini key and every site it has sorted

### Focus sessions
- no timer, 30 min, 1 hr, 2 hr or 3 hr
- live timer on the home screen, and a small one on other pages
- ending a timed session early fails it, no-timer sessions end whenever you want
- closing Arete during a session fails it
- sessions under 10 min don't count
- when it's done you see what you earned and can keep going 30 more min
- study schedules start a session on their own when your study time starts

### The climb
- 3 mountains: Fuji, then Everest, then the Matterhorn
- each one has 8 checkpoints with a name and a message
- you go up 1% per focused hour in a session, based on how focused you were
- bounce back bonus for getting back to work fast after a break (up to 0.25%, max 1% a day)
- slips only cost 0.33%, so you always go up faster than you go down
- you can't fall below a boss you already beat
- the climb card on the home screen has a mini map, your %, and your last change (green or red)
- the map page has your stage, meters, bosses beaten, next goal, arrows to switch mountains, trees that move in the wind, birds and planes, your climber hopping along, and completed / locked banners

### Bosses
- 9 bosses, 3 per mountain
  - Fuji: Lantern Keeper, Ash Spirit, Fuji Guardian
  - Everest: Icefall Yeti, Death Zone Wraith, Everest Guardian
  - Matterhorn: Hornli Troll, Ridge Eagle, Matterhorn King
- boss health is in focus minutes, the first has 45 and each one after has 25 more
- every focused minute in a session hits it
- opening a distraction heals it 5 min instead of dropping your climb
- boss card on the home screen with a health bar
- popup when a boss shows up (it laughs) and when you beat it (it spins away with confetti)
- all hand drawn and animated, with glowing eyes, blinking, flames, rain and lightning, and X eyes when it gets hit

### Home screen
- says hello, what mountain you're on, and your streak
- order: boss, climb, focus session, today's stats, today's time tracked, weekly stats
- stats for today and the week: time focused, productive hours, rebound speed
- "show more stats" dropdowns
- productive vs unproductive bar plus apps and websites lists

### Settings
- changes start 1 hour after you save them, then lock for 3 days
- you can cancel a change before it starts
- break count and length
- study schedules, as many as you want
- AI tab
- parental controls with a PIN that locks the settings you pick
- testing tools in debug mode (force quit, reset locks, clear memory, blocking switch, set climb %, beat boss)

### Look
- light and dark mode with a sun / moon button
- painted sky in the back, day has sun, clouds and hills, night has stars, moon and ridges
- see through rounded cards and a rounded scrollbar
- animations on pretty much everything
- friendly wording, nothing guilt trippy
- "A" mountain icon on the window, mountain icon in the tray

### Other
- Python desktop app with PySide6, runs on Windows and Mac
- all data is saved on your own computer
- old FocusGuard data moves over by itself
- F5 in VS Code sets everything up

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
