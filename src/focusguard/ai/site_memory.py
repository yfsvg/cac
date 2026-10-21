"""Cache of site root -> verdict, so each site is only classified once."""

from __future__ import annotations

from focusguard.core.models import Verdict


class SiteMemory:
    def get(self, root: str) -> Verdict | None:
        raise NotImplementedError

    def remember(self, root: str, verdict: Verdict) -> None:
        raise NotImplementedError
