# Arete Features

Arete is a desktop productivity app for students. It stops impulsive decisions without guilt, and turns focus into a climb up three mountains.

## Tracking
- Checks which app or window you're using every second
- Sorts every app as productive, neutral, browser or unproductive, using built-in lists of unproductive apps and sites
- Ignores background and system apps
- Reads which website is open in the browser, on Windows and macOS
- Saves your time every 10 seconds and when the app closes
- Away detection: after 5 minutes with no mouse or keyboard input, the focus session pauses, and "Welcome back!" shows when you return
- Keep-alive helper reopens Arete if it's closed or killed
- Runs with admin rights, hidden from the terminal, and only one copy can run at a time

## Pause Screen
- Opening something unproductive brings up a full-screen "Taking a break with ___?" prompt
- Warm wording: "That's okay! Just let us know what's up."
- You pick a reason:
  - Taking a short break
  - Done with my work for now
  - Need it for school
  - Other (you type why)
  - Emergency
- **"Open anyway" unlocks after a 15 second wait.** Choosing Emergency skips the wait.
- "Back to work" closes the app or tab
- The box wiggles if you click outside it
- After you get through, the same app won't ask again for 10 minutes
- If you're not at a boss, a slip costs 0.33% of the climb, at most once a minute

## Breaks
- A set number of breaks per day (1 to 8, default 4), each 3 to 15 minutes long (default 5)
- A "Break time!" badge counts down in the corner. It fades when your cursor is near and can end the break early.
- A check-in when the break ends: "I'm ready, back to work" or "Still feeling down, continue break"
- When the breaks run out, unproductive apps stay closed until tomorrow, with a kind notification
- Unproductive apps get a warning at 2.5 minutes and close at 3 minutes with "Take a breath, you've got this."

## AI Website Sorting
- New websites are sorted by Google Gemini Flash Lite
- Only the site's public homepage is read, never your screen or the page you're on
- Each answer is remembered, so a site is only checked once
- Up to 100 AI checks per day
- Catches niche web-game sites that blacklists miss, without blocking useful sites like a whitelist would
- The settings tab holds the Gemini key and lists every site checked and how it was sorted

## Focus Sessions
- Choose no timer, 30 minutes, 1 hour, 2 hours or 3 hours
- A live countdown, or count-up for no timer, shows on the home panel. A small timer shows on other pages.
- Ending a timed session early fails it. A no-timer session ends whenever you choose.
- Closing Arete during a session fails it
- Sessions under 10 minutes don't count toward the climb
- A "Session done!" popup shows what you earned and offers "Keep going 30 min"
- Study schedules: Arete starts a focus session on its own when a scheduled study block begins

## The Climb
- Three hand-made mountains: Mount Fuji, then Mount Everest, then the Matterhorn
- Each mountain has 8 named checkpoints, each with its own short message
- You climb 1% per focused hour in a session, scaled by how focused you stayed
- Bounce-back bonus: getting back to work quickly after a break earns up to 0.25%, capped at 1% a day
- Slips cost only 0.33%, so the climb always goes up faster than it goes down
- You never fall below a boss you've already beaten
- The home screen climb card shows a mini map, your %, and your last change (green for a gain, red for a loss)
- The full map page shows:
  - the stage name and message, meters climbed, bosses beaten and the next goal
  - arrows to switch between mountains
  - trees moving in the wind, birds and planes
  - your climber hopping along the trail
  - "Completed" and "Locked" banners

## Bosses
- 9 bosses, 3 per mountain:
  - **Fuji:** The Lantern Keeper, The Ash Spirit, The Fuji Guardian
  - **Everest:** The Icefall Yeti, The Death Zone Wraith, The Everest Guardian
  - **Matterhorn:** The Hornli Troll, The Ridge Eagle, The Matterhorn King
- Each boss blocks the trail. Its health is measured in focus minutes, starting at 45 and growing 25 per boss.
- Every focused minute in a session hits the boss
- Opening a distraction heals the boss 5 minutes, instead of costing climb
- The home screen boss card shows its health bar
- Popups show when a boss appears (it laughs) and when it's defeated (it spins away with confetti)
- Hand-drawn animated characters:
  - glowing eyes that blink
  - flickering flames, drifting embers, rain and lightning, sparkling crown jewels
  - X eyes when hurt

## Home Screen
- "Hello!", the mountain you're currently climbing and a daily streak, with a drifting sun and clouds
- Order: boss card, climb card, focus session, today's stats, today's time tracked, weekly stats
- Stats for today and this week:
  - time focused %, productive hours and rebound speed
  - numbers count up, icons wiggle on hover and status chips show below
- "Show more stats" dropdowns
- Time tracked: a productive vs unproductive bar, plus apps and websites lists

## Settings
- **Changes start 1 hour after saving, then lock for 3 days**, so plans can't be undone on impulse
- Pending changes can be canceled before they start
- Break settings: how many breaks and how long each lasts
- Study schedules: pick the days and times, as many as you want
- AI tab: the Gemini key and the list of sorted sites
- Parental controls:
  - a PIN locks chosen settings
  - the PIN can be changed or turned off
- Testing tools (debug mode only):
  - force quit, reset lock timers, clear memory
  - turn blocking on or off
  - set climb % and beat the current boss

## Look and Feel
- Light and dark themes with an animated sun/moon toggle
- A painted sky behind everything: a sun, clouds and hills by day, stars, a moon and ridges by night
- Rounded see-through cards and a custom rounded scrollbar
- Animations everywhere:
  - page fades and staggered entrances
  - count-ups and expanding dropdowns
  - sliding popups and confetti
- Kind, encouraging wording throughout
- An "A" mountain icon on the window and a snow-capped mountain in the system tray
- Tray notifications

## Behind the Scenes
- Python desktop app for Windows and macOS, built with PySide6 (Qt)
- All data is stored locally on your computer
- Older FocusGuard data is moved over automatically
- One-click setup for developers: pressing F5 in VS Code sets everything up
- A release version would use a local AI model, so no data leaves the computer
