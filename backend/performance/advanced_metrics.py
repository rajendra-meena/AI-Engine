"""
Advanced Performance Metrics — Sharpe, Sortino, Calmar, MAE/MFE, streaks.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def compute_sharpe(returns: list[float], risk_free: float = 0.0, annualize: bool = True) -> float | None:
    if len(returns) < 3:
        return None
    avg_r = sum(returns) / len(returns)
    var_r = sum((r - avg_r) ** 2 for r in returns) / len(returns)
    std = math.sqrt(var_r)
    if std == 0:
        return None
    sharpe = (avg_r - risk_free) / std
    if annualize:
        sharpe *= math.sqrt(252)
    return round(sharpe, 3)


def compute_sortino(returns: list[float], risk_free: float = 0.0, annualize: bool = True) -> float | None:
    if len(returns) < 3:
        return None
    avg_r = sum(returns) / len(returns)
    neg = [r for r in returns if r < 0]
    if not neg:
        return None
    dd = math.sqrt(sum(r ** 2 for r in neg) / len(neg))
    if dd == 0:
        return None
    sortino = (avg_r - risk_free) / dd
    if annualize:
        sortino *= math.sqrt(252)
    return round(sortino, 3)


def compute_calmar(returns: list[float], total_return_pct: float, max_dd_pct: float) -> float | None:
    if max_dd_pct <= 0 or len(returns) < 2:
        return None
    years = len(returns) / 252
    if years <= 0:
        return None
    annualized = ((1 + total_return_pct / 100) ** (1 / years)) - 1
    return round(annualized / (max_dd_pct / 100), 3) if max_dd_pct > 0 else None


def compute_recovery_factor(net_pnl: float, max_drawdown: float) -> float | None:
    if max_drawdown <= 0:
        return None
    return round(net_pnl / abs(max_drawdown), 3)


def compute_streaks(pnl_list: list[float]) -> dict[str, Any]:
    cur_win, cur_loss = 0, 0
    win_streaks, loss_streaks = [], []
    for pnl in pnl_list:
        if pnl > 0:
            cur_win += 1
            if cur_loss > 0:
                loss_streaks.append(cur_loss)
                cur_loss = 0
        else:
            cur_loss += 1
            if cur_win > 0:
                win_streaks.append(cur_win)
                cur_win = 0
    if cur_win > 0:
        win_streaks.append(cur_win)
    if cur_loss > 0:
        loss_streaks.append(cur_loss)
    return {
        "max_consecutive_wins": max(win_streaks) if win_streaks else 0,
        "max_consecutive_losses": max(loss_streaks) if loss_streaks else 0,
        "avg_consecutive_wins": round(sum(win_streaks) / len(win_streaks), 1) if win_streaks else 0,
        "avg_consecutive_losses": round(sum(loss_streaks) / len(loss_streaks), 1) if loss_streaks else 0,
        "current_streak": cur_win if cur_win > 0 else -cur_loss,
    }


def compute_holding_time(trades: list[dict]) -> dict[str, Any]:
    durations = []
    for t in trades:
        et = t.get("entry_time") or t.get("entry_timestamp")
        xt = t.get("exit_time") or t.get("exit_timestamp")
        if et and xt:
            try:
                d = (datetime.fromisoformat(xt) - datetime.fromisoformat(et)).total_seconds() / 3600
                durations.append(d)
            except (ValueError, TypeError):
                pass
    if not durations:
        return {"avg_hours": 0, "median_hours": 0, "min_hours": 0, "max_hours": 0}
    durations.sort()
    return {
        "avg_hours": round(sum(durations) / len(durations), 2),
        "median_hours": round(durations[len(durations) // 2], 2),
        "min_hours": round(durations[0], 2),
        "max_hours": round(durations[-1], 2),
    }


def compute_mae_mfe(trades: list[dict]) -> dict[str, Any]:
    mae_vals, mfe_vals = [], []
    win_mae, win_mfe, loss_mae, loss_mfe = [], [], [], []
    for t in trades:
        mae = abs(t.get("mae") or 0)
        mfe = abs(t.get("mfe") or 0)
        mae_vals.append(mae)
        mfe_vals.append(mfe)
        pnl = t.get("net_pnl") or t.get("pnl") or 0
        if pnl > 0:
            win_mae.append(mae)
            win_mfe.append(mfe)
        else:
            loss_mae.append(mae)
            loss_mfe.append(mfe)

    def stats(vals):
        if not vals:
            return {"avg": 0, "max": 0}
        return {"avg": round(sum(vals) / len(vals), 2), "max": round(max(vals), 2)}
    return {
        "mae": stats(mae_vals),
        "mfe": stats(mfe_vals),
        "win_mae": stats(win_mae),
        "win_mfe": stats(win_mfe),
        "loss_mae": stats(loss_mae),
        "loss_mfe": stats(loss_mfe),
    }
