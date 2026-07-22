"use client"

import { cn } from "@/lib/utils"
import type { IndicatorMetric } from "@/services/analyticsService"

interface IndicatorTableProps {
  data: IndicatorMetric[]
  className?: string
}

const INDICATOR_COLORS: Record<string, string> = {
  ema_9: "#6366f1",
  ema_20: "#f59e0b",
  ema_50: "#10b981",
  ema_200: "#ef4444",
  rsi: "#ec4899",
  macd: "#8b5cf6",
  adx: "#06b6d4",
  atr: "#f97316",
  vwap: "#22c55e",
  supertrend: "#a855f7",
}

export function IndicatorTable({ data, className }: IndicatorTableProps) {
  if (!data.length) {
    return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">Indicator analytics available with decision data</div>
  }

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Indicator Performance</div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-3 py-1.5">Indicator</th>
              <th className="text-right font-medium px-3 py-1.5">Accuracy</th>
              <th className="text-right font-medium px-3 py-1.5">Usage</th>
              <th className="text-right font-medium px-3 py-1.5">Avg Win Rate</th>
              <th className="text-right font-medium px-3 py-1.5">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {data.map((ind, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-3 py-1.5 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: INDICATOR_COLORS[ind.name.toLowerCase()] || "#888" }} />
                  <span className="font-medium">{ind.name}</span>
                </td>
                <td className={cn("px-3 py-1.5 text-right font-mono font-medium", ind.accuracy >= 60 ? "text-emerald-500" : "text-amber-500")}>
                  {ind.accuracy.toFixed(1)}%
                </td>
                <td className="px-3 py-1.5 text-right font-mono">{ind.usage.toFixed(0)}%</td>
                <td className="px-3 py-1.5 text-right font-mono">{ind.avgWinRate.toFixed(1)}%</td>
                <td className="px-3 py-1.5 text-right font-mono">
                  <div className="inline-flex items-center gap-1">
                    <div className="h-1.5 w-12 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(ind.contributionScore, 100)}%` }} />
                    </div>
                    <span className="text-[8px]">{ind.contributionScore.toFixed(0)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
