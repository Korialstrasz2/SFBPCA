"""Simple logging helpers to capture loop decisions in a downloadable file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "run.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("sfbpca.looplog")
if not _logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)sZ - %(message)s")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log_loop_event(message: str) -> None:
    """Append an informational entry to the shared loop log."""

    _logger.info(message)


def read_log_lines() -> List[str]:
    """Return the current log as a list of lines."""

    if LOG_FILE.exists():
        return LOG_FILE.read_text(encoding="utf-8").splitlines()
    return []


def read_log_bytes() -> bytes:
    """Return the raw log content for download purposes."""

    if LOG_FILE.exists():
        return LOG_FILE.read_bytes()
    return b""
