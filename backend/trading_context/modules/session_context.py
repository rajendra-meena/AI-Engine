"""Session Context — determines current market session from timestamp."""

from datetime import datetime
from typing import Any


class SessionContext:
    """Determines trading session from a candle timestamp."""

    @staticmethod
    def evaluate(timestamp: str | None = None) -> dict[str, Any]:
        try:
            dt = datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
        except (ValueError, TypeError):
            dt = datetime.utcnow()

        hour = dt.hour
        minute = dt.minute
        total_min = hour * 60 + minute

        # Indian market sessions (IST)
        if total_min < 555:  # before 9:15
            session = "PREMARKET"
        elif total_min < 585:  # 9:15-9:45
            session = "OPENING"
        elif total_min < 780:  # 9:45-13:00
            session = "MORNING"
        elif total_min < 855:  # 13:00-14:15
            session = "MIDDAY"
        elif total_min < 930:  # 14:15-15:30
            session = "CLOSING"
        else:
            session = "AFTERMARKET"

        return {"session": session}
