"use client"

import { cn } from "@/lib/utils"
import { ContributionBar } from "./ContributionBar"
import type { IndicatorContribution } from "@/services/explainabilityService"

interface IndicatorContributionProps {
  indicators: IndicatorContribution[]
}

const DIR_COLORS: Record<string, string> = { bullish: "#22c55e", bearish: "#ef4444", neutral: "#888" }

export function IndicatorContributions({ indicators }: IndicatorContributionProps) {
  if (!indicators.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">Indicator data unavailable</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Indicator Contributions</div>
      <div className="grid grid-cols-2 gap-2">
        {indicators.map((ind) => (
          <div key={ind.name} className="rounded-md border p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium">{ind.name}</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded font-medium", ind.status === "active" ? "bg-emerald-500/10 text-emerald-500" : "bg-muted/30 text-muted-foreground")}>
                {ind.status}
              </span>
            </div>
            <div className="flex items-center gap-1 text-[9px]">
              <span style={{ color: DIR_COLORS[ind.direction] }}>{ind.direction.toUpperCase()}</span>
              <span className="text-muted-foreground">Conf: {ind.confidence}%</span>
            </div>
            <ContributionBar label="" value={ind.contribution} color={DIR_COLORS[ind.direction]} size="sm" />
          </div>
        ))}
      </div>
    </div>
  )
}
