from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from app.config import PROJECT_ROOT


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        PROJECT_ROOT / "logs" / "wealth_advisor.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(file_handler)
