"use client"

import { ContributionBar } from "./ContributionBar"
import type { StructureContribution } from "@/services/explainabilityService"

interface StructureContributionProps {
  items: StructureContribution[]
}

export function StructureContributions({ items }: StructureContributionProps) {
  if (!items.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">Structure data unavailable</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Structure Contributions</div>
      <div className="grid grid-cols-2 gap-1.5">
        {items.map((item) => (
          <ContributionBar key={item.label} label={item.label} value={item.value} color={item.color ?? "#6366f1"} detail={` · ${item.detail ?? ""}`} size="sm" />
        ))}
      </div>
    </div>
  )
}
