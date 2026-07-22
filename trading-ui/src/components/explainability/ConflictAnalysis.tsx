"use client"

import { cn } from "@/lib/utils"
import { AlertTriangle, XCircle, AlertCircle } from "lucide-react"
import type { ConflictItem } from "@/services/explainabilityService"

interface ConflictAnalysisProps {
  conflicts: ConflictItem[]
}

const SEVERITY_ICONS = { low: <AlertCircle className="w-3 h-3" />, medium: <AlertTriangle className="w-3 h-3" />, high: <XCircle className="w-3 h-3" /> }
const SEVERITY_COLORS = { low: "text-amber-500 border-amber-500/20", medium: "text-orange-500 border-orange-500/20", high: "text-red-500 border-red-500/20" }

export function ConflictAnalysis({ conflicts }: ConflictAnalysisProps) {
  if (!conflicts.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-emerald-500 text-center">No conflicts detected</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Conflict Analysis</div>
      <div className="space-y-1">
        {conflicts.map((c, i) => (
          <div key={i} className={cn("flex items-start gap-2 rounded-md border p-2", SEVERITY_COLORS[c.severity])}>
            <span className="shrink-0 mt-0.5">{SEVERITY_ICONS[c.severity]}</span>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-medium">{c.label}</div>
              <div className="text-[8px] text-muted-foreground">{c.description}</div>
            </div>
            <span className="text-[8px] font-medium uppercase">{c.severity}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
