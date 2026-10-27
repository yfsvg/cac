## Hello Congressional App Judges! tdlr things to know:
1. Arete is built on purpose to be really hard to close (that's kind of the whole point because its for students that have low impules control and high procrastination). So PLEASE run it in **debug mode** or you won't be able to get rid of it. Debug mode gives you a Force quit button and lets Ctrl+C work. How to turn it on is right below in "How to access". It's also usually possible to kill if you use task manager or activity monitor and kill all python processes at once (both app + helper)
2. Arete doesn't open a normal window. It lives up in your **menu bar (Mac) or system tray (Windows)**, click the purple mountain stopwatch icon to open the dashboard. you can probably also check the video on mac to see where its at
3. Sorting websites with AI needs a gemini ai api key. Paste it in Settings > AI Categorizations. Without one Arete still works, it just only knows the sites already on its hardcoded blacklist. We used one in private for our vieo and testing, although ofc if you email us we'd be more than happy to provide the key we used if youre guys interested in testing.



Also forgot to say this in the demo video but we used AI to help solve difficult merges

***

# Arete

A productivity app for students that you control yourself, no parents or teachers locking you out. It watches what app or website you're on, and when you open something unproductive it doesn't just slam it shut, it pauses you and asks what's up. You get a few breaks a day, and once those run out the distractions stay closed until tomorrow.

To make it actually fun, every focused minute climbs you up a mountain: Mount Fuji, then Everest, then the Matterhorn. There are 9 bosses blocking the trail that you beat by staying focused. Stay on task = go up, slack off = slide down a tiny bit.

Everything is saved on your own computer, nothing goes anywhere except the website check (and even that only reads the site's public homepage, never your screen).

***

# How to access

Download it from the **Releases** page on the right side of the GitHub repo (v1.0.0), there's a Mac zip and a Windows zip.

- **Mac:** unzip and move Arete to Appilcations. It's not from the App Store so the first time you have to **right click > Open**. To run it in debug mode open Terminal and type `open /Applications/Arete.app --args --debug`
- **Windows:** unzip and run Arete.exe, if Windows warns you click **More info > Run anyway**. To run it in debug mode open a terminal in that folder and type `Arete.exe --debug`

You can also run it straight from the code, which is the better option if you want to check on it:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/arete --debug
```

or just open the folder in VS Code and press **F5**, it sets everything up by itself and runs in debug mode automatically.

## Mac permissions

The first time it runs, macOS asks for a few permissions. Arete can't see what you're doing without them:
- **Accessibility** so it can see which app you're on
- **Automation** so it can read the website in your browser (macOS asks once per browser)
- **Screen Recording** so it can read window titles. It doesn't record or screenshot anything, macOS just puts window titles under that permission for some reason

If you run it from a terminal, macOS gives the permissions to the terminal app instead of Arete, that's normal.

On Windows it asks for admin when it starts (it closes apps for you, so it needs it). Debug mode skips that.

***

# How to use

## Focus sessions

On the home screen pick how long you want to focus: no timer, 30 min, 1 hour, 2 hours or 3 hours. A timer shows up and every minute you're on something productive counts. When it's done you see how far you climbed and you can keep going for 30 more minutes.

Timed sessions are a promise to yourself, so ending one early or closing Arete fails it and it doesn't count. No timer sessions end whenever you want. Sessions under 10 minutes don't count, and if you walk away from the computer for 5 minutes your session pauses and welcomes you back.

You can also set study times in settings (as many as you want), and Arete starts a session for you when one begins.

## The pause screen

Open something unproductive and you get a "Taking a break with ___?" screen. Pick why: short break, done with work, need it for school, other (you have to type it out), or emergency. You have to wait 15 seconds before "Open anyway" works, emergency skips the wait. "Back to work" closes it for you.

Once you get past it, that app won't ask again for 10 minutes.

## Breaks

You get breaks every day (4 by default, 1 to 8) and each one is 5 minutes by default (3 to 15). A little badge counts down in the corner, it fades when your mouse gets near so you can see under it. When the break ends it checks in with you: back to work, or keep the break going.

If you stay on something unproductive outside a break, you get a heads up at 2.5 minutes and it closes at 3. Once you're out of breaks for the day, unproductive apps just stay closed until tomorrow.

## The climb

Click open map on the climb card to see your mountain. Each mountain has 8 checkpoints, all with their own name and message.

- a fully focused hour in a session = **1%** up the mountain
- getting back to work fast after a break = a little bonus (up to 0.25%, max 1% a day)
- opening something unproductive = **0.33%** down (at most once a minuet)

so you always go up way faster than you go down (part of our emotional design philosophy)


## Bosses

There are 9 bosses, 3 on each mountain, and each one blocks the trail until you beat it. This is in order of what way they are in the app:
1. Fuji: The Lantern Keeper, The Ash Spirit, The Fuji Guardian
2. everest: The Icefall Yeti, The Death Zone Wraith, Monsoon God
3. matterhorn: The Hornli Troll, The Ridge Eagle, The Matterhorn King

Their health is in focus minutes (45 for the first one, 25 more for every one after). Every minute you stay focused in a session hits the boss, and opening something distracting heals it 5 minutes. A popup shows up when a boss appears (it laughs at you) and when you beat it (it spins away with confetti).



## AI website sorting

Arete knows a lot of sites already. When you stay on one it doesn't know for 10 seconds, it asks Gemini if it's productive. It only reads the site's **public homepage**, first just the description and if that's not enough a little bit of its text, never your screen or the page you're actually on. Each site only gets checked once and there's a limit of 100 checks a day. You can see every site it sorted in Settings > AI Categorizations.

## Other stuff
- light and dark mode with the sun / moon button, with a painted day sky or night sky behind everything
- today's and this week's stats: time focused, productive hours, and how fast you bounce back from breaks
- time tracked for every app and website you used today
- a streak for every day in a row you open it




***









# Debug mode

Run with `--debug` (or set `ARETE_DEBUG=1`, or press F5 in VS Code). In debug mode:
- Ctrl+C closes it and nothing reopens it
- no Windows admin prompt
- Settings has a Debug card with Force quit, Reset lock timers, Clear all memory, a Blocking on switch, a box to set your climb %, and a Beat boss now button
- every waiting settings change gets an Apply now button
- **Turn off debug until restart** hides all of that again, if you want to see what it's like for a normal user

Emeegency stop on Windows if it's not in debug mode: `taskkill /F /IM Arete.exe` from an admin terminal (or `taskkill /F /IM pythonw.exe` if you ran it from the code)

***

# To build

Go to the Actions tab and click the "Build" action on the left. Click run workflow, wait a bit, and then you'll see the zipped apps for Mac and Windows :) these have everything inside so they can be shared with anybody without needing python



May parth bless suprathik

# Contact
my discord is @yefoi dm me for questions 🙀🙀🙀
yifeichengmi@gmail.com