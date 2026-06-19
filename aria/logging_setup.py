"""Centralized logging configuration for ARIA.

Importing modules should call `get_logger(__name__)` to obtain a module-scoped
logger. The root logger is configured lazily by `configure_root_logging()`,
which `main.py` invokes once on startup. Re-configuration is a no-op.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Final

_CONFIGURED: bool = False
_DEFAULT_FORMAT: Final[str] = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_root_logging(level: str | int | None = None) -> None:
    """Configure the root logger exactly once per process.

    Idempotent: subsequent calls are silently ignored so re-entrant imports
    (e.g. tests re-running main) do not duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved_level = level or os.getenv("ARIA_LOG_LEVEL", "INFO")
    if isinstance(resolved_level, str):
        resolved_level = resolved_level.upper()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)

    # Quiet noisy third-party loggers unless explicitly debugging.
    for noisy in ("httpx", "httpcore", "telegram", "telegram.ext", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, ensuring root config has run."""
    if not _CONFIGURED:
        configure_root_logging()
    return logging.getLogger(name)
