"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown } from "lucide-react"
import type { ScannerRow } from "@/store/useScannerStore"

interface OpportunityCardsProps {
  rows: ScannerRow[]
  className?: string
}

export function OpportunityCards({ rows, className }: OpportunityCardsProps) {
  const topOpportunities = rows
    .filter((r) => r.score >= 60 && r.rr >= 1)
    .slice(0, 6)

  if (!topOpportunities.length) return null

  return (
    <div className={cn("space-y-1", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Top Opportunities</div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-1.5">
        {topOpportunities.map((row) => {
          const isBullish = row.institutionalBias === "BULLISH"
          return (
            <div
              key={row.symbol}
              className={cn(
                "rounded-lg border p-2 space-y-1.5 transition-colors",
                isBullish ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5",
              )}
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold">{row.symbol}</span>
                <span className={cn("flex items-center gap-1 text-[9px] font-medium", isBullish ? "text-emerald-500" : "text-red-500")}>
                  {isBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {row.institutionalBias}
                </span>
              </div>

              {/* Score & Confidence */}
              <div className="flex items-center gap-2 text-[9px]">
                <span className={cn("font-mono font-bold", row.score >= 80 ? "text-emerald-500" : row.score >= 60 ? "text-blue-500" : "text-amber-500")}>
                  Score: {row.score}
                </span>
                <span className="text-muted-foreground">Conf: {row.confidence}%</span>
                <span className={cn("font-medium", row.risk === "LOW" ? "text-emerald-500" : row.risk === "HIGH" ? "text-red-500" : "text-amber-500")}>
                  {row.risk}
                </span>
              </div>

              {/* RR */}
              <div className="flex items-center gap-2 text-[9px]">
                <span className="text-muted-foreground">RR:</span>
                <span className={cn("font-mono font-bold", row.rr >= 2 ? "text-emerald-500" : "text-amber-500")}>
                  {row.rr.toFixed(1)}:1
                </span>
                {row.pattern && (
                  <span className="text-muted-foreground ml-1">{row.pattern}</span>
                )}
              </div>

              {/* Trend + Support/Resistance */}
              <div className="flex items-center gap-2 text-[8px] text-muted-foreground">
                <span>{row.trend === "UPTREND" ? "↑" : row.trend === "DOWNTREND" ? "↓" : "→"}</span>
                {row.supportDistance != null && <span>S: {row.supportDistance.toFixed(1)}%</span>}
                {row.resistanceDistance != null && <span>R: {row.resistanceDistance.toFixed(1)}%</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
