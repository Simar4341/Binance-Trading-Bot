"""
Logging configuration for the Binance Futures Trading Bot.
Sets up dual-output logging: DEBUG+ to rotating file, WARNING+ to console.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir: str = "logs", log_level: int = logging.DEBUG) -> str:
    """
    Initialise logging with a rotating file handler and a console handler.

    Args:
        log_dir:   Directory where log files are stored.
        log_level: Minimum level written to the log file.

    Returns:
        Absolute path to the active log file.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"trading_bot_{timestamp}.log")

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Rotating file handler — keeps up to 5 × 5 MB files
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_fmt)

    # Console handler — only warnings and above to keep stdout clean
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_fmt)

    root = logging.getLogger()
    root.setLevel(log_level)
    # Avoid adding duplicate handlers if setup_logging is called more than once
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)  # silence noisy lib

    logger = logging.getLogger(__name__)
    logger.info("Logging initialised | log_file=%s", log_file)
    return log_file
