"""Escalation: warn -> grace period -> close."""

from __future__ import annotations

from focusguard.core.models import ActiveWindow, EnforcementAction


class Enforcer:
    def __init__(self, grace_seconds: float = 60) -> None:
        self.grace_seconds = grace_seconds

    def decide(self, window: ActiveWindow, allowed: bool) -> EnforcementAction:
        raise NotImplementedError

    def apply(self, window: ActiveWindow, action: EnforcementAction) -> None:
        raise NotImplementedError
