"use client"

import type { PortfolioSummary } from "@/store/usePortfolioStore"

interface PortfolioDashboardProps {
  summary: PortfolioSummary
  onTabChange: (tab: string) => void
}

function StatCard({ label, value, prefix, suffix, color }: { label: string; value: string | number; prefix?: string; suffix?: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono ${color || ""}`}>
        {prefix}{typeof value === "number" ? value.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : value}{suffix}
      </div>
    </div>
  )
}

export function PortfolioDashboard({ summary, onTabChange }: PortfolioDashboardProps) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        <StatCard label="Total Value" value={summary.totalValue} prefix="₹ " color="text-foreground" />
        <StatCard label="Today PnL" value={summary.todayPnL} prefix="₹ " color={summary.todayPnL >= 0 ? "text-emerald-500" : "text-red-500"} />
        <StatCard label="Total PnL" value={summary.totalPnL} prefix="₹ " color={summary.totalPnL >= 0 ? "text-emerald-500" : "text-red-500"} />
        <StatCard label="Win Rate" value={summary.winRate.toFixed(1)} suffix="%" color={summary.winRate >= 50 ? "text-emerald-500" : "text-red-500"} />
        <StatCard label="Open Positions" value={summary.openPositions} />
        <StatCard label="Closed Positions" value={summary.closedPositions} />
        <StatCard label="Avg RR" value={summary.avgRR.toFixed(2)} color={summary.avgRR >= 1 ? "text-emerald-500" : "text-amber-500"} />
        <StatCard label="Exposure" value={summary.exposure.toFixed(1)} suffix="%" color={summary.exposure < 50 ? "text-emerald-500" : summary.exposure < 80 ? "text-amber-500" : "text-red-500"} />
        <StatCard label="Available Margin" value={summary.availableMargin} prefix="₹ " />
        <StatCard label="Used Margin" value={summary.usedMargin} prefix="₹ " />
        <StatCard label="Paper Capital" value={summary.capitalAllocation} prefix="₹ " />
      </div>

      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <button onClick={() => onTabChange("positions")} className="px-2 py-1 rounded hover:bg-accent transition-colors">View Positions →</button>
        <button onClick={() => onTabChange("trades")} className="px-2 py-1 rounded hover:bg-accent transition-colors">View Closed Trades →</button>
        <button onClick={() => onTabChange("analytics")} className="px-2 py-1 rounded hover:bg-accent transition-colors">View Analytics →</button>
      </div>
    </div>
  )
}
