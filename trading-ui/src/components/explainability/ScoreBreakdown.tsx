"use client"

import { ContributionBar } from "./ContributionBar"
import type { ScoreContribution } from "@/services/explainabilityService"

interface ScoreBreakdownProps {
  items: ScoreContribution[]
}

export function ScoreBreakdown({ items }: ScoreBreakdownProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Score Breakdown</div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <ContributionBar key={item.label} label={item.label} value={item.value} color={item.color} detail={` · ${item.weight}%`} size="sm" />
        ))}
      </div>
      <div className="border-t pt-1 text-[9px] text-muted-foreground text-center">
        Total weighted contribution determines the final AI Score
      </div>
    </div>
  )
}
