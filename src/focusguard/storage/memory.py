
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


def _data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FocusGuard"




FILE = _data_dir() / "memory.json"



def load() -> dict:
    defaults = {"first_time": True}
    try:
        data = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return defaults
    if not isinstance(data, dict):
        return defaults
    return {**defaults, **data}


def save(memory: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(memory, indent=2))
    os.replace(tmp, FILE)


def startupOpened() -> bool:
    return bool(load()["startupOpened"])


def mark_opened() -> None:
    memory = load()
    memory["startupOpened"] = False
    save(memory)
