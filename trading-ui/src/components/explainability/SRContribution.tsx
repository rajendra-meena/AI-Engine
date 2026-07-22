"use client"

import { ContributionBar } from "./ContributionBar"
import type { SRContribution } from "@/services/explainabilityService"

interface SRContributionProps {
  items: SRContribution[]
}

export function SRContributions({ items }: SRContributionProps) {
  if (!items.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">S/R data unavailable</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Support & Resistance</div>
      <div className="grid grid-cols-2 gap-1.5">
        {items.map((item) => (
          <ContributionBar key={item.label} label={item.label} value={item.contribution} color={item.color} detail={item.price != null ? ` ₹${item.price.toFixed(0)}` : item.distance != null ? ` ${item.distance}` : ""} size="sm" />
        ))}
      </div>
    </div>
  )
}
