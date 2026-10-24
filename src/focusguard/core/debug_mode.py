from __future__ import annotations
import os
import sys


def isDebugMode() -> bool:
    if "--debug" in sys.argv:
        return True
    if os.environ.get("FOCUSGUARD_DEBUG") == "1":
        return True
    return "debugpy" in sys.modules
