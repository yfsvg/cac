import base64
import json
import os

KEY = "focusguard"
FILE = os.path.join(os.path.dirname(__file__), "memory.dat")


def new_settings():
    return {
        "pin": "",
        "blocked_apps": [],
        "blocked_sites": [],
        "study_times": [],
        "study_allowed": [],
        "time_limits": [],
        "usage_day": "",
        "usage": {},
    }


def scramble(text):
    result = ""
    for i in range(len(text)):
        result = result + chr(ord(text[i]) ^ ord(KEY[i % len(KEY)]))
    return result


def load():
    if not os.path.exists(FILE):
        save(new_settings())
    try:
        f = open(FILE, "r")
        data = f.read()
        f.close()
        settings = json.loads(scramble(base64.b64decode(data).decode()))
    except (ValueError, OSError):
        settings = new_settings()
    defaults = new_settings()
    for key in defaults:
        if key not in settings:
            settings[key] = defaults[key]
    return settings


def save(settings):
    text = scramble(json.dumps(settings))
    data = base64.b64encode(text.encode()).decode()
    f = open(FILE + ".tmp", "w")
    f.write(data)
    f.close()
    os.replace(FILE + ".tmp", FILE)


def save_key(key, value):
    settings = load()
    settings[key] = value
    save(settings)
