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
    # Set to WARNING to reduce terminal noise (use debug panel for debugging)
    logger.setLevel(logging.WARNING)

__all__ = ["logger"]
