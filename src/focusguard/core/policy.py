"""Schedule blocks and the "is this allowed right now?" decision."""

from __future__ import annotations

from datetime import datetime

from focusguard.core.models import ScheduleBlock, Verdict


class Policy:
    def __init__(self, blocks: list[ScheduleBlock]) -> None:
        self.blocks = blocks

    def active_block(self, now: datetime) -> ScheduleBlock | None:
        """The schedule block covering `now`, if any."""
        raise NotImplementedError

    def is_allowed(self, verdict: Verdict, target: str, now: datetime) -> bool:
        """Whether an app/site with this verdict may be used at `now`."""
        raise NotImplementedError
