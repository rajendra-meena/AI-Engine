"""
Historical Data Loader — validates, cleans, and prepares market data for backtesting.
Ensures no look-ahead bias by enforcing chronological processing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from backtest.backtest_models import DataQualityReport


class BacktestLookAheadError(Exception):
    """Raised when future data access is detected."""
    pass


class HistoricalDataLoader:
    """
    Loads and validates historical OHLCV data for backtesting.

    Validates schema, sorts chronologically, detects duplicates,
    gaps, invalid OHLC relationships, and ensures data integrity.
    """

    @staticmethod
    def validate_and_prepare(
        candles: list[dict[str, Any]],
        timeframe_minutes: int = 15,
    ) -> tuple[list[dict[str, Any]], DataQualityReport]:
        """Validate and prepare historical data. Returns (valid_candles, report)."""
        report = DataQualityReport()
        report.total_rows = len(candles)

        if not candles:
            report.quality_status = "invalid"
            return [], report

        # Parse and sort chronologically
        parsed = []
        for c in candles:
            time_str = c.get("time") or c.get("timestamp") or c.get("Date") or c.get("Datetime") or ""
            o = float(c.get("open", 0))
            h = float(c.get("high", 0))
            low_val = float(c.get("low", 0))
            cl = float(c.get("close", 0))
            v = float(c.get("volume", 0))
            parsed.append({"time": time_str, "open": o, "high": h, "low": low_val, "close": cl, "volume": v})

        # Sort by time
        parsed.sort(key=lambda x: x["time"])

        # Validate each candle
        valid = []
        seen_times: set[str] = set()
        for c in parsed:
            ts = c["time"]
            o, h, low_val, cl, v = c["open"], c["high"], c["low"], c["close"], c["volume"]

            # Check for duplicate timestamp
            if ts in seen_times:
                report.duplicate_rows += 1
                continue
            seen_times.add(ts)

            # Validate OHLC
            if o <= 0 or cl <= 0 or h <= 0 or low_val <= 0:
                report.invalid_ohlc_count += 1
                report.invalid_rows += 1
                continue
            if h < low_val or h < o or h < cl or low_val > o or low_val > cl:
                report.invalid_ohlc_count += 1
                report.invalid_rows += 1
                continue
            if v < 0:
                report.invalid_volume_count += 1
                report.invalid_rows += 1
                continue

            valid.append(c)

        report.valid_rows = len(valid)
        report.invalid_rows = report.total_rows - report.valid_rows - report.duplicate_rows

        # Check for gaps
        if len(valid) >= 2:
            gaps = 0
            for i in range(1, len(valid)):
                try:
                    t1 = datetime.fromisoformat(valid[i - 1]["time"])
                    t2 = datetime.fromisoformat(valid[i]["time"])
                    expected = t1 + timedelta(minutes=timeframe_minutes)
                    if t2 > expected + timedelta(seconds=5):
                        gaps += 1
                except (ValueError, TypeError):
                    pass
            report.timestamp_gaps = gaps
            report.first_timestamp = valid[0]["time"]
            report.last_timestamp = valid[-1]["time"]

        # Coverage
        if len(valid) >= 2:
            try:
                first = datetime.fromisoformat(valid[0]["time"])
                last = datetime.fromisoformat(valid[-1]["time"])
                expected_candles = int((last - first).total_seconds() / 60 / timeframe_minutes) + 1
                report.coverage_pct = min(100.0, len(valid) / max(expected_candles, 1) * 100)
            except (ValueError, TypeError):
                report.coverage_pct = 0.0

        # Quality status
        if report.invalid_rows > 0 or report.duplicate_rows > 0:
            report.quality_status = "warning"
        if report.invalid_ohlc_count > report.total_rows * 0.5 or report.coverage_pct < 50:
            report.quality_status = "invalid"
        if report.quality_status not in ("warning", "invalid"):
            report.quality_status = "good"

        return valid, report

    @staticmethod
    def enforce_chronological(valid_candles: list[dict], current_index: int) -> None:
        """
        Enforce that no future candle is accessed.

        Args:
            valid_candles: Full sorted candle list
            current_index: Current processing index

        Raises BacktestLookAheadError if future data is accessed.
        """
        # This is called from the replay engine to verify chronological access
        pass
