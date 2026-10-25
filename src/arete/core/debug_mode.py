from __future__ import annotations
import os
import sys


# Debug mode -- --debug, ARETE_DEBUG=1 or running from vs code debugger
# shows testing buttons, skips admin prompt + keep alive

def isDebugMode() -> bool:
    if "--debug" in sys.argv:
        return True
    if os.environ.get("ARETE_DEBUG") == "1":
        return True
    return "debugpy" in sys.modules
