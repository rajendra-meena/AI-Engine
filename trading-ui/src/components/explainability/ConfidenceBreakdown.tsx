"use client"

import { ReasonCard } from "./ReasonCard"
import type { ConfidenceFactor } from "@/services/explainabilityService"

interface ConfidenceBreakdownProps {
  factors: ConfidenceFactor[]
  confidence: number
}

export function ConfidenceBreakdown({ factors, confidence }: ConfidenceBreakdownProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Confidence Factors</span>
        <span className="text-lg font-bold font-mono">{confidence}%</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {factors.map((f) => (
          <ReasonCard key={f.label} label={f.label} value={`${f.value}%`} status={f.status} detail={f.detail} />
        ))}
      </div>
    </div>
  )
}
