# Configures Loguru for the whole application.
# Use logger.info/debug/error instead of print() — gives structured logs.
# Every agent and module should import the logger from here.

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(level: str = "DEBUG") -> None:
    """Configure Loguru — console + rotating file."""
    logger.remove()

    # Console — with color
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File — rotate at 10 MB, keep for 7 days
    logger.add(
        _LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )


# Set up as soon as the module is imported
setup_logger()

__all__ = ["logger"]
