"""SQLite access layer."""

from __future__ import annotations

from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> None:
        raise NotImplementedError

    def migrate(self) -> None:
        raise NotImplementedError
