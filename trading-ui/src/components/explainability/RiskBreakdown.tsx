"use client"

import { cn } from "@/lib/utils"
import type { RiskFactor } from "@/services/explainabilityService"

interface RiskBreakdownProps {
  factors: RiskFactor[]
}

const LEVEL_COLORS = { LOW: "text-emerald-500 bg-emerald-500/10", MEDIUM: "text-amber-500 bg-amber-500/10", HIGH: "text-red-500 bg-red-500/10", EXTREME: "text-red-600 bg-red-600/10" }

export function RiskBreakdown({ factors }: RiskBreakdownProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Risk Factors</div>
      <div className="grid grid-cols-2 gap-1.5">
        {factors.map((f) => (
          <div key={f.label} className="rounded-md border p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] text-muted-foreground">{f.label}</span>
              <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", LEVEL_COLORS[f.level])}>{f.level}</span>
            </div>
            <div className="text-[11px] font-mono font-bold">{f.value}</div>
            {f.detail && <div className="text-[8px] text-muted-foreground">{f.detail}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
