"""
Market Condition Performance — analyzes strategy performance under various market conditions.

Classifies sessions, volatility regimes, and volume conditions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"mc_{uuid.uuid4().hex[:12]}"


class MarketConditionAnalyzer:
    """Analyzes trade performance under different market conditions."""

    @staticmethod
    def compute_condition_performance(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """For each condition type+value, compute trades, win_rate, avg_return, profit_factor."""
        conditions: dict[str, dict[str, list[dict[str, Any]]]] = {
            "volatility": {}, "volume": {}, "session": {}, "trending": {},
        }

        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            outcome = (outcomes or {}).get(pid, {})
            actual_return = outcome.get("actual_return", 0) if outcome else 0
            merged = dict(p)
            if outcome:
                merged.update(outcome)

            # Classify volatility
            vol = p.get("volatility")
            vol_class = "NORMAL"
            vol_values = [pr.get("volatility", 0) for pr in predictions if pr.get("volatility") is not None]
            if vol is not None and isinstance(vol, (int, float)):
                vol_class = MarketConditionAnalyzer._classify_value(vol, vol_values)
            conditions["volatility"].setdefault(vol_class, []).append(merged)

            # Classify session from timestamp
            ts = p.get("created_at") or p.get("timestamp", "")
            session = MarketConditionAnalyzer._classify_session(ts)
            conditions["session"].setdefault(session, []).append(merged)

            # Classify trending / ranging
            regime = p.get("market_regime") or p.get("regime", "")
            if isinstance(regime, str):
                if regime.upper() in ("TRENDING", "BULLISH", "BEARISH", "UPTREND", "DOWNTREND"):
                    conditions["trending"].setdefault("TRENDING", []).append(merged)
                else:
                    conditions["trending"].setdefault("RANGING", []).append(merged)
            else:
                conditions["trending"].setdefault("UNKNOWN", []).append(merged)

            # Classify volume from indicator_snapshot
            ind_snap = p.get("indicator_snapshot")
            if ind_snap and isinstance(ind_snap, str):
                try:
                    import json
                    ind = json.loads(ind_snap)
                    vol_val = ind.get("candle_volume") or ind.get("volume", 0)
                    avg_vol = ind.get("average_volume", 0)
                    if vol_val and avg_vol and avg_vol > 0:
                        ratio = vol_val / avg_vol
                        if ratio > 1.5:
                            vol_class = "HIGH"
                        elif ratio < 0.5:
                            vol_class = "LOW"
                        else:
                            vol_class = "NORMAL"
                    else:
                        vol_class = "NORMAL"
                except Exception:
                    vol_class = "NORMAL"
            else:
                vol_class = "NORMAL"
            conditions["volume"].setdefault(vol_class, []).append(merged)

        results = []
        for ctype, values in conditions.items():
            for cvalue, trades in values.items():
                total = len(trades)
                if total == 0:
                    continue
                wins = [t for t in trades if (t.get("actual_return") or 0) > 0]
                win_count = len(wins)
                win_rate = round((win_count / total) * 100, 1)
                returns = [t.get("actual_return", 0) for t in trades]
                avg_ret = round(sum(returns) / total, 2)
                gross_profit = sum(r for r in returns if r > 0)
                gross_loss = abs(sum(r for r in returns if r < 0))
                pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

                results.append({
                    "condition_type": ctype,
                    "condition_value": cvalue,
                    "total_trades": total,
                    "win_count": win_count,
                    "win_rate": win_rate,
                    "avg_return": avg_ret,
                    "profit_factor": pf,
                })

        results.sort(key=lambda r: r["total_trades"], reverse=True)
        return results

    @staticmethod
    def snapshot_conditions(db_conn: Any) -> int:
        """Compute and persist current market condition performance."""
        from learning.engine import _get_db as get_learning_db
        try:
            ldb = get_learning_db()
            rows = ldb.execute(
                "SELECT pj.*, po.* FROM prediction_journal pj "
                "LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id "
                "ORDER BY pj.created_at DESC"
            ).fetchall()
            predictions = [dict(r) for r in rows]
            ldb.close()
        except Exception:
            predictions = []

        outcomes: dict[str, dict[str, Any]] = {}
        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            if "actual_return" in p:
                outcomes[pid] = p

        conditions = MarketConditionAnalyzer.compute_condition_performance(predictions, outcomes)
        date_str = _now()[:10]
        count = 0
        for c in conditions:
            cid = _new_id()
            try:
                db_conn.execute(
                    "INSERT OR IGNORE INTO ai_perf_market_condition "
                    "(id, condition_type, condition_value, total_trades, win_count, "
                    "win_rate, avg_return, profit_factor, observation_date) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        cid, c["condition_type"], c["condition_value"],
                        c["total_trades"], c["win_count"], c["win_rate"],
                        c["avg_return"], c["profit_factor"], date_str,
                    ),
                )
                count += 1
            except Exception:
                pass
        db_conn.commit()
        return count

    @staticmethod
    def _classify_session(timestamp: str) -> str:
        """Classify timestamp into OPENING/MID/CLOSING session."""
        if not timestamp or "T" not in timestamp:
            return "UNKNOWN"
        try:
            parts = timestamp.split("T")[1].split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            total_min = hour * 60 + minute
            # Indian market: 9:15-15:30. Opening first 30min, closing last 30min
            market_open = 9 * 60 + 15  # 9:15
            market_close = 15 * 60 + 30  # 15:30
            if total_min < market_open or total_min > market_close:
                return "CLOSED"
            if total_min <= market_open + 30:
                return "OPENING"
            if total_min >= market_close - 30:
                return "CLOSING"
            return "MID"
        except (ValueError, IndexError):
            return "UNKNOWN"

    @staticmethod
    def _classify_value(value: float, all_values: list[float]) -> str:
        """Classify a value as HIGH/LOW/NORMAL relative to its distribution."""
        if not all_values or len(all_values) < 3:
            return "NORMAL"
        sorted_vals = sorted(all_values)
        n = len(sorted_vals)
        p33 = sorted_vals[int(n * 0.33)]
        p66 = sorted_vals[int(n * 0.66)]
        if value >= p66:
            return "HIGH"
        elif value <= p33:
            return "LOW"
        return "NORMAL"
