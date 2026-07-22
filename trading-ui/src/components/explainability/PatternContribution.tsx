"use client"

import { cn } from "@/lib/utils"
import { ContributionBar } from "./ContributionBar"
import type { PatternContribution } from "@/services/explainabilityService"

interface PatternContributionProps {
  patterns: PatternContribution[]
}

export function PatternContributions({ patterns }: PatternContributionProps) {
  if (!patterns.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">Pattern data unavailable</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Pattern Contributions</div>
      <div className="space-y-1.5">
        {patterns.map((p, i) => (
          <div key={i} className="rounded-md border p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium">{p.name}</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded", p.direction === "bullish" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                {p.direction}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[8px] text-muted-foreground">
              <span>Type: {p.type}</span>
              <span>Prob: {(p.probability * 100).toFixed(0)}%</span>
              <span>Conf: {p.confidence.toFixed(0)}%</span>
            </div>
            <ContributionBar label="Weight" value={Math.round(p.weight * 100)} size="sm" />
          </div>
        ))}
      </div>
    </div>
  )
}
