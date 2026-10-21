"""Screenshot -> productive / unproductive, for sites we haven't seen before."""

from __future__ import annotations

from focusguard.core.models import Verdict


def classify_screenshot(png: bytes, site_root: str) -> Verdict:
    raise NotImplementedError
