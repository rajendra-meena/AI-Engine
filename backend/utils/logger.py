"""
MarketMind AI — Logging Utility

Replaces ad-hoc print() calls with structured, timestamped logging.
"""

import sys
from datetime import datetime, timezone


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_info(message: str, **kwargs):
    """Log an informational message."""
    extra = f" | {kwargs}" if kwargs else ""
    print(f"[{_timestamp()}] INFO  {message}{extra}", flush=True)


def log_warn(message: str, **kwargs):
    """Log a warning message."""
    extra = f" | {kwargs}" if kwargs else ""
    print(f"[{_timestamp()}] WARN  {message}{extra}", flush=True)


def log_error(message: str, **kwargs):
    """Log an error message."""
    extra = f" | {kwargs}" if kwargs else ""
    print(f"[{_timestamp()}] ERROR {message}{extra}", file=sys.stderr, flush=True)


def log_startup(message: str):
    """Log a startup event."""
    print(f"[{_timestamp()}] START {message}", flush=True)
