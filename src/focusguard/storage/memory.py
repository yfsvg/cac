
from __future__ import annotations
import json
import os
import sys
from pathlib import Path


# Json storage system, for now just tracks if you've opened the application before for persistent
# memory demo. Also not hashed just for quick mvp

# TO CHECK OR EDIT:
# ~/Library/Application Support/FocusGuard/ on macOS and %APPDATA%\FocusGuard\ on Windows.
# it wont show up in project tree sorry


def dataDirectory() -> Path:
    if sys.platform == "win32":
        baseDirectory = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        baseDirectory = Path.home() / "Library" / "Application Support"
    else:
        baseDirectory = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return baseDirectory / "FocusGuard"




FILE = dataDirectory() / "memory.json"



def load() -> dict:
    defaultMemory = {"first_time": True}
    try:
        loadedMemory = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return defaultMemory
    if not isinstance(loadedMemory, dict):
        return defaultMemory
    returnVal = dict(defaultMemory)
    returnVal.update(loadedMemory)
    return returnVal


def save(memory: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tempFile = FILE.with_suffix(".tmp")
    tempFile.write_text(json.dumps(memory, indent=2))
    os.replace(tempFile, FILE)


def startupOpened() -> bool:
    return bool(load()["startupOpened"])


def markOpened() -> None:
    memory = load()
    memory["startupOpened"] = False
    save(memory)
