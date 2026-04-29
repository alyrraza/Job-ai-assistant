# Yeh file Loguru configure karti hai puri application ke liye.
# print() ki jagah logger.info/debug/error use karo — structured logs milte hain.
# Har agent aur module yahan se logger import kare.

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(level: str = "DEBUG") -> None:
    """Loguru ko configure karo — console + rotating file dono."""
    logger.remove()

    # Console — color ke saath
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

    # File — 10 MB rotate, 7 din raho
    logger.add(
        _LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )


# Module import hote hi setup ho jaaye
setup_logger()

__all__ = ["logger"]
