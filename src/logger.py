"""Centralized logger for the AI Chat application."""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger("ai_chat")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Default to DEBUG; change to INFO in production
    logger.setLevel(logging.DEBUG)

__all__ = ["logger"]
