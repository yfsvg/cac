"""Random-interval check loop (~2 minutes with jitter)."""

from __future__ import annotations

from collections.abc import Callable

DEFAULT_INTERVAL_SECONDS = 120
DEFAULT_JITTER_SECONDS = 45


class CheckScheduler:
    """Calls `on_check` at jittered intervals so checks can't be predicted and dodged."""

    def __init__(
        self,
        on_check: Callable[[], None],
        interval: float = DEFAULT_INTERVAL_SECONDS,
        jitter: float = DEFAULT_JITTER_SECONDS,
    ) -> None:
        self.on_check = on_check
        self.interval = interval
        self.jitter = jitter

    def next_delay(self) -> float:
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError
