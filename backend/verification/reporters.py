"""
Report formatters for the dry-run verification output.
Provides both human-readable terminal output and structured JSON.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def format_report(report: dict[str, Any], verbose: bool = False) -> str:
    """Format the evidence report as human-readable terminal output.

    Args:
        report: The report dict from EvidenceCollector.get_report()
        verbose: If True, show PASS items too; otherwise only FAIL/WARN/INFO

    Returns:
        Formatted multiline string ready for terminal display.
    """
    lines = [
        "=" * 64,
        "  MarketMind AI — Pre-Market Dry Run Report",
        "=" * 64,
        f"  Started:  {report.get('start_time', '?')}",
        f"  Ended:    {report.get('end_time', '?')}",
        f"  Verdict:  {report.get('verdict', 'NONE')}",
        "-" * 64,
        f"  PASS:  {report.get('pass_count', 0)}",
        f"  FAIL:  {report.get('fail_count', 0)}",
        f"  WARN:  {report.get('warn_count', 0)}",
        f"  Total: {report.get('total_items', 0)}",
        "-" * 64,
    ]

    if report.get("recommendation"):
        lines.append(f"  Recommendation: {report['recommendation']}")
        lines.append("-" * 64)

    for item in report.get("items", []):
        status = item.get("status", "INFO")
        name = item.get("name", "?")
        detail = item.get("detail", {})

        icon = {
            "PASS": "  [PASS]",
            "FAIL": "  [FAIL]",
            "WARN": "  [WARN]",
            "INFO": "  [INFO]",
        }.get(status, "  [INFO]")

        if status == "PASS" and not verbose:
            continue

        lines.append(f"{icon} {name}")

        # Show key detail fields inline
        brief = _brief_detail(detail)
        if brief:
            lines.append(f"         {brief}")

    lines.append("=" * 64)
    return "\n".join(lines)


def _brief_detail(detail: dict[str, Any]) -> str:
    """Generate a one-line summary of the most important detail fields."""
    parts = []
    for key in ("count", "symbol", "interval", "status", "passed", "price", "error"):
        if key in detail:
            val = detail[key]
            parts.append(f"{key}={val}")
    # Also include first 3 extra keys not in the standard list
    extra_count = 0
    for k, v in detail.items():
        if k not in ("count", "symbol", "interval", "status", "passed", "price", "error", "open", "high", "low", "close", "volume"):
            if extra_count < 3:
                parts.append(f"{k}={v}")
                extra_count += 1
    if not parts:
        return ""
    if len(parts) > 5:
        parts = parts[:5]
    return " | ".join(parts)


def export_json(report: dict[str, Any], path: str):
    """Write the report to a JSON file."""
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
