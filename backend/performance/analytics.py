"""
Performance Analytics Engine — paper trade validation, signal funnel, and metrics.
All data comes from stored paper trades — no mock/fake values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _sample_level(count: int) -> str:
    if count < 20:
        return "insufficient_sample"
    if count < 50:
        return "low_confidence"
    if count < 100:
        return "moderate_sample"
    return "stronger_sample"


def compute_overview(trades: list[dict[str, Any]], blocked: list[dict[str, Any]], signals: int = 0) -> dict[str, Any]:
    """Compute overall performance summary from paper trades."""
    total = len(trades)
    wins = [t for t in trades if (t.get("realized_pnl") or t.get("pnl") or 0) > 0]
    losses = [t for t in trades if (t.get("realized_pnl") or t.get("pnl") or 0) <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in wins)
    gross_loss = abs(sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in losses))
    net_pnl = gross_profit - gross_loss

    avg_win = gross_profit / win_count if win_count > 0 else 0
    avg_loss = gross_loss / loss_count if loss_count > 0 else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0
    expectancy = round((win_count / total * avg_win - loss_count / total * avg_loss) if total > 0 else 0, 2)

    largest_win = max((t.get("realized_pnl") or t.get("pnl") or 0) for t in trades) if trades else 0
    largest_loss = min((t.get("realized_pnl") or t.get("pnl") or 0) for t in trades) if trades else 0

    durations = []
    for t in trades:
        o = t.get("created_at") or t.get("opened_at") or t.get("entry_timestamp")
        c = t.get("closed_at") or t.get("exit_timestamp")
        if o and c:
            try:
                d = (datetime.fromisoformat(c) - datetime.fromisoformat(o)).total_seconds() / 3600
                durations.append(d)
            except (ValueError, TypeError):
                pass

    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0

    target_hit = sum(1 for t in trades if t.get("exit_reason") == "target")
    sl_hit = sum(1 for t in trades if t.get("exit_reason") == "stop_loss")

    long_trades = [t for t in trades if t.get("direction") == "LONG"]
    short_trades = [t for t in trades if t.get("direction") == "SHORT"]

    return {
        "total_trades": total,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate": round(win_count / total * 100, 1) if total > 0 else 0,
        "loss_rate": round(loss_count / total * 100, 1) if total > 0 else 0,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_pnl": round(net_pnl, 2),
        "average_win": round(avg_win, 2),
        "average_loss": round(avg_loss, 2),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "avg_holding_hours": avg_duration,
        "target_hit_rate": round(target_hit / total * 100, 1) if total > 0 else 0,
        "stoploss_hit_rate": round(sl_hit / total * 100, 1) if total > 0 else 0,
        "long_trades": len(long_trades),
        "short_trades": len(short_trades),
        "long_win_rate": round(
            sum(1 for t in long_trades if (t.get("realized_pnl") or 0) > 0) / max(len(long_trades), 1) * 100, 1
        ),
        "short_win_rate": round(
            sum(1 for t in short_trades if (t.get("realized_pnl") or 0) > 0) / max(len(short_trades), 1) * 100, 1
        ),
        "blocked_count": len(blocked),
        "sample_size": total,
        "sample_level": _sample_level(total),
    }


def compute_r_multiple(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute R-multiple distribution from paper trades."""
    r_values = []
    for t in trades:
        entry = t.get("entry_price") or 0
        sl = t.get("stop_loss") or 0
        pnl = t.get("realized_pnl") or t.get("pnl") or 0
        quantity = t.get("quantity") or 1
        if entry and sl and entry > 0 and sl > 0:
            initial_risk = abs(entry - sl) * quantity
            r = pnl / initial_risk if initial_risk > 0 else 0
        else:
            r = 0
        r_values.append(r)

    return {
        "r_values": [round(r, 2) for r in r_values],
        "avg_r": round(sum(r_values) / len(r_values), 2) if r_values else 0,
        "median_r": round(sorted(r_values)[len(r_values) // 2], 2) if r_values else 0,
        "distribution": {
            "ge_2r": sum(1 for r in r_values if r >= 2),
            "ge_1r_lt_2r": sum(1 for r in r_values if 1 <= r < 2),
            "ge_0r_lt_1r": sum(1 for r in r_values if 0 <= r < 1),
            "ge_neg1r_lt_0r": sum(1 for r in r_values if -1 <= r < 0),
            "lt_neg1r": sum(1 for r in r_values if r < -1),
        },
        "sample_count": len(r_values),
    }


def compute_calibration(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Analyze AI confidence calibration against paper trade outcomes."""
    buckets = [
        (0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100),
    ]
    results = []
    for lo, hi in buckets:
        bucket_trades = [
            t for t in trades
            if (t.get("ai_confidence") or t.get("confidence") or 50) >= lo
            and (t.get("ai_confidence") or t.get("confidence") or 50) <= hi
        ]
        count = len(bucket_trades)
        wins = sum(1 for t in bucket_trades if (t.get("realized_pnl") or t.get("pnl") or 0) > 0)
        avg_r = 0
        r_vals = []
        for t in bucket_trades:
            entry = t.get("entry_price") or 0
            sl = t.get("stop_loss") or 0
            pnl = t.get("realized_pnl") or t.get("pnl") or 0
            qty = t.get("quantity") or 1
            if entry and sl and entry > 0:
                risk = abs(entry - sl) * qty
                r_vals.append(pnl / risk if risk > 0 else 0)
        avg_r = round(sum(r_vals) / len(r_vals), 2) if r_vals else 0

        results.append({
            "bucket": f"{lo}-{hi}",
            "bucket_min": lo,
            "bucket_max": hi,
            "trade_count": count,
            "win_count": wins,
            "win_rate": round(wins / count * 100, 1) if count > 0 else 0,
            "avg_r": avg_r,
            "sample_level": _sample_level(count),
        })
    return results


def compute_funnel(
    total_signals: int, buy_count: int, sell_count: int, wait_count: int,
    qualified: int, risk_approved: int, executed: int, closed: int,
) -> dict[str, Any]:
    """Build signal funnel from pipeline stage counts."""
    return {
        "total_signals": total_signals,
        "buy": buy_count,
        "sell": sell_count,
        "wait": wait_count,
        "strategy_qualified": qualified,
        "risk_approved": risk_approved,
        "paper_executed": executed,
        "closed": closed,
        "conversion_rate": round(executed / max(total_signals, 1) * 100, 1),
        "qualification_rate": round(qualified / max(buy_count + sell_count, 1) * 100, 1),
        "approval_rate": round(risk_approved / max(qualified, 1) * 100, 1),
    }


def compute_regime_performance(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Break down performance by market regime."""
    regimes: dict[str, list[dict]] = {}
    for t in trades:
        regime = t.get("market_regime") or t.get("regime") or "unknown"
        if regime not in regimes:
            regimes[regime] = []
        regimes[regime].append(t)

    results = []
    for regime, ts in sorted(regimes.items()):
        wins = sum(1 for t in ts if (t.get("realized_pnl") or t.get("pnl") or 0) > 0)
        total = len(ts)
        pnl = sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in ts)
        results.append({
            "regime": regime,
            "trade_count": total,
            "win_count": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "net_pnl": round(pnl, 2),
            "sample_level": _sample_level(total),
        })
    return results


def compute_timeframe_performance(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Break down performance by timeframe."""
    tfs: dict[str, list[dict]] = {}
    for t in trades:
        tf = t.get("interval") or t.get("timeframe") or "unknown"
        if tf not in tfs:
            tfs[tf] = []
        tfs[tf].append(t)

    results = []
    for tf, ts in sorted(tfs.items()):
        wins = sum(1 for t in ts if (t.get("realized_pnl") or t.get("pnl") or 0) > 0)
        total = len(ts)
        pnl = sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in ts)
        results.append({
            "timeframe": tf,
            "trade_count": total,
            "win_count": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "net_pnl": round(pnl, 2),
            "sample_level": _sample_level(total),
        })
    return results


def compute_symbol_performance(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Break down performance by symbol."""
    syms: dict[str, list[dict]] = {}
    for t in trades:
        sym = t.get("symbol") or "unknown"
        if sym not in syms:
            syms[sym] = []
        syms[sym].append(t)

    results = []
    for sym, ts in sorted(syms.items()):
        wins = sum(1 for t in ts if (t.get("realized_pnl") or t.get("pnl") or 0) > 0)
        total = len(ts)
        pnl = sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in ts)
        results.append({
            "symbol": sym,
            "trade_count": total,
            "win_count": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "net_pnl": round(pnl, 2),
            "sample_level": _sample_level(total),
        })
    return results


def compute_direction_performance(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare LONG vs SHORT performance."""
    directions: dict[str, list[dict]] = {}
    for t in trades:
        d = t.get("direction") or "UNKNOWN"
        if d not in directions:
            directions[d] = []
        directions[d].append(t)

    results = []
    for d, ts in sorted(directions.items()):
        wins = sum(1 for t in ts if (t.get("realized_pnl") or t.get("pnl") or 0) > 0)
        total = len(ts)
        pnl = sum(t.get("realized_pnl") or t.get("pnl") or 0 for t in ts)
        results.append({
            "direction": d,
            "trade_count": total,
            "win_count": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "net_pnl": round(pnl, 2),
            "sample_level": _sample_level(total),
        })
    return results


def compute_blocked_analysis(blocked: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze blocked trades by reason."""
    reasons: dict[str, int] = {}
    for b in blocked:
        r = b.get("blocked_by") or b.get("reason") or "unknown"
        reasons[r] = reasons.get(r, 0) + 1

    return {
        "total_blocked": len(blocked),
        "by_reason": [{"reason": k, "count": v} for k, v in sorted(reasons.items(), key=lambda i: -i[1])],
    }


def compute_equity_curve(trades: list[dict[str, Any]], initial_capital: float = 100000.0) -> dict[str, Any]:
    """Build equity curve and drawdown from paper trades."""
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    points = [{"time": "start", "equity": equity, "drawdown": 0}]

    for t in sorted(trades, key=lambda x: x.get("closed_at") or x.get("created_at") or ""):
        pnl = t.get("realized_pnl") or t.get("pnl") or 0
        equity += pnl
        if equity > peak:
            peak = equity
        dd = round((peak - equity) / peak * 100, 2) if peak > 0 else 0
        max_dd = max(max_dd, dd)
        points.append({
            "time": t.get("closed_at") or t.get("created_at") or "",
            "equity": round(equity, 2),
            "drawdown": dd,
        })

    return {
        "initial_capital": initial_capital,
        "current_equity": round(equity, 2),
        "peak_equity": round(peak, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "total_return_pct": round((equity - initial_capital) / initial_capital * 100, 2) if initial_capital > 0 else 0,
        "points": points,
    }
