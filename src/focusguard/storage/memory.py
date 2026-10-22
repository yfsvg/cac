import base64
import json
import os

KEY = "focusguard"
FILE = os.path.join(os.path.dirname(__file__), "memory.dat")


def scramble(text):
    result = ""
    for i in range(len(text)):
        result = result + chr(ord(text[i]) ^ ord(KEY[i % len(KEY)]))
    return result


def load():
    if not os.path.exists(FILE):
        settings = {
            "pin": "",
            "blocked_apps": [],
            "blocked_sites": [],
            "study_times": [],
            "time_limits": [],
        }
        save(settings)
        return settings
    f = open(FILE, "r")
    data = f.read()
    f.close()
    text = scramble(base64.b64decode(data).decode())
    return json.loads(text)


def save(settings):
    text = scramble(json.dumps(settings))
    data = base64.b64encode(text.encode()).decode()
    f = open(FILE, "w")
    f.write(data)
    f.close()
