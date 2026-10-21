"""Picks the OS backend. Import `get_backend` rather than a specific backend module."""

from __future__ import annotations

import sys
from functools import cache

from focusguard.platform.base import PlatformBackend

__all__ = ["PlatformBackend", "get_backend"]


@cache
def get_backend() -> PlatformBackend:
    if sys.platform == "darwin":
        from focusguard.platform.macos import MacOSBackend

        return MacOSBackend()
    if sys.platform == "win32":
        from focusguard.platform.windows import WindowsBackend

        return WindowsBackend()
    raise NotImplementedError(f"FocusGuard doesn't support {sys.platform} yet")
