"""Picks the OS backend. Import `get_backend` rather than a specific backend module."""

from __future__ import annotations

import sys
from functools import cache

from arete.platform.base import PlatformBackend

__all__ = ["PlatformBackend", "get_backend"]


@cache
# backend contains all of the OS-specific function calls that we made that we build off of (gdoc page 3)
# USE BACKEND CODE ALWAYS AND IF THERE IS NONE THEN JUST ADD IT TO BACKEND INSTEAD OF ADDING IT NATIVELY
def get_backend() -> PlatformBackend:
    if sys.platform == "darwin":
        from arete.platform.macos import MacOSBackend

        return MacOSBackend()
    if sys.platform == "win32":
        from arete.platform.windows import WindowsBackend

        return WindowsBackend()
    raise NotImplementedError(f"Arete doesn't support {sys.platform} yet")
