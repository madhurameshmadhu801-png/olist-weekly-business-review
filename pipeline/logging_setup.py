"""Logging setup for pipeline execution."""
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from pipeline.config import LOG_FILE, LOGS_DIR


def setup_logger(name: str = "olist_pipeline", log_file: Path = LOG_FILE) -> logging.Logger:
    """Configures a logger with both console and file handlers."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on rerun
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console Handler
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setLevel(logging.INFO)
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)

        # File Handler
        f_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        f_handler.setLevel(logging.INFO)
        f_handler.setFormatter(formatter)
        logger.addHandler(f_handler)

    return logger


@contextmanager
def log_step(logger: logging.Logger, step_name: str):
    """Context manager to measure and log duration of pipeline steps."""
    logger.info(f"===> START: {step_name}")
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time
        logger.info(f"<=== COMPLETED: {step_name} in {duration:.2f}s")
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f"<=== FAILED: {step_name} after {duration:.2f}s with error: {exc}")
        raise
