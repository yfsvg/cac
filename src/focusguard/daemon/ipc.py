"""Local socket the UI uses to talk to the daemon."""

from __future__ import annotations


class IpcServer:
    def start(self) -> None:
        raise NotImplementedError


class IpcClient:
    def send(self, message: dict) -> dict:
        raise NotImplementedError
