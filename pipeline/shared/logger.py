"""
Shared logger factory for the RAG pipeline.

Usage:
    from pipeline.shared.logger import get_logger
    log = get_logger(__name__)
    log.info("message")
"""

import logging

_FORMATTER = logging.Formatter(
    "%(asctime)s  %(name)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a StreamHandler and standard format. Idempotent."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_FORMATTER)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
