"""
Evidence collector — thread-safe singleton for capturing dry-run evidence.

Usage:
    from verification.evidence import EvidenceCollector
    EvidenceCollector.record("live_ticks", "PASS", count=5, ...)
    report = EvidenceCollector.get_report()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class EvidenceItem:
    """Single evidence data point captured during the dry run."""

    name: str  # e.g. "live_ticks", "candle_closed", "ai_decision"
    status: str  # PASS | FAIL | WARN | INFO
    detail: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EvidenceCollector:
    """Thread-safe singleton evidence aggregator.

    All public methods are classmethods so evidence capture is simple
    one-liners from any module.
    """

    _lock = threading.Lock()
    _items: list[EvidenceItem] = []
    _start_time: str = datetime.now(timezone.utc).isoformat()

    @classmethod
    def record(cls, name: str, status: str, **detail: Any) -> EvidenceItem:
        """Record a single evidence item.

        Args:
            name: Evidence category name (e.g. "live_ticks", "candle_volume")
            status: PASS, FAIL, WARN, or INFO
            **detail: Arbitrary key-value evidence payload

        Returns:
            The created EvidenceItem.
        """
        item = EvidenceItem(name=name, status=status, detail=detail)
        with cls._lock:
            cls._items.append(item)
        return item

    @classmethod
    def get_report(cls) -> dict[str, Any]:
        """Generate the final evidence report.

        Returns:
            Dict with timestamp, summary stats, and all evidence items.
        """
        with cls._lock:
            total = len(cls._items)
            passed = sum(1 for i in cls._items if i.status == "PASS")
            failed = sum(1 for i in cls._items if i.status == "FAIL")
            warned = sum(1 for i in cls._items if i.status == "WARN")

            return {
                "start_time": cls._start_time,
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_items": total,
                "pass_count": passed,
                "fail_count": failed,
                "warn_count": warned,
                "items": [asdict(i) for i in cls._items],
            }

    @classmethod
    def reset(cls):
        """Clear all collected evidence. Useful for running multiple passes."""
        with cls._lock:
            cls._items.clear()
            cls._start_time = datetime.now(timezone.utc).isoformat()

    @classmethod
    def summary(cls) -> str:
        """One-line summary for terminal output."""
        with cls._lock:
            total = len(cls._items)
            passed = sum(1 for i in cls._items if i.status == "PASS")
            failed = sum(1 for i in cls._items if i.status == "FAIL")
            return f"[Evidence] {passed}/{total} passed, {failed} failed"
