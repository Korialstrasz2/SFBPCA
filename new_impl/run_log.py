"""Simple in-memory run log for import and alert cycles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class LogEntry:
    """Single log line with optional context."""

    timestamp: str
    level: str
    message: str
    context: Dict[str, object]


class RunLog:
    """Collects application events that should be visible to the user."""

    def __init__(self) -> None:
        self.reset()

    def reset(self, reason: str | None = None) -> None:
        """Clears previous entries and optionally notes the reset reason."""

        self._entries: List[LogEntry] = []
        if reason:
            self.info(f"Log azzerato per nuovo ciclo: {reason}")

    def log(self, level: str, message: str, **context: object) -> None:
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            level=level.upper(),
            message=message,
            context=context,
        )
        self._entries.append(entry)

    def debug(self, message: str, **context: object) -> None:
        self.log("DEBUG", message, **context)

    def info(self, message: str, **context: object) -> None:
        self.log("INFO", message, **context)

    def warning(self, message: str, **context: object) -> None:
        self.log("WARNING", message, **context)

    def error(self, message: str, **context: object) -> None:
        self.log("ERROR", message, **context)

    def entries(self) -> List[Dict[str, object]]:
        return [
            {
                "timestamp": entry.timestamp,
                "level": entry.level,
                "message": entry.message,
                "context": entry.context,
            }
            for entry in self._entries
        ]

    def to_text(self) -> str:
        lines = []
        for entry in self._entries:
            context = (
                " "
                + " ".join(f"{key}={value}" for key, value in entry.context.items())
                if entry.context
                else ""
            )
            lines.append(f"{entry.timestamp} [{entry.level}] {entry.message}{context}")
        return "\n".join(lines)


RUN_LOG = RunLog()
"""Singleton registry shared across import and alert modules."""
