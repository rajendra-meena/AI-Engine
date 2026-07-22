"use client"

import { AlertTriangle } from "lucide-react"

interface WarningPanelProps {
  warnings: string[]
}

export function WarningPanel({ warnings }: WarningPanelProps) {
  if (!warnings.length) return null

  return (
    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-1">
      <div className="flex items-center gap-1 text-[9px] font-medium text-amber-500 uppercase tracking-wider">
        <AlertTriangle className="w-3 h-3" /> Warnings
      </div>
      {warnings.map((w, i) => (
        <div key={i} className="text-[9px] text-amber-500/80 flex items-start gap-1">
          <span className="text-[8px] mt-0.5">•</span> {w}
        </div>
      ))}
    </div>
  )
}
