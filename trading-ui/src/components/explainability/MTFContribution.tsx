"use client"

import { cn } from "@/lib/utils"
import { ContributionBar } from "./ContributionBar"
import type { MTFContribution } from "@/services/explainabilityService"

interface MTFContributionProps {
  items: MTFContribution[]
}

export function MTFContributions({ items }: MTFContributionProps) {
  if (!items.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">MTF data unavailable</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Multi-Timeframe Alignment</div>
      <div className="grid grid-cols-2 gap-1.5">
        {items.map((item) => (
          <div key={item.timeframe} className="rounded-md border p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-medium">{item.timeframe}</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded font-medium", item.bias === "BULLISH" ? "bg-emerald-500/10 text-emerald-500" : item.bias === "BEARISH" ? "bg-red-500/10 text-red-500" : "bg-muted/30 text-muted-foreground")}>
                {item.bias}
              </span>
            </div>
            <div className="text-[8px] text-muted-foreground">Alignment: {item.alignment} · Conf: {item.confidence}%</div>
            <ContributionBar label="" value={item.contribution} size="sm" />
          </div>
        ))}
      </div>
    </div>
  )
}
